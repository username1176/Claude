"""Workflow engine — runs tabs/subtasks in sequence and integrates results.

The actual LLM calls go through `execute_task`.  By default this uses a
**stub** that echoes the prompt back (so the app can be demo'd without API
keys).  Swap `_stub_execute` for a real implementation that calls your
preferred LLM provider.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from gumbo.models import Project, SequenceTab, SubTask

logger = logging.getLogger(__name__)

# ── Task execution ───────────────────────────────────────────────────


@dataclass
class TaskResult:
    """Wrapper returned by the executor."""

    text: str
    llm_used: str
    tools_used: list[str] = field(default_factory=list)
    error: Optional[str] = None


ExecutorFn = Callable[[str, str, list[str], Optional[str]], TaskResult]


def _stub_execute(
    prompt: str,
    llm: str,
    tools: list[str],
    context: Optional[str] = None,
) -> TaskResult:
    """Demo executor — returns a simulated response."""
    ctx_note = f"  [with prior context: {context[:80]}...]" if context else ""
    body = (
        f"[Simulated {llm} response]\n"
        f"Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}\n"
        f"Tools: {', '.join(tools) if tools else 'none'}"
        f"{ctx_note}"
    )
    return TaskResult(text=body, llm_used=llm, tools_used=tools)


# ── Workflow runner ──────────────────────────────────────────────────


class WorkflowEngine:
    """Runs an entire project workflow: tabs → subtasks → integration."""

    def __init__(self, executor: ExecutorFn = _stub_execute) -> None:
        self._execute = executor

    # -- single task --------------------------------------------------

    def run_task(
        self,
        prompt: str,
        llm: str,
        tools: list[str],
        context: Optional[str] = None,
    ) -> TaskResult:
        logger.info("Executing task  llm=%s  tools=%s", llm, tools)
        return self._execute(prompt, llm, tools, context)

    # -- full tab (main prompt + subtasks) ----------------------------

    def run_tab(self, tab: SequenceTab) -> str:
        """Run a single tab: main prompt first, then subtasks in order."""
        result = self.run_task(tab.main_prompt, tab.llm, tab.tools)
        tab.output = result.text
        context = result.text

        for sub in tab.subtasks:
            sub_result = self.run_task(sub.prompt, sub.llm, sub.tools, context)
            sub.output = sub_result.text
            context += "\n" + sub_result.text

        return context

    # -- full project run --------------------------------------------

    def run_project(self, project: Project) -> str:
        """Run every tab in sequence, then integrate."""
        all_outputs: list[str] = []

        for tab in sorted(project.tabs, key=lambda t: t.position):
            tab_context = self.run_tab(tab)
            all_outputs.append(f"## {tab.title}\n{tab_context}")

        combined = "\n\n---\n\n".join(all_outputs)
        integration_prompt = project.integrator_prompt.format(outputs=combined)

        final = self.run_task(integration_prompt, project.integrator_llm, [])
        project.final_result = final.text
        project.touch()
        return final.text
