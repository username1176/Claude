"""Gumbo — Streamlit application entry-point.

Run with:  streamlit run gumbo/app.py
"""

from __future__ import annotations

import streamlit as st

from gumbo.models import (
    AVAILABLE_LLMS,
    AVAILABLE_TOOLS,
    Project,
    SequenceTab,
    SubTask,
)
from gumbo.engine import WorkflowEngine
from gumbo.storage import (
    delete_project,
    list_projects,
    load_project,
    save_project,
)

# ── Page config ──────────────────────────────────────────────────────

st.set_page_config(page_title="Gumbo", page_icon="🍲", layout="wide")

# ── Session-state bootstrap ─────────────────────────────────────────


def _init_state() -> None:
    if "project" not in st.session_state:
        st.session_state.project = None
    if "engine" not in st.session_state:
        st.session_state.engine = WorkflowEngine()
    if "run_complete" not in st.session_state:
        st.session_state.run_complete = False


_init_state()


# ── Helpers ──────────────────────────────────────────────────────────


def _current_project() -> Project | None:
    return st.session_state.project


def _set_project(proj: Project) -> None:
    st.session_state.project = proj
    st.session_state.run_complete = False


# ── Sidebar ──────────────────────────────────────────────────────────


def _render_sidebar() -> None:
    st.sidebar.title("🍲 Gumbo")
    st.sidebar.markdown("---")

    # -- New project --------------------------------------------------
    with st.sidebar.expander("New Project", expanded=_current_project() is None):
        name = st.text_input("Project name", value="Life Tracker")
        desc = st.text_area("Description", value="", height=68)
        if st.button("Create Project"):
            proj = Project(name=name, description=desc)
            proj.add_tab("Tab 1")
            save_project(proj)
            _set_project(proj)
            st.rerun()

    # -- Load existing ------------------------------------------------
    saved = list_projects()
    if saved:
        st.sidebar.markdown("### Saved Projects")
        for entry in saved:
            col_load, col_del = st.sidebar.columns([3, 1])
            with col_load:
                if st.button(entry["name"], key=f"load_{entry['id']}"):
                    proj = load_project(entry["id"])
                    if proj:
                        _set_project(proj)
                        st.rerun()
            with col_del:
                if st.button("🗑", key=f"del_{entry['id']}"):
                    delete_project(entry["id"])
                    if (
                        _current_project()
                        and _current_project().id == entry["id"]
                    ):
                        st.session_state.project = None
                    st.rerun()

    # -- Integrator config -------------------------------------------
    proj = _current_project()
    if proj:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Integrator")
        proj.integrator_llm = st.sidebar.selectbox(
            "Integrator LLM",
            AVAILABLE_LLMS,
            index=AVAILABLE_LLMS.index(proj.integrator_llm),
        )
        proj.integrator_prompt = st.sidebar.text_area(
            "Integrator prompt template",
            value=proj.integrator_prompt,
            height=100,
            help="Use {outputs} as a placeholder for combined tab outputs.",
        )

        # -- Run all ---------------------------------------------------
        st.sidebar.markdown("---")
        if st.sidebar.button("▶ Run All Tabs", type="primary", use_container_width=True):
            engine: WorkflowEngine = st.session_state.engine
            with st.spinner("Running workflow..."):
                engine.run_project(proj)
            save_project(proj)
            st.session_state.run_complete = True
            st.rerun()

        if st.sidebar.button("💾 Save Project", use_container_width=True):
            save_project(proj)
            st.sidebar.success("Saved!")


# ── Tab editor ───────────────────────────────────────────────────────


def _render_tab_editor(tab: SequenceTab, tab_index: int) -> None:
    """Render the editor for a single SequenceTab."""

    # Title
    tab.title = st.text_input(
        "Tab title",
        value=tab.title,
        key=f"title_{tab.id}",
    )

    # Main prompt
    tab.main_prompt = st.text_area(
        "Main prompt",
        value=tab.main_prompt,
        height=120,
        key=f"prompt_{tab.id}",
        placeholder="Enter the main prompt for this tab...",
    )

    # LLM + tools for main prompt
    col_llm, col_tools = st.columns([1, 2])
    with col_llm:
        tab.llm = st.selectbox(
            "LLM",
            AVAILABLE_LLMS,
            index=AVAILABLE_LLMS.index(tab.llm),
            key=f"llm_{tab.id}",
        )
    with col_tools:
        tab.tools = st.multiselect(
            "Tools",
            AVAILABLE_TOOLS,
            default=tab.tools,
            key=f"tools_{tab.id}",
        )

    # Main-prompt output (read-only)
    if tab.output:
        with st.expander("Main prompt output", expanded=True):
            st.text(tab.output)

    # -- Subtasks -----------------------------------------------------
    st.markdown("#### Sub-tasks")

    for si, sub in enumerate(tab.subtasks):
        with st.container():
            st.markdown(f"**Sub-task {si + 1}**")
            sub.prompt = st.text_input(
                "Prompt",
                value=sub.prompt,
                key=f"sub_prompt_{sub.id}",
                label_visibility="collapsed",
                placeholder="Enter sub-task prompt...",
            )
            sc1, sc2, sc3 = st.columns([2, 3, 1])
            with sc1:
                sub.llm = st.selectbox(
                    "LLM",
                    AVAILABLE_LLMS,
                    index=AVAILABLE_LLMS.index(sub.llm),
                    key=f"sub_llm_{sub.id}",
                )
            with sc2:
                sub.tools = st.multiselect(
                    "Tools",
                    AVAILABLE_TOOLS,
                    default=sub.tools,
                    key=f"sub_tools_{sub.id}",
                )
            with sc3:
                if st.button("Remove", key=f"sub_rm_{sub.id}"):
                    tab.subtasks = [
                        s for s in tab.subtasks if s.id != sub.id
                    ]
                    st.rerun()

            if sub.output:
                with st.expander(f"Sub-task {si + 1} output"):
                    st.text(sub.output)

    if st.button("+ Add Sub-task", key=f"add_sub_{tab.id}"):
        tab.subtasks.append(SubTask())
        st.rerun()


# ── Main area ────────────────────────────────────────────────────────


def _render_main() -> None:
    proj = _current_project()

    if proj is None:
        st.title("🍲 Gumbo")
        st.info(
            "Create a new project or load an existing one from the sidebar."
        )
        return

    st.title(f"📋 {proj.name}")
    if proj.description:
        st.caption(proj.description)

    # -- Tab bar + add tab button -------------------------------------
    tab_titles = [t.title for t in proj.tabs]
    if not tab_titles:
        proj.add_tab("Tab 1")
        tab_titles = [proj.tabs[0].title]

    ui_tabs = st.tabs(tab_titles + ["➕ Add Tab"])

    for idx, ui_tab in enumerate(ui_tabs[:-1]):
        with ui_tab:
            _render_tab_editor(proj.tabs[idx], idx)

            if st.button("🗑 Remove this tab", key=f"rm_tab_{proj.tabs[idx].id}"):
                proj.remove_tab(proj.tabs[idx].id)
                save_project(proj)
                st.rerun()

    # "Add Tab" pseudo-tab
    with ui_tabs[-1]:
        new_title = st.text_input("New tab title", value="New Tab", key="new_tab_title")
        if st.button("Create Tab"):
            proj.add_tab(new_title)
            save_project(proj)
            st.rerun()

    # -- Final integrated result panel --------------------------------
    if st.session_state.run_complete and proj.final_result:
        st.markdown("---")
        st.subheader("Integrated Result")
        st.markdown(proj.final_result)


# ── Entrypoint ───────────────────────────────────────────────────────

_render_sidebar()
_render_main()
