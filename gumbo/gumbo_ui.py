"""Gumbo UI — full-featured Streamlit front-end for project management.

Run with:
    streamlit run gumbo/gumbo_ui.py

Features:
  - Sidebar API-key configuration (Anthropic / OpenAI / xAI)
  - Real LLM calls + sequential tool pipeline via gumbo_executors
  - Graceful fallback to stub executor when no keys are configured
  - st.progress bars for Run Tab / Run All Tabs operations
  - Dynamic sequence tabs + action items with per-item output display
  - Project save / load / export as JSON
"""

from __future__ import annotations

import json
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
)
from gumbo.storage import delete_project, list_projects, load_project, save_project

# ── Page configuration ───────────────────────────────────────────────

st.set_page_config(page_title="Gumbo", page_icon="\U0001f372", layout="wide")

# ── Custom CSS ───────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    div[data-testid="stExpander"] details summary p {
        font-weight: 600;
    }
    .tab-badge {
        display: inline-block;
        background: #4A90D9;
        color: white;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.75rem;
        margin-right: 6px;
    }
    .run-ok  { color: #28a745; font-weight: 600; }
    .run-err { color: #dc3545; font-weight: 600; }
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
    .tool-step-block {
        background: #e8f4fd;
        border-left: 3px solid #0ea5e9;
        padding: 6px 10px;
        border-radius: 3px;
        margin: 4px 0;
        font-family: monospace;
        font-size: 0.82rem;
        white-space: pre-wrap;
    }
    .key-ok  { color: #28a745; }
    .key-miss { color: #999; }
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
    # API keys (empty string = not configured)
    "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "",
    "XAI_API_KEY": "",
    "GOOGLE_CSE_API_KEY": "",
    "GOOGLE_CSE_CX": "",
    # Executor mode
    "use_real_executor": False,
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


# ── HTML helpers ─────────────────────────────────────────────────────


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_output(output: str | None, key_prefix: str) -> None:
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


# ── Sidebar ──────────────────────────────────────────────────────────


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

        # Status indicators
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

    # ── Execution mode toggle ────────────────────────────────────────
    st.session_state["use_real_executor"] = st.sidebar.toggle(
        "Use real LLM APIs",
        value=st.session_state["use_real_executor"],
        help=(
            "ON = call real LLM APIs (requires keys above).  "
            "OFF = use simulated stub responses for demo/testing."
        ),
        key="sb_exec_toggle",
    )
    if st.session_state["use_real_executor"] and not _has_any_key():
        st.sidebar.warning("Real mode is on but no API keys are set.")

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

    # ── Load Project ─────────────────────────────────────────────────
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
            progress_bar = st.sidebar.progress(0, text="Starting...")

            def _project_progress(step: int, total: int, label: str) -> None:
                frac = min(step / max(total, 1), 1.0)
                progress_bar.progress(frac, text=f"[{step}/{total}] {label}")

            engine.run_project(proj, on_progress=_project_progress)
            progress_bar.progress(1.0, text="Done!")
            save_project(proj)
            st.session_state.run_complete = True
            _flash("Workflow complete \u2014 all tabs executed and integrated!")
            st.rerun()


# ── Subtask renderer ─────────────────────────────────────────────────


def _render_subtask(sub: SubTask, index: int, tab: SequenceTab) -> None:
    label = f"Action Item {index + 1}"
    if sub.prompt:
        preview = sub.prompt[:40] + ("..." if len(sub.prompt) > 40 else "")
        label += f" \u2014 {preview}"
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
            ):
                tab.subtasks = [s for s in tab.subtasks if s.id != sub.id]
                st.rerun()

        if sub.output:
            st.markdown("**Output:**")
            _render_output(sub.output, key_prefix=f"subout_{sub.id}")


# ── Sequence-tab editor ──────────────────────────────────────────────


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

    cl, ct = st.columns([1, 2])
    with cl:
        tab.llm = _llm_selector(
            tab.llm, key_prefix=f"tab_{tab.id}", label="LLM for this tab"
        )
    with ct:
        tab.tools = _tool_selector(
            tab.tools, key_prefix=f"tab_{tab.id}", label="Tools for this tab"
        )

    # Main prompt output
    if tab.output:
        with st.expander("Main prompt output", expanded=True):
            _render_output(tab.output, key_prefix=f"tabout_{tab.id}")

    # ── Action Items ─────────────────────────────────────────────────
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

    # ── Run Tab / Clear ──────────────────────────────────────────────
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
            total_steps = 1 + len(tab.subtasks)
            progress_bar = st.progress(0, text=f"Running \"{tab.title}\"...")
            status_text = st.empty()

            def _tab_progress(step: int, total: int, label: str) -> None:
                frac = min((step + 1) / max(total, 1), 1.0)
                progress_bar.progress(frac, text=f"[{step + 1}/{total}] {label}")
                status_text.caption(f"Executing: {label}")

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
        ):
            tab.output = None
            for sub in tab.subtasks:
                sub.output = None
            st.rerun()


# ── Main area ────────────────────────────────────────────────────────


def _render_main() -> None:
    proj = _project()

    # Flash message
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

        with st.expander("How it works"):
            st.markdown(
                "1. **Add your API keys** in the sidebar under "
                "\U0001f511 API Keys.  Toggle *Use real LLM APIs* on.\n"
                "2. **Create** a project and give it a name.\n"
                "3. **Add sequence tabs** \u2014 each tab represents a major step "
                "in your workflow (e.g. *Research*, *Draft*, *Review*).\n"
                "4. For each tab, write a **main prompt** and optionally add "
                "**action items** (sub-tasks).\n"
                "5. **Pick an LLM** (Claude-3, GPT-4, Grok, or Custom) "
                "and **select tools** for every prompt.  Tools run in "
                "sequence before the LLM call:\n"
                "   - **Web Search** \u2014 Google Custom Search or DuckDuckGo\n"
                "   - **Code Execution** \u2014 runs Python in a subprocess\n"
                "   - **Browse Page** \u2014 fetches & extracts text from URLs\n"
                "   - **Image Viewer** \u2014 acknowledges image references\n"
                "   - **PDF Search** \u2014 PDF extraction (placeholder)\n"
                "6. Click **Run Tab** to execute a single tab, or **Run All "
                "Tabs** in the sidebar.  Progress bars show each step.\n"
                "7. **Save** to disk or **Export** as JSON to share."
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

    # Execution mode indicator
    mode = "Real APIs" if st.session_state.use_real_executor else "Simulated (stub)"
    st.caption(f"Execution mode: **{mode}**")

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

    # ── Tabs ─────────────────────────────────────────────────────────
    if not proj.tabs:
        proj.add_tab("Tab 1")

    tab_labels = [t.title for t in proj.tabs] + ["\u2795 New Tab"]
    ui_tabs = st.tabs(tab_labels)

    for idx in range(len(proj.tabs)):
        with ui_tabs[idx]:
            _render_sequence_tab(proj.tabs[idx], idx, proj)

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

    # ── Integrated result ────────────────────────────────────────────
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
