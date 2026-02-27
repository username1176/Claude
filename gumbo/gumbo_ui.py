"""Gumbo UI — full-featured Streamlit front-end for project management.

Run with:
    streamlit run gumbo/gumbo_ui.py

Features:
  - Editable project title in the main area
  - Sidebar: New Project / Load Project (file upload) / Save Project (download)
  - Dynamic sequence tabs with drag-style prompt text areas
  - Dynamic sub-slots (action items) under each tab
  - Per-task LLM selector + tool checkboxes
  - Workflow execution with live progress + integrated result panel
  - Full session-state persistence across reruns
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

# ── Custom CSS for a cleaner look ────────────────────────────────────

st.markdown(
    """
    <style>
    /* tighten spacing inside subtask cards */
    div[data-testid="stExpander"] details summary p {
        font-weight: 600;
    }
    /* pill badge for tab position */
    .tab-badge {
        display: inline-block;
        background: #4A90D9;
        color: white;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.75rem;
        margin-right: 6px;
    }
    /* subtle card wrapper for subtasks */
    .subtask-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        background: #fafafa;
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

        # Also show saved-on-disk projects for quick switching
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
            index=AVAILABLE_LLMS.index(proj.integrator_llm),
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
            engine: WorkflowEngine = st.session_state.engine
            with st.spinner("Running workflow..."):
                engine.run_project(proj)
            save_project(proj)
            st.session_state.run_complete = True
            _flash("Workflow complete!")
            st.rerun()


# ── Subtask card renderer ────────────────────────────────────────────


def _render_subtask(
    sub: SubTask, index: int, tab: SequenceTab
) -> None:
    """Render a single action-item sub-slot."""
    with st.expander(
        f"Action Item {index + 1}"
        + (f" — {sub.prompt[:40]}..." if len(sub.prompt) > 40 else (f" — {sub.prompt}" if sub.prompt else "")),
        expanded=not sub.output,
    ):
        sub.prompt = st.text_area(
            "Sub-task prompt",
            value=sub.prompt,
            key=f"subp_{sub.id}",
            height=80,
            placeholder="Drop your prompt here\u2026",
            label_visibility="collapsed",
        )

        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            sub.llm = st.selectbox(
                "LLM",
                AVAILABLE_LLMS,
                index=AVAILABLE_LLMS.index(sub.llm),
                key=f"subllm_{sub.id}",
            )
        with c2:
            sub.tools = st.multiselect(
                "Tools",
                AVAILABLE_TOOLS,
                default=sub.tools,
                key=f"subtools_{sub.id}",
            )
        with c3:
            st.markdown("")  # vertical spacer
            if st.button(
                "\U0001f5d1 Remove",
                key=f"subrm_{sub.id}",
                use_container_width=True,
            ):
                tab.subtasks = [s for s in tab.subtasks if s.id != sub.id]
                st.rerun()

        if sub.output:
            st.markdown("**Output:**")
            st.code(sub.output, language=None)


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
        tab.llm = st.selectbox(
            "LLM for this tab",
            AVAILABLE_LLMS,
            index=AVAILABLE_LLMS.index(tab.llm),
            key=f"tllm_{tab.id}",
        )
    with ct:
        tab.tools = st.multiselect(
            "Tools for this tab",
            AVAILABLE_TOOLS,
            default=tab.tools,
            key=f"ttools_{tab.id}",
        )

    # ── Main prompt output ───────────────────────────────────────────
    if tab.output:
        with st.expander("Main prompt output", expanded=True):
            st.code(tab.output, language=None)

    # ── Sub-tasks / Action Items ─────────────────────────────────────
    st.markdown("---")
    st.markdown("##### Action Items")

    if not tab.subtasks:
        st.caption("No action items yet. Click below to add one.")

    for si, sub in enumerate(tab.subtasks):
        _render_subtask(sub, si, tab)

    if st.button(
        "\u2795 Add Action Item",
        key=f"addsub_{tab.id}",
        use_container_width=True,
    ):
        tab.subtasks.append(SubTask())
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
        return

    # ── Editable project title ───────────────────────────────────────
    proj.name = st.text_input(
        "Project Title",
        value=proj.name,
        key="main_proj_name",
        label_visibility="collapsed",
        placeholder="Project name...",
    )
    # Show as big header after the input
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

    tab_labels = [f"{t.title}" for t in proj.tabs] + ["\u2795 New Tab"]
    ui_tabs = st.tabs(tab_labels)

    # Render each existing tab
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
        st.markdown(proj.final_result)

        # Offer download of the final result
        st.download_button(
            "\u2b07 Download Result",
            data=proj.final_result.encode("utf-8"),
            file_name=f"{proj.name.replace(' ', '_').lower()}_result.txt",
            mime="text/plain",
        )


# ── Entrypoint ───────────────────────────────────────────────────────

_render_sidebar()
_render_main()
