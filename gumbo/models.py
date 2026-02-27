"""Data models for Gumbo projects."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ── Constants ────────────────────────────────────────────────────────

AVAILABLE_LLMS: list[str] = [
    "GPT-4",
    "GPT-4o",
    "Claude-3",
    "Claude-3.5-Sonnet",
    "Grok",
    "Gemini-Pro",
    "Llama-3",
]

AVAILABLE_TOOLS: list[str] = [
    "web_search",
    "code_execution",
    "file_reader",
    "image_generation",
    "data_analysis",
    "summarizer",
]

DEFAULT_INTEGRATOR_PROMPT = (
    "You are a project integrator. Combine the following outputs from different "
    "project tabs into a single, coherent project result. Preserve key details "
    "from every section.\n\n{outputs}"
)


# ── Models ───────────────────────────────────────────────────────────


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SubTask(BaseModel):
    """A single action-item / bullet-point task beneath a tab."""

    id: str = Field(default_factory=_new_id)
    prompt: str = ""
    llm: str = AVAILABLE_LLMS[0]
    tools: list[str] = Field(default_factory=list)
    output: Optional[str] = None


class SequenceTab(BaseModel):
    """One tab in the project sequence (e.g. 'Health', 'Finance')."""

    id: str = Field(default_factory=_new_id)
    title: str = "New Tab"
    main_prompt: str = ""
    llm: str = AVAILABLE_LLMS[0]
    tools: list[str] = Field(default_factory=list)
    subtasks: list[SubTask] = Field(default_factory=list)
    output: Optional[str] = None
    position: int = 0


class Project(BaseModel):
    """Top-level project container."""

    id: str = Field(default_factory=_new_id)
    name: str = "Untitled Project"
    description: str = ""
    tabs: list[SequenceTab] = Field(default_factory=list)
    integrator_llm: str = AVAILABLE_LLMS[0]
    integrator_prompt: str = DEFAULT_INTEGRATOR_PROMPT
    final_result: Optional[str] = None
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    # ── helpers ──────────────────────────────────────────────────

    def add_tab(self, title: str = "New Tab") -> SequenceTab:
        tab = SequenceTab(title=title, position=len(self.tabs))
        self.tabs.append(tab)
        self.touch()
        return tab

    def remove_tab(self, tab_id: str) -> None:
        self.tabs = [t for t in self.tabs if t.id != tab_id]
        for i, t in enumerate(self.tabs):
            t.position = i
        self.touch()

    def touch(self) -> None:
        self.updated_at = _now_iso()
