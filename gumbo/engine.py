"""Workflow engine — runs tabs/subtasks in sequence and integrates results.

The engine accepts an ``executor`` callable that actually performs each
task (tool pipeline + LLM call).  Two executors ship out of the box:

  - ``_stub_execute`` (default) — echoes prompts back so the app can be
    demo'd without API keys.
  - ``gumbo_executors.execute_task`` — calls real LLM APIs and runs real
    tool functions.

Progress callbacks
------------------
``run_tab`` and ``run_project`` accept an optional ``on_progress``
callback of the form ``(step_index, total_steps, label) -> None``.
The UI uses this to drive ``st.progress`` bars.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from gumbo.models import Project, SequenceTab, SubTask

logger = logging.getLogger(__name__)

# ── Result containers ────────────────────────────────────────────────


@dataclass
class ToolStepResult:
    """Output from a single tool step in the pipeline."""

    tool: str
    text: str


@dataclass
class TaskResult:
    """Wrapper returned by the executor."""

    text: str
    llm_used: str
    tools_used: list[str] = field(default_factory=list)
    tool_steps: list[ToolStepResult] = field(default_factory=list)
    error: Optional[str] = None


# ── Type aliases ─────────────────────────────────────────────────────

ExecutorFn = Callable[[str, str, list[str], Optional[str]], TaskResult]
ProgressFn = Callable[[int, int, str], None]


# ── Default stub executor (no API keys needed) ──────────────────────


def _stub_execute(
    prompt: str,
    llm: str,
    tools: list[str],
    context: Optional[str] = None,
) -> TaskResult:
    """Demo executor — simulates sequential multi-tool pipeline execution."""
    active_tools = [t for t in tools if t != "None"]

    ctx_note = ""
    if context:
        ctx_note = f"\n  [Prior context: {context[:80]}...]"

    tool_steps: list[ToolStepResult] = []
    if active_tools:
        for i, tool in enumerate(active_tools):
            step_text = (
                f"[{tool}]: Processed "
                f"\"{prompt[:60]}{'...' if len(prompt) > 60 else ''}\""
            )
            tool_steps.append(ToolStepResult(tool=tool, text=step_text))

        tool_summary = "\n".join(
            f"  Step {i + 1}/{len(active_tools)}: {s.tool} -> {s.text}"
            for i, s in enumerate(tool_steps)
        )
    else:
        tool_summary = "  (no tools selected)"

    body = (
        f"[Simulated {llm} response]\n"
        f"Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}\n"
        f"Tool pipeline ({len(active_tools)} tool{'s' if len(active_tools) != 1 else ''}):\n"
        f"{tool_summary}"
        f"{ctx_note}"
    )

    return TaskResult(
        text=body,
        llm_used=llm,
        tools_used=active_tools,
        tool_steps=tool_steps,
    )


# ── Workflow runner ──────────────────────────────────────────────────


class WorkflowEngine:
    """Runs an entire project workflow: tabs -> subtasks -> integration."""

    def __init__(self, executor: ExecutorFn = _stub_execute) -> None:
        self._execute = executor

    def swap_executor(self, executor: ExecutorFn) -> None:
        """Hot-swap the executor (e.g. switch between stub and real)."""
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

    def run_tab(
        self,
        tab: SequenceTab,
        on_progress: Optional[ProgressFn] = None,
    ) -> str:
        """Run a single tab: main prompt first, then subtasks in order.

        Each subtask receives the accumulated context from the main prompt
        and all prior subtasks, so later steps can build on earlier results.
        """
        total = 1 + len(tab.subtasks)

        if on_progress:
            on_progress(0, total, f"Main prompt: {tab.title}")

        result = self.run_task(tab.main_prompt, tab.llm, tab.tools)
        tab.output = result.text
        context = result.text

        for i, sub in enumerate(tab.subtasks):
            if on_progress:
                label = sub.prompt[:40] if sub.prompt else f"Action item {i + 1}"
                on_progress(i + 1, total, label)

            sub_result = self.run_task(sub.prompt, sub.llm, sub.tools, context)
            sub.output = sub_result.text
            context += "\n" + sub_result.text

        return context

    # -- full project run --------------------------------------------

    def run_project(
        self,
        project: Project,
        on_progress: Optional[ProgressFn] = None,
    ) -> str:
        """Run every tab in sequence, then integrate."""
        all_outputs: list[str] = []
        tabs = sorted(project.tabs, key=lambda t: t.position)

        # Total steps: every (main + subtasks) across all tabs + 1 integration
        total = sum(1 + len(t.subtasks) for t in tabs) + 1
        step = 0

        for tab in tabs:
            if on_progress:
                on_progress(step, total, f"Tab: {tab.title}")

            result = self.run_task(tab.main_prompt, tab.llm, tab.tools)
            tab.output = result.text
            context = result.text
            step += 1

            for i, sub in enumerate(tab.subtasks):
                if on_progress:
                    label = sub.prompt[:40] if sub.prompt else f"Action item {i + 1}"
                    on_progress(step, total, f"{tab.title} > {label}")

                sub_result = self.run_task(sub.prompt, sub.llm, sub.tools, context)
                sub.output = sub_result.text
                context += "\n" + sub_result.text
                step += 1

            all_outputs.append(f"## {tab.title}\n{context}")

        # Integration step
        if on_progress:
            on_progress(step, total, "Integrating results...")

        combined = "\n\n---\n\n".join(all_outputs)
        integration_prompt = project.integrator_prompt.format(outputs=combined)

        final = self.run_task(integration_prompt, project.integrator_llm, [])
        project.final_result = final.text
        project.touch()
        return final.text
