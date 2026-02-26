// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — AI Recommendation Engine
// Full RAG pipeline: questionnaire → retrieve → Claude claude-sonnet-4-6 → save strategies.
// Called fire-and-forget from /api/questionnaire/submit.
// ─────────────────────────────────────────────────────────────────────────────

import Anthropic from "@anthropic-ai/sdk";
import { createAdminClient } from "@/lib/supabase/admin";
import {
  retrieveMultiQuery,
  buildSystemPrompt,
  buildUserPrompt,
  extractJson,
  type QuestionnaireProfile,
} from "@/lib/tax-rag";

// Allow up to 5 minutes for Claude + RAG
export const maxDuration = 300;

// ─── Types ────────────────────────────────────────────────────────────────────

interface AiStrategy {
  category: string;
  title: string;
  description: string;
  detailed_explanation: string | null;
  irc_sections: string[];
  obbba_sections: string[];
  state_law_refs: string[];
  irs_publications: string[];
  estimated_annual_savings: number;
  implementation_cost: number;
  payback_period_months: number;
  priority: "critical" | "high" | "medium" | "low";
  complexity: "simple" | "medium" | "complex" | "attorney_required";
  timeline_days: number;
  requires_attorney: boolean;
  requires_cpa: boolean;
  action_items: string[];
}

interface AiResponse {
  executive_summary: string;
  recommended_entity_structure: string;
  entity_rationale: string;
  current_estimated_tax: number;
  optimized_estimated_tax: number;
  projected_annual_savings: number;
  projected_10yr_savings: number;
  law_version_date: string;
  savings_breakdown: Record<string, number>;
  strategies: AiStrategy[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapToProfile(q: Record<string, any>): QuestionnaireProfile {
  return {
    businessStage: q.business_stage ?? null,
    entityTypeCurrent: q.entity_type_current ?? null,
    stateOfFormation: q.state_of_formation ?? null,
    annualRevenue: q.annual_revenue ?? null,
    annualProfit: q.annual_profit ?? null,
    w2WagesPaid: q.w2_wages_paid ?? null,
    totalNetWorth: q.total_net_worth ?? null,
    realEstateValue: q.real_estate_value ?? null,
    hasQsbsStock: q.has_qsbs_stock ?? null,
    marriedFilingJointly: q.married_filing_jointly ?? null,
    childrenCount: q.children_count ?? null,
    goalMinimizeTaxes: q.goal_minimize_taxes ?? false,
    goalAssetProtection: q.goal_asset_protection ?? false,
    goalEstatePlanning: q.goal_estate_planning ?? false,
    goalExitStrategy: q.goal_exit_strategy ?? false,
    goalRetirementPlanning: q.goal_retirement_planning ?? false,
    goalHireFamily: q.goal_hire_family ?? false,
    planningHorizon: q.planning_horizon ?? null,
    riskTolerance:
      ((q.additional_data as Record<string, unknown> | null)
        ?.riskTolerance as string | null) ?? null,
  };
}

const VALID_CATEGORIES = new Set([
  "entity_structure",
  "retirement",
  "depreciation",
  "deductions",
  "real_estate",
  "estate_planning",
  "asset_protection",
  "exit",
  "family_employment",
  "qsbs",
  "opportunity_zone",
  "credits",
  "state_tax",
]);
const VALID_PRIORITIES = new Set(["critical", "high", "medium", "low"]);
const VALID_COMPLEXITIES = new Set([
  "simple",
  "medium",
  "complex",
  "attorney_required",
]);

function coerceStrategy(s: Partial<AiStrategy>, idx: number): AiStrategy {
  return {
    category: VALID_CATEGORIES.has(s.category ?? "")
      ? s.category!
      : "deductions",
    title: String(s.title ?? `Strategy ${idx + 1}`).slice(0, 200),
    description: String(s.description ?? "").slice(0, 500),
    detailed_explanation: s.detailed_explanation
      ? String(s.detailed_explanation).slice(0, 3_000)
      : null,
    irc_sections: Array.isArray(s.irc_sections)
      ? s.irc_sections.map(String)
      : [],
    obbba_sections: Array.isArray(s.obbba_sections)
      ? s.obbba_sections.map(String)
      : [],
    state_law_refs: Array.isArray(s.state_law_refs)
      ? s.state_law_refs.map(String)
      : [],
    irs_publications: Array.isArray(s.irs_publications)
      ? s.irs_publications.map(String)
      : [],
    estimated_annual_savings: Number(s.estimated_annual_savings) || 0,
    implementation_cost: Number(s.implementation_cost) || 0,
    payback_period_months: Number(s.payback_period_months) || 0,
    priority: VALID_PRIORITIES.has(s.priority ?? "") ? s.priority! : "medium",
    complexity: VALID_COMPLEXITIES.has(s.complexity ?? "")
      ? s.complexity!
      : "medium",
    timeline_days: Number(s.timeline_days) || 30,
    requires_attorney: Boolean(s.requires_attorney),
    requires_cpa: s.requires_cpa !== false,
    action_items: Array.isArray(s.action_items)
      ? s.action_items.map(String)
      : [],
  };
}

// ─── Route handler ────────────────────────────────────────────────────────────

export async function POST(req: Request) {
  const { recommendationId, questionnaireId, businessId, userId } =
    (await req.json()) as {
      recommendationId?: string;
      questionnaireId?: string;
      businessId?: string;
      userId?: string;
    };

  if (!recommendationId || !questionnaireId || !businessId || !userId) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const supabase = createAdminClient() as any;

  try {
    // 1. Fetch questionnaire
    const { data: q, error: qErr } = await supabase
      .from("questionnaire_responses")
      .select("*")
      .eq("id", questionnaireId)
      .single();

    if (qErr || !q) {
      console.error("[ai/recommend] questionnaire not found:", qErr);
      await supabase
        .from("recommendations")
        .update({ status: "outdated" })
        .eq("id", recommendationId);
      return Response.json(
        { error: "Questionnaire not found" },
        { status: 404 }
      );
    }

    // 2. Build profile + run multi-query RAG retrieval
    const profile = mapToProfile(q as Record<string, unknown>);
    const chunks = await retrieveMultiQuery(profile, 12);
    console.log(
      `[ai/recommend] ${chunks.length} chunks for rec ${recommendationId}`
    );

    // 3. Build prompts
    const systemPrompt = buildSystemPrompt(chunks);
    const userPrompt = buildUserPrompt(
      profile,
      (q as Record<string, unknown>).additional_data as
        | Record<string, unknown>
        | undefined
    );

    // 4. Call Claude claude-sonnet-4-6
    const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const message = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 8_000,
      system: systemPrompt,
      messages: [{ role: "user", content: userPrompt }],
    });

    const rawText =
      message.content[0].type === "text" ? message.content[0].text : "";

    // 5. Parse JSON response
    let parsed: Partial<AiResponse>;
    try {
      parsed = JSON.parse(extractJson(rawText)) as Partial<AiResponse>;
    } catch (parseErr) {
      console.error("[ai/recommend] JSON parse failed:", parseErr);
      await supabase
        .from("recommendations")
        .update({
          status: "outdated",
          raw_ai_response: rawText.slice(0, 10_000),
        })
        .eq("id", recommendationId);
      return Response.json(
        { error: "AI response parse failed" },
        { status: 500 }
      );
    }

    const strategies = (parsed.strategies ?? []).map((s, i) =>
      coerceStrategy(s, i)
    );

    // 6. Update recommendation with AI output
    await supabase
      .from("recommendations")
      .update({
        status: "complete",
        executive_summary: parsed.executive_summary?.slice(0, 2_000) ?? null,
        recommended_entity_structure:
          parsed.recommended_entity_structure ?? null,
        entity_rationale: parsed.entity_rationale?.slice(0, 1_000) ?? null,
        current_estimated_tax: parsed.current_estimated_tax ?? null,
        optimized_estimated_tax: parsed.optimized_estimated_tax ?? null,
        projected_annual_savings: parsed.projected_annual_savings ?? null,
        projected_10yr_savings: parsed.projected_10yr_savings ?? null,
        savings_breakdown: parsed.savings_breakdown ?? null,
        model_used: "claude-sonnet-4-6",
        rag_chunks_used: chunks.length,
        raw_ai_response: rawText.slice(0, 20_000),
        law_version_date:
          parsed.law_version_date ??
          new Date().toISOString().split("T")[0],
      })
      .eq("id", recommendationId);

    // 7. Insert strategies sorted by savings desc
    if (strategies.length > 0) {
      const sorted = [...strategies].sort(
        (a, b) => b.estimated_annual_savings - a.estimated_annual_savings
      );
      const rows = sorted.map((s, i) => ({
        recommendation_id: recommendationId,
        user_id: userId,
        category: s.category,
        title: s.title,
        description: s.description,
        detailed_explanation: s.detailed_explanation,
        irc_sections: s.irc_sections,
        obbba_sections: s.obbba_sections,
        state_law_refs: s.state_law_refs,
        irs_publications: s.irs_publications,
        estimated_annual_savings: s.estimated_annual_savings,
        implementation_cost: s.implementation_cost,
        payback_period_months: s.payback_period_months,
        priority: s.priority,
        complexity: s.complexity,
        timeline_days: s.timeline_days,
        requires_attorney: s.requires_attorney,
        requires_cpa: s.requires_cpa,
        action_items: s.action_items,
        user_status: "pending",
        sort_order: i,
      }));

      const { error: stratErr } = await supabase
        .from("strategies")
        .insert(rows);
      if (stratErr) {
        console.error("[ai/recommend] strategy insert error:", stratErr);
      }
    }

    console.log(
      `[ai/recommend] complete: ${strategies.length} strategies, ` +
        `savings=$${parsed.projected_annual_savings ?? 0}`
    );

    return Response.json({
      ok: true,
      recommendationId,
      strategiesCount: strategies.length,
      ragChunks: chunks.length,
    });
  } catch (err) {
    console.error("[ai/recommend] fatal:", err);
    await supabase
      .from("recommendations")
      .update({ status: "outdated" })
      .eq("id", recommendationId)
      .catch(() => {});
    return Response.json({ error: "Internal error" }, { status: 500 });
  }
}
