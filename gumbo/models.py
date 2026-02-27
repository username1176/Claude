"""Data models for Gumbo projects."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ── Constants ────────────────────────────────────────────────────────

AVAILABLE_LLMS: list[str] = [
    "Claude-3",
    "GPT-4",
    "Grok",
    "Custom",
]

AVAILABLE_TOOLS: list[str] = [
    "Web Search",
    "Code Execution",
    "Browse Page",
    "Image Viewer",
    "PDF Search",
    "None",
]

DEFAULT_INTEGRATOR_PROMPT = (
    "You are a project integrator. Combine the following outputs from different "
    "project tabs into a single, coherent project result. Preserve key details "
    "from every section.\n\n{outputs}"
)

DEFAULT_COMPILE_PROMPT = (
    "You are a senior editor. Below are outputs from every section of a project. "
    "Produce a polished, well-structured Markdown document that:\n"
    "1. Opens with an executive summary\n"
    "2. Organizes each section under clear headings\n"
    "3. Highlights key findings and action items\n"
    "4. Ends with a consolidated next-steps section\n\n"
    "{outputs}"
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
    compile_llm: str = AVAILABLE_LLMS[0]
    compile_prompt: str = DEFAULT_COMPILE_PROMPT
    final_result: Optional[str] = None
    compiled_result: Optional[str] = None
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

    def tabs_with_output(self) -> list[SequenceTab]:
        """Return tabs that have at least one output."""
        return [t for t in self.tabs if t.output]


# ── Sample project factory ──────────────────────────────────────────


def create_sample_project() -> Project:
    """Build a fully-populated 'Life Tracker' demo project.

    5 tabs, each with 2-3 action items and realistic prompts.
    """
    proj = Project(
        name="Life Tracker",
        description=(
            "A comprehensive personal life-management project that tracks "
            "health, finances, career growth, relationships, and personal goals."
        ),
    )

    # ── 1. Health & Fitness ──────────────────────────────────────────
    t1 = proj.add_tab("Health & Fitness")
    t1.main_prompt = (
        "Analyze my current health and fitness routine. Summarize weekly "
        "exercise patterns, nutrition balance, and sleep quality. Identify "
        "areas for improvement and suggest an optimized weekly plan."
    )
    t1.llm = "Claude-3"
    t1.tools = ["Web Search"]
    t1.subtasks = [
        SubTask(
            prompt=(
                "Create a balanced weekly meal plan (breakfast, lunch, dinner, "
                "snacks) targeting 2000 calories/day with macro ratios of "
                "40% carbs, 30% protein, 30% fat."
            ),
            llm="Claude-3",
            tools=["Web Search"],
        ),
        SubTask(
            prompt=(
                "Design a 5-day exercise schedule alternating strength training "
                "and cardio, with rest days. Include specific exercises, sets, "
                "reps, and estimated calorie burn."
            ),
            llm="GPT-4",
            tools=[],
        ),
        SubTask(
            prompt=(
                "Build a health metrics dashboard specification: track weight, "
                "BMI, resting heart rate, sleep hours, and water intake. "
                "Suggest visualization formats for each metric."
            ),
            llm="Claude-3",
            tools=["Code Execution"],
        ),
    ]

    # ── 2. Finance ───────────────────────────────────────────────────
    t2 = proj.add_tab("Finance")
    t2.main_prompt = (
        "Review a typical monthly budget for a mid-career professional. "
        "Categorize expenses (housing, food, transport, entertainment, savings), "
        "identify optimization opportunities, and recommend a savings strategy "
        "targeting 20% of net income."
    )
    t2.llm = "GPT-4"
    t2.tools = []
    t2.subtasks = [
        SubTask(
            prompt=(
                "Break down a $5,000/month budget into detailed categories. "
                "Include percentages, dollar amounts, and flag any categories "
                "exceeding recommended thresholds."
            ),
            llm="GPT-4",
            tools=["Code Execution"],
        ),
        SubTask(
            prompt=(
                "Design a 12-month savings goal tracker. Start with $1,000 "
                "emergency fund, then build toward a $10,000 annual savings "
                "target. Include monthly milestones and catch-up strategies."
            ),
            llm="Claude-3",
            tools=[],
        ),
    ]

    # ── 3. Career & Learning ────────────────────────────────────────
    t3 = proj.add_tab("Career & Learning")
    t3.main_prompt = (
        "Assess professional development priorities for a software engineer "
        "with 5 years experience looking to move into a senior/lead role. "
        "Identify skill gaps, recommend learning resources, and outline a "
        "6-month growth plan."
    )
    t3.llm = "Claude-3"
    t3.tools = ["Web Search"]
    t3.subtasks = [
        SubTask(
            prompt=(
                "Evaluate current skills in Python, system design, and "
                "leadership. Rate each 1-10 and identify the top 3 areas "
                "needing improvement with specific resources for each."
            ),
            llm="Claude-3",
            tools=[],
        ),
        SubTask(
            prompt=(
                "Create weekly learning goals for the next month: one "
                "technical deep-dive, one soft-skill exercise, and one "
                "networking activity per week."
            ),
            llm="GPT-4",
            tools=[],
        ),
        SubTask(
            prompt=(
                "Draft a portfolio review checklist: list the projects to "
                "showcase, key metrics to highlight, and presentation format "
                "for job interviews and promotion discussions."
            ),
            llm="Claude-3",
            tools=[],
        ),
    ]

    # ── 4. Relationships & Social ───────────────────────────────────
    t4 = proj.add_tab("Relationships & Social")
    t4.main_prompt = (
        "Help organize my social and relationship goals. I want to maintain "
        "close friendships, strengthen family bonds, and expand my professional "
        "network. Suggest a structured approach to each area."
    )
    t4.llm = "GPT-4"
    t4.tools = []
    t4.subtasks = [
        SubTask(
            prompt=(
                "Design a communication tracker: categorize contacts into "
                "close friends, family, colleagues, and acquaintances. "
                "Suggest optimal contact frequency for each tier."
            ),
            llm="GPT-4",
            tools=[],
        ),
        SubTask(
            prompt=(
                "Plan one social event and one family activity per month "
                "for the next quarter. Include budget estimates, logistics, "
                "and backup options."
            ),
            llm="Claude-3",
            tools=["Web Search"],
        ),
    ]

    # ── 5. Mindfulness & Goals ──────────────────────────────────────
    t5 = proj.add_tab("Mindfulness & Goals")
    t5.main_prompt = (
        "Create a holistic personal development framework combining "
        "mindfulness practices, habit tracking, and quarterly goal reviews. "
        "The framework should be actionable and sustainable."
    )
    t5.llm = "Claude-3"
    t5.tools = []
    t5.subtasks = [
        SubTask(
            prompt=(
                "Design a daily habit checklist covering: morning routine, "
                "meditation (10 min), journaling, exercise, reading (30 min), "
                "and evening reflection. Include time blocks."
            ),
            llm="Claude-3",
            tools=[],
        ),
        SubTask(
            prompt=(
                "Write a monthly goal review template with sections for: "
                "goals achieved, goals missed (root cause), lessons learned, "
                "and adjusted goals for the next month."
            ),
            llm="GPT-4",
            tools=[],
        ),
        SubTask(
            prompt=(
                "Suggest 5 mindfulness exercises suitable for a busy "
                "professional: box breathing, body scan, gratitude log, "
                "mindful walking, and digital detox schedule."
            ),
            llm="Claude-3",
            tools=["Web Search"],
        ),
    ]

    return proj
