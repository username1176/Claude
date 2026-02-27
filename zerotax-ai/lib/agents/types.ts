// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — 5-Agent Graph: Shared Types
// Equivalent to the Python dataclasses / TypedDicts used in LangGraph.
// State flows through: Intake → Research → Optimizer → Risk → Synthesis
// ─────────────────────────────────────────────────────────────────────────────

import type { RagChunk, QuestionnaireProfile } from "@/lib/tax-rag";

export type { RagChunk, QuestionnaireProfile };

// ─── Enums ────────────────────────────────────────────────────────────────────

export type BusinessStage = "idea" | "startup" | "growth" | "established" | "mature";
export type EntityType =
  | "sole_prop" | "single_llc" | "multi_llc" | "s_corp"
  | "c_corp" | "partnership" | "nonprofit";
export type RiskTolerance = "conservative" | "moderate" | "aggressive";
export type Priority = "critical" | "high" | "medium" | "low";
export type Complexity = "simple" | "medium" | "complex" | "attorney_required";
export type IrsScrutiny = "low" | "medium" | "high" | "very_high";
export type ScenarioRisk = "low" | "medium" | "high";
export type StrategyApplicability = "applies" | "maybe" | "not_applicable";

export type StrategyCategory =
  | "entity_structure" | "retirement" | "depreciation" | "deductions"
  | "real_estate" | "estate_planning" | "asset_protection" | "exit"
  | "family_employment" | "qsbs" | "opportunity_zone" | "credits"
  | "state_tax" | "captive_insurance" | "jurisdiction";

// ─── Normalized Profile (Intake Agent output) ─────────────────────────────────

export interface NormalizedProfile {
  // Core financials (numeric, clean)
  entityType: EntityType;
  businessStage: BusinessStage;
  state: string;
  annualRevenue: number;
  annualProfit: number;           // net profit before SE deduction
  w2WagesPaid: number;            // wages paid to employees/self
  totalNetWorth: number;
  realEstateValue: number;
  retirementAccounts: number;
  investmentPortfolio: number;
  isMarried: boolean;
  spouseIncome: number;
  children: number;
  hasQsbs: boolean;
  goals: string[];
  riskTolerance: RiskTolerance;
  planningHorizon: string;

  // Derived tax metrics
  estimatedMarginalRate: number;  // federal income tax marginal rate (decimal)
  effectiveSERate: number;        // self-employment tax effective rate (decimal)
  estimatedCurrentTax: number;    // rough annual total tax burden
  agi: number;                    // estimated adjusted gross income
  seBase: number;                 // profit * 0.9235 (SE tax base)
  qbiEligible: boolean;
  qbiDeductionAmount: number;     // 20% × QBI (if eligible)

  // Strategy flags (quick filter for downstream agents)
  scorpOpportunity: boolean;      // meaningful SE tax savings available
  highIncome: boolean;            // AGI > $220K MFJ or $110K single
  ultraHighNetWorth: boolean;     // total assets > $5M
  realEstateInvestor: boolean;    // real estate value > $200K
  exitCandidate: boolean;         // goal includes exit strategy
  estatePlanningUrgent: boolean;  // net worth > $3M
  captiveCandidate: boolean;      // profit > $500K + business risk

  // Data quality
  dataGaps: string[];             // missing fields that limit analysis
  confidence: "high" | "medium" | "low";
}

// ─── Strategy Research (Research Agent output) ────────────────────────────────

export interface StrategyApplicabilityResult {
  strategyId: string;
  name: string;
  category: StrategyCategory;
  applicability: StrategyApplicability;
  reasoning: string;
  estimatedSavingsBallpark: number;  // rough $$ before detailed math
  priority: Priority;
  urgency: "immediate" | "this_year" | "multi_year" | "when_ready";
}

export interface StrategyResearchResult {
  strategyId: string;
  ragContext: string;       // relevant knowledge base text for this strategy
  currentLawSummary: string;
  keyIrcSections: string[];
  recentChanges: string;    // OBBBA, TCJA, etc.
  pitfalls: string[];
}

// ─── Tax Scenarios (Optimizer Agent output) ───────────────────────────────────

export interface TaxScenario {
  name: "conservative" | "optimal" | "aggressive";
  label: string;
  description: string;
  strategiesIncluded: string[];   // strategy IDs
  currentTax: number;
  optimizedTax: number;
  annualSavings: number;
  tenYearSavings: number;
  implementationCost: number;
  netFirstYearSavings: number;    // annualSavings - implementationCost
  riskLevel: ScenarioRisk;
  assumptions: string[];
  caveats: string[];
}

// ─── Optimized Strategy (Optimizer Agent output) ──────────────────────────────

export interface OptimizedStrategy {
  strategyId: string;
  name: string;
  category: StrategyCategory;
  estimatedAnnualSavings: number;
  savingsCalculation: {
    formula: string;             // e.g. "(profit - salary) × 0.153 × 0.9235"
    inputs: Record<string, number>; // the values plugged into formula
    result: number;
    conservativeResult: number;  // 20% haircut on optimistic
  };
  assumptions: string[];
  ircSections: string[];
  obbaSections: string[];
  priority: Priority;
  complexity: Complexity;
  implementationCost: number;    // CPA + attorney fees
  timelineDays: number;
  requiresAttorney: boolean;
  requiresCpa: boolean;
  actionItems: string[];
  formationDocsNeeded: string[]; // docs user needs to create
  chainOfThought: string;        // internal reasoning (hidden from user)
}

// ─── Compliance Flag (Risk Agent output) ──────────────────────────────────────

export interface ComplianceFlag {
  strategyId: string;
  flagType: "listed_transaction" | "aggressive" | "disclosure_required" | "state_conflict" | "warning";
  severity: "blocking" | "major" | "minor";
  description: string;
  irsReference: string;          // e.g. "Notice 2016-66"
  recommendedAction: string;
  disclosureForm: string | null; // e.g. "Form 8886"
}

// ─── Risk-Scored Strategy (Risk Agent output) ─────────────────────────────────

export interface RiskScoredStrategy extends OptimizedStrategy {
  riskScore: number;             // 1–10 (1=minimal risk, 10=abusive shelter)
  riskFactors: string[];
  irsScrutinyLevel: IrsScrutiny;
  isListedTransaction: boolean;
  requiresDisclosure: boolean;
  disclosureForm: string | null;
  complianceNotes: string[];
  caveats: string[];             // what can go wrong
  approvedForReport: boolean;    // false = removed from final output (too aggressive)
  riskAdjustedSavings: number;   // savings after probability-weighting for audit risk
}

// ─── Final Report (Synthesis Agent output) ────────────────────────────────────

export interface RoadmapPhase {
  phase: number;
  title: string;
  timeframe: string;             // e.g. "Days 1–30"
  strategies: string[];          // strategy names
  estimatedSavings: number;
  milestones: string[];
  prerequisites: string[];
}

export interface FinalReport {
  headlineInsight: string;       // 1-sentence hook, e.g. "You're leaving $127K/yr on the table"
  executiveSummary: string;      // 3–5 paragraph overview for non-lawyer
  entityRecommendation: string;
  entityRationale: string;
  currentEstimatedTax: number;
  optimizedEstimatedTax: number;
  projectedAnnualSavings: number;
  projected10YearSavings: number;
  savingsBreakdown: Record<string, number>;
  lawVersionDate: string;
  strategies: RiskScoredStrategy[];  // approved strategies only, sorted by savings
  scenarios: TaxScenario[];
  implementationRoadmap: RoadmapPhase[];
  urgentActions: string[];       // do THIS WEEK
  totalRiskScore: number;        // portfolio risk across all strategies
  ragChunksUsed: number;
  formationDocsAvailable: string[];  // list of templates included
}

// ─── Agent Log ────────────────────────────────────────────────────────────────

export interface AgentLogEntry {
  agent: "intake" | "research" | "optimizer" | "risk" | "synthesis";
  startedAt: string;
  completedAt: string;
  durationMs: number;
  tokensUsed: number;
  inputTokens: number;
  outputTokens: number;
  success: boolean;
  error: string | null;
  reasoning: string;             // chain-of-thought (internal, not shown to user)
}

// ─── Graph State (full shared state flowing through all 5 agents) ──────────────

export interface GraphInput {
  questionnaire: Record<string, unknown>;
  profile: QuestionnaireProfile;
  recommendationId: string;
  userId: string;
  businessId: string;
}

export interface GraphState extends GraphInput {
  // ── Intake Agent ──────────────────────────────────────────────────────────
  normalizedProfile: NormalizedProfile | null;
  applicableStrategies: StrategyApplicabilityResult[];
  intakeCompleted: boolean;

  // ── Research Agent ────────────────────────────────────────────────────────
  ragChunks: RagChunk[];
  strategyResearch: StrategyResearchResult[];
  relevantIrcSections: string[];
  taxLawHighlights: string[];    // notable recent changes from RAG
  researchCompleted: boolean;

  // ── Optimizer Agent ───────────────────────────────────────────────────────
  optimizedStrategies: OptimizedStrategy[];
  scenarios: TaxScenario[];
  optimizerCompleted: boolean;

  // ── Risk Agent ────────────────────────────────────────────────────────────
  riskScoredStrategies: RiskScoredStrategy[];
  complianceFlags: ComplianceFlag[];
  overallPortfolioRisk: number;
  redFlags: string[];
  riskCompleted: boolean;

  // ── Synthesis Agent ───────────────────────────────────────────────────────
  finalReport: FinalReport | null;
  synthesisCompleted: boolean;

  // ── Metadata ──────────────────────────────────────────────────────────────
  agentLog: AgentLogEntry[];
  totalTokensUsed: number;
  startedAt: string;
  errors: string[];
  currentAgent: string;
}
