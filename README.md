<div align="center">

# ⚡ ZeroTax AI

**The AI tax strategist that casually outperforms any $500/hr human accountant.**

*Powered by Claude claude-sonnet-4-6 · 79 Strategies · OBBBA 2025 · One-click PDF Reports*

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Claude claude-sonnet-4-6](https://img.shields.io/badge/Claude-claude--sonnet--4--6-orange?logo=anthropic)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## What It Does

ZeroTax AI is a full-stack AI tax strategy platform that:

1. **Ingests** your business and personal financial profile via a 4-step wizard
2. **Analyzes** your situation through a 5-agent Claude pipeline (Intake → Research → Optimizer → Risk → Synthesis)
3. **Screens** 79 proven tax strategies against your profile with real IRC math
4. **Scores** each strategy for IRS scrutiny, audit risk, and disclosure requirements
5. **Generates** a beautiful branded PDF report with a savings waterfall chart, implementation roadmap, state filing portal links, attorney referral template, and 3-page legal disclaimer
6. **Drafts** a ready-to-send email to your CPA with the full analysis

Typical analysis finds **$50K–$300K+ in annual tax savings** for small business owners.

---

## Screenshots

> 📹 **Video Demo Placeholder**
> 
> *[RECORD A LOOM/YOUTUBE VIDEO HERE — recommended flow:]*
> *1. Login page (10 sec) — show the dark premium UI*
> *2. New Plan wizard (30 sec) — fill in a $500K profit LLC owner in California*
> *3. Analysis running (20 sec) — show the 5-agent progress animation*
> *4. Results page (60 sec) — waterfall chart, scroll through strategies, risk matrix*
> *5. PDF download (15 sec) — show the branded PDF report*
> *6. Email to CPA button (10 sec) — show the pre-filled email template*
> *7. Settings page (10 sec) — API key management*
> *Total: ~2.5 minutes*

```
┌─────────────────────────────────────────────────────────────┐
│  ⚡ ZeroTax AI                              [Dashboard]     │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  📊 Dashboard│   Good morning, Jane 👋                     │
│  ✨ New Plan │   Thursday, February 27, 2026               │
│  ⚙ Settings │                                              │
│              │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  Knowledge   │  │ $127,000 │ │    3     │ │  OBBBA   │    │
│  Updated:    │  │ savings  │ │  plans   │ │  2025    │    │
│  2026-02-27  │  └──────────┘ └──────────┘ └──────────┘    │
│              │                                              │
│              │  ┌─────────────────────────────────────┐    │
│              │  │ 🟢 Complete                         │    │
│              │  │ Acme LLC Tax Plan 2025              │    │
│              │  │ $127,000/yr  · 14 strategies        │    │
│  🚪 Sign Out │  └─────────────────────────────────────┘    │
└──────────────┴──────────────────────────────────────────────┘
```

---

## Strategies Covered

| Category | Strategies | Example |
|---|---|---|
| Entity Structure | S-Corp, C-Corp, Holding Co | S-Corp election saves $18K/yr on $200K profit |
| Retirement Plans | Solo 401k, SEP-IRA, DB Plan, Roth | DB plan deducts up to $275K/yr |
| Depreciation | Bonus §168k, §179, Cost Seg | 100% bonus depreciation (OBBBA permanent) |
| Deductions | QBI §199A, Augusta Rule, Accountable Plan | QBI saves 20% on pass-through income |
| Family Employment | Hire children, employ spouse | Up to $43,800 tax-free to 3 kids |
| Real Estate | 1031 Exchange, REPS, STR Loophole | Cost seg reclassifies 25% to 5-yr property |
| Estate Planning | SLAT, GRAT, DAF, Annual Gifts | $15M OBBBA exemption strategies |
| QSBS | §1202 Exclusion, Stacking, §1045 Rollover | $10M gain excluded tax-free |
| Exit Planning | ESOP §1042, Installment Sale, Asset vs Stock | 0% capital gains via ESOP |
| State Tax | PTE Election, Residency, Nexus | $40K SALT cap workaround (OBBBA) |
| Credits | R&D §41, WOTC, Energy Credits | R&D credit for software companies |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **AI** | Anthropic Claude claude-sonnet-4-6 (5-agent pipeline) |
| **Frontend** | Streamlit + Plotly + custom dark CSS |
| **PDF** | ReportLab + Matplotlib |
| **Database** | SQLite (local) / Supabase pgvector (Next.js version) |
| **Auth** | PBKDF2 + SHA-256 (no external auth service) |
| **Embeddings** | OpenAI text-embedding-3-small (optional RAG) |

**Alternative Next.js stack** (in `/zerotax-ai/`):  
TypeScript · Next.js 15 · Supabase · Vercel · pgvector RAG

---

## Quick Start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-api03-...
streamlit run app.py
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment options (Docker, Railway, Render, Streamlit Cloud).

---

## Project Structure

```
.
├── app.py                  ← Streamlit UI (login, dashboard, wizard, results, settings)
├── ai_engine.py            ← Claude API integration + prompt builder
├── report_generator.py     ← PDF report (ReportLab + Matplotlib)
├── charts.py               ← Plotly interactive charts (waterfall, gauge, risk matrix)
├── database.py             ← SQLite persistence (users, plans, API keys)
├── auth.py                 ← PBKDF2 authentication
├── state_portals.py        ← All 50 state filing portals + attorney template
├── styles/
│   └── custom.css          ← Premium dark mode CSS
├── .streamlit/
│   └── config.toml         ← Streamlit theme config
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── render.yaml
├── DEPLOYMENT.md
│
└── zerotax-ai/             ← Production Next.js app (5-agent TypeScript pipeline)
    ├── app/api/ai/
    │   ├── recommend/      ← Original single-agent Claude endpoint
    │   └── strategist/     ← New 5-agent graph endpoint
    ├── lib/agents/
    │   ├── types.ts        ← GraphState + all interfaces
    │   ├── strategies-db.ts← 50+ strategies with TypeScript apply() functions
    │   ├── prompts.ts      ← 5 agent system prompts
    │   └── graph.ts        ← Sequential orchestrator
    └── lib/tax-rag.ts      ← pgvector RAG retrieval
```

---

## Law Version

This analysis engine is current through **OBBBA 2025** (One Big Beautiful Bill Act), covering:

- §199A QBI deduction: Permanent at 23% (2026+)
- §168(k) Bonus depreciation: Restored to 100% permanently
- §174 R&D: Immediate expensing restored
- SALT cap: $40,000 for income ≤ $500K
- Estate exemption: $15M per person ($30M MFJ)
- Standard deduction: $30,000 MFJ / $15,000 Single
- Solo 401k: $70,000 limit (2025)
- SS wage base: $176,100 (2025)

---

## Disclaimer

ZeroTax AI is an AI-powered information tool. **It does not provide legal, tax, or financial advice.** All strategies must be reviewed by a licensed CPA or tax attorney before implementation. Savings estimates are illustrative and depend on your specific circumstances. See the in-app disclaimer for full disclosures.

---

## License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">
Built with ⚡ by ZeroTax AI · Powered by Anthropic Claude
</div>
