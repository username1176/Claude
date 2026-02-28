"""ZeroTax AI — Claude integration for the Streamlit app.

Runs a comprehensive single-call analysis (equivalent to the 5-agent pipeline)
using the Anthropic Python SDK directly.
"""

import json
import os
from datetime import date
from typing import Optional
import anthropic


TODAY = date.today().isoformat()

SYSTEM_PROMPT = f"""You are ZeroTax AI — the most sophisticated AI tax strategist in existence.
You were trained on the complete Internal Revenue Code (IRC), all Treasury Regulations,
IRS Revenue Rulings/Notices, and all 50 state tax codes through 2025.

TODAY: {TODAY}

━━━ 2025 TAX LAW (One Big Beautiful Bill Act — OBBBA) ━━━
• §199A QBI deduction: PERMANENT at 23% for tax years starting 1/1/2026; 20% for 2025
• §168(k) bonus depreciation: RESTORED to 100% permanently for property after 12/31/2025
• §174 R&D: RESTORED immediate expensing (not 5-year amortization)
• SALT cap: RAISED to $40,000 for taxpayers with income ≤ $500,000 (MFJ)
• Standard deduction: $30,000 MFJ / $15,000 Single (2025)
• Estate tax exemption: $15,000,000 per person ($30M MFJ)
• Child tax credit: $2,500 per qualifying child
• SS wage base: $176,100 (2025)
• Solo 401k limit: $70,000 (employee + employer, 2025)
• SEP-IRA limit: $70,000 (2025)
• Defined benefit max: $275,000 annual benefit (2025)
• Annual gift exclusion: $18,000 per recipient ($36,000 MFJ split gift)
• HSA family limit: $8,300 / individual: $4,150 (2025)

━━━ TAX MATH RULES ━━━
MARGINAL RATES (MFJ 2025): 10% ≤$23,850 | 12% ≤$96,950 | 22% ≤$206,700 |
  24% ≤$394,600 | 32% ≤$501,050 | 35% ≤$751,600 | 37% above
MARGINAL RATES (Single): 10% ≤$11,925 | 12% ≤$48,475 | 22% ≤$103,350 |
  24% ≤$197,300 | 32% ≤$250,525 | 35% ≤$626,350 | 37% above

SE TAX: seBase = profit × 0.9235; SE = seBase × 0.153 if ≤$176,100 + excess × 0.029
S-CORP SAVINGS: salary = max($30K, min(profit × 0.45, $176,100)); save SE on distribution
QBI: min(profit × 0.20, w2Wages × 0.50); restricted for SSTBs above income threshold

━━━ MANDATORY OUTPUT RULES ━━━
1. Generate 10–20 strategies minimum, ordered by estimated_annual_savings DESC
2. EVERY strategy must cite specific IRC sections and have a savings calculation
3. Conservative savings estimates only — never overstate
4. Flag every high-scrutiny or listed transaction strategy
5. Respond ONLY with valid JSON — no markdown, no preamble, no text outside JSON

━━━ RISK SCORING ━━━
1-3: Well-established, bright-line rules (§179, Solo 401k, health insurance)
4-5: Valid but fact-intensive, common audit areas (S-Corp salary, home office)
6-7: Aggressive, IRS has litigated (captive insurance, REPS, FLP discounts)
8+:  Listed transaction or near-abusive — flag approvedForReport = false"""


USER_PROMPT_TEMPLATE = """Analyze this taxpayer and generate a complete tax optimization plan.

TAXPAYER PROFILE:
{profile_block}

Return ONLY this exact JSON structure (no markdown, raw JSON):
{{
  "headline_insight": "You are leaving $X/year on the table — here is how to fix it",
  "executive_summary": "4-paragraph plain-English summary with specific dollar amounts",
  "entity_recommendation": "e.g. S-Corporation",
  "entity_rationale": "2-3 sentences with IRC citation",
  "current_estimated_tax": <number>,
  "optimized_estimated_tax": <number>,
  "projected_annual_savings": <number>,
  "projected_10yr_savings": <number>,
  "law_version_date": "{today}",
  "savings_breakdown": {{
    "entity_restructuring": <number or 0>,
    "retirement_plans": <number or 0>,
    "qbi_deduction": <number or 0>,
    "depreciation": <number or 0>,
    "family_employment": <number or 0>,
    "state_tax": <number or 0>,
    "other_deductions": <number or 0>
  }},
  "scenarios": [
    {{
      "name": "conservative",
      "label": "Safe & Certain",
      "description": "Low-risk strategies only — fully established law",
      "annual_savings": <number>,
      "strategies_included": ["strategy names"],
      "risk_level": "low",
      "implementation_cost": <number>
    }},
    {{
      "name": "optimal",
      "label": "Best Risk-Adjusted",
      "description": "Maximum savings with acceptable audit risk",
      "annual_savings": <number>,
      "strategies_included": ["strategy names"],
      "risk_level": "medium",
      "implementation_cost": <number>
    }},
    {{
      "name": "aggressive",
      "label": "Maximum Reduction",
      "description": "All legal strategies including higher-scrutiny positions",
      "annual_savings": <number>,
      "strategies_included": ["strategy names"],
      "risk_level": "high",
      "implementation_cost": <number>
    }}
  ],
  "strategies": [
    {{
      "id": "unique_snake_case_id",
      "name": "Strategy Name",
      "category": "entity_structure|retirement|depreciation|deductions|real_estate|estate_planning|asset_protection|exit|family_employment|qsbs|opportunity_zone|credits|state_tax",
      "description": "One-sentence description (max 200 chars)",
      "detailed_explanation": "Full 300-600 char explanation with IRC sections, effective date, and calculation",
      "irc_sections": ["199A", "1361"],
      "obbba_sections": [],
      "estimated_annual_savings": <number>,
      "savings_calculation": {{
        "formula": "plain-English formula used",
        "inputs": {{"key": value}},
        "result": <number>,
        "conservative_result": <number>
      }},
      "implementation_cost": <number>,
      "payback_period_months": <number>,
      "priority": "critical|high|medium|low",
      "complexity": "simple|medium|complex|attorney_required",
      "timeline_days": <number>,
      "requires_attorney": <boolean>,
      "requires_cpa": <boolean>,
      "risk_score": <1-10>,
      "irs_scrutiny_level": "low|medium|high|very_high",
      "approved_for_report": <boolean — false if risk_score >= 9>,
      "action_items": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
      "caveats": ["what can go wrong"],
      "compliance_notes": []
    }}
  ],
  "roadmap": [
    {{
      "phase": 1,
      "title": "Immediate Wins (Days 1–30)",
      "timeframe": "Days 1–30",
      "strategies": ["strategy names"],
      "estimated_savings": <number>,
      "milestones": ["Milestone 1", "Milestone 2"],
      "prerequisites": []
    }},
    {{
      "phase": 2,
      "title": "Quick Implementation (Days 31–90)",
      "timeframe": "Days 31–90",
      "strategies": ["strategy names"],
      "estimated_savings": <number>,
      "milestones": ["Milestone 1"],
      "prerequisites": ["Phase 1 complete"]
    }},
    {{
      "phase": 3,
      "title": "Mid-Term Strategies (Months 4–12)",
      "timeframe": "Months 4–12",
      "strategies": ["strategy names"],
      "estimated_savings": <number>,
      "milestones": ["Milestone 1"],
      "prerequisites": []
    }},
    {{
      "phase": 4,
      "title": "Long-Term Optimization (Year 2+)",
      "timeframe": "Year 2+",
      "strategies": ["strategy names"],
      "estimated_savings": <number>,
      "milestones": ["Milestone 1"],
      "prerequisites": ["Phase 2–3 complete"]
    }}
  ],
  "urgent_actions": [
    "Action 1 (deadline: [DATE])",
    "Action 2 (deadline: [DATE])"
  ],
  "overall_risk_score": <1-10>,
  "compliance_flags": [
    {{
      "strategy_id": "string",
      "flag_type": "aggressive|disclosure_required|warning",
      "severity": "major|minor",
      "description": "string",
      "recommended_action": "string"
    }}
  ]
}}"""


def _build_profile_block(data: dict) -> str:
    goals = []
    if data.get("goal_minimize_taxes"):     goals.append("Minimize taxes now")
    if data.get("goal_asset_protection"):   goals.append("Asset protection")
    if data.get("goal_estate_planning"):    goals.append("Estate planning")
    if data.get("goal_exit_strategy"):      goals.append("Exit / sell business")
    if data.get("goal_retirement"):         goals.append("Retirement planning")
    if data.get("goal_hire_family"):        goals.append("Employ family members")

    def fmt(n):
        try:
            return f"${int(n):,}"
        except Exception:
            return str(n) if n else "Not provided"

    entity = data.get("entity_type", "unknown")
    suboptimal = ""
    if entity in ("sole_prop", "single_llc", "multi_llc"):
        profit = float(data.get("annual_profit", 0) or 0)
        if profit > 40_000:
            suboptimal = "  ⚠️ SUBOPTIMAL ENTITY — S-Corp election is likely #1 opportunity"

    lines = [
        "BUSINESS",
        f"  Stage:          {data.get('business_stage', 'unknown')}",
        f"  Entity:         {entity}{suboptimal}",
        f"  State:          {data.get('state', 'unknown')}",
        f"  Business Name:  {data.get('business_name', 'Not provided')}",
        "",
        "FINANCIALS",
        f"  Annual Revenue: {fmt(data.get('annual_revenue'))}",
        f"  Annual Profit:  {fmt(data.get('annual_profit'))}",
        f"  W-2 Wages Paid: {fmt(data.get('w2_wages_paid'))}",
        f"  Total Assets:   {fmt(data.get('total_net_worth'))}",
        f"  Real Estate:    {fmt(data.get('real_estate_value'))}",
        f"  Retirement Accts:{fmt(data.get('retirement_accounts'))}",
        f"  Investment Port: {fmt(data.get('investment_portfolio'))}",
        "",
        "PERSONAL",
        f"  Married (MFJ):  {'Yes' if data.get('is_married') else 'No'}",
        f"  Spouse Income:  {fmt(data.get('spouse_income', 0))}",
        f"  Children:       {data.get('children', 0)}",
        f"  QSBS Stock:     {'Yes' if data.get('has_qsbs') else 'No'}",
        "",
        "GOALS (priority order):",
    ]
    lines += [f"  {i+1}. {g}" for i, g in enumerate(goals)] if goals else ["  Not specified"]
    lines += [
        "",
        "PLANNING PARAMETERS",
        f"  Risk Tolerance:    {data.get('risk_tolerance', 'moderate')}",
        f"  Planning Horizon:  {data.get('planning_horizon', '3 years')}",
        f"  Industry:          {data.get('industry', 'Not specified')}",
    ]
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    fence = __import__("re").search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        return fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


def run_analysis(wizard_data: dict, api_key: str) -> dict:
    """Run the full AI analysis and return parsed JSON result."""
    client = anthropic.Anthropic(api_key=api_key)

    profile_block = _build_profile_block(wizard_data)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        profile_block=profile_block,
        today=TODAY,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10_000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text if message.content[0].type == "text" else ""
    try:
        result = json.loads(_extract_json(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {e}\n\nRaw (first 500 chars):\n{raw[:500]}")

    # Inject metadata
    result["_tokens_used"] = message.usage.input_tokens + message.usage.output_tokens
    result["_model"] = "claude-sonnet-4-6"
    result["_analyzed_at"] = TODAY

    return result


def get_cpa_email_body(plan_name: str, result: dict, wizard_data: dict) -> str:
    """Generate a professional email body to send to a CPA."""
    savings = result.get("projected_annual_savings", 0)
    strategies = [s for s in result.get("strategies", []) if s.get("approved_for_report", True)]
    top_strats = strategies[:5]
    urgent = result.get("urgent_actions", [])

    lines = [
        f"Subject: Tax Planning Analysis — {plan_name} — ${savings:,.0f}/yr Opportunity",
        "",
        "Hi [CPA Name],",
        "",
        f"I've completed a preliminary AI-assisted tax analysis for {wizard_data.get('business_name', 'my business')} "
        f"and identified approximately ${savings:,.0f} in potential annual tax savings. "
        "I'd like to discuss these opportunities with you and get your professional assessment.",
        "",
        "HEADLINE OPPORTUNITY:",
        result.get("headline_insight", ""),
        "",
        "TOP STRATEGIES IDENTIFIED:",
    ]
    lines += [
        f"• {s['name']} — ~${s.get('estimated_annual_savings', 0):,.0f}/yr "
        f"(IRC §{', §'.join(s.get('irc_sections', [])[:2])})"
        for s in top_strats
    ]
    lines += [
        "",
        "ENTITY RECOMMENDATION:",
        f"Current: {wizard_data.get('entity_type', 'Unknown')} → Recommended: {result.get('entity_recommendation', 'See analysis')}",
        result.get("entity_rationale", ""),
        "",
        "URGENT ITEMS (year-end deadlines):",
    ]
    lines += [f"• {a}" for a in urgent[:3]] if urgent else ["• No immediate deadlines identified"]
    lines += [
        "",
        "FULL ANALYSIS ATTACHED (ZeroTax AI — for reference only, not legal/tax advice)",
        "",
        "Business Profile:",
        f"• Entity: {wizard_data.get('entity_type')}",
        f"• State: {wizard_data.get('state')}",
        f"• Annual Revenue: ${float(wizard_data.get('annual_revenue', 0) or 0):,.0f}",
        f"• Annual Profit: ${float(wizard_data.get('annual_profit', 0) or 0):,.0f}",
        "",
        "Please let me know your availability for a 30-minute call to review.",
        "",
        "Thank you,",
        "[YOUR NAME]",
        "",
        "─────────────────────────────────────────────────",
        "DISCLAIMER: This analysis was generated by ZeroTax AI and is provided",
        "for informational purposes only. It does not constitute legal or tax advice.",
        "All strategies must be reviewed by a licensed CPA or tax attorney before",
        "implementation. Past savings estimates are not guarantees of future results.",
    ]
    return "\n".join(lines)
