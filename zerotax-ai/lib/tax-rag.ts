// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Tax RAG Module  (equivalent to tax_rag.py)
// LangChain-style retriever using Supabase pgvector + OpenAI embeddings.
// Always forces Claude to cite the latest retrieved documents with date.
// ─────────────────────────────────────────────────────────────────────────────

import OpenAI from "openai";
import { createAdminClient } from "@/lib/supabase/admin";
import {
  buildRecommendSystemPrompt,
  formatRagContext,
} from "@/knowledge_base/prompts";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface RagChunk {
  id: string;
  title: string;
  content: string;
  source_type: string;
  document_title: string | null;
  document_number: string | null;
  jurisdiction: string | null;
  url: string | null;
  effective_date: string | null;
  impact_score: number;
  similarity: number;
}

export interface QuestionnaireProfile {
  businessStage?: string | null;
  entityTypeCurrent?: string | null;
  stateOfFormation?: string | null;
  annualRevenue?: number | null;
  annualProfit?: number | null;
  w2WagesPaid?: number | null;
  totalNetWorth?: number | null;
  realEstateValue?: number | null;
  hasQsbsStock?: boolean | null;
  marriedFilingJointly?: boolean | null;
  childrenCount?: number | null;
  goalMinimizeTaxes?: boolean;
  goalAssetProtection?: boolean;
  goalEstatePlanning?: boolean;
  goalExitStrategy?: boolean;
  goalRetirementPlanning?: boolean;
  goalHireFamily?: boolean;
  planningHorizon?: string | null;
  riskTolerance?: string | null;
}

// ─── OpenAI client (lazy init) ────────────────────────────────────────────────

let _openai: OpenAI | null = null;

function getOpenAI(): OpenAI {
  if (!_openai) {
    if (!process.env.OPENAI_API_KEY) {
      throw new Error("OPENAI_API_KEY environment variable is not set");
    }
    _openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  }
  return _openai;
}

// ─── Embedding ────────────────────────────────────────────────────────────────

/**
 * Generate a 1536-dim embedding for a text string using text-embedding-3-small.
 * The DB schema uses vector(1536) so this is the correct model.
 */
export async function embed(text: string): Promise<number[]> {
  const openai = getOpenAI();
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: text.slice(0, 8_000), // stay within token limit
    dimensions: 1536,
  });
  return response.data[0].embedding;
}

/**
 * Batch embed multiple texts in a single API call (up to 2048 per call).
 * Returns embeddings in the same order as the input array.
 */
export async function batchEmbed(texts: string[]): Promise<number[][]> {
  if (texts.length === 0) return [];
  const openai = getOpenAI();
  const truncated = texts.map((t) => t.slice(0, 8_000));
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: truncated,
    dimensions: 1536,
  });
  // Sort by index to maintain order (OpenAI guarantees order but best practice)
  return response.data
    .sort((a, b) => a.index - b.index)
    .map((d) => d.embedding);
}

// ─── Retriever ────────────────────────────────────────────────────────────────

/**
 * Semantic similarity search against the knowledge_base table.
 * Uses the Supabase RPC function `match_knowledge_base` (created in migration 002/004).
 *
 * @param query      - Natural language query to embed and search
 * @param jurisdiction - Optional state code to filter (e.g. 'CA'). Federal docs always included.
 * @param k          - Number of results to return
 * @param threshold  - Minimum cosine similarity (0–1)
 */
export async function retrieve(
  query: string,
  jurisdiction?: string | null,
  k = 8,
  threshold = 0.25
): Promise<RagChunk[]> {
  const embedding = await embed(query);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const supabase = createAdminClient() as any;

  const { data, error } = await supabase.rpc("match_knowledge_base", {
    query_embedding: embedding,
    match_threshold: threshold,
    match_count: k,
    filter_jurisdiction: jurisdiction ?? null,
  });

  if (error) {
    console.error("[tax-rag] retrieve error:", error);
    return [];
  }

  return (data ?? []) as RagChunk[];
}

// ─── Multi-query retrieval (better coverage) ──────────────────────────────────

/**
 * Generate 4–6 targeted search queries from a questionnaire profile.
 * Running multiple queries and deduplicating results yields much better
 * RAG coverage than a single generic query.
 */
export function generateSearchQueries(profile: QuestionnaireProfile): string[] {
  const queries: string[] = [];

  // ── Core entity + stage ──────────────────────────────────────────────────
  const entity = profile.entityTypeCurrent ?? "business";
  const stage = profile.businessStage ?? "";
  queries.push(`${entity} ${stage} tax optimization strategies IRC deduction`);

  // ── SE tax / S-Corp opportunity ──────────────────────────────────────────
  const profit = profile.annualProfit ?? 0;
  if (
    profit > 50_000 &&
    ["sole_prop", "single_llc", "multi_llc"].includes(entity)
  ) {
    queries.push(
      "S-Corporation election IRC Section 1361 self-employment tax reduction reasonable salary"
    );
  }

  // ── QBI deduction ────────────────────────────────────────────────────────
  if (entity !== "c_corp" && profit > 0) {
    queries.push(
      "Section 199A qualified business income QBI deduction 20 percent pass-through OBBBA"
    );
  }

  // ── Retirement ───────────────────────────────────────────────────────────
  if (profile.goalRetirementPlanning) {
    if (profit > 150_000) {
      queries.push(
        "defined benefit pension plan cash balance annual contribution limit IRC 415 412"
      );
    } else {
      queries.push(
        "Solo 401k SEP-IRA retirement plan contribution limit IRC 401 self-employed"
      );
    }
  }

  // ── Asset protection ─────────────────────────────────────────────────────
  const assets = profile.totalNetWorth ?? 0;
  if (profile.goalAssetProtection || assets > 500_000) {
    queries.push(
      "asset protection LLC charging order domestic asset protection trust DAPT Wyoming Nevada"
    );
  }

  // ── Real estate ──────────────────────────────────────────────────────────
  const re = profile.realEstateValue ?? 0;
  if (re > 0) {
    queries.push(
      "real estate LLC section 1031 like-kind exchange cost segregation bonus depreciation"
    );
  }

  // ── QSBS / exit ──────────────────────────────────────────────────────────
  if (profile.hasQsbsStock || profile.goalExitStrategy) {
    queries.push(
      "qualified small business stock QSBS Section 1202 exclusion C-Corporation exit capital gains"
    );
  }

  // ── Estate planning ──────────────────────────────────────────────────────
  if (profile.goalEstatePlanning) {
    queries.push(
      "estate planning irrevocable trust SLAT GRAT gift tax annual exclusion IRC 2503 2505"
    );
  }

  // ── Family employment ────────────────────────────────────────────────────
  const kids = profile.childrenCount ?? 0;
  if (kids > 0 || profile.goalHireFamily) {
    queries.push(
      "hire children family members IRC 3121 FICA exemption standard deduction wages"
    );
  }

  // ── State-specific ───────────────────────────────────────────────────────
  if (profile.stateOfFormation) {
    queries.push(
      `${profile.stateOfFormation} state income tax business formation planning strategies`
    );
  }

  return queries.slice(0, 6);
}

/**
 * Run multiple search queries, deduplicate by chunk ID, and return the
 * top-K chunks sorted by similarity score.
 */
export async function retrieveMultiQuery(
  profile: QuestionnaireProfile,
  totalK = 12
): Promise<RagChunk[]> {
  const queries = generateSearchQueries(profile);
  const seen = new Map<string, RagChunk>();

  await Promise.all(
    queries.map(async (q) => {
      try {
        const chunks = await retrieve(q, profile.stateOfFormation, 8, 0.2);
        for (const c of chunks) {
          if (!seen.has(c.id) || seen.get(c.id)!.similarity < c.similarity) {
            seen.set(c.id, c);
          }
        }
      } catch {
        // Silently skip failed queries — other results still useful
      }
    })
  );

  return Array.from(seen.values())
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, totalK);
}

// ─── Prompt Builders ──────────────────────────────────────────────────────────

/**
 * Build the full system prompt for the recommend endpoint.
 * Combines mandatory citation rules + retrieved RAG context.
 */
export function buildSystemPrompt(chunks: RagChunk[]): string {
  const today = new Date().toISOString().split("T")[0];
  const ragContext = formatRagContext(chunks);
  return buildRecommendSystemPrompt(today, chunks.length) + "\n\n" + ragContext;
}

/**
 * Build the user message for the recommend endpoint.
 * Contains the taxpayer's full profile and the required JSON schema.
 */
export function buildUserPrompt(
  profile: QuestionnaireProfile,
  questionnaireRaw?: Record<string, unknown>
): string {
  const goals: string[] = [];
  if (profile.goalMinimizeTaxes) goals.push("Minimize taxes now (primary)");
  if (profile.goalAssetProtection) goals.push("Asset protection");
  if (profile.goalEstatePlanning) goals.push("Estate & legacy planning");
  if (profile.goalExitStrategy) goals.push("Exit / sell business");
  if (profile.goalRetirementPlanning) goals.push("Build retirement wealth");
  if (profile.goalHireFamily) goals.push("Employ family members");

  const entityWarning = ["sole_prop", "single_llc", "multi_llc"].includes(
    profile.entityTypeCurrent ?? ""
  )
    ? " ⚠️ SUBOPTIMAL ENTITY — restructuring is likely the #1 opportunity"
    : "";

  const profileBlock = `TAXPAYER FINANCIAL PROFILE
════════════════════════════════════════════════════════
BUSINESS
  • Stage:          ${profile.businessStage ?? "unknown"}
  • Entity Type:    ${profile.entityTypeCurrent ?? "unknown"}${entityWarning}
  • State:          ${profile.stateOfFormation ?? "unknown"}

FINANCIALS
  • Annual Revenue: ${fmt(profile.annualRevenue)}
  • Annual Profit:  ${fmt(profile.annualProfit)}
  • W-2 Wages Paid: ${fmt(profile.w2WagesPaid)}
  • Total Assets:   ${fmt(profile.totalNetWorth)}
  • Real Estate:    ${fmt(profile.realEstateValue)}

PERSONAL
  • Married (MFJ):  ${boolStr(profile.marriedFilingJointly)}
  • Children:       ${profile.childrenCount ?? 0}
  • QSBS Eligible:  ${boolStr(profile.hasQsbsStock)}

GOALS (priority order):
  ${goals.length > 0 ? goals.map((g, i) => `${i + 1}. ${g}`).join("\n  ") : "Not specified"}

PLANNING PARAMETERS
  • Risk Tolerance:   ${profile.riskTolerance ?? "moderate"}
  • Planning Horizon: ${profile.planningHorizon ?? "3_year"}
`;

  const schema = `
REQUIRED OUTPUT SCHEMA (return ONLY valid JSON, no markdown):
{
  "executive_summary": "3–5 sentence overview of the tax situation and top opportunities",
  "recommended_entity_structure": "e.g. S-Corporation",
  "entity_rationale": "2–3 sentence explanation of why, with IRC citation",
  "current_estimated_tax": <number: estimated annual federal + SE tax under current setup>,
  "optimized_estimated_tax": <number: estimated annual tax after top strategies>,
  "projected_annual_savings": <number: current minus optimized>,
  "projected_10yr_savings": <number: annual × 10, conservative>,
  "law_version_date": "${new Date().toISOString().split("T")[0]}",
  "savings_breakdown": {
    "entity_restructuring": <number or 0>,
    "retirement_plans": <number or 0>,
    "qbi_deduction": <number or 0>,
    "depreciation": <number or 0>,
    "family_employment": <number or 0>,
    "asset_protection": 0,
    "other": <number or 0>
  },
  "strategies": [
    {
      "category": "entity_structure|retirement|depreciation|deductions|real_estate|estate_planning|asset_protection|exit|family_employment|qsbs|opportunity_zone|credits|state_tax",
      "title": "Strategy name (max 80 chars)",
      "description": "One-sentence description (max 200 chars)",
      "detailed_explanation": "Full explanation 300–800 chars. MUST include IRC section(s), effective date, and calculation if applicable.",
      "irc_sections": ["199A", "1361"],
      "obbba_sections": [],
      "state_law_refs": [],
      "irs_publications": [],
      "estimated_annual_savings": <number>,
      "implementation_cost": <number: estimated CPA/attorney fees>,
      "payback_period_months": <number: implementation_cost / (estimated_annual_savings/12)>,
      "priority": "critical|high|medium|low",
      "complexity": "simple|medium|complex|attorney_required",
      "timeline_days": <number: realistic days to implement>,
      "requires_attorney": <boolean>,
      "requires_cpa": <boolean>,
      "action_items": ["Step 1", "Step 2", "Step 3"]
    }
  ]
}`;

  return profileBlock + schema + (questionnaireRaw
    ? `\n\nFULL QUESTIONNAIRE DATA (additional context):\n${JSON.stringify(questionnaireRaw, null, 2)}`
    : "");
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "Not provided";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function boolStr(v: boolean | null | undefined): string {
  if (v === null || v === undefined) return "Not provided";
  return v ? "Yes" : "No";
}

/**
 * Robustly extract JSON from a Claude response that may contain markdown
 * code fences or surrounding text.
 */
export function extractJson(text: string): string {
  // Try to find a JSON code block first
  const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenceMatch) return fenceMatch[1].trim();

  // Find the outermost { ... } object
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start !== -1 && end !== -1 && end > start) {
    return text.slice(start, end + 1);
  }

  return text.trim();
}
