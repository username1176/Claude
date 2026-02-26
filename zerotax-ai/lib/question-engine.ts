// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Adaptive Question Engine
// Equivalent to question_engine.py — full branching logic, validation, and
// answer-to-database mapping for the 12–18 question adaptive wizard.
// ─────────────────────────────────────────────────────────────────────────────

// ─── Types ───────────────────────────────────────────────────────────────────

export type QuestionType =
  | "select"       // Single choice — auto-advances on click
  | "multiselect"  // Multi-choice — requires Continue button
  | "currency"     // Dollar amount — requires Continue button
  | "boolean"      // Yes / No — auto-advances on click
  | "state_select"; // US state dropdown — requires Continue button

export interface SelectOption {
  value: string;
  label: string;
  emoji?: string;
  description?: string;
}

export interface Question {
  id: string;
  emoji: string;
  text: string;
  subtitle?: string;
  tooltipTitle: string;
  tooltip: string;
  type: QuestionType;
  options?: SelectOption[];
  /** If true, user can skip with null value */
  optional?: boolean;
  placeholder?: string;
  /** showIf = undefined means always visible */
  showIf?: (answers: Answers) => boolean;
}

export type Answers = Record<string, unknown>;

// ─── All Questions (max 17, adaptive branching trims to 10–15 per user) ──────

export const QUESTIONS: Question[] = [
  // ── Q1: Country ────────────────────────────────────────────────────────────
  {
    id: "country",
    emoji: "🌎",
    text: "Where is your business primarily based?",
    subtitle: "We'll tailor every strategy to your jurisdiction's tax laws.",
    tooltipTitle: "Why your location matters",
    tooltip:
      "U.S. tax law has uniquely powerful tools — S-Corp elections, opportunity zones, Section 1202 QSBS exclusions — that can legally eliminate most of your tax burden. Outside the U.S.? We still find cross-border strategies, but the playbook differs significantly.",
    type: "select",
    options: [
      { value: "us", label: "United States", emoji: "🇺🇸" },
      { value: "ca", label: "Canada", emoji: "🇨🇦" },
      { value: "uk", label: "United Kingdom", emoji: "🇬🇧" },
      { value: "au", label: "Australia", emoji: "🇦🇺" },
      { value: "other", label: "Other country", emoji: "🌍" },
    ],
  },

  // ── Q2: Business Stage ─────────────────────────────────────────────────────
  {
    id: "business_stage",
    emoji: "🚀",
    text: "What stage is your business in?",
    subtitle: "This determines which strategies are immediately available to you.",
    tooltipTitle: "Stage changes your entire strategy",
    tooltip:
      "An idea-stage founder needs entity selection and startup deductions. A 7-figure established business needs S-Corp/C-Corp restructuring, defined benefit pension plans, and asset protection fortress structures. The right strategy at the wrong stage wastes money.",
    type: "select",
    options: [
      { value: "idea", label: "Pre-revenue / idea stage", emoji: "💡", description: "Planning or just starting out" },
      { value: "startup", label: "Startup (< $250K revenue)", emoji: "🌱", description: "Early growth, under 2 years" },
      { value: "growth", label: "Growth ($250K – $1M)", emoji: "📈", description: "Scaling operations fast" },
      { value: "established", label: "Established ($1M – $10M)", emoji: "🏢", description: "Profitable, growing steadily" },
      { value: "mature", label: "Mature ($10M+)", emoji: "🏆", description: "Complex multi-entity operation" },
    ],
  },

  // ── Q3: Entity Type ────────────────────────────────────────────────────────
  {
    id: "entity_type",
    emoji: "🏛️",
    text: "What is your current business structure?",
    tooltipTitle: "Entity type is the #1 tax lever",
    tooltip:
      "Switching from a sole proprietorship to an S-Corp alone saves most profitable business owners $10K–$40K per year in self-employment taxes. Your entity choice is the single most impactful variable in your entire tax strategy.",
    type: "select",
    options: [
      { value: "sole_prop", label: "Sole proprietor / DBA", emoji: "👤", description: "No formal entity" },
      { value: "single_llc", label: "Single-member LLC", emoji: "🔵", description: "Taxed as sole prop by default" },
      { value: "multi_llc", label: "Multi-member LLC", emoji: "🟣", description: "Taxed as partnership by default" },
      { value: "s_corp", label: "S-Corporation", emoji: "🟢" },
      { value: "c_corp", label: "C-Corporation", emoji: "🔴" },
      { value: "partnership", label: "Partnership / LP", emoji: "🤝" },
      { value: "not_formed", label: "Haven't formed one yet", emoji: "❓" },
    ],
  },

  // ── Q4: State (US only) ────────────────────────────────────────────────────
  {
    id: "state",
    emoji: "📍",
    text: "Which state is your business registered in?",
    subtitle: "Where you're formed matters almost as much as how you're structured.",
    tooltipTitle: "State selection can save thousands",
    tooltip:
      "Wyoming, Nevada, and Delaware have zero state income tax and the strongest asset protection laws in the country. Even if you operate in California or New York, a holding company registered in Wyoming can legally redirect income — potentially saving five figures annually.",
    type: "state_select",
    showIf: (a) => a.country === "us",
  },

  // ── Q5: Annual Revenue ─────────────────────────────────────────────────────
  {
    id: "annual_revenue",
    emoji: "💰",
    text: "What is your approximate annual revenue?",
    subtitle: "Rough estimate is perfectly fine — we won't judge.",
    tooltipTitle: "Revenue unlocks different strategies",
    tooltip:
      "Revenue thresholds determine which strategies open up. S-Corp election is most powerful at $60K+ net profit. Defined benefit pension plans need $200K+. Real zero-tax fortress structures typically become available at $500K+ revenue.",
    type: "currency",
    optional: true,
    placeholder: "0",
    showIf: (a) => a.business_stage !== "idea",
  },

  // ── Q6: Annual Profit ──────────────────────────────────────────────────────
  {
    id: "annual_profit",
    emoji: "📊",
    text: "What is your estimated annual net profit?",
    subtitle: "Revenue minus all business expenses — this is what gets taxed.",
    tooltipTitle: "We optimize profit, not revenue",
    tooltip:
      "Your tax bill is calculated on profit, not revenue. This number is what we're attacking. If you're not sure, a rough estimate is fine — even knowing the ballpark unlocks specific strategy recommendations.",
    type: "currency",
    optional: true,
    placeholder: "0",
    showIf: (a) => {
      const rev = Number(a.annual_revenue ?? 0);
      return a.business_stage !== "idea" && rev > 0;
    },
  },

  // ── Q7: Employees ──────────────────────────────────────────────────────────
  {
    id: "has_employees",
    emoji: "👥",
    text: "Do you have W-2 employees besides yourself?",
    tooltipTitle: "Employees create tax opportunities",
    tooltip:
      "W-2 employees unlock powerful strategies: paying your children tax-free wages, Section 199A QBI deductions that scale with payroll, defined benefit pension plans, and group benefit programs that are deductible to the business but deeply valuable to you personally.",
    type: "boolean",
    showIf: (a) => a.business_stage !== "idea",
  },

  // ── Q8: W-2 Wages Paid ────────────────────────────────────────────────────
  {
    id: "w2_wages",
    emoji: "💼",
    text: "How much do you pay in total W-2 wages annually?",
    subtitle: "All employee wages combined — exclude your own salary.",
    tooltipTitle: "W-2 wages affect your QBI deduction",
    tooltip:
      "The Section 199A Qualified Business Income (QBI) deduction — worth 20% of eligible income — has a W-2 wage test for high earners. High-revenue, high-payroll businesses can dramatically increase this deduction by understanding the wage threshold.",
    type: "currency",
    optional: true,
    placeholder: "0",
    showIf: (a) => a.has_employees === true && a.business_stage !== "idea",
  },

  // ── Q9: Total Assets (triggers deep dive at $500K+) ───────────────────────
  {
    id: "total_assets",
    emoji: "🏦",
    text: "What is the approximate total value of your assets?",
    subtitle: "Business equity, real estate, investments, cash, retirement accounts.",
    tooltipTitle: "Assets over $500K need protection",
    tooltip:
      "Once your net worth exceeds ~$500K, you become a prime target for frivolous lawsuits. We'll recommend holding company structures, charging order protection LLCs, and Domestic Asset Protection Trusts (DAPTs) to create legal walls around your wealth before any judgment can touch it.",
    type: "select",
    options: [
      { value: "under_100k", label: "Under $100,000", emoji: "🌱" },
      { value: "100k_500k", label: "$100K – $500K", emoji: "💼" },
      { value: "500k_1m", label: "$500K – $1M", emoji: "🏠", description: "Asset protection becomes critical" },
      { value: "1m_5m", label: "$1M – $5M", emoji: "🏰", description: "Full fortress structure recommended" },
      { value: "over_5m", label: "Over $5M", emoji: "🏯", description: "Advanced fortress strategy essential" },
    ],
  },

  // ── Q10: Real Estate (asset protection deep dive — $500K+ assets) ─────────
  {
    id: "real_estate",
    emoji: "🏠",
    text: "What is the approximate value of your real estate holdings?",
    subtitle: "Primary home, rental properties, commercial real estate — all of it.",
    tooltipTitle: "Real estate needs separate LLC protection",
    tooltip:
      "Real estate is a prime lawsuit target. Each property (or portfolio of similar properties) should be held in a separate LLC to contain liability. A Series LLC can protect multiple properties efficiently. Land trusts add another privacy layer. We'll map the right structure for your portfolio.",
    type: "currency",
    optional: true,
    placeholder: "0",
    showIf: (a) =>
      ["500k_1m", "1m_5m", "over_5m"].includes(a.total_assets as string),
  },

  // ── Q11: QSBS Eligibility ─────────────────────────────────────────────────
  {
    id: "has_qsbs",
    emoji: "📈",
    text: "Is your company a C-Corp (or considering converting) for QSBS purposes?",
    subtitle: "Section 1202 Qualified Small Business Stock — the most powerful exit tax break in the code.",
    tooltipTitle: "QSBS: up to $10M tax-free on exit",
    tooltip:
      "Section 1202 QSBS exclusion can make up to $10 million (or 10× your investment, whichever is greater) of capital gain completely tax-free when you sell. To qualify: C-Corp, under $50M in assets at issuance, held for 5+ years. We can help you position for this.",
    type: "boolean",
    optional: true,
    showIf: (a) => {
      const stage = a.business_stage as string;
      return (
        a.entity_type === "c_corp" ||
        ["growth", "established", "mature"].includes(stage)
      );
    },
  },

  // ── Q12: Marital Status ────────────────────────────────────────────────────
  {
    id: "married",
    emoji: "💑",
    text: "Are you married or in a domestic partnership?",
    tooltipTitle: "Marriage doubles several strategies",
    tooltip:
      "Married couples can double their QSBS exclusion with proper planning, stack spousal IRA contributions, split gifts for estate planning, and use Spousal Lifetime Access Trusts (SLATs) for asset protection. Being married significantly expands your tax planning toolkit.",
    type: "boolean",
  },

  // ── Q13: Children ──────────────────────────────────────────────────────────
  {
    id: "children_count",
    emoji: "👨‍👩‍👧‍👦",
    text: "Do you have dependent children?",
    subtitle: "Children under 18 create significant tax planning opportunities.",
    tooltipTitle: "Hire your kids: $14,600 tax-free each",
    tooltip:
      "Paying your children legitimate wages for real work in your business is 100% legal and IRS-approved. Each child can earn up to the standard deduction ($14,600 in 2024) completely tax-free. In a sole prop or single-member LLC, you avoid FICA taxes entirely — that's a 15.3% extra savings.",
    type: "select",
    options: [
      { value: "0", label: "No children", emoji: "✖️" },
      { value: "1", label: "1 child", emoji: "1️⃣" },
      { value: "2", label: "2 children", emoji: "2️⃣" },
      { value: "3", label: "3 children", emoji: "3️⃣" },
      { value: "4_plus", label: "4 or more", emoji: "👨‍👩‍👧‍👦" },
    ],
  },

  // ── Q14: Goals (multiselect) ───────────────────────────────────────────────
  {
    id: "goals",
    emoji: "🎯",
    text: "What are your primary financial goals?",
    subtitle: "Select all that apply — we'll prioritize your plan accordingly.",
    tooltipTitle: "Goals shape your entire strategy mix",
    tooltip:
      "Tax minimization today vs. estate planning vs. exit optimization require fundamentally different structures. Knowing your priorities lets us surface the highest-ROI strategies first and avoid building structures that conflict with your actual objectives.",
    type: "multiselect",
    options: [
      { value: "minimize_taxes", label: "Minimize taxes now", emoji: "📉", description: "Immediate, aggressive reduction" },
      { value: "asset_protection", label: "Protect from lawsuits", emoji: "🛡️", description: "Legal liability shields" },
      { value: "estate_planning", label: "Estate & legacy planning", emoji: "🏛️", description: "Wealth transfer to heirs" },
      { value: "exit_strategy", label: "Exit / sell the business", emoji: "🚪", description: "Tax-efficient exit planning" },
      { value: "retirement", label: "Build retirement wealth", emoji: "🌅", description: "Tax-advantaged accounts" },
      { value: "hire_family", label: "Employ family members", emoji: "👨‍👩‍👧", description: "Pay family tax-efficiently" },
    ],
  },

  // ── Q15: Risk Tolerance ────────────────────────────────────────────────────
  {
    id: "risk_tolerance",
    emoji: "⚖️",
    text: "How aggressive do you want to be with tax strategies?",
    subtitle: "All strategies we recommend are 100% legal — the question is complexity.",
    tooltipTitle: "Risk tolerance shapes your recommendations",
    tooltip:
      "Conservative = fully settled IRS positions with zero audit risk (S-Corp elections, standard retirement accounts). Moderate = well-established but complex structures requiring professional help (defined benefit plans, holding companies). Aggressive = strategies that may attract scrutiny but are legal with meticulous documentation (Puerto Rico Act 60, DSTs, advanced trust structures).",
    type: "select",
    options: [
      { value: "conservative", label: "Conservative", emoji: "🟢", description: "Proven, settled strategies only" },
      { value: "moderate", label: "Moderate", emoji: "🟡", description: "Complex structures with professional help" },
      { value: "aggressive", label: "Aggressive", emoji: "🔴", description: "Maximize every legal strategy available" },
    ],
  },

  // ── Q16: Planning Horizon ──────────────────────────────────────────────────
  {
    id: "planning_horizon",
    emoji: "🕐",
    text: "What is your tax planning time horizon?",
    tooltipTitle: "Time horizon changes everything",
    tooltip:
      "A 1-year horizon means we focus on deductions and deferral that save money this tax year. A 5+ year horizon means we build structures — entity conversions, retirement systems, trust frameworks — that compound savings over decades and can ultimately reduce your lifetime tax rate to near zero.",
    type: "select",
    options: [
      { value: "immediate", label: "This tax year only", emoji: "⚡", description: "I need wins immediately" },
      { value: "1_year", label: "1–2 years", emoji: "📅", description: "Short-term planning" },
      { value: "3_year", label: "3–5 years", emoji: "📆", description: "Mid-term strategy" },
      { value: "5_plus", label: "5+ years", emoji: "🏗️", description: "Long-term wealth building" },
    ],
  },

  // ── Q17: Exit Timeline (only if exit is a goal) ────────────────────────────
  {
    id: "exit_timeline",
    emoji: "🚪",
    text: "When are you planning to exit or sell your business?",
    tooltipTitle: "Exit planning starts years in advance",
    tooltip:
      "QSBS requires a 5-year holding period. ESOPs, installment sales, and Charitable Remainder Trusts all need years of advance setup to work properly. The sooner we structure your exit, the more of your proceeds can be tax-free. A rushed exit is a taxable exit.",
    type: "select",
    optional: true,
    options: [
      { value: "1_2_years", label: "1–2 years", emoji: "⚡", description: "Start planning immediately" },
      { value: "3_5_years", label: "3–5 years", emoji: "📅" },
      { value: "5_10_years", label: "5–10 years", emoji: "📆" },
      { value: "over_10_years", label: "10+ years", emoji: "🏗️" },
      { value: "no_plan", label: "No specific timeline", emoji: "🤷" },
    ],
    showIf: (a) =>
      Array.isArray(a.goals) &&
      (a.goals as string[]).includes("exit_strategy"),
  },
];

// ─── Engine Functions ─────────────────────────────────────────────────────────

/** Returns all questions that should be shown based on current answers */
export function getVisibleQuestions(answers: Answers): Question[] {
  return QUESTIONS.filter((q) => !q.showIf || q.showIf(answers));
}

/** Returns the next unanswered question, or null if complete */
export function getNextQuestion(
  answers: Answers,
  history: string[]
): Question | null {
  const visible = getVisibleQuestions(answers);
  return visible.find((q) => !history.includes(q.id)) ?? null;
}

/** Returns progress metadata */
export function getProgress(
  answers: Answers,
  history: string[]
): { answered: number; total: number; percent: number } {
  const visible = getVisibleQuestions(answers);
  const answered = history.length;
  const total = visible.length;
  return {
    answered,
    total,
    percent: total > 0 ? Math.round((answered / total) * 100) : 0,
  };
}

// ─── Strategy Estimation (for Summary Page) ───────────────────────────────────

export interface StrategyEstimate {
  strategyCount: number;
  annualSavingsMin: number;
  annualSavingsMax: number;
  highlights: string[];
}

export function estimateStrategies(answers: Answers): StrategyEstimate {
  const highlights: string[] = [];
  let count = 3; // Baseline: deductions, depreciation, basic retirement
  let savingsMin = 0;
  let savingsMax = 0;

  const profit = Number(answers.annual_profit ?? 0);
  const revenue = Number(answers.annual_revenue ?? 0);
  const stage = (answers.business_stage as string) ?? "";
  const entity = (answers.entity_type as string) ?? "";
  const assets = (answers.total_assets as string) ?? "";
  const goals = (answers.goals as string[]) ?? [];
  const childrenStr = (answers.children_count as string) ?? "0";
  const married = answers.married as boolean;

  // ── S-Corp opportunity ──────────────────────────────────────────────────
  if (
    ["sole_prop", "single_llc", "multi_llc", "not_formed"].includes(entity) &&
    profit > 60000
  ) {
    const seSavings = Math.min(Math.round(profit * 0.145), 34000);
    count++;
    savingsMin += Math.round(seSavings * 0.4);
    savingsMax += seSavings;
    highlights.push(
      `S-Corp election — eliminate up to $${seSavings.toLocaleString()}/yr in SE tax`
    );
  }

  // ── Section 199A QBI Deduction ──────────────────────────────────────────
  if (profit > 50_000 && entity !== "c_corp") {
    const qbi = Math.round(profit * 0.2 * 0.22);
    count++;
    savingsMin += Math.round(qbi * 0.5);
    savingsMax += qbi;
    highlights.push(`Section 199A QBI deduction — 20% of qualified income excluded`);
  }

  // ── Defined Benefit Pension Plan ────────────────────────────────────────
  if (profit > 150_000) {
    const dbSavings = Math.round(Math.min(profit * 0.35, 70_000));
    count += 2;
    savingsMin += Math.round(dbSavings * 0.4);
    savingsMax += dbSavings;
    highlights.push(`Defined benefit pension — shelter up to $275,000/yr tax-free`);
  }

  // ── Solo 401(k) ─────────────────────────────────────────────────────────
  if (goals.includes("retirement") && profit > 20_000) {
    const k401 = Math.round(Math.min(profit * 0.25, 16_500));
    count++;
    savingsMin += Math.round(k401 * 0.3);
    savingsMax += k401;
    highlights.push(`Solo 401(k) + backdoor Roth — maximize retirement tax shelter`);
  }

  // ── C-Corp flat rate + fringe benefits ──────────────────────────────────
  if (entity === "c_corp" && revenue > 0) {
    const corpSavings = Math.round(Math.min(revenue * 0.06, 55_000));
    count++;
    savingsMin += Math.round(corpSavings * 0.3);
    savingsMax += corpSavings;
    highlights.push(`C-Corp 21% flat rate + deductible fringe benefit programs`);
  }

  // ── Hire children ───────────────────────────────────────────────────────
  if (childrenStr !== "0") {
    const childCount =
      childrenStr === "4_plus" ? 4 : parseInt(childrenStr, 10);
    const childSavings = Math.round(childCount * 14_600 * 0.28);
    count++;
    savingsMin += Math.round(childSavings * 0.6);
    savingsMax += childSavings;
    highlights.push(
      `Hire your children — up to $${childSavings.toLocaleString()}/yr in tax-free wages`
    );
  }

  // ── Asset protection structures ─────────────────────────────────────────
  if (["500k_1m", "1m_5m", "over_5m"].includes(assets)) {
    count += 2;
    highlights.push(`Asset protection fortress — holding company + DAPT structure`);
  }

  // ── QSBS exclusion ──────────────────────────────────────────────────────
  if (answers.has_qsbs === true) {
    count++;
    highlights.push(`QSBS Section 1202 — up to $10M of exit gain completely tax-free`);
  }

  // ── Estate planning ─────────────────────────────────────────────────────
  if (goals.includes("estate_planning")) {
    count += 2;
    highlights.push(`Irrevocable trust strategies — minimize estate + gift taxes`);
  }

  // ── Exit optimization ────────────────────────────────────────────────────
  if (
    goals.includes("exit_strategy") &&
    ["growth", "established", "mature"].includes(stage)
  ) {
    count++;
    highlights.push(`Exit optimization — ESOP, installment sale, or QSBS structure`);
  }

  // ── Spousal strategies ───────────────────────────────────────────────────
  if (married && profit > 80_000) {
    count++;
    savingsMin += 2_000;
    savingsMax += 8_000;
    highlights.push(`Spousal IRA contribution stacking + income splitting strategies`);
  }

  // ── Baseline estimates if no profit entered ──────────────────────────────
  if (savingsMin === 0 && stage !== "idea") {
    savingsMin = 5_000;
    savingsMax = 30_000;
  }

  return {
    strategyCount: Math.min(count, 18),
    annualSavingsMin: savingsMin,
    annualSavingsMax: savingsMax,
    highlights: highlights.slice(0, 5),
  };
}

// ─── Answer → Database Mapping ────────────────────────────────────────────────
// Maps adaptive wizard answers to the camelCase format expected by
// /api/questionnaire/save and /api/questionnaire/submit

const ASSET_RANGE_MIDPOINTS: Record<string, number> = {
  under_100k: 50_000,
  "100k_500k": 300_000,
  "500k_1m": 750_000,
  "1m_5m": 3_000_000,
  over_5m: 7_500_000,
};

const CHILDREN_TO_NUMBER: Record<string, number> = {
  "0": 0,
  "1": 1,
  "2": 2,
  "3": 3,
  "4_plus": 4,
};

const EXIT_TIMELINE_TO_YEARS: Record<string, number | null> = {
  "1_2_years": 1,
  "3_5_years": 3,
  "5_10_years": 7,
  over_10_years: 15,
  no_plan: null,
};

export function mapAnswersToDb(answers: Answers): Record<string, unknown> {
  const goals = (answers.goals as string[]) ?? [];
  const assetsStr = answers.total_assets as string;
  const childrenStr = answers.children_count as string;
  const exitStr = answers.exit_timeline as string;

  return {
    businessStage: answers.business_stage,
    entityTypeCurrent: answers.entity_type,
    stateOfFormation: answers.state,
    statesOperating: answers.state ? [answers.state] : undefined,
    annualRevenue: answers.annual_revenue
      ? Number(answers.annual_revenue)
      : undefined,
    annualProfit: answers.annual_profit
      ? Number(answers.annual_profit)
      : undefined,
    w2WagesPaid: answers.w2_wages ? Number(answers.w2_wages) : undefined,
    totalNetWorth: assetsStr ? ASSET_RANGE_MIDPOINTS[assetsStr] : undefined,
    realEstateValue: answers.real_estate
      ? Number(answers.real_estate)
      : undefined,
    hasQsbsStock:
      answers.has_qsbs !== undefined ? (answers.has_qsbs as boolean) : undefined,
    marriedFilingJointly:
      answers.married !== undefined ? (answers.married as boolean) : undefined,
    childrenCount: childrenStr ? CHILDREN_TO_NUMBER[childrenStr] : undefined,
    goalMinimizeTaxes: goals.includes("minimize_taxes"),
    goalAssetProtection: goals.includes("asset_protection"),
    goalEstatePlanning: goals.includes("estate_planning"),
    goalExitStrategy: goals.includes("exit_strategy"),
    goalRetirementPlanning: goals.includes("retirement"),
    goalHireFamily: goals.includes("hire_family"),
    planningHorizon: answers.planning_horizon,
    exitTimelineYears:
      exitStr && EXIT_TIMELINE_TO_YEARS[exitStr] !== undefined
        ? EXIT_TIMELINE_TO_YEARS[exitStr]
        : undefined,
  };
}

// ─── Display Helpers (used by SummaryPage) ────────────────────────────────────

export const STAGE_LABELS: Record<string, string> = {
  idea: "Pre-revenue / idea stage",
  startup: "Startup (< $250K revenue)",
  growth: "Growth ($250K – $1M)",
  established: "Established ($1M – $10M)",
  mature: "Mature ($10M+)",
};

export const ENTITY_LABELS: Record<string, string> = {
  sole_prop: "Sole Proprietor / DBA",
  single_llc: "Single-Member LLC",
  multi_llc: "Multi-Member LLC",
  s_corp: "S-Corporation",
  c_corp: "C-Corporation",
  partnership: "Partnership / LP",
  not_formed: "Not formed yet",
};

export const ASSET_LABELS: Record<string, string> = {
  under_100k: "Under $100,000",
  "100k_500k": "$100K – $500K",
  "500k_1m": "$500K – $1M",
  "1m_5m": "$1M – $5M",
  over_5m: "Over $5M",
};

export const HORIZON_LABELS: Record<string, string> = {
  immediate: "This tax year only",
  "1_year": "1–2 years",
  "3_year": "3–5 years",
  "5_plus": "5+ years",
};

export const RISK_LABELS: Record<string, string> = {
  conservative: "Conservative 🟢",
  moderate: "Moderate 🟡",
  aggressive: "Aggressive 🔴",
};

export const EXIT_LABELS: Record<string, string> = {
  "1_2_years": "1–2 years",
  "3_5_years": "3–5 years",
  "5_10_years": "5–10 years",
  over_10_years: "10+ years",
  no_plan: "No specific timeline",
};

export const COUNTRY_LABELS: Record<string, string> = {
  us: "United States 🇺🇸",
  ca: "Canada 🇨🇦",
  uk: "United Kingdom 🇬🇧",
  au: "Australia 🇦🇺",
  other: "Other",
};

export const GOAL_LABELS: Record<string, string> = {
  minimize_taxes: "Minimize taxes now 📉",
  asset_protection: "Asset protection 🛡️",
  estate_planning: "Estate & legacy planning 🏛️",
  exit_strategy: "Exit / sell business 🚪",
  retirement: "Build retirement wealth 🌅",
  hire_family: "Employ family members 👨‍👩‍👧",
};
