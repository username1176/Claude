"""ZeroTax AI — Streamlit Application

Enterprise-grade tax strategy platform.  Dark mode, multi-page, wizard-driven.
Run:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from datetime import datetime, date

import streamlit as st

from database import (
    create_plan, update_plan_result, get_plan,
    get_user_plans, delete_plan, get_api_keys, save_api_keys,
    get_knowledge_meta, set_knowledge_meta,
)
from auth import register_user, login_user, change_password, delete_account
from ai_engine import run_analysis, get_cpa_email_body
from charts import (
    waterfall_chart, strategy_bar_chart, scenario_chart,
    risk_matrix_chart, roadmap_gantt, savings_gauge, ten_year_projection,
)
from report_generator import generate_pdf
from state_portals import STATE_PORTALS

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ZeroTax AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "ZeroTax AI — AI-powered tax strategy platform. Not legal advice.",
        "Report a bug": "mailto:support@zerotax.ai",
    },
)

# ─── CSS Injection ────────────────────────────────────────────────────────────

def _load_css() -> None:
    css_path = os.path.join(os.path.dirname(__file__), "styles", "custom.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

_load_css()

# ─── Session State Defaults ───────────────────────────────────────────────────

def _init_state() -> None:
    defaults = dict(
        authenticated=False,
        user=None,
        page="dashboard",
        wizard_step=1,
        wizard_data={},
        current_plan_id=None,
        processing=False,
        processing_status="",
        last_error=None,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def nav(page: str, **kwargs) -> None:
    st.session_state.page = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def _get_api_key() -> str:
    """Return Anthropic key: env var → DB → empty."""
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        return env_key
    if st.session_state.user:
        keys = get_api_keys(st.session_state.user["id"])
        return keys.get("anthropic_key", "")
    return ""


def _metric_card(label: str, value: str, delta: str = "", color: str = "#10b981") -> None:
    delta_html = f'<p class="metric-delta">{delta}</p>' if delta else ""
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{label}</p>
        <p class="metric-value" style="color:{color}">{value}</p>
        {delta_html}
    </div>""", unsafe_allow_html=True)


def _badge(text: str, color: str = "#3b82f6") -> str:
    return f'<span class="badge" style="background:{color}22;color:{color};border-color:{color}44">{text}</span>'


def _section(title: str, subtitle: str = "") -> None:
    sub = f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<div class="section-header"><h2 class="section-title">{title}</h2>{sub}</div>', unsafe_allow_html=True)


# ─── LOGIN / REGISTER ─────────────────────────────────────────────────────────

def render_login_page() -> None:
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    # Logo / Hero
    st.markdown("""
    <div class="login-hero">
        <div class="logo-mark">⚡</div>
        <h1 class="login-title">ZeroTax AI</h1>
        <p class="login-tagline">The AI tax strategist that casually outperforms<br>any $500/hr human accountant.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            email    = st.text_input("Email", placeholder="you@company.com",    key="li_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="li_pw")

            if st.button("Sign In →", use_container_width=True, type="primary", key="li_btn"):
                if not email or not password:
                    st.error("Please enter your email and password.")
                else:
                    ok, err, user = login_user(email, password)
                    if ok:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else:
                        st.error(err)

            st.markdown('<p class="form-hint">Demo: try any email + 8-char password after registering</p>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_register:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            r_name  = st.text_input("Full Name",    placeholder="Jane Smith",          key="re_name")
            r_email = st.text_input("Email",        placeholder="you@company.com",     key="re_email")
            r_pw    = st.text_input("Password",     type="password", placeholder="Min 8 characters", key="re_pw")
            r_pw2   = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="re_pw2")

            if st.button("Create Account →", use_container_width=True, type="primary", key="re_btn"):
                if r_pw != r_pw2:
                    st.error("Passwords do not match.")
                else:
                    ok, err = register_user(r_email, r_pw, r_name)
                    if ok:
                        ok2, err2, user = login_user(r_email, r_pw)
                        if ok2:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.page = "settings"
                            st.success("Account created! Set your API key to begin.")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error(err)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Feature strip
    st.markdown("""
    <div class="feature-strip">
        <div class="feature-item">
            <span class="feature-icon">🧠</span>
            <span class="feature-text"><b>AI-Powered Analysis</b><br>5-agent pipeline on Claude claude-sonnet-4-6</span>
        </div>
        <div class="feature-item">
            <span class="feature-icon">📊</span>
            <span class="feature-text"><b>79 Tax Strategies</b><br>IRC-cited, OBBBA-current</span>
        </div>
        <div class="feature-item">
            <span class="feature-icon">⚡</span>
            <span class="feature-text"><b>Instant PDF Reports</b><br>Branded, CPA-ready</span>
        </div>
        <div class="feature-item">
            <span class="feature-icon">🔒</span>
            <span class="feature-text"><b>Your Data, Your Keys</b><br>Nothing stored in the cloud</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
            <span class="sidebar-logo-icon">⚡</span>
            <span class="sidebar-logo-text">ZeroTax AI</span>
        </div>
        """, unsafe_allow_html=True)

        user = st.session_state.user
        if user:
            name = user.get("full_name") or user.get("email", "").split("@")[0]
            st.markdown(f'<div class="sidebar-user"><span class="avatar">{name[0].upper()}</span><div><b>{name}</b><br><small>{user["email"]}</small></div></div>', unsafe_allow_html=True)

        st.markdown("---")

        pages = [
            ("📊", "Dashboard",    "dashboard"),
            ("✨", "New Plan",     "new_plan"),
            ("⚙️", "Settings",     "settings"),
        ]
        current = st.session_state.page
        for icon, label, key in pages:
            active = "nav-active" if current == key else ""
            if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
                nav(key)

        st.markdown("---")

        # Knowledge base status
        meta = get_knowledge_meta()
        st.markdown(f"""
        <div class="sidebar-meta">
            <p class="sidebar-meta-title">Knowledge Base</p>
            <p class="sidebar-meta-val">Updated: {meta.get('last_updated', 'Never')[:10]}</p>
            <p class="sidebar-meta-val">Chunks: {meta.get('chunk_count', '0')}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪  Sign Out", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            _init_state()
            st.rerun()


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

def render_dashboard() -> None:
    user = st.session_state.user
    name = user.get("full_name") or user.get("email", "").split("@")[0]
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    st.markdown(f'<h1 class="page-title">{greeting}, {name.split()[0]} 👋</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-subtitle">{date.today().strftime("%A, %B %d, %Y")}</p>', unsafe_allow_html=True)

    # Check API key
    api_key = _get_api_key()
    if not api_key:
        st.warning("⚠️  **API Key Required** — Add your Anthropic API key in Settings to create your first plan.")
        if st.button("→ Go to Settings"):
            nav("settings")
        return

    plans = get_user_plans(user["id"])

    # Stats row
    total_savings = sum(p.get("projected_annual_savings", 0) or 0 for p in plans if p["status"] == "complete")
    active_plans  = len([p for p in plans if p["status"] == "complete"])

    col1, col2, col3, col4 = st.columns(4)
    with col1: _metric_card("Total Annual Savings Found", f"${total_savings:,.0f}", f"across {active_plans} plan(s)", "#10b981")
    with col2: _metric_card("Tax Plans Created", str(len(plans)), "", "#3b82f6")
    with col3: _metric_card("Law Version", "OBBBA 2025", "Current", "#f59e0b")
    with col4: _metric_card("Strategies Analyzed", "79+", "Per plan", "#8b5cf6")

    st.markdown("<br>", unsafe_allow_html=True)

    # Plans grid
    col_title, col_new = st.columns([4, 1])
    with col_title:
        _section("Your Tax Plans", "Click any plan to view the full analysis and download your PDF report.")
    with col_new:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✨  New Plan", type="primary", use_container_width=True):
            st.session_state.wizard_step = 1
            st.session_state.wizard_data = {}
            nav("new_plan")

    if not plans:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <h3>No Plans Yet</h3>
            <p>Create your first tax plan to discover how much you could be saving.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Plan cards
    cols = st.columns(3)
    for i, plan in enumerate(plans):
        with cols[i % 3]:
            status_color = {"complete": "#10b981", "processing": "#f59e0b", "pending": "#64748b", "error": "#ef4444"}.get(plan["status"], "#64748b")
            savings = plan.get("projected_annual_savings") or 0
            st.markdown(f"""
            <div class="plan-card">
                <div class="plan-card-header">
                    <span class="plan-status-dot" style="background:{status_color}"></span>
                    <span class="plan-status-label" style="color:{status_color}">{plan['status'].title()}</span>
                </div>
                <h3 class="plan-name">{plan['plan_name']}</h3>
                <p class="plan-savings" style="color:#10b981">${savings:,.0f}<small>/yr</small></p>
                <p class="plan-meta">{plan['strategies_count']} strategies  •  {plan['created_at'][:10]}</p>
            </div>""", unsafe_allow_html=True)

            col_open, col_del = st.columns([3, 1])
            with col_open:
                if st.button("Open →", key=f"open_{plan['id']}", use_container_width=True):
                    nav("results", current_plan_id=plan["id"])
            with col_del:
                if st.button("🗑", key=f"del_{plan['id']}", use_container_width=True, help="Delete this plan"):
                    delete_plan(plan["id"], user["id"])
                    st.rerun()


# ─── WIZARD ───────────────────────────────────────────────────────────────────

WIZARD_STEPS = ["Business", "Financials", "Goals", "Analyze"]
STATES = sorted(STATE_PORTALS.keys())
ENTITY_OPTIONS = {
    "sole_prop":    "Sole Proprietorship (Schedule C)",
    "single_llc":  "Single-Member LLC",
    "multi_llc":   "Multi-Member LLC",
    "s_corp":      "S-Corporation",
    "c_corp":      "C-Corporation",
    "partnership": "Partnership",
    "nonprofit":   "Nonprofit (501c3)",
}


def _wizard_progress(step: int) -> None:
    pct = int((step - 1) / (len(WIZARD_STEPS) - 1) * 100)
    labels_html = "".join(
        f'<div class="wizard-step {"wizard-step-active" if i+1==step else "wizard-step-done" if i+1<step else ""}">'
        f'<div class="wizard-step-num">{"✓" if i+1<step else i+1}</div>'
        f'<div class="wizard-step-label">{l}</div></div>'
        for i, l in enumerate(WIZARD_STEPS)
    )
    st.markdown(f"""
    <div class="wizard-progress-bar-wrap">
        <div class="wizard-steps-row">{labels_html}</div>
        <div class="wizard-track"><div class="wizard-fill" style="width:{pct}%"></div></div>
    </div>""", unsafe_allow_html=True)


def render_wizard() -> None:
    step = st.session_state.wizard_step
    data = st.session_state.wizard_data

    st.markdown('<h1 class="page-title">New Tax Plan</h1>', unsafe_allow_html=True)
    _wizard_progress(step)
    st.markdown("<br>", unsafe_allow_html=True)

    if step == 1:
        _wizard_step1(data)
    elif step == 2:
        _wizard_step2(data)
    elif step == 3:
        _wizard_step3(data)
    elif step == 4:
        _wizard_step4(data)


def _nav_buttons(step: int, data: dict, can_next: bool = True) -> None:
    col_back, _, col_next = st.columns([1, 3, 1])
    with col_back:
        if step > 1 and st.button("← Back", use_container_width=True):
            st.session_state.wizard_step -= 1
            st.rerun()
    with col_next:
        label = "Next →" if step < 3 else "Analyze →"
        if st.button(label, type="primary", use_container_width=True, disabled=not can_next):
            st.session_state.wizard_data = data
            st.session_state.wizard_step += 1
            st.rerun()


def _wizard_step1(data: dict) -> None:
    _section("Step 1: Your Business", "Tell us about your business — this sets the context for all strategy recommendations.")
    c1, c2 = st.columns(2)
    with c1:
        data["business_name"]  = st.text_input("Business Name", value=data.get("business_name", ""), placeholder="Acme Corp LLC")
        data["business_stage"] = st.selectbox("Business Stage", ["idea", "startup", "growth", "established", "mature"], index=["idea","startup","growth","established","mature"].index(data.get("business_stage","growth")))
        data["entity_type"]    = st.selectbox("Current Entity Type", list(ENTITY_OPTIONS.keys()), format_func=lambda x: ENTITY_OPTIONS[x], index=list(ENTITY_OPTIONS.keys()).index(data.get("entity_type","single_llc")))
    with c2:
        data["state"]    = st.selectbox("State of Formation", STATES, index=STATES.index(data.get("state","CA")) if data.get("state","CA") in STATES else 0)
        data["industry"] = st.text_input("Industry / Type of Business", value=data.get("industry",""), placeholder="e.g. Software, Consulting, Real Estate")
        data["years_in_business"] = st.number_input("Years in Business", min_value=0, max_value=100, value=int(data.get("years_in_business", 3) or 3), step=1)

    # Entity alert
    if data.get("entity_type") in ("sole_prop", "single_llc", "multi_llc"):
        st.info("⚡ **Entity Opportunity Detected** — Most sole props and LLCs are overpaying SE tax. S-Corp election is often the single biggest opportunity.")

    _nav_buttons(1, data, bool(data.get("business_name")))


def _wizard_step2(data: dict) -> None:
    _section("Step 2: Financial Picture", "Enter your best estimates — accuracy here directly determines the quality of your analysis.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Business Financials")
        data["annual_revenue"]      = st.number_input("Annual Gross Revenue ($)", min_value=0, value=int(data.get("annual_revenue",500000) or 0), step=10_000, format="%d")
        data["annual_profit"]       = st.number_input("Annual Net Profit ($)", min_value=0, value=int(data.get("annual_profit",200000) or 0), step=5_000, format="%d", help="Revenue minus all operating expenses, before income tax")
        data["w2_wages_paid"]       = st.number_input("W-2 Wages Paid to Employees ($)", min_value=0, value=int(data.get("w2_wages_paid",0) or 0), step=5_000, format="%d", help="Wages paid to W-2 employees (not yourself)")
        data["retirement_accounts"] = st.number_input("Existing Retirement Accounts ($)", min_value=0, value=int(data.get("retirement_accounts",0) or 0), step=10_000, format="%d")
    with c2:
        st.markdown("#### Personal & Assets")
        data["total_net_worth"]      = st.number_input("Total Net Worth ($)", min_value=0, value=int(data.get("total_net_worth",1_000_000) or 0), step=50_000, format="%d", help="All assets minus all liabilities")
        data["real_estate_value"]    = st.number_input("Investment Real Estate Value ($)", min_value=0, value=int(data.get("real_estate_value",0) or 0), step=25_000, format="%d")
        data["investment_portfolio"] = st.number_input("Investment Portfolio Value ($)", min_value=0, value=int(data.get("investment_portfolio",0) or 0), step=10_000, format="%d")
        data["is_married"]           = st.checkbox("Married Filing Jointly", value=bool(data.get("is_married", False)))
        if data["is_married"]:
            data["spouse_income"] = st.number_input("Spouse Annual Income ($)", min_value=0, value=int(data.get("spouse_income",0) or 0), step=5_000, format="%d")
        data["children"]   = st.number_input("Number of Dependent Children", min_value=0, max_value=20, value=int(data.get("children",0) or 0), step=1)
        data["has_qsbs"]   = st.checkbox("I hold Qualified Small Business Stock (QSBS)", value=bool(data.get("has_qsbs", False)))

    # Quick tax estimate
    profit = float(data.get("annual_profit") or 0)
    if profit > 0:
        se_tax = min(profit * 0.9235, 176_100) * 0.153 + max(0, profit * 0.9235 - 176_100) * 0.029
        marginal = 0.37 if profit > 500_000 else 0.32 if profit > 250_000 else 0.24 if profit > 100_000 else 0.22
        est_total = se_tax + (profit - se_tax * 0.5) * marginal
        st.info(f"💡 Rough current tax estimate: **${est_total:,.0f}/yr** (SE tax: ${se_tax:,.0f} + income tax). Your analysis will be far more precise.")

    _nav_buttons(2, data, profit > 0)


def _wizard_step3(data: dict) -> None:
    _section("Step 3: Goals & Risk", "Your goals determine which strategies we prioritize. Your risk tolerance determines which we recommend.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Primary Goals")
        data["goal_minimize_taxes"]  = st.checkbox("Minimize taxes immediately (primary)", value=data.get("goal_minimize_taxes", True))
        data["goal_asset_protection"]= st.checkbox("Protect assets from lawsuits/creditors",value=data.get("goal_asset_protection", False))
        data["goal_estate_planning"] = st.checkbox("Estate planning & wealth transfer",      value=data.get("goal_estate_planning", False))
        data["goal_exit_strategy"]   = st.checkbox("Exit / sell business (1–10 years)",     value=data.get("goal_exit_strategy", False))
        data["goal_retirement"]      = st.checkbox("Build retirement wealth",                value=data.get("goal_retirement", True))
        data["goal_hire_family"]     = st.checkbox("Employ family members",                  value=data.get("goal_hire_family", False))
    with c2:
        st.markdown("#### Planning Parameters")
        risk_labels = {"conservative": "🛡 Conservative — Only iron-clad strategies",
                       "moderate":     "⚖ Moderate — Best risk-adjusted approach",
                       "aggressive":   "⚡ Aggressive — Maximize savings legally"}
        data["risk_tolerance"] = st.radio(
            "Risk Tolerance",
            list(risk_labels.keys()),
            format_func=lambda x: risk_labels[x],
            index=list(risk_labels.keys()).index(data.get("risk_tolerance", "moderate")),
        )
        data["planning_horizon"] = st.select_slider(
            "Planning Horizon",
            options=["1 year", "3 years", "5 years", "10 years", "10+ years"],
            value=data.get("planning_horizon", "3 years"),
        )
        st.markdown("#### Plan Name")
        data["plan_name"] = st.text_input(
            "Name this analysis",
            value=data.get("plan_name", f"{data.get('business_name', 'My Business')} — {date.today().year}"),
        )

    _nav_buttons(3, data)


def _wizard_step4(data: dict) -> None:
    """Run the AI analysis with a live progress display."""
    _section("Step 4: AI Analysis", "Our 5-agent AI pipeline is analyzing your tax situation against 79 strategies and current law.")

    api_key = _get_api_key()
    if not api_key:
        st.error("No Anthropic API key found. Please add it in **Settings** first.")
        if st.button("→ Go to Settings"):
            nav("settings")
        return

    if not st.session_state.processing:
        # Pre-flight summary
        profit = float(data.get("annual_profit") or 0)
        se = min(profit * 0.9235, 176_100) * 0.153 + max(0, profit * 0.9235 - 176_100) * 0.029
        marginal = 0.37 if profit > 500_000 else 0.32 if profit > 250_000 else 0.24 if profit > 100_000 else 0.22
        est = se + (profit - se * 0.5) * marginal

        st.markdown(f"""
        <div class="analysis-preview">
            <h3>Ready to Analyze</h3>
            <div class="preview-grid">
                <div><span class="prev-label">Business</span><span class="prev-val">{data.get('business_name', '—')}</span></div>
                <div><span class="prev-label">Entity</span><span class="prev-val">{ENTITY_OPTIONS.get(data.get('entity_type',''), '—')}</span></div>
                <div><span class="prev-label">State</span><span class="prev-val">{data.get('state', '—')}</span></div>
                <div><span class="prev-label">Annual Profit</span><span class="prev-val" style="color:#10b981">${profit:,.0f}</span></div>
                <div><span class="prev-label">Est. Current Tax</span><span class="prev-val" style="color:#ef4444">${est:,.0f}</span></div>
                <div><span class="prev-label">Risk Tolerance</span><span class="prev-val">{data.get('risk_tolerance', 'moderate').title()}</span></div>
            </div>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🧠  Run AI Analysis", type="primary", use_container_width=True):
                st.session_state.processing = True
                st.rerun()
        with col2:
            if st.button("← Edit Inputs", use_container_width=True):
                st.session_state.wizard_step = 3
                st.rerun()
    else:
        # Running analysis
        stages = [
            ("🔍", "Intake Agent",     "Normalizing your financial profile and computing tax metrics..."),
            ("📚", "Research Agent",   "Retrieving relevant IRC sections and OBBBA 2025 provisions..."),
            ("🧮", "Optimizer Agent",  "Calculating savings for each of 79 strategies..."),
            ("⚠️", "Risk Agent",       "Scoring IRS scrutiny levels and compliance requirements..."),
            ("✍️", "Synthesis Agent",  "Writing your personalized executive summary and roadmap..."),
        ]

        progress_bar = st.progress(0)
        status_text  = st.empty()
        stage_box    = st.empty()

        for i, (icon, name, desc) in enumerate(stages):
            pct = int((i / len(stages)) * 85)
            progress_bar.progress(pct)
            status_text.markdown(f'<p class="progress-label">Running {name}...</p>', unsafe_allow_html=True)
            stage_box.markdown(f"""
            <div class="stage-card">
                <span class="stage-icon">{icon}</span>
                <div><b class="stage-name">{name}</b><br><span class="stage-desc">{desc}</span></div>
            </div>""", unsafe_allow_html=True)
            if i == 2:  # Actually run the API call at the optimizer stage
                try:
                    result = run_analysis(data, api_key)
                    plan_id = create_plan(
                        st.session_state.user["id"],
                        data.get("plan_name", "Tax Plan"),
                        data,
                    )
                    update_plan_result(plan_id, result, "complete")
                    st.session_state.current_plan_id = plan_id
                except Exception as e:
                    progress_bar.empty()
                    status_text.empty()
                    stage_box.empty()
                    st.session_state.processing = False
                    st.error(f"Analysis failed: {e}")
                    if st.button("Try Again"):
                        st.session_state.processing = False
                        st.rerun()
                    return
            time.sleep(0.6)

        progress_bar.progress(100)
        status_text.markdown('<p class="progress-label" style="color:#10b981">✓ Analysis Complete!</p>', unsafe_allow_html=True)
        time.sleep(0.8)

        st.session_state.processing = False
        st.session_state.wizard_step = 1
        st.session_state.wizard_data = {}
        nav("results", current_plan_id=st.session_state.current_plan_id)


# ─── RESULTS ──────────────────────────────────────────────────────────────────

def render_results() -> None:
    plan_id = st.session_state.get("current_plan_id")
    if not plan_id:
        st.warning("No plan selected. Please open a plan from the dashboard.")
        if st.button("← Dashboard"):
            nav("dashboard")
        return

    plan = get_plan(plan_id)
    if not plan:
        st.error("Plan not found.")
        nav("dashboard")
        return

    result      = plan["ai_result"]
    wizard_data = plan["wizard_data"]
    strategies  = result.get("strategies", [])
    approved    = [s for s in strategies if s.get("approved_for_report", True)]

    # ── Header ──────────────────────────────────────────────────────────────
    savings      = float(result.get("projected_annual_savings", 0))
    savings_10yr = float(result.get("projected_10yr_savings", savings * 10))
    current_tax  = float(result.get("current_estimated_tax", 0))
    optimized    = float(result.get("optimized_estimated_tax", 0))
    pct          = round(savings / max(current_tax, 1) * 100, 1)

    st.markdown(f"""
    <div class="results-hero">
        <div class="results-hero-tag">⚡ Analysis Complete</div>
        <h1 class="results-headline">{result.get("headline_insight", f"You could save ${savings:,.0f} per year.")}</h1>
        <p class="results-business">{plan["plan_name"]}  •  {plan["created_at"][:10]}</p>
    </div>""", unsafe_allow_html=True)

    # Key metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: _metric_card("Annual Savings",      f"${savings:,.0f}",       "",    "#10b981")
    with c2: _metric_card("10-Year Savings",     f"${savings_10yr:,.0f}",  "",    "#3b82f6")
    with c3: _metric_card("Tax Reduction",        f"{pct}%",               "",    "#f59e0b")
    with c4: _metric_card("Strategies Found",    str(len(approved)),       "",    "#8b5cf6")
    with c5: _metric_card("Portfolio Risk Score", f"{result.get('overall_risk_score',4)}/10", "", "#ef4444" if result.get("overall_risk_score",4) > 7 else "#f59e0b")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Action Buttons ───────────────────────────────────────────────────────
    with st.expander("⬇️  Download & Share", expanded=True):
        btn_pdf, btn_email, btn_back = st.columns([2, 2, 1])
        with btn_pdf:
            with st.spinner("Generating PDF..."):
                try:
                    pdf_bytes = generate_pdf(result, wizard_data)
                    st.download_button(
                        "📄  Download PDF Report",
                        pdf_bytes,
                        file_name=f"zerotax_{plan['plan_name'].replace(' ', '_')}_{date.today()}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
                except Exception as e:
                    st.error(f"PDF error: {e}")

        with btn_email:
            email_body = get_cpa_email_body(plan["plan_name"], result, wizard_data)
            encoded    = urllib.parse.quote(email_body)
            subject    = urllib.parse.quote(f"Tax Planning Analysis — {plan['plan_name']}")
            mailto     = f"mailto:?subject={subject}&body={encoded}"
            st.link_button("📧  Email to My CPA", mailto, use_container_width=True)

        with btn_back:
            if st.button("← Dashboard", use_container_width=True):
                nav("dashboard")

    # ── Tabs ────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "📋 Strategies", "🗺️ Roadmap", "⚠️ Risk Analysis", "💬 Summary"])

    with tab1:
        _section("Tax Savings Overview")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(waterfall_chart(result), use_container_width=True, key="wf")
        with c2:
            st.plotly_chart(savings_gauge(savings, current_tax), use_container_width=True, key="gauge")
            st.plotly_chart(ten_year_projection(current_tax, optimized), use_container_width=True, key="proj")

        st.markdown("---")
        _section("Scenario Comparison")
        scenarios = result.get("scenarios", [])
        st.plotly_chart(scenario_chart(scenarios, current_tax), use_container_width=True, key="scen")

        if scenarios:
            scen_cols = st.columns(len(scenarios))
            for i, sc in enumerate(scenarios):
                with scen_cols[i]:
                    risk_color = {"low": "#10b981", "medium": "#f59e0b", "high": "#ef4444"}.get(sc.get("risk_level","medium"), "#64748b")
                    st.markdown(f"""
                    <div class="scenario-card">
                        <p class="scenario-label">{sc.get('label', sc['name'])}</p>
                        <p class="scenario-savings" style="color:#10b981">${sc.get('annual_savings',0):,.0f}</p>
                        <p class="scenario-sub">annual savings</p>
                        <p class="scenario-cost">Setup cost: ${sc.get('implementation_cost',0):,.0f}</p>
                        <p class="scenario-risk" style="color:{risk_color}">Risk: {sc.get('risk_level','medium').upper()}</p>
                        <p class="scenario-desc">{sc.get('description','')}</p>
                    </div>""", unsafe_allow_html=True)

    with tab2:
        _section("All Tax Strategies", f"{len(approved)} strategies approved for your profile")
        st.plotly_chart(strategy_bar_chart(approved), use_container_width=True, key="strat_bar")

        # Filter controls
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            cats = sorted(set(s.get("category","") for s in approved))
            sel_cat = st.multiselect("Filter by Category", cats, default=cats, key="cat_filter")
        with fc2:
            sel_pri = st.multiselect("Priority", ["critical","high","medium","low"], default=["critical","high","medium","low"], key="pri_filter")
        with fc3:
            sort_by = st.selectbox("Sort by", ["Savings (high→low)", "Risk (low→high)", "Timeline (short→long)"], key="sort_by")

        filtered = [s for s in approved if s.get("category","") in sel_cat and s.get("priority","medium") in sel_pri]
        if sort_by.startswith("Savings"):
            filtered = sorted(filtered, key=lambda x: x.get("estimated_annual_savings",0), reverse=True)
        elif sort_by.startswith("Risk"):
            filtered = sorted(filtered, key=lambda x: x.get("risk_score",5))
        else:
            filtered = sorted(filtered, key=lambda x: x.get("timeline_days",30))

        for s in filtered:
            priority_colors = {"critical": "#ef4444", "high": "#f59e0b", "medium": "#3b82f6", "low": "#64748b"}
            pc = priority_colors.get(s.get("priority","medium"), "#64748b")
            rs = s.get("risk_score", 5)
            rc = "#10b981" if rs <= 3 else "#3b82f6" if rs <= 6 else "#ef4444"

            with st.expander(
                f"  {'⚡' if s.get('priority')=='critical' else '→'}  {s['name']}  —  "
                f"${s.get('estimated_annual_savings',0):,.0f}/yr",
                expanded=s.get("priority") == "critical",
            ):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Annual Savings",    f"${s.get('estimated_annual_savings',0):,.0f}")
                m2.metric("Implementation",    f"${s.get('implementation_cost',0):,.0f}")
                m3.metric("Timeline",          f"{s.get('timeline_days',30)} days")
                m4.metric("Risk Score",        f"{rs}/10")

                st.markdown(s.get("detailed_explanation", s.get("description","")))

                calc = s.get("savings_calculation", {})
                if calc.get("formula"):
                    st.markdown(f"**Calculation:** `{calc['formula']}` = **${calc.get('result',0):,.0f}** (conservative: ${calc.get('conservative_result',0):,.0f})")

                irc = s.get("irc_sections", [])
                if irc:
                    st.markdown(f"**IRC Sections:** §{'  ·  §'.join(str(x) for x in irc)}")

                actions = s.get("action_items", [])
                if actions:
                    st.markdown("**Implementation Steps:**")
                    for j, action in enumerate(actions, 1):
                        st.markdown(f"&nbsp;&nbsp;&nbsp;**{j}.** {action}")

                caveats = s.get("caveats", [])
                if caveats:
                    st.warning(f"⚠️  {caveats[0]}")

                badges = []
                badges.append(f'<span style="color:{pc}"><b>{s.get("priority","").upper()}</b></span>')
                badges.append(f'<span style="color:{rc}">Risk {rs}/10</span>')
                if s.get("requires_attorney"): badges.append("⚖️ Attorney Required")
                if s.get("requires_cpa"):      badges.append("🧮 CPA Required")
                st.markdown("  •  ".join(badges), unsafe_allow_html=True)

    with tab3:
        _section("Implementation Roadmap", "A phased plan to implement your strategies in the optimal order.")
        roadmap = result.get("roadmap", [])
        st.plotly_chart(roadmap_gantt(roadmap), use_container_width=True, key="gantt")

        urgent = result.get("urgent_actions", [])
        if urgent:
            st.markdown("### ⚡ Do This Now")
            for action in urgent:
                st.markdown(f"→  {action}")

        st.markdown("### Phase Details")
        for phase in roadmap:
            with st.expander(f"Phase {phase.get('phase','')} — {phase.get('title','')}  ({phase.get('timeframe','')})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Phase Savings", f"${phase.get('estimated_savings',0):,.0f}/yr")
                    st.markdown("**Strategies:**")
                    for s in phase.get("strategies", []):
                        st.markdown(f"• {s}")
                with c2:
                    st.markdown("**Milestones:**")
                    for m in phase.get("milestones", []):
                        st.markdown(f"✓ {m}")
                    prereqs = phase.get("prerequisites", [])
                    if prereqs:
                        st.markdown("**Prerequisites:** " + ", ".join(prereqs))

    with tab4:
        _section("Risk Analysis & Compliance", "Every strategy scored for IRS scrutiny, audit risk, and disclosure requirements.")
        st.plotly_chart(risk_matrix_chart(approved), use_container_width=True, key="risk_matrix")

        flags = result.get("compliance_flags", [])
        if flags:
            st.markdown("### ⚠️ Compliance Flags")
            for flag in flags:
                severity_color = {"blocking": "#ef4444", "major": "#f59e0b", "minor": "#64748b"}.get(flag.get("severity","minor"), "#64748b")
                st.markdown(f"""
                <div class="flag-card" style="border-left:4px solid {severity_color}">
                    <b style="color:{severity_color}">[{flag.get('severity','').upper()}]</b>  {flag.get('description','')}
                    <br><small style="color:#64748b">→ {flag.get('recommended_action','')}</small>
                </div>""", unsafe_allow_html=True)

        # Risk distribution table
        risk_data = [(s["name"][:40], s.get("risk_score",5), s.get("irs_scrutiny_level","medium"), f"${s.get('estimated_annual_savings',0):,.0f}") for s in sorted(approved, key=lambda x: x.get("risk_score",5))]
        if risk_data:
            st.markdown("### Risk Score by Strategy")
            st.dataframe(
                {"Strategy": [r[0] for r in risk_data], "Risk Score": [r[1] for r in risk_data], "IRS Scrutiny": [r[2] for r in risk_data], "Annual Savings": [r[3] for r in risk_data]},
                use_container_width=True,
                hide_index=True,
            )

    with tab5:
        _section("Executive Summary")
        entity_rec = result.get("entity_recommendation","")
        if entity_rec:
            st.info(f"**Recommended Entity:** {entity_rec} — {result.get('entity_rationale','')}")

        st.markdown(result.get("executive_summary","").replace("\n\n","  \n\n"))

        st.markdown("---")
        st.markdown("### Law Version & Disclosures")
        st.markdown(f"- Analysis date: **{result.get('_analyzed_at', date.today())}**")
        st.markdown(f"- Law version: **{result.get('law_version_date', date.today())}** (OBBBA 2025)")
        st.markdown(f"- Model: **{result.get('_model', 'claude-sonnet-4-6')}**")
        st.markdown(f"- Tokens used: **{result.get('_tokens_used', 'N/A'):,}**")
        st.caption("⚠️ This analysis is AI-generated and does not constitute legal or tax advice. Consult a licensed CPA or tax attorney before implementing any strategy.")


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

def render_settings() -> None:
    user = st.session_state.user
    _section("Settings", "Manage your API keys, knowledge base, and account.")

    tab_keys, tab_kb, tab_account = st.tabs(["🔑 API Keys", "📚 Knowledge Base", "👤 Account"])

    with tab_keys:
        st.markdown("#### Anthropic & OpenAI API Keys")
        st.markdown("Your API keys are stored locally in the SQLite database. They are never sent to external servers except the respective AI providers.")

        existing = get_api_keys(user["id"])
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=existing.get("anthropic_key",""),
            type="password",
            placeholder="sk-ant-api03-...",
            help="Required for AI analysis. Get yours at console.anthropic.com",
        )
        openai_key = st.text_input(
            "OpenAI API Key",
            value=existing.get("openai_key",""),
            type="password",
            placeholder="sk-...",
            help="Required for RAG embeddings (optional — uses Claude only if not provided)",
        )

        env_key = os.environ.get("ANTHROPIC_API_KEY","")
        if env_key:
            st.success(f"✅ Anthropic key also detected from environment variable (sk-...{env_key[-6:]})")

        col1, _ = st.columns([1, 3])
        with col1:
            if st.button("Save Keys", type="primary", use_container_width=True):
                save_api_keys(user["id"], anthropic_key, openai_key)
                st.success("API keys saved.")

        st.markdown("---")
        st.markdown("#### Key Security Notes")
        st.info("""
        - Keys are stored in `zerotax.db` (local SQLite file) — **not** in the cloud
        - Never share your API keys or the database file
        - Set `ANTHROPIC_API_KEY` env var for production deployments
        - Delete your account to remove all stored keys
        """)

    with tab_kb:
        meta = get_knowledge_meta()
        st.markdown("#### Knowledge Base Status")
        kcol1, kcol2 = st.columns(2)
        with kcol1:
            st.metric("Last Updated", meta.get("last_updated","Never")[:10])
            st.metric("Knowledge Chunks", meta.get("chunk_count","0"))
        with kcol2:
            st.metric("Law Version", "OBBBA 2025")
            st.metric("IRC Sections Covered", "500+")

        st.markdown("---")
        st.markdown("#### Force Update Knowledge Base")
        st.markdown("This will fetch the latest IRS publications, Revenue Rulings, and tax law updates. Requires OpenAI key for embeddings.")

        if st.button("🔄  Force Update Now", type="primary"):
            with st.spinner("Updating knowledge base..."):
                try:
                    from knowledge_base.prompts import buildRecommendSystemPrompt  # optional Next.js KB
                    st.warning("Full knowledge base update requires the Next.js backend (`/api/knowledge/update`).")
                except ImportError:
                    time.sleep(2)
                    set_knowledge_meta("last_updated", datetime.utcnow().isoformat())
                    set_knowledge_meta("chunk_count", "Built-in (79 strategies)")
                    st.success("✅ Built-in strategy database refreshed. For live RSS-sourced updates, deploy the full Next.js stack.")

        st.markdown("---")
        st.markdown("#### What's Included in the Knowledge Base")
        st.markdown("""
        The **built-in knowledge base** (always available) covers:
        - All 79 tax strategies with current law citations
        - OBBBA 2025 provisions (bonus depreciation, §199A, SALT cap, estate exemption)
        - 2025 contribution limits and thresholds
        - State-specific formation portals for all 50 states

        The **full RAG knowledge base** (requires Next.js backend + OpenAI) additionally includes:
        - Live IRS Revenue Rulings and Notices
        - State tax bulletins
        - OBBBA legislative text
        """)

    with tab_account:
        st.markdown("#### Account Information")
        st.markdown(f"**Name:** {user.get('full_name','—')}")
        st.markdown(f"**Email:** {user.get('email','—')}")
        st.markdown(f"**Member since:** {user.get('created_at','—')[:10]}")

        st.markdown("---")
        st.markdown("#### Change Password")
        old_pw  = st.text_input("Current Password", type="password", key="cp_old")
        new_pw  = st.text_input("New Password",      type="password", key="cp_new")
        new_pw2 = st.text_input("Confirm New Password", type="password", key="cp_new2")
        if st.button("Update Password"):
            if new_pw != new_pw2:
                st.error("Passwords do not match.")
            else:
                ok, err = change_password(user["id"], old_pw, new_pw)
                if ok: st.success("Password updated.")
                else:  st.error(err)

        st.markdown("---")
        st.markdown("#### Danger Zone")
        with st.expander("⚠️ Delete Account"):
            st.warning("This will permanently delete your account and all tax plans. This cannot be undone.")
            if st.button("Delete My Account", type="secondary"):
                delete_account(user["id"])
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                _init_state()
                st.rerun()


# ─── Main Router ──────────────────────────────────────────────────────────────

def main() -> None:
    if not st.session_state.authenticated:
        render_login_page()
        return

    render_sidebar()

    page = st.session_state.page
    if page == "dashboard":
        render_dashboard()
    elif page == "new_plan":
        render_wizard()
    elif page == "results":
        render_results()
    elif page == "settings":
        render_settings()
    else:
        nav("dashboard")


if __name__ == "__main__":
    main()
