"""Workflow engine — runs tabs/subtasks in sequence and integrates results.

The actual LLM calls go through `execute_task`.  By default this uses a
**stub** that echoes the prompt back (so the app can be demo'd without API
keys).  Swap `_stub_execute` for a real implementation that calls your
preferred LLM provider.

Multi-tool support
------------------
When a task specifies multiple tools, each tool is executed **in sequence**
on the task input.  The output of one tool becomes additional context for the
next, producing a pipeline effect:

    prompt → [Web Search] → result₁ → [Code Execution] → result₂ → …

The "None" tool is a pass-through and produces no additional output.
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


# ── Type alias for executor functions ────────────────────────────────

ExecutorFn = Callable[[str, str, list[str], Optional[str]], TaskResult]


# ── Simulated tool runner ────────────────────────────────────────────


def _simulate_tool(tool: str, prompt: str, prior_output: str) -> str:
    """Simulate a single tool execution.  Returns a descriptive string."""
    context_note = f" (building on prior output)" if prior_output else ""
    return f"  [{tool}]{context_note}: Processed \"{prompt[:60]}{'...' if len(prompt) > 60 else ''}\""


# ── Default stub executor ────────────────────────────────────────────


def _stub_execute(
    prompt: str,
    llm: str,
    tools: list[str],
    context: Optional[str] = None,
) -> TaskResult:
    """Demo executor — simulates sequential multi-tool pipeline execution."""

    # Filter out "None" tool — it's a pass-through
    active_tools = [t for t in tools if t != "None"]

    ctx_note = ""
    if context:
        ctx_note = f"\n  [Prior context: {context[:80]}...]"

    # ── Sequential tool pipeline ─────────────────────────────────────
    tool_steps: list[ToolStepResult] = []
    pipeline_output = ""

    if active_tools:
        for i, tool in enumerate(active_tools):
            step_text = _simulate_tool(tool, prompt, pipeline_output)
            tool_steps.append(ToolStepResult(tool=tool, text=step_text))
            pipeline_output += step_text + "\n"

        tool_pipeline_summary = "\n".join(
            f"  Step {i + 1}/{len(active_tools)}: {step.tool} -> {step.text.strip()}"
            for i, step in enumerate(tool_steps)
        )
    else:
        tool_pipeline_summary = "  (no tools selected)"

    body = (
        f"[Simulated {llm} response]\n"
        f"Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}\n"
        f"Tool pipeline ({len(active_tools)} tool{'s' if len(active_tools) != 1 else ''}):\n"
        f"{tool_pipeline_summary}"
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
        """Run a single tab: main prompt first, then subtasks in order.

        Each subtask receives the accumulated context from the main prompt
        and all prior subtasks, so later steps can build on earlier results.
        """
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
