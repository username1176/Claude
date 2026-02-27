// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Strategy Catalog
// Static registry of all 79 tax strategies the agents can recommend.
// Each entry carries the data needed for quick applicability filtering and
// savings estimation; the Optimizer agent fills in profile-specific numbers.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  StrategyCategory,
  Priority,
  Complexity,
  IrsScrutiny,
  NormalizedProfile,
  StrategyApplicabilityResult,
  StrategyApplicability,
} from "./types";

// ─── Catalog Entry ────────────────────────────────────────────────────────────

export interface StrategyCatalogEntry {
  id: string;
  name: string;
  category: StrategyCategory;
  defaultPriority: Priority;
  complexity: Complexity;
  irsScrutiny: IrsScrutiny;
  requiresAttorney: boolean;
  requiresCpa: boolean;
  ircSections: string[];
  obbaSections: string[];
  minProfitThreshold: number;   // strategy not applicable below this annual profit
  minNetWorthThreshold: number; // strategy not applicable below this total net worth
  urgency: "immediate" | "this_year" | "multi_year" | "when_ready";
  /** Returns an applicability verdict plus a rough savings ballpark */
  apply: (p: NormalizedProfile) => { applicability: StrategyApplicability; reasoning: string; ballpark: number };
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

// ─── Catalog ──────────────────────────────────────────────────────────────────

export const STRATEGIES: StrategyCatalogEntry[] = [

  // ── ENTITY STRUCTURE ────────────────────────────────────────────────────────

  {
    id: "s_corp_election",
    name: "S-Corporation Election",
    category: "entity_structure",
    defaultPriority: "critical",
    complexity: "medium",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["1361", "1362", "1366", "1402"],
    obbaSections: [],
    minProfitThreshold: 40_000,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const ok = ["sole_prop", "single_llc", "multi_llc"].includes(p.entityType) && p.annualProfit >= 40_000;
      if (!ok) return { applicability: "not_applicable", reasoning: "Already corporate or profit too low for meaningful SE savings.", ballpark: 0 };
      const salary = clamp(p.annualProfit * 0.45, 30_000, 175_000);
      const distribution = p.annualProfit - salary;
      const seTaxSaved = distribution * 0.9235 * 0.153;
      const ballpark = Math.max(0, seTaxSaved - 2_500); // net of S-Corp admin costs
      const applicability: StrategyApplicability = p.scorpOpportunity ? "applies" : "maybe";
      return { applicability, reasoning: `S-Corp election saves SE tax on ~$${Math.round(distribution / 1000)}K distributions. Est. net savings: $${Math.round(ballpark / 1000)}K/yr.`, ballpark };
    },
  },

  {
    id: "c_corp_accumulation",
    name: "C-Corporation Income Accumulation",
    category: "entity_structure",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["11", "531", "541", "1202"],
    obbaSections: [],
    minProfitThreshold: 300_000,
    minNetWorthThreshold: 0,
    urgency: "multi_year",
    apply(p) {
      if (p.annualProfit < 300_000 || p.entityType === "c_corp") return { applicability: "not_applicable", reasoning: "Best for high earners not already in C-Corp.", ballpark: 0 };
      const corpTax = p.annualProfit * 0.21;
      const currentTax = p.annualProfit * p.estimatedMarginalRate;
      const ballpark = Math.max(0, currentTax - corpTax - 5_000);
      return { applicability: "maybe", reasoning: `21% flat C-Corp rate vs. ${Math.round(p.estimatedMarginalRate * 100)}% individual rate — saves ~$${Math.round(ballpark / 1000)}K if profits retained.`, ballpark };
    },
  },

  {
    id: "llc_series",
    name: "Series LLC Asset Segregation",
    category: "entity_structure",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: false,
    ircSections: [],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 500_000,
    urgency: "when_ready",
    apply(p) {
      const ok = p.realEstateInvestor || p.ultraHighNetWorth;
      return ok
        ? { applicability: "maybe", reasoning: "Series LLC separates liability per asset. Tax-neutral but powerful asset protection.", ballpark: 0 }
        : { applicability: "not_applicable", reasoning: "Most useful for multiple real estate assets or very high net worth.", ballpark: 0 };
    },
  },

  {
    id: "holding_company",
    name: "Holding Company Structure",
    category: "entity_structure",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["243", "1504"],
    obbaSections: [],
    minProfitThreshold: 200_000,
    minNetWorthThreshold: 1_000_000,
    urgency: "multi_year",
    apply(p) {
      if (p.annualProfit < 200_000 || p.totalNetWorth < 1_000_000) return { applicability: "not_applicable", reasoning: "Adds complexity without commensurate benefit at this size.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Holding company enables dividend-received deduction and asset protection across business lines.", ballpark: p.annualProfit * 0.03 };
    },
  },

  {
    id: "professional_corp",
    name: "Professional Corporation Election",
    category: "entity_structure",
    defaultPriority: "low",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["269A", "448"],
    obbaSections: [],
    minProfitThreshold: 100_000,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      return { applicability: "maybe", reasoning: "For licensed professionals — enables liability segregation and fringe benefits.", ballpark: p.annualProfit * 0.02 };
    },
  },

  // ── RETIREMENT ───────────────────────────────────────────────────────────────

  {
    id: "solo_401k",
    name: "Solo 401(k) Maximization",
    category: "retirement",
    defaultPriority: "high",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["401", "402", "415"],
    obbaSections: [],
    minProfitThreshold: 20_000,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      if (!["sole_prop", "single_llc", "s_corp"].includes(p.entityType)) return { applicability: "not_applicable", reasoning: "Requires self-employed income.", ballpark: 0 };
      const maxContrib = Math.min(70_000, p.annualProfit * 0.25 + 23_500);
      const ballpark = maxContrib * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `Max $${Math.round(maxContrib / 1000)}K contribution deductible, saving ~$${Math.round(ballpark / 1000)}K in taxes.`, ballpark };
    },
  },

  {
    id: "sep_ira",
    name: "SEP-IRA Contribution",
    category: "retirement",
    defaultPriority: "high",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["408", "415"],
    obbaSections: [],
    minProfitThreshold: 15_000,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const maxContrib = Math.min(70_000, p.annualProfit * 0.25);
      const ballpark = maxContrib * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `25% of comp, up to $70K deductible — saves ~$${Math.round(ballpark / 1000)}K.`, ballpark };
    },
  },

  {
    id: "defined_benefit_plan",
    name: "Defined Benefit / Cash Balance Plan",
    category: "retirement",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["412", "415", "404"],
    obbaSections: [],
    minProfitThreshold: 150_000,
    minNetWorthThreshold: 0,
    urgency: "this_year",
    apply(p) {
      if (p.annualProfit < 150_000) return { applicability: "not_applicable", reasoning: "DB/CB plans require consistent high income to sustain.", ballpark: 0 };
      const maxContrib = Math.min(275_000, p.annualProfit * 0.6);
      const ballpark = maxContrib * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `DB plan allows up to $${Math.round(maxContrib / 1000)}K deduction — saves ~$${Math.round(ballpark / 1000)}K/yr for 10–15 years.`, ballpark };
    },
  },

  {
    id: "roth_conversion",
    name: "Roth Conversion Ladder",
    category: "retirement",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["408A", "72"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 100_000,
    urgency: "multi_year",
    apply(p) {
      if (p.retirementAccounts < 100_000) return { applicability: "not_applicable", reasoning: "Insufficient retirement balance to make conversions meaningful.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Convert traditional IRA to Roth in low-income years to lock in low rates.", ballpark: p.retirementAccounts * 0.02 };
    },
  },

  {
    id: "backdoor_roth",
    name: "Backdoor Roth IRA",
    category: "retirement",
    defaultPriority: "medium",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["408A", "408"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "this_year",
    apply(p) {
      if (!p.highIncome) return { applicability: "not_applicable", reasoning: "Only meaningful above Roth income phase-out ($150K+ single / $236K+ MFJ).", ballpark: 0 };
      const ballpark = 7_000 * p.estimatedMarginalRate * 20; // lifetime tax-free growth estimate
      return { applicability: "applies", reasoning: "Non-deductible IRA → immediate Roth conversion bypasses income limits.", ballpark };
    },
  },

  {
    id: "hsa_maximization",
    name: "Health Savings Account Maximization",
    category: "retirement",
    defaultPriority: "medium",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["223"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const contrib = p.isMarried ? 8_300 : 4_150;
      const ballpark = contrib * (p.estimatedMarginalRate + 0.0765);
      return { applicability: "applies", reasoning: `Triple tax-free HSA: $${contrib.toLocaleString()} deduction + FICA savings ≈ $${Math.round(ballpark / 100) * 100}.`, ballpark };
    },
  },

  {
    id: "simple_ira",
    name: "SIMPLE IRA for Small Business",
    category: "retirement",
    defaultPriority: "low",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["408", "408p"],
    obbaSections: [],
    minProfitThreshold: 30_000,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      if (p.w2WagesPaid === 0) return { applicability: "not_applicable", reasoning: "SIMPLE IRA best when you have W-2 employees.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Employee benefit that also reduces payroll tax base.", ballpark: 16_000 * p.estimatedMarginalRate };
    },
  },

  // ── DEPRECIATION ─────────────────────────────────────────────────────────────

  {
    id: "bonus_depreciation",
    name: "100% Bonus Depreciation (IRC §168k)",
    category: "depreciation",
    defaultPriority: "high",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["168"],
    obbaSections: ["Section 168(k) OBBBA permanent extension"],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const assets = p.annualProfit * 0.3; // rough proxy if no direct data
      if (assets < 5_000) return { applicability: "not_applicable", reasoning: "No qualifying property purchases apparent.", ballpark: 0 };
      const ballpark = assets * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `OBBBA made 100% bonus permanent. Deduct full cost of qualifying property year 1 — saves ~$${Math.round(ballpark / 1000)}K.`, ballpark };
    },
  },

  {
    id: "section_179",
    name: "Section 179 Expensing",
    category: "depreciation",
    defaultPriority: "high",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["179"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      return { applicability: "applies", reasoning: "Up to $1.22M of business property expensed immediately (2025 limit). Always check before year-end.", ballpark: p.annualProfit * 0.05 * p.estimatedMarginalRate };
    },
  },

  {
    id: "cost_segregation",
    name: "Cost Segregation Study",
    category: "depreciation",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["168", "1250"],
    obbaSections: [],
    minProfitThreshold: 50_000,
    minNetWorthThreshold: 200_000,
    urgency: "this_year",
    apply(p) {
      if (!p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Requires commercial real estate ownership.", ballpark: 0 };
      const ballpark = p.realEstateValue * 0.15 * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `Cost seg reclassifies ~15–40% of building cost to 5/15-yr property. Est. first-year deduction boost: ~$${Math.round(ballpark / 1000)}K.`, ballpark };
    },
  },

  {
    id: "qualified_improvement_property",
    name: "Qualified Improvement Property (15-year)",
    category: "depreciation",
    defaultPriority: "medium",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["168"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "this_year",
    apply(p) {
      if (!p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Requires interior improvements to nonresidential property.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "QIP (interior non-structural improvements) = 15-yr life + bonus eligible.", ballpark: p.realEstateValue * 0.05 * p.estimatedMarginalRate };
    },
  },

  {
    id: "listed_property",
    name: "Luxury Auto / Listed Property Planning",
    category: "depreciation",
    defaultPriority: "low",
    complexity: "simple",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["168", "280F"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      return { applicability: "maybe", reasoning: "Heavy SUVs (>6,000 lbs GVWR) qualify for §179 up to $30,500 and full bonus depreciation.", ballpark: p.annualProfit * 0.03 * p.estimatedMarginalRate };
    },
  },

  // ── DEDUCTIONS ────────────────────────────────────────────────────────────────

  {
    id: "qbi_deduction",
    name: "Qualified Business Income (QBI) Deduction — IRC §199A",
    category: "deductions",
    defaultPriority: "critical",
    complexity: "medium",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["199A"],
    obbaSections: ["OBBBA §199A permanent extension + 23% rate for 2025+"],
    minProfitThreshold: 10_000,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      if (!p.qbiEligible) return { applicability: "not_applicable", reasoning: "C-Corps and certain SSTBs above threshold are excluded.", ballpark: 0 };
      const ballpark = p.qbiDeductionAmount * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `QBI deduction = $${Math.round(p.qbiDeductionAmount / 1000)}K (20% × QBI), saving ~$${Math.round(ballpark / 1000)}K. OBBBA made this permanent.`, ballpark };
    },
  },

  {
    id: "home_office",
    name: "Home Office Deduction",
    category: "deductions",
    defaultPriority: "medium",
    complexity: "simple",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["280A"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const ballpark = 2_500 * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: "Exclusive-use home office: ~$2–5K deduction for most taxpayers.", ballpark };
    },
  },

  {
    id: "accountable_plan",
    name: "Accountable Plan for Employee Expenses",
    category: "deductions",
    defaultPriority: "high",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["62", "132"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      if (p.entityType === "sole_prop") return { applicability: "not_applicable", reasoning: "Sole proprietors can deduct directly on Schedule C.", ballpark: 0 };
      return { applicability: "applies", reasoning: "Reimburse owner/employees tax-free for biz expenses via documented accountable plan.", ballpark: p.annualProfit * 0.04 * p.estimatedMarginalRate };
    },
  },

  {
    id: "augusta_rule",
    name: 'Augusta Rule — IRC §280A(g) Home Rental',
    category: "deductions",
    defaultPriority: "medium",
    complexity: "simple",
    irsScrutiny: "high",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["280A"],
    obbaSections: [],
    minProfitThreshold: 40_000,
    minNetWorthThreshold: 0,
    urgency: "this_year",
    apply(p) {
      if (p.entityType === "sole_prop") return { applicability: "not_applicable", reasoning: "Must have separate C/S-Corp to rent home to.", ballpark: 0 };
      const ballpark = 14 * 1_200 * p.estimatedMarginalRate; // 14 days × daily rate
      return { applicability: "maybe", reasoning: "Rent personal residence to your corporation ≤14 days/yr tax-free to you; corp deducts expense.", ballpark };
    },
  },

  {
    id: "business_meals_travel",
    name: "Business Meals & Travel Deductions",
    category: "deductions",
    defaultPriority: "low",
    complexity: "simple",
    irsScrutiny: "high",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["162", "274"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const ballpark = p.annualProfit * 0.03 * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: "50% meals, 100% travel if ordinary/necessary. Requires documentation.", ballpark };
    },
  },

  {
    id: "health_insurance_deduction",
    name: "Self-Employed Health Insurance Deduction",
    category: "deductions",
    defaultPriority: "high",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["162", "106"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const premium = p.isMarried ? 28_000 : 15_000;
      const ballpark = premium * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `100% health/dental/vision premium deductible above-the-line (~$${Math.round(premium / 1000)}K for your situation).`, ballpark };
    },
  },

  {
    id: "cell_phone_deduction",
    name: "Business Cell Phone & Technology",
    category: "deductions",
    defaultPriority: "low",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["162", "274"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      return { applicability: "applies", reasoning: "Business-use % of phone, internet, and equipment fully deductible.", ballpark: 3_000 * p.estimatedMarginalRate };
    },
  },

  {
    id: "education_deduction",
    name: "Business Education & Professional Development",
    category: "deductions",
    defaultPriority: "low",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["162", "127"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      return { applicability: "applies", reasoning: "Courses, conferences, books deductible if maintaining/improving skills in current profession.", ballpark: 5_000 * p.estimatedMarginalRate };
    },
  },

  {
    id: "vehicle_deduction",
    name: "Business Vehicle Deduction Strategy",
    category: "deductions",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "high",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["162", "168", "179", "280F"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "this_year",
    apply(p) {
      const ballpark = p.annualProfit * 0.05 * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: "Standard mileage (67¢/mile) vs. actual method. Heavy SUVs add bonus depreciation opportunity.", ballpark };
    },
  },

  {
    id: "qo_zone",
    name: "Opportunity Zone Investment",
    category: "opportunity_zone",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["1400Z-2"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 500_000,
    urgency: "when_ready",
    apply(p) {
      if (p.investmentPortfolio < 100_000) return { applicability: "not_applicable", reasoning: "Requires capital gains to defer.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Defer + reduce capital gains by investing in Qualified Opportunity Funds. 10-yr hold = no tax on appreciation.", ballpark: p.investmentPortfolio * 0.15 * 0.2 };
    },
  },

  // ── REAL ESTATE ──────────────────────────────────────────────────────────────

  {
    id: "1031_exchange",
    name: "1031 Like-Kind Exchange",
    category: "real_estate",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["1031"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 200_000,
    urgency: "when_ready",
    apply(p) {
      if (!p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Only for investment/business real estate, not primary residence.", ballpark: 0 };
      const ballpark = p.realEstateValue * 0.2 * 0.15; // rough cap gains deferred
      return { applicability: "applies", reasoning: `Exchange investment property to defer capital gains. On $${Math.round(p.realEstateValue / 1000)}K real estate, could defer ~$${Math.round(ballpark / 1000)}K in gains.`, ballpark };
    },
  },

  {
    id: "real_estate_professional",
    name: "Real Estate Professional Status (REPS)",
    category: "real_estate",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "very_high",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["469", "469(c)(7)"],
    obbaSections: [],
    minProfitThreshold: 100_000,
    minNetWorthThreshold: 200_000,
    urgency: "this_year",
    apply(p) {
      if (!p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Requires materially participating in real estate as primary activity (>750 hrs/yr).", ballpark: 0 };
      const ballpark = p.realEstateValue * 0.1 * p.estimatedMarginalRate;
      return { applicability: "maybe", reasoning: "REPS unlocks unlimited passive RE losses against ordinary income. High scrutiny — must track hours meticulously.", ballpark };
    },
  },

  {
    id: "short_term_rental_loophole",
    name: "Short-Term Rental (STR) Loophole",
    category: "real_estate",
    defaultPriority: "high",
    complexity: "medium",
    irsScrutiny: "high",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["469", "469(c)", "168"],
    obbaSections: [],
    minProfitThreshold: 100_000,
    minNetWorthThreshold: 200_000,
    urgency: "this_year",
    apply(p) {
      if (!p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Requires STR property with avg stay ≤7 days.", ballpark: 0 };
      const ballpark = p.realEstateValue * 0.25 * p.estimatedMarginalRate;
      return { applicability: "maybe", reasoning: "STRs with avg stay ≤7 days are non-passive if you materially participate — cost seg losses offset W-2/business income.", ballpark };
    },
  },

  {
    id: "depreciation_recapture_planning",
    name: "Depreciation Recapture Planning",
    category: "real_estate",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["1245", "1250", "1231"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 200_000,
    urgency: "multi_year",
    apply(p) {
      if (!p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Only relevant for RE asset sales.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Plan property dispositions to maximize §1231 gains and minimize §1250 recapture.", ballpark: p.realEstateValue * 0.02 };
    },
  },

  {
    id: "installment_sale",
    name: "Installment Sale Method",
    category: "real_estate",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["453"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 500_000,
    urgency: "when_ready",
    apply(p) {
      if (!p.exitCandidate && !p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Most relevant when planning to sell assets or real estate.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Spread asset sale gains over multiple years to stay in lower brackets — defers gain recognition.", ballpark: p.realEstateValue * 0.03 };
    },
  },

  // ── FAMILY EMPLOYMENT ────────────────────────────────────────────────────────

  {
    id: "hire_children",
    name: "Hire Children / Family Employment",
    category: "family_employment",
    defaultPriority: "high",
    complexity: "simple",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["3121", "162"],
    obbaSections: [],
    minProfitThreshold: 30_000,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      if (p.children === 0) return { applicability: "not_applicable", reasoning: "No children to employ.", ballpark: 0 };
      const kidsToHire = Math.min(p.children, 3);
      const wages = kidsToHire * 14_600; // up to standard deduction
      const ballpark = wages * (p.estimatedMarginalRate + p.effectiveSERate);
      return { applicability: "applies", reasoning: `Hire ${kidsToHire} child(ren) at ≤$14,600/yr (standard deduction): saves ~$${Math.round(ballpark / 1000)}K in income + SE tax.`, ballpark };
    },
  },

  {
    id: "hire_spouse",
    name: "Employ Spouse for Benefits",
    category: "family_employment",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["162", "105", "106"],
    obbaSections: [],
    minProfitThreshold: 80_000,
    minNetWorthThreshold: 0,
    urgency: "this_year",
    apply(p) {
      if (!p.isMarried) return { applicability: "not_applicable", reasoning: "Only applicable if married.", ballpark: 0 };
      if (p.spouseIncome > 50_000) return { applicability: "maybe", reasoning: "Spouse already has separate income; benefits strategy may still add HRA value.", ballpark: 5_000 * p.estimatedMarginalRate };
      return { applicability: "applies", reasoning: "Employ spouse to provide health/HRA benefits, deductible as business expense.", ballpark: 28_000 * p.estimatedMarginalRate };
    },
  },

  {
    id: "family_limited_partnership",
    name: "Family Limited Partnership (FLP)",
    category: "family_employment",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "high",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["704", "2036"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 2_000_000,
    urgency: "multi_year",
    apply(p) {
      if (p.totalNetWorth < 2_000_000) return { applicability: "not_applicable", reasoning: "FLP overhead justified only for significant asset transfer goals.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "FLP allows valuation discounts (20–40%) on gifted limited partnership interests — estate + income tax shifting.", ballpark: p.totalNetWorth * 0.01 };
    },
  },

  // ── ASSET PROTECTION ─────────────────────────────────────────────────────────

  {
    id: "dapt",
    name: "Domestic Asset Protection Trust (DAPT)",
    category: "asset_protection",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: [],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 1_000_000,
    urgency: "multi_year",
    apply(p) {
      if (p.totalNetWorth < 1_000_000) return { applicability: "not_applicable", reasoning: "DAPT setup costs justified only at $1M+ in exposed assets.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Irrevocable self-settled trust (WY/NV/SD) shields assets from future creditors. Not a tax play — pure protection.", ballpark: 0 };
    },
  },

  {
    id: "charging_order_protection",
    name: "LLC Charging Order Protection",
    category: "asset_protection",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: false,
    ircSections: [],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 200_000,
    urgency: "when_ready",
    apply(p) {
      return { applicability: "maybe", reasoning: "Wyoming/Delaware LLC with single-member charging-order-only remedy limits creditor access.", ballpark: 0 };
    },
  },

  {
    id: "captive_insurance",
    name: "Captive Insurance Company",
    category: "captive_insurance",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "very_high",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["831", "162"],
    obbaSections: [],
    minProfitThreshold: 500_000,
    minNetWorthThreshold: 500_000,
    urgency: "multi_year",
    apply(p) {
      if (!p.captiveCandidate) return { applicability: "not_applicable", reasoning: "Captive insurance best for profits >$500K with genuine insurable business risks.", ballpark: 0 };
      const premium = Math.min(p.annualProfit * 0.15, 2_400_000);
      const ballpark = premium * p.estimatedMarginalRate;
      return { applicability: "maybe", reasoning: `§831(b) micro-captive: up to $2.8M premium deductible. Est. savings: ~$${Math.round(ballpark / 1000)}K. IRS listed — requires bona fide risk transfer.`, ballpark };
    },
  },

  // ── ESTATE PLANNING ──────────────────────────────────────────────────────────

  {
    id: "annual_gift_exclusion",
    name: "Annual Gift Tax Exclusion Strategy",
    category: "estate_planning",
    defaultPriority: "high",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["2503", "2505"],
    obbaSections: ["OBBBA estate tax threshold $15M per person"],
    minProfitThreshold: 0,
    minNetWorthThreshold: 500_000,
    urgency: "immediate",
    apply(p) {
      if (!p.estatePlanningUrgent) return { applicability: "not_applicable", reasoning: "Most impactful above $3M net worth.", ballpark: 0 };
      const giftable = (p.isMarried ? 36_000 : 18_000) * (p.children + 2);
      return { applicability: "applies", reasoning: `Gift $${Math.round(giftable / 1000)}K/yr ($18K/recipient, $36K if married) tax-free. Removes future appreciation from estate.`, ballpark: giftable * 0.4 };
    },
  },

  {
    id: "irrevocable_life_insurance_trust",
    name: "Irrevocable Life Insurance Trust (ILIT)",
    category: "estate_planning",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["2042", "2035"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 3_000_000,
    urgency: "multi_year",
    apply(p) {
      if (p.totalNetWorth < 3_000_000) return { applicability: "not_applicable", reasoning: "Estate planning tools most impactful above OBBBA $15M threshold when combined with FLP/trusts.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "ILIT keeps life insurance proceeds out of taxable estate — critical for high-NW families.", ballpark: p.totalNetWorth * 0.005 };
    },
  },

  {
    id: "grat",
    name: "Grantor Retained Annuity Trust (GRAT)",
    category: "estate_planning",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["2702"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 5_000_000,
    urgency: "multi_year",
    apply(p) {
      if (!p.ultraHighNetWorth) return { applicability: "not_applicable", reasoning: "GRATs are estate freeze techniques for very high NW.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Zero-out GRAT transfers appreciation above §7520 hurdle rate to heirs gift-tax free.", ballpark: p.totalNetWorth * 0.02 };
    },
  },

  {
    id: "slat",
    name: "Spousal Lifetime Access Trust (SLAT)",
    category: "estate_planning",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["2511", "2503"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 3_000_000,
    urgency: "multi_year",
    apply(p) {
      if (!p.isMarried || p.totalNetWorth < 3_000_000) return { applicability: "not_applicable", reasoning: "Requires marriage and significant estate.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "SLAT removes assets from taxable estate while spouse retains beneficial access. Use $13.99M lifetime exemption before it drops (if OBBBA not extended).", ballpark: p.totalNetWorth * 0.015 };
    },
  },

  {
    id: "charitable_remainder_trust",
    name: "Charitable Remainder Trust (CRT)",
    category: "estate_planning",
    defaultPriority: "low",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["664", "170"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 500_000,
    urgency: "multi_year",
    apply(p) {
      if (!p.exitCandidate && !p.estatePlanningUrgent) return { applicability: "not_applicable", reasoning: "Best for appreciated asset exit + charitable intent.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "CRT avoids immediate capital gains on sale, provides income stream, charitable deduction.", ballpark: p.investmentPortfolio * 0.05 };
    },
  },

  {
    id: "donor_advised_fund",
    name: "Donor Advised Fund (DAF) Bunching",
    category: "estate_planning",
    defaultPriority: "medium",
    complexity: "simple",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["170"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "this_year",
    apply(p) {
      if (!p.highIncome) return { applicability: "not_applicable", reasoning: "Bunching charitable deductions most valuable above standard deduction threshold.", ballpark: 0 };
      return { applicability: "applies", reasoning: "Bunch 3–5 years of charitable gifts into DAF for immediate full deduction, distribute to charities over time.", ballpark: p.annualProfit * 0.05 * p.estimatedMarginalRate };
    },
  },

  // ── QSBS ──────────────────────────────────────────────────────────────────────

  {
    id: "qsbs_exclusion",
    name: "QSBS Gain Exclusion — IRC §1202",
    category: "qsbs",
    defaultPriority: "critical",
    complexity: "medium",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["1202"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      if (!p.hasQsbs) return { applicability: "not_applicable", reasoning: "No QSBS stock indicated.", ballpark: 0 };
      return { applicability: "applies", reasoning: "100% federal capital gains exclusion on up to $10M ($20M MFJ) from qualified C-Corp stock held 5+ years.", ballpark: p.totalNetWorth * 0.15 * 0.238 };
    },
  },

  {
    id: "qsbs_stacking",
    name: "QSBS Stacking via Entity Structuring",
    category: "qsbs",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["1202", "1045"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      if (!p.hasQsbs || p.totalNetWorth < 1_000_000) return { applicability: "not_applicable", reasoning: "Stacking applicable for high-value QSBS positions.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Multiple trusts/entities each hold separate $10M exclusion — multiplies §1202 benefit.", ballpark: p.totalNetWorth * 0.08 };
    },
  },

  {
    id: "qsbs_rollover",
    name: "QSBS §1045 Rollover",
    category: "qsbs",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["1045"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      if (!p.hasQsbs) return { applicability: "not_applicable", reasoning: "No QSBS stock indicated.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Roll QSBS gain into new QSBS within 60 days to reset 5-year holding clock without tax.", ballpark: 0 };
    },
  },

  // ── EXIT ─────────────────────────────────────────────────────────────────────

  {
    id: "earnout_structuring",
    name: "Earnout / Installment Sale Exit Structuring",
    category: "exit",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["453", "1060"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 1_000_000,
    urgency: "when_ready",
    apply(p) {
      if (!p.exitCandidate) return { applicability: "not_applicable", reasoning: "No exit goal indicated.", ballpark: 0 };
      return { applicability: "applies", reasoning: "Structure sale with earnouts to spread gain recognition — may keep seller in lower bracket each year.", ballpark: p.annualProfit * 2 * 0.1 };
    },
  },

  {
    id: "asset_vs_stock_sale",
    name: "Asset Sale vs. Stock Sale Tax Planning",
    category: "exit",
    defaultPriority: "critical",
    complexity: "complex",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["1001", "338", "1060"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 500_000,
    urgency: "when_ready",
    apply(p) {
      if (!p.exitCandidate) return { applicability: "not_applicable", reasoning: "No exit goal indicated.", ballpark: 0 };
      return { applicability: "applies", reasoning: "Stock sale = capital gains; asset sale = mix of ordinary + capital. Optimize allocation to minimize tax.", ballpark: p.annualProfit * 3 * 0.05 };
    },
  },

  {
    id: "employee_ownership_plan",
    name: "ESOP / Employee Ownership Sale",
    category: "exit",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: ["1042", "4975"],
    obbaSections: [],
    minProfitThreshold: 500_000,
    minNetWorthThreshold: 0,
    urgency: "multi_year",
    apply(p) {
      if (!p.exitCandidate || p.annualRevenue < 1_000_000) return { applicability: "not_applicable", reasoning: "ESOP feasible for established businesses ($1M+ revenue) with exit intent.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "C-Corp ESOP sale: §1042 rollover defers 100% of capital gains. S-Corp ESOP: distributions tax-free to the extent trust-owned.", ballpark: p.annualProfit * 4 * 0.2 };
    },
  },

  // ── CREDITS ───────────────────────────────────────────────────────────────────

  {
    id: "r_and_d_credit",
    name: "R&D Tax Credit — IRC §41",
    category: "credits",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["41", "174"],
    obbaSections: ["OBBBA §174 R&D expensing restoration"],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      return { applicability: "maybe", reasoning: "§41 R&D credit = 20% of qualifying expenses above base. OBBBA restored immediate §174 expensing. Even startups can apply credit against payroll taxes.", ballpark: p.annualRevenue * 0.01 };
    },
  },

  {
    id: "work_opportunity_credit",
    name: "Work Opportunity Tax Credit (WOTC)",
    category: "credits",
    defaultPriority: "low",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: false,
    ircSections: ["51"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      if (p.w2WagesPaid === 0) return { applicability: "not_applicable", reasoning: "Requires W-2 employees from target groups.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "Up to $9,600 credit per qualifying new hire (veterans, ex-felons, long-term unemployed, etc.).", ballpark: p.w2WagesPaid * 0.02 };
    },
  },

  {
    id: "emp_retention_credit",
    name: "Energy-Efficiency / Green Building Credits",
    category: "credits",
    defaultPriority: "low",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["48", "45L", "179D"],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      if (!p.realEstateInvestor) return { applicability: "not_applicable", reasoning: "Primarily for RE owners and commercial builders.", ballpark: 0 };
      return { applicability: "maybe", reasoning: "§179D commercial building deduction up to $5/sqft; §45L new home credit; §48 ITC for solar.", ballpark: p.realEstateValue * 0.02 };
    },
  },

  // ── STATE TAX ─────────────────────────────────────────────────────────────────

  {
    id: "state_residency_planning",
    name: "State Income Tax Residency Planning",
    category: "state_tax",
    defaultPriority: "high",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: [],
    obbaSections: [],
    minProfitThreshold: 200_000,
    minNetWorthThreshold: 0,
    urgency: "multi_year",
    apply(p) {
      const highTaxStates = new Set(["CA", "NY", "NJ", "OR", "MN", "VT", "DC", "HI"]);
      if (!highTaxStates.has(p.state.toUpperCase())) return { applicability: "not_applicable", reasoning: `${p.state} is not a high-tax state.`, ballpark: 0 };
      const stateRate = p.state === "CA" ? 0.133 : 0.1;
      const ballpark = p.annualProfit * stateRate;
      return { applicability: "applies", reasoning: `Moving from ${p.state} to a no-income-tax state could save ~$${Math.round(ballpark / 1000)}K/yr. Requires genuine domicile change (183-day rule).`, ballpark };
    },
  },

  {
    id: "salt_workaround",
    name: "SALT Cap Workaround (PTE Election)",
    category: "state_tax",
    defaultPriority: "high",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: false,
    requiresCpa: true,
    ircSections: ["164"],
    obbaSections: ["OBBBA §164 SALT cap increased to $40K for income <$500K"],
    minProfitThreshold: 100_000,
    minNetWorthThreshold: 0,
    urgency: "immediate",
    apply(p) {
      const saltableSates = ["CA", "NY", "NJ", "IL", "MA", "OR", "MD", "CT"];
      if (!saltableSates.includes(p.state.toUpperCase())) return { applicability: "not_applicable", reasoning: `${p.state} PTE election not available or not beneficial.`, ballpark: 0 };
      const stateTax = p.annualProfit * 0.09;
      const ballpark = stateTax * p.estimatedMarginalRate;
      return { applicability: "applies", reasoning: `Pass-through entity election lets the entity pay state tax, bypassing $40K SALT cap at individual level. Saves ~$${Math.round(ballpark / 1000)}K.`, ballpark };
    },
  },

  {
    id: "nexus_planning",
    name: "Multi-State Nexus & Apportionment Planning",
    category: "state_tax",
    defaultPriority: "medium",
    complexity: "complex",
    irsScrutiny: "medium",
    requiresAttorney: true,
    requiresCpa: true,
    ircSections: [],
    obbaSections: [],
    minProfitThreshold: 200_000,
    minNetWorthThreshold: 0,
    urgency: "multi_year",
    apply(p) {
      return { applicability: "maybe", reasoning: "Review economic nexus thresholds across operating states; apportionments may reduce state tax exposure.", ballpark: p.annualProfit * 0.02 };
    },
  },

  {
    id: "jurisdiction_planning",
    name: "Business Jurisdiction Optimization (WY/DE/NV)",
    category: "jurisdiction",
    defaultPriority: "medium",
    complexity: "medium",
    irsScrutiny: "low",
    requiresAttorney: true,
    requiresCpa: false,
    ircSections: [],
    obbaSections: [],
    minProfitThreshold: 0,
    minNetWorthThreshold: 0,
    urgency: "when_ready",
    apply(p) {
      return { applicability: "maybe", reasoning: "Form holding entities in WY/DE for favorable charging-order law, low franchise fees, and privacy.", ballpark: 0 };
    },
  },

];

// ─── Lookup helpers ───────────────────────────────────────────────────────────

const CATALOG_MAP = new Map<string, StrategyCatalogEntry>(
  STRATEGIES.map((s) => [s.id, s])
);

export function getStrategy(id: string): StrategyCatalogEntry | undefined {
  return CATALOG_MAP.get(id);
}

/**
 * Quick-filter catalog against a normalized profile and return applicability
 * results sorted by estimated savings descending.
 */
export function screenStrategies(profile: NormalizedProfile): StrategyApplicabilityResult[] {
  const results: StrategyApplicabilityResult[] = [];

  for (const s of STRATEGIES) {
    if (profile.annualProfit < s.minProfitThreshold) continue;
    if (profile.totalNetWorth < s.minNetWorthThreshold) continue;

    const { applicability, reasoning, ballpark } = s.apply(profile);
    if (applicability === "not_applicable") continue;

    results.push({
      strategyId: s.id,
      name: s.name,
      category: s.category,
      applicability,
      reasoning,
      estimatedSavingsBallpark: ballpark,
      priority: s.defaultPriority,
      urgency: s.urgency,
    });
  }

  return results.sort((a, b) => b.estimatedSavingsBallpark - a.estimatedSavingsBallpark);
}
