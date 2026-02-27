"""Gumbo UI — full-featured Streamlit front-end for project management.

Run with:
    streamlit run gumbo/gumbo_ui.py

Features:
  - Editable project title in the main area
  - Sidebar: New Project / Load Project (file upload) / Save Project (download)
  - Dynamic sequence tabs with drag-style prompt text areas
  - Dynamic sub-slots (action items) under each tab
  - Per-task LLM dropdown (Claude-3, GPT-4, Grok, Custom) + custom model input
  - Per-task multi-select tools (Web Search, Code Execution, Browse Page, etc.)
  - "Run Tab" button per tab — executes the sequential multi-tool pipeline
  - "Run All Tabs" in sidebar — full project execution + integration
  - Output display below each item after running
  - Full session-state persistence across Streamlit reruns
"""

from __future__ import annotations

import json
from io import BytesIO

import streamlit as st

from gumbo.engine import WorkflowEngine
from gumbo.models import (
    AVAILABLE_LLMS,
    AVAILABLE_TOOLS,
    Project,
    SequenceTab,
    SubTask,
)
from gumbo.storage import delete_project, list_projects, load_project, save_project

# ── Page configuration ───────────────────────────────────────────────

st.set_page_config(page_title="Gumbo", page_icon="\U0001f372", layout="wide")

# ── Custom CSS ───────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* expander label weight */
    div[data-testid="stExpander"] details summary p {
        font-weight: 600;
    }
    /* pill badge for sequence position */
    .tab-badge {
        display: inline-block;
        background: #4A90D9;
        color: white;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.75rem;
        margin-right: 6px;
    }
    /* run-status indicator */
    .run-ok  { color: #28a745; font-weight: 600; }
    .run-err { color: #dc3545; font-weight: 600; }
    /* output block styling */
    .output-block {
        background: #f0f2f6;
        border-left: 4px solid #4A90D9;
        padding: 10px 14px;
        border-radius: 4px;
        margin: 6px 0 12px 0;
        font-family: monospace;
        font-size: 0.85rem;
        white-space: pre-wrap;
    }
    .tool-step {
        background: #e8f4fd;
        border-left: 3px solid #0ea5e9;
        padding: 6px 10px;
        border-radius: 3px;
        margin: 4px 0;
        font-family: monospace;
        font-size: 0.82rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state bootstrap ──────────────────────────────────────────

_DEFAULTS: dict = {
    "project": None,
    "engine": WorkflowEngine(),
    "run_complete": False,
    "status_msg": None,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _project() -> Project | None:
    return st.session_state.project


def _set_project(proj: Project) -> None:
    st.session_state.project = proj
    st.session_state.run_complete = False
    st.session_state.status_msg = None


def _flash(msg: str) -> None:
    st.session_state.status_msg = msg


def _engine() -> WorkflowEngine:
    return st.session_state.engine


# ── LLM selector helper (handles "Custom" with text input) ───────────


def _llm_selector(
    current_llm: str,
    key_prefix: str,
    label: str = "LLM",
) -> str:
    """Render an LLM dropdown.  When 'Custom' is chosen, show a text input.

    Returns the resolved LLM string (either a preset name or the custom value).
    """
    # Determine dropdown index
    if current_llm in AVAILABLE_LLMS:
        idx = AVAILABLE_LLMS.index(current_llm)
    else:
        # Previously-entered custom value — show Custom selected
        idx = AVAILABLE_LLMS.index("Custom")

    chosen = st.selectbox(
        label,
        AVAILABLE_LLMS,
        index=idx,
        key=f"{key_prefix}_llm",
    )

    if chosen == "Custom":
        # Preserve a previous custom value as the default
        default_custom = current_llm if current_llm not in AVAILABLE_LLMS else ""
        custom_val = st.text_input(
            "Custom model name",
            value=default_custom,
            key=f"{key_prefix}_llm_custom",
            placeholder="e.g. mistral-large, llama-3.1-70b...",
        )
        return custom_val if custom_val else "Custom"

    return chosen


# ── Tool multi-select helper ─────────────────────────────────────────


def _tool_selector(
    current_tools: list[str],
    key_prefix: str,
    label: str = "Tools (run in sequence)",
) -> list[str]:
    """Render a multi-select for tools.  Filters out 'None' from the result."""
    # Ensure defaults are valid options
    valid_defaults = [t for t in current_tools if t in AVAILABLE_TOOLS]

    selected = st.multiselect(
        label,
        AVAILABLE_TOOLS,
        default=valid_defaults,
        key=f"{key_prefix}_tools",
        help="Tools execute in sequence: output of one feeds into the next.",
    )

    # If user explicitly picks "None" alongside others, only keep "None"
    if "None" in selected and len(selected) > 1:
        return ["None"]
    return selected


# ── Output renderer ──────────────────────────────────────────────────


def _render_output(output: str | None, key_prefix: str) -> None:
    """Display the output block for a completed task."""
    if not output:
        return

    st.markdown(
        f'<div class="output-block">{_escape_html(output)}</div>',
        unsafe_allow_html=True,
    )


def _escape_html(text: str) -> str:
    """Minimal HTML escaping for safe rendering inside markdown blocks."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ── Sidebar ──────────────────────────────────────────────────────────


def _render_sidebar() -> None:
    st.sidebar.title("\U0001f372 Gumbo")
    st.sidebar.caption("LLM-orchestrated project workflows")
    st.sidebar.markdown("---")

    # ── New Project ──────────────────────────────────────────────────
    with st.sidebar.expander(
        "\U00002795  New Project", expanded=_project() is None
    ):
        new_name = st.text_input(
            "Project name",
            value="Life Tracker",
            key="sb_new_name",
            placeholder="e.g. Life Tracker",
        )
        new_desc = st.text_area(
            "Description (optional)",
            value="",
            height=68,
            key="sb_new_desc",
            placeholder="Brief description of this project...",
        )
        if st.button("Create Project", use_container_width=True):
            proj = Project(name=new_name, description=new_desc)
            proj.add_tab("Tab 1")
            save_project(proj)
            _set_project(proj)
            _flash(f"Created project \"{proj.name}\"")
            st.rerun()

    # ── Load Project (file uploader) ─────────────────────────────────
    with st.sidebar.expander("\U0001f4c2  Load Project"):
        uploaded = st.file_uploader(
            "Upload a project JSON file",
            type=["json"],
            key="sb_upload",
        )
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                proj = Project(**data)
                save_project(proj)
                _set_project(proj)
                _flash(f"Loaded \"{proj.name}\" from file")
                st.rerun()
            except (json.JSONDecodeError, Exception) as exc:
                st.error(f"Invalid project file: {exc}")

        saved = list_projects()
        if saved:
            st.markdown("**Saved on disk:**")
            for entry in saved:
                cols = st.columns([4, 1])
                with cols[0]:
                    if st.button(
                        entry["name"],
                        key=f"sb_load_{entry['id']}",
                        use_container_width=True,
                    ):
                        proj = load_project(entry["id"])
                        if proj:
                            _set_project(proj)
                            _flash(f"Opened \"{proj.name}\"")
                            st.rerun()
                with cols[1]:
                    if st.button(
                        "\U0001f5d1",
                        key=f"sb_del_{entry['id']}",
                        help="Delete this project",
                    ):
                        delete_project(entry["id"])
                        if _project() and _project().id == entry["id"]:
                            st.session_state.project = None
                        st.rerun()

    # ── Save / Download ──────────────────────────────────────────────
    proj = _project()
    if proj:
        st.sidebar.markdown("---")

        col_save, col_dl = st.sidebar.columns(2)
        with col_save:
            if st.button(
                "\U0001f4be Save", use_container_width=True, help="Save to disk"
            ):
                save_project(proj)
                _flash("Project saved!")
                st.rerun()
        with col_dl:
            blob = proj.model_dump_json(indent=2).encode("utf-8")
            st.download_button(
                "\u2b07 Export",
                data=BytesIO(blob),
                file_name=f"{proj.name.replace(' ', '_').lower()}.json",
                mime="application/json",
                use_container_width=True,
                help="Download project as JSON",
            )

        # ── Integrator configuration ─────────────────────────────────
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Integrator")
        proj.integrator_llm = st.sidebar.selectbox(
            "Integrator LLM",
            AVAILABLE_LLMS,
            index=AVAILABLE_LLMS.index(
                proj.integrator_llm
                if proj.integrator_llm in AVAILABLE_LLMS
                else AVAILABLE_LLMS[0]
            ),
            key="sb_int_llm",
        )
        proj.integrator_prompt = st.sidebar.text_area(
            "Integrator prompt",
            value=proj.integrator_prompt,
            height=100,
            key="sb_int_prompt",
            help="Use {outputs} as placeholder for combined tab outputs.",
        )

        # ── Run All ──────────────────────────────────────────────────
        st.sidebar.markdown("---")
        if st.sidebar.button(
            "\u25b6  Run All Tabs",
            type="primary",
            use_container_width=True,
        ):
            engine = _engine()
            with st.spinner("Running full workflow..."):
                engine.run_project(proj)
            save_project(proj)
            st.session_state.run_complete = True
            _flash("Workflow complete — all tabs executed and integrated!")
            st.rerun()


# ── Subtask card renderer ────────────────────────────────────────────


def _render_subtask(sub: SubTask, index: int, tab: SequenceTab) -> None:
    """Render a single action-item sub-slot with LLM/tool selectors and output."""

    # Build expander label with prompt preview
    label = f"Action Item {index + 1}"
    if sub.prompt:
        preview = sub.prompt[:40] + ("..." if len(sub.prompt) > 40 else "")
        label += f" \u2014 {preview}"
    if sub.output:
        label += "  \u2705"

    with st.expander(label, expanded=not sub.output):
        # ── Prompt ───────────────────────────────────────────────────
        sub.prompt = st.text_area(
            "Sub-task prompt",
            value=sub.prompt,
            key=f"subp_{sub.id}",
            height=80,
            placeholder="Drop your prompt here\u2026",
            label_visibility="collapsed",
        )

        # ── LLM + Tools + Remove ────────────────────────────────────
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            sub.llm = _llm_selector(sub.llm, key_prefix=f"sub_{sub.id}")
        with c2:
            sub.tools = _tool_selector(sub.tools, key_prefix=f"sub_{sub.id}")
        with c3:
            st.markdown("")  # vertical spacer
            if st.button(
                "\U0001f5d1 Remove",
                key=f"subrm_{sub.id}",
                use_container_width=True,
            ):
                tab.subtasks = [s for s in tab.subtasks if s.id != sub.id]
                st.rerun()

        # ── Output display ───────────────────────────────────────────
        if sub.output:
            st.markdown("**Output:**")
            _render_output(sub.output, key_prefix=f"subout_{sub.id}")


# ── Sequence-tab editor ──────────────────────────────────────────────


def _render_sequence_tab(tab: SequenceTab, tab_idx: int, proj: Project) -> None:
    """Render the full editor for one SequenceTab."""

    # ── Tab header row ───────────────────────────────────────────────
    hdr1, hdr2 = st.columns([5, 1])
    with hdr1:
        tab.title = st.text_input(
            "Tab title",
            value=tab.title,
            key=f"ttl_{tab.id}",
            label_visibility="collapsed",
            placeholder="Tab title...",
        )
    with hdr2:
        if st.button(
            "\U0001f5d1 Remove Tab",
            key=f"rmtab_{tab.id}",
            use_container_width=True,
        ):
            proj.remove_tab(tab.id)
            save_project(proj)
            st.rerun()

    st.markdown(
        f'<span class="tab-badge">Step {tab_idx + 1}</span>'
        f" Sequence position {tab_idx + 1} of {len(proj.tabs)}",
        unsafe_allow_html=True,
    )

    # ── Main prompt ──────────────────────────────────────────────────
    st.markdown("##### Main Prompt")
    tab.main_prompt = st.text_area(
        "Main prompt",
        value=tab.main_prompt,
        height=140,
        key=f"mp_{tab.id}",
        placeholder="Drop your prompt here\u2026",
        label_visibility="collapsed",
    )

    # ── LLM + Tools for main prompt ──────────────────────────────────
    cl, ct = st.columns([1, 2])
    with cl:
        tab.llm = _llm_selector(tab.llm, key_prefix=f"tab_{tab.id}", label="LLM for this tab")
    with ct:
        tab.tools = _tool_selector(tab.tools, key_prefix=f"tab_{tab.id}", label="Tools for this tab")

    # ── Main prompt output ───────────────────────────────────────────
    if tab.output:
        with st.expander("Main prompt output", expanded=True):
            _render_output(tab.output, key_prefix=f"tabout_{tab.id}")

    # ── Sub-tasks / Action Items ─────────────────────────────────────
    st.markdown("---")
    st.markdown("##### Action Items")

    if not tab.subtasks:
        st.caption("No action items yet. Click below to add one.")

    for si, sub in enumerate(tab.subtasks):
        _render_subtask(sub, si, tab)

    # ── Add Action Item button ───────────────────────────────────────
    if st.button(
        "\u2795 Add Action Item",
        key=f"addsub_{tab.id}",
        use_container_width=True,
    ):
        tab.subtasks.append(SubTask())
        st.rerun()

    # ── Run Tab button ───────────────────────────────────────────────
    st.markdown("---")
    run_col, clear_col = st.columns([3, 1])
    with run_col:
        if st.button(
            f"\u25b6  Run \"{tab.title}\"",
            key=f"runtab_{tab.id}",
            type="primary",
            use_container_width=True,
        ):
            engine = _engine()
            with st.spinner(f"Running \"{tab.title}\"..."):
                engine.run_tab(tab)
            save_project(proj)
            _flash(f"Tab \"{tab.title}\" execution complete!")
            st.rerun()
    with clear_col:
        if st.button(
            "\u21bb Clear outputs",
            key=f"cleartab_{tab.id}",
            use_container_width=True,
        ):
            tab.output = None
            for sub in tab.subtasks:
                sub.output = None
            st.rerun()


# ── Main area ────────────────────────────────────────────────────────


def _render_main() -> None:
    proj = _project()

    # ── Flash message ────────────────────────────────────────────────
    if st.session_state.status_msg:
        st.success(st.session_state.status_msg)
        st.session_state.status_msg = None

    # ── Landing page ─────────────────────────────────────────────────
    if proj is None:
        st.title("\U0001f372 Gumbo")
        st.markdown(
            "**Design multi-step LLM workflows visually.**  \n"
            "Create a project, add sequence tabs with prompts and action "
            "items, pick an LLM and tools for each step, then run everything "
            "in sequence and integrate the results."
        )
        st.info(
            "\u2190 Use the sidebar to **create** a new project or **load** "
            "an existing one."
        )

        # Quick-start reference
        with st.expander("How it works"):
            st.markdown(
                "1. **Create** a project and give it a name.\n"
                "2. **Add sequence tabs** \u2014 each tab represents a major step "
                "in your workflow (e.g. *Research*, *Draft*, *Review*).\n"
                "3. For each tab, write a **main prompt** and optionally add "
                "**action items** (sub-tasks).\n"
                "4. **Pick an LLM** (Claude-3, GPT-4, Grok, or a Custom model) "
                "and **select tools** for every prompt. Tools run in sequence: "
                "the output of one feeds into the next.\n"
                "5. Click **Run Tab** to execute a single tab, or **Run All "
                "Tabs** in the sidebar to execute the full workflow and "
                "integrate results.\n"
                "6. **Save** to disk or **Export** as JSON to share."
            )
        return

    # ── Editable project title ───────────────────────────────────────
    proj.name = st.text_input(
        "Project Title",
        value=proj.name,
        key="main_proj_name",
        label_visibility="collapsed",
        placeholder="Project name...",
    )
    st.title(proj.name)

    if proj.description:
        proj.description = st.text_input(
            "Description",
            value=proj.description,
            key="main_proj_desc",
            label_visibility="collapsed",
            placeholder="Project description...",
        )
    else:
        new_desc = st.text_input(
            "Description",
            value="",
            key="main_proj_desc",
            label_visibility="collapsed",
            placeholder="Add a project description (optional)...",
        )
        if new_desc:
            proj.description = new_desc

    st.markdown("---")

    # ── Sequence tabs ────────────────────────────────────────────────
    if not proj.tabs:
        proj.add_tab("Tab 1")

    tab_labels = [t.title for t in proj.tabs] + ["\u2795 New Tab"]
    ui_tabs = st.tabs(tab_labels)

    for idx in range(len(proj.tabs)):
        with ui_tabs[idx]:
            _render_sequence_tab(proj.tabs[idx], idx, proj)

    # "+ New Tab" pseudo-tab
    with ui_tabs[-1]:
        st.markdown("### Add a Sequence Tab")
        new_title = st.text_input(
            "Tab title",
            value="New Tab",
            key="new_tab_input",
            placeholder="e.g. Health, Finance, Goals...",
        )
        if st.button("Add Sequence Tab", use_container_width=True):
            proj.add_tab(new_title)
            save_project(proj)
            st.rerun()

    # ── Integrated result panel ──────────────────────────────────────
    if st.session_state.run_complete and proj.final_result:
        st.markdown("---")
        st.subheader("\U0001f4cb Integrated Project Result")
        _render_output(proj.final_result, key_prefix="final")

        st.download_button(
            "\u2b07 Download Result",
            data=proj.final_result.encode("utf-8"),
            file_name=f"{proj.name.replace(' ', '_').lower()}_result.txt",
            mime="text/plain",
        )


# ── Entrypoint ───────────────────────────────────────────────────────

_render_sidebar()
_render_main()
