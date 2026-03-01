"""Gumbo UI — production-ready Streamlit front-end for project management.

Run with:
    streamlit run gumbo/gumbo_ui.py

Features:
  - Sidebar API-key config (Anthropic / OpenAI / xAI / Google CSE)
  - Real LLM calls + sequential tool pipeline via gumbo_executors
  - Graceful fallback to stub executor when no keys configured
  - "Compile Project" button: merge all tab outputs into a polished Markdown doc
  - Undo for tab / action-item removal
  - Tooltips (st.info) and contextual help throughout
  - Built-in "Life Tracker" demo project (5 tabs, 13 action items)
  - st.progress bars for Run Tab / Run All / Compile
  - Production logging
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so "from gumbo.X" imports resolve
# regardless of how Streamlit launches this script.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import json
import logging
from io import BytesIO

import streamlit as st

from gumbo.engine import WorkflowEngine, _stub_execute
from gumbo.gumbo_executors import execute_task as real_execute_task
from gumbo.models import (
    AVAILABLE_LLMS,
    AVAILABLE_TOOLS,
    Project,
    SequenceTab,
    SubTask,
    create_sample_project,
)
from gumbo.graph_view import render_graph
from gumbo.storage import delete_project, list_projects, load_project, save_project

# ── Logging ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gumbo.ui")

# ── Page configuration ───────────────────────────────────────────────

st.set_page_config(page_title="Gumbo", page_icon="\U0001f372", layout="wide")

# ── Custom CSS ───────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    div[data-testid="stExpander"] details summary p { font-weight: 600; }
    .tab-badge {
        display: inline-block; background: #4A90D9; color: white;
        border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; margin-right: 6px;
    }
    .output-block {
        background: #f0f2f6; border-left: 4px solid #4A90D9;
        padding: 10px 14px; border-radius: 4px; margin: 6px 0 12px 0;
        font-family: monospace; font-size: 0.85rem; white-space: pre-wrap;
    }
    .compile-block {
        background: #f8f9fa; border: 1px solid #dee2e6;
        padding: 16px 20px; border-radius: 6px; margin: 10px 0;
    }
    .key-ok   { color: #28a745; }
    .key-miss { color: #999; }
    .undo-bar {
        background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;
        padding: 8px 14px; margin-bottom: 12px;
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
    # API keys
    "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "",
    "XAI_API_KEY": "",
    "GOOGLE_CSE_API_KEY": "",
    "GOOGLE_CSE_CX": "",
    # Executor mode
    "use_real_executor": False,
    # Undo stack: list of (action, payload) tuples
    "undo_stack": [],
    # View mode: "list" (default tab editor) or "graph" (Obsidian-style web)
    "view_mode": "list",
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Accessors ────────────────────────────────────────────────────────


def _project() -> Project | None:
    return st.session_state.project


def _set_project(proj: Project) -> None:
    st.session_state.project = proj
    st.session_state.run_complete = False
    st.session_state.status_msg = None
    logger.info("Active project set: %s (%s)", proj.name, proj.id)


def _flash(msg: str) -> None:
    st.session_state.status_msg = msg


def _engine() -> WorkflowEngine:
    engine: WorkflowEngine = st.session_state.engine
    if st.session_state.use_real_executor:
        engine.swap_executor(real_execute_task)
    else:
        engine.swap_executor(_stub_execute)
    return engine


def _has_any_key() -> bool:
    return any(
        st.session_state.get(k)
        for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY")
    )


# ── Undo system ──────────────────────────────────────────────────────


def _push_undo(action: str, payload: dict) -> None:
    stack: list = st.session_state.undo_stack
    stack.append({"action": action, "payload": payload})
    # Keep last 20 actions
    if len(stack) > 20:
        st.session_state.undo_stack = stack[-20:]


def _pop_undo() -> dict | None:
    stack: list = st.session_state.undo_stack
    if not stack:
        return None
    return stack.pop()


def _apply_undo(entry: dict) -> str:
    """Apply an undo action and return a human-readable description."""
    proj = _project()
    if proj is None:
        return "No project to undo into."

    action = entry["action"]
    p = entry["payload"]

    if action == "remove_tab":
        tab = SequenceTab(**p["tab_data"])
        proj.tabs.insert(p["position"], tab)
        for i, t in enumerate(proj.tabs):
            t.position = i
        proj.touch()
        save_project(proj)
        return f"Restored tab \"{tab.title}\""

    elif action == "remove_subtask":
        tab = next((t for t in proj.tabs if t.id == p["tab_id"]), None)
        if tab is None:
            return "Parent tab no longer exists."
        sub = SubTask(**p["subtask_data"])
        pos = min(p["position"], len(tab.subtasks))
        tab.subtasks.insert(pos, sub)
        save_project(proj)
        return f"Restored action item in \"{tab.title}\""

    return f"Unknown undo action: {action}"


# ── HTML helpers ─────────────────────────────────────────────────────


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_output(output: str | None) -> None:
    if not output:
        return
    st.markdown(
        f'<div class="output-block">{_esc(output)}</div>',
        unsafe_allow_html=True,
    )


# ── LLM selector ────────────────────────────────────────────────────


def _llm_selector(current_llm: str, key_prefix: str, label: str = "LLM") -> str:
    if current_llm in AVAILABLE_LLMS:
        idx = AVAILABLE_LLMS.index(current_llm)
    else:
        idx = AVAILABLE_LLMS.index("Custom")

    chosen = st.selectbox(label, AVAILABLE_LLMS, index=idx, key=f"{key_prefix}_llm")

    if chosen == "Custom":
        default_custom = current_llm if current_llm not in AVAILABLE_LLMS else ""
        custom_val = st.text_input(
            "Custom model name",
            value=default_custom,
            key=f"{key_prefix}_llm_custom",
            placeholder="e.g. mistral-large, llama-3.1-70b...",
        )
        return custom_val if custom_val else "Custom"
    return chosen


# ── Tool selector ────────────────────────────────────────────────────


def _tool_selector(
    current_tools: list[str], key_prefix: str, label: str = "Tools (run in sequence)"
) -> list[str]:
    valid_defaults = [t for t in current_tools if t in AVAILABLE_TOOLS]
    selected = st.multiselect(
        label,
        AVAILABLE_TOOLS,
        default=valid_defaults,
        key=f"{key_prefix}_tools",
        help="Tools execute in sequence: output of one feeds into the next.",
    )
    if "None" in selected and len(selected) > 1:
        return ["None"]
    return selected


# ══════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════


def _render_sidebar() -> None:
    st.sidebar.title("\U0001f372 Gumbo")
    st.sidebar.caption("LLM-orchestrated project workflows")
    st.sidebar.markdown("---")

    # ── API Key Configuration ────────────────────────────────────────
    with st.sidebar.expander("\U0001f511  API Keys", expanded=not _has_any_key()):
        st.session_state["ANTHROPIC_API_KEY"] = st.text_input(
            "Anthropic API Key",
            value=st.session_state["ANTHROPIC_API_KEY"],
            type="password",
            key="sb_key_anthropic",
            placeholder="sk-ant-...",
            help="Required for Claude-3 calls",
        )
        st.session_state["OPENAI_API_KEY"] = st.text_input(
            "OpenAI API Key",
            value=st.session_state["OPENAI_API_KEY"],
            type="password",
            key="sb_key_openai",
            placeholder="sk-...",
            help="Required for GPT-4 calls",
        )
        st.session_state["XAI_API_KEY"] = st.text_input(
            "xAI API Key (Grok)",
            value=st.session_state["XAI_API_KEY"],
            type="password",
            key="sb_key_xai",
            placeholder="xai-...",
            help="Required for Grok calls",
        )

        with st.popover("Optional: Search keys"):
            st.session_state["GOOGLE_CSE_API_KEY"] = st.text_input(
                "Google CSE API Key",
                value=st.session_state["GOOGLE_CSE_API_KEY"],
                type="password",
                key="sb_key_gcse",
                placeholder="AIza...",
                help="For Web Search tool (falls back to DuckDuckGo)",
            )
            st.session_state["GOOGLE_CSE_CX"] = st.text_input(
                "Google CSE CX ID",
                value=st.session_state["GOOGLE_CSE_CX"],
                key="sb_key_gcse_cx",
                placeholder="a1b2c3...",
            )

        def _key_dot(name: str, label: str) -> str:
            cls = "key-ok" if st.session_state.get(name) else "key-miss"
            sym = "\u2705" if st.session_state.get(name) else "\u26aa"
            return f'<span class="{cls}">{sym} {label}</span>'

        st.markdown(
            _key_dot("ANTHROPIC_API_KEY", "Anthropic")
            + "&nbsp;&nbsp;"
            + _key_dot("OPENAI_API_KEY", "OpenAI")
            + "&nbsp;&nbsp;"
            + _key_dot("XAI_API_KEY", "xAI"),
            unsafe_allow_html=True,
        )

    # ── Execution mode ───────────────────────────────────────────────
    st.session_state["use_real_executor"] = st.sidebar.toggle(
        "Use real LLM APIs",
        value=st.session_state["use_real_executor"],
        help=(
            "ON = call real LLM APIs (keys required).  "
            "OFF = simulated stub responses for demo/testing."
        ),
        key="sb_exec_toggle",
    )
    if st.session_state["use_real_executor"] and not _has_any_key():
        st.sidebar.warning("Real mode is on but no API keys are set.")

    st.sidebar.markdown("---")

    # ── New / Demo / Load ────────────────────────────────────────────
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
        c_create, c_demo = st.columns(2)
        with c_create:
            if st.button("Create", use_container_width=True, help="Create a blank project"):
                proj = Project(name=new_name, description=new_desc)
                proj.add_tab("Tab 1")
                save_project(proj)
                _set_project(proj)
                _flash(f"Created project \"{proj.name}\"")
                st.rerun()
        with c_demo:
            if st.button(
                "Demo",
                use_container_width=True,
                help="Load sample 'Life Tracker' with 5 tabs and 13 action items",
            ):
                proj = create_sample_project()
                save_project(proj)
                _set_project(proj)
                _flash(
                    "Loaded demo project \"Life Tracker\" with 5 tabs "
                    "and 13 action items."
                )
                st.rerun()

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

    # ── Save / Export ────────────────────────────────────────────────
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

        # ── Integrator config ────────────────────────────────────────
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
            help="LLM used when 'Run All Tabs' integrates results.",
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
            help="Execute every tab in sequence, then integrate the results.",
        ):
            engine = _engine()
            progress_bar = st.sidebar.progress(0, text="Starting...")

            def _project_progress(step: int, total: int, label: str) -> None:
                frac = min(step / max(total, 1), 1.0)
                progress_bar.progress(frac, text=f"[{step}/{total}] {label}")

            logger.info("Running all tabs for project '%s'", proj.name)
            engine.run_project(proj, on_progress=_project_progress)
            progress_bar.progress(1.0, text="Done!")
            save_project(proj)
            st.session_state.run_complete = True
            _flash("Workflow complete - all tabs executed and integrated!")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  SUBTASK RENDERER
# ══════════════════════════════════════════════════════════════════════


def _render_subtask(sub: SubTask, index: int, tab: SequenceTab) -> None:
    label = f"Action Item {index + 1}"
    if sub.prompt:
        preview = sub.prompt[:40] + ("..." if len(sub.prompt) > 40 else "")
        label += f" - {preview}"
    if sub.output:
        label += "  \u2705"

    with st.expander(label, expanded=not sub.output):
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
            sub.llm = _llm_selector(sub.llm, key_prefix=f"sub_{sub.id}")
        with c2:
            sub.tools = _tool_selector(sub.tools, key_prefix=f"sub_{sub.id}")
        with c3:
            st.markdown("")
            if st.button(
                "\U0001f5d1 Remove",
                key=f"subrm_{sub.id}",
                use_container_width=True,
                help="Remove this action item (can be undone)",
            ):
                # Push undo before removing
                _push_undo("remove_subtask", {
                    "tab_id": tab.id,
                    "position": index,
                    "subtask_data": sub.model_dump(),
                })
                tab.subtasks = [s for s in tab.subtasks if s.id != sub.id]
                logger.info("Removed subtask %s from tab %s", sub.id, tab.title)
                st.rerun()

        if sub.output:
            st.markdown("**Output:**")
            _render_output(sub.output)


# ══════════════════════════════════════════════════════════════════════
#  SEQUENCE TAB EDITOR
# ══════════════════════════════════════════════════════════════════════


def _render_sequence_tab(tab: SequenceTab, tab_idx: int, proj: Project) -> None:
    # ── Header ───────────────────────────────────────────────────────
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
            help="Remove this tab (can be undone)",
        ):
            _push_undo("remove_tab", {
                "position": tab_idx,
                "tab_data": tab.model_dump(),
            })
            proj.remove_tab(tab.id)
            save_project(proj)
            logger.info("Removed tab '%s'", tab.title)
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

    cl, ct = st.columns([1, 2])
    with cl:
        tab.llm = _llm_selector(
            tab.llm, key_prefix=f"tab_{tab.id}", label="LLM for this tab"
        )
    with ct:
        tab.tools = _tool_selector(
            tab.tools, key_prefix=f"tab_{tab.id}", label="Tools for this tab"
        )

    if tab.output:
        with st.expander("Main prompt output", expanded=True):
            _render_output(tab.output)

    # ── Action Items ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### Action Items")

    if not tab.subtasks:
        st.info(
            "No action items yet. Action items are sub-tasks that execute "
            "after the main prompt. Each one receives the accumulated context "
            "from all prior steps.",
            icon="\U0001f4a1",
        )

    for si, sub in enumerate(tab.subtasks):
        _render_subtask(sub, si, tab)

    if st.button(
        "\u2795 Add Action Item",
        key=f"addsub_{tab.id}",
        use_container_width=True,
    ):
        tab.subtasks.append(SubTask())
        st.rerun()

    # ── Run Tab / Clear ──────────────────────────────────────────────
    st.markdown("---")
    run_col, clear_col = st.columns([3, 1])
    with run_col:
        if st.button(
            f"\u25b6  Run \"{tab.title}\"",
            key=f"runtab_{tab.id}",
            type="primary",
            use_container_width=True,
            help="Execute main prompt + all action items in sequence.",
        ):
            engine = _engine()
            progress_bar = st.progress(0, text=f"Running \"{tab.title}\"...")
            status_text = st.empty()

            def _tab_progress(step: int, total: int, label: str) -> None:
                frac = min((step + 1) / max(total, 1), 1.0)
                progress_bar.progress(frac, text=f"[{step + 1}/{total}] {label}")
                status_text.caption(f"Executing: {label}")

            logger.info("Running tab '%s'", tab.title)
            engine.run_tab(tab, on_progress=_tab_progress)
            progress_bar.progress(1.0, text="Done!")
            status_text.empty()
            save_project(proj)
            _flash(f"Tab \"{tab.title}\" execution complete!")
            st.rerun()
    with clear_col:
        if st.button(
            "\u21bb Clear",
            key=f"cleartab_{tab.id}",
            use_container_width=True,
            help="Clear all outputs from this tab.",
        ):
            tab.output = None
            for sub in tab.subtasks:
                sub.output = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  COMPILE PROJECT PANEL
# ══════════════════════════════════════════════════════════════════════


def _render_compile_panel(proj: Project) -> None:
    """Render the 'Compile Project' section below the tabs."""
    tabs_ready = proj.tabs_with_output()

    st.markdown("---")
    st.subheader("\U0001f4d6 Compile Project")

    if not tabs_ready:
        st.info(
            "Run at least one tab first. The Compile step takes existing "
            "tab outputs and produces a polished Markdown document.",
            icon="\u2139\ufe0f",
        )
        return

    st.caption(
        f"{len(tabs_ready)} of {len(proj.tabs)} tabs have output. "
        "Compile will merge them into a final document."
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        proj.compile_llm = _llm_selector(
            proj.compile_llm,
            key_prefix="compile",
            label="Compile with",
        )
    with c2:
        proj.compile_prompt = st.text_area(
            "Compile prompt",
            value=proj.compile_prompt,
            height=100,
            key="compile_prompt",
            help="Use {outputs} as placeholder. The LLM receives all tab outputs here.",
        )

    if st.button(
        "\U0001f4d6  Compile Project",
        type="primary",
        use_container_width=True,
        help="Merge all tab outputs into a polished Markdown document.",
    ):
        engine = _engine()
        progress_bar = st.progress(0, text="Compiling...")

        def _compile_progress(step: int, total: int, label: str) -> None:
            frac = min((step + 1) / max(total, 1), 1.0)
            progress_bar.progress(frac, text=label)

        logger.info("Compiling project '%s'", proj.name)
        engine.compile_project(proj, on_progress=_compile_progress)
        progress_bar.progress(1.0, text="Done!")
        save_project(proj)
        _flash("Project compiled successfully!")
        st.rerun()

    # Display compiled result
    if proj.compiled_result:
        st.markdown("---")
        st.markdown("##### Compiled Document")

        # Render as proper Markdown
        with st.container():
            st.markdown(
                f'<div class="compile-block">{proj.compiled_result}</div>'
                if st.session_state.use_real_executor is False
                else "",
                unsafe_allow_html=True,
            )
            # When using real APIs the output is actual markdown; render natively
            if st.session_state.use_real_executor:
                st.markdown(proj.compiled_result)
            else:
                _render_output(proj.compiled_result)

        # Download as Markdown
        md_bytes = proj.compiled_result.encode("utf-8")
        st.download_button(
            "\u2b07 Download as Markdown",
            data=BytesIO(md_bytes),
            file_name=f"{proj.name.replace(' ', '_').lower()}_compiled.md",
            mime="text/markdown",
            use_container_width=True,
        )


# ══════════════════════════════════════════════════════════════════════
#  MAIN AREA
# ══════════════════════════════════════════════════════════════════════


def _render_main() -> None:
    proj = _project()

    # Flash message
    if st.session_state.status_msg:
        st.success(st.session_state.status_msg)
        st.session_state.status_msg = None

    # Undo bar
    if st.session_state.undo_stack:
        last = st.session_state.undo_stack[-1]
        action_desc = (
            f"Removed tab \"{last['payload'].get('tab_data', {}).get('title', '?')}\""
            if last["action"] == "remove_tab"
            else f"Removed action item from tab"
        )
        if st.button(
            f"\u21a9 Undo: {action_desc}",
            key="undo_btn",
            use_container_width=True,
        ):
            entry = _pop_undo()
            if entry:
                msg = _apply_undo(entry)
                _flash(f"Undo: {msg}")
                st.rerun()

    # ── Landing page ─────────────────────────────────────────────────
    if proj is None:
        st.title("\U0001f372 Gumbo")
        st.markdown(
            "**Design multi-step LLM workflows visually.**  \n"
            "Create a project, add sequence tabs with prompts and action "
            "items, pick an LLM and tools for each step, then run everything "
            "in sequence and integrate the results."
        )

        col_start, col_demo = st.columns(2)
        with col_start:
            st.info(
                "\u2190 Use the sidebar to **create** a new project or "
                "**load** an existing one.",
                icon="\U0001f449",
            )
        with col_demo:
            if st.button(
                "\U0001f680 Load Demo Project",
                use_container_width=True,
                help="Load 'Life Tracker' with 5 tabs and 13 action items",
            ):
                proj = create_sample_project()
                save_project(proj)
                _set_project(proj)
                _flash("Loaded demo: Life Tracker (5 tabs, 13 action items)")
                st.rerun()

        with st.expander("How it works", expanded=True):
            st.markdown(
                "1. **Add your API keys** in the sidebar under "
                "\U0001f511 API Keys.  Toggle *Use real LLM APIs* on.\n"
                "2. **Create** a project (or click **Demo** to load a sample).\n"
                "3. **Add sequence tabs** \u2014 each represents a major step "
                "(e.g. *Research*, *Draft*, *Review*).\n"
                "4. Write a **main prompt** per tab and add **action items** "
                "(sub-tasks that chain context).\n"
                "5. **Pick an LLM** (Claude-3, GPT-4, Grok, Custom) "
                "and **select tools** per prompt:\n"
                "   - **Web Search** \u2014 Google CSE or DuckDuckGo\n"
                "   - **Code Execution** \u2014 sandboxed Python subprocess\n"
                "   - **Browse Page** \u2014 fetches & extracts web page text\n"
                "   - **Image Viewer** \u2014 image reference for LLM context\n"
                "   - **PDF Search** \u2014 PDF extraction (placeholder)\n"
                "6. **Run Tab** executes one tab. **Run All Tabs** runs "
                "everything and integrates.\n"
                "7. **Compile Project** merges all outputs into a polished "
                "Markdown document you can download.\n"
                "8. **Save** / **Export** your project at any time. "
                "**Undo** restores accidentally removed tabs or items."
            )
        return

    # ── Project header ───────────────────────────────────────────────
    proj.name = st.text_input(
        "Project Title",
        value=proj.name,
        key="main_proj_name",
        label_visibility="collapsed",
        placeholder="Project name...",
    )
    st.title(proj.name)

    # Status bar
    mode = "Real APIs" if st.session_state.use_real_executor else "Simulated (stub)"
    n_tabs = len(proj.tabs)
    n_subs = sum(len(t.subtasks) for t in proj.tabs)
    n_done = sum(1 for t in proj.tabs if t.output)
    st.caption(
        f"Execution: **{mode}** &nbsp;|&nbsp; "
        f"Tabs: **{n_done}/{n_tabs}** run &nbsp;|&nbsp; "
        f"Action items: **{n_subs}** total"
    )

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

    # ── View toggle ─────────────────────────────────────────────────
    v_list, v_graph, v_spacer = st.columns([1, 1, 4])
    with v_list:
        if st.button(
            "\U0001f4cb List View",
            use_container_width=True,
            type="primary" if st.session_state.view_mode == "list" else "secondary",
            key="view_list_btn",
        ):
            st.session_state.view_mode = "list"
            st.rerun()
    with v_graph:
        if st.button(
            "\U0001f578\ufe0f Graph View",
            use_container_width=True,
            type="primary" if st.session_state.view_mode == "graph" else "secondary",
            key="view_graph_btn",
        ):
            st.session_state.view_mode = "graph"
            st.rerun()

    # ── Graph view ──────────────────────────────────────────────────
    if st.session_state.view_mode == "graph":
        render_graph(proj)

        # Still show integrated result + compile below the graph
        if st.session_state.run_complete and proj.final_result:
            st.markdown("---")
            st.subheader("\U0001f4cb Integrated Result")
            _render_output(proj.final_result)

        _render_compile_panel(proj)
        return

    # ── Tabs (list view) ─────────────────────────────────────────────
    if not proj.tabs:
        proj.add_tab("Tab 1")

    tab_labels = []
    for t in proj.tabs:
        lbl = t.title
        if t.output:
            lbl += " \u2705"
        tab_labels.append(lbl)
    tab_labels.append("\u2795 New Tab")

    ui_tabs = st.tabs(tab_labels)

    for idx in range(len(proj.tabs)):
        with ui_tabs[idx]:
            _render_sequence_tab(proj.tabs[idx], idx, proj)

    with ui_tabs[-1]:
        st.markdown("### Add a Sequence Tab")
        st.info(
            "Each tab represents a step in your workflow. Tabs execute in "
            "order and their outputs feed into the final integration.",
            icon="\U0001f4a1",
        )
        new_title = st.text_input(
            "Tab title",
            value="New Tab",
            key="new_tab_input",
            placeholder="e.g. Research, Draft, Review...",
        )
        if st.button("Add Sequence Tab", use_container_width=True):
            proj.add_tab(new_title)
            save_project(proj)
            st.rerun()

    # ── Integrated result (from Run All) ─────────────────────────────
    if st.session_state.run_complete and proj.final_result:
        st.markdown("---")
        st.subheader("\U0001f4cb Integrated Result")
        _render_output(proj.final_result)
        st.download_button(
            "\u2b07 Download Integrated Result",
            data=proj.final_result.encode("utf-8"),
            file_name=f"{proj.name.replace(' ', '_').lower()}_integrated.txt",
            mime="text/plain",
        )

    # ── Compile Project panel ────────────────────────────────────────
    _render_compile_panel(proj)


# ── Entrypoint ───────────────────────────────────────────────────────

_render_sidebar()
_render_main()
