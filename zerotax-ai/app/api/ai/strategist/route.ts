// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — 5-Agent Strategist Endpoint
// POST /api/ai/strategist
// Runs the full agent graph and saves the FinalReport to Supabase.
// Called fire-and-forget from /api/questionnaire/submit (same pattern as /api/ai/recommend).
// ─────────────────────────────────────────────────────────────────────────────

import { createAdminClient } from "@/lib/supabase/admin";
import { runAgentGraph } from "@/lib/agents/graph";
import type { GraphInput } from "@/lib/agents/types";
import type { QuestionnaireProfile } from "@/lib/tax-rag";

// Allow up to 10 minutes — 5 sequential Claude calls
export const maxDuration = 600;

// ─── Profile mapper (same logic as recommend route) ──────────────────────────

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
      console.error("[strategist] questionnaire not found:", qErr);
      await supabase
        .from("recommendations")
        .update({ status: "outdated" })
        .eq("id", recommendationId);
      return Response.json({ error: "Questionnaire not found" }, { status: 404 });
    }

    // 2. Mark recommendation as processing
    await supabase
      .from("recommendations")
      .update({ status: "processing" })
      .eq("id", recommendationId);

    // 3. Build graph input
    const profile = mapToProfile(q as Record<string, unknown>);
    const input: GraphInput = {
      questionnaire: q as Record<string, unknown>,
      profile,
      recommendationId,
      userId,
      businessId,
    };

    // 4. Run 5-agent graph
    console.log(`[strategist] starting agent graph for rec ${recommendationId}`);
    const finalState = await runAgentGraph(input);

    const report = finalState.finalReport;
    if (!report) {
      throw new Error("Agent graph produced no final report");
    }

    // 5. Update recommendation with full report
    await supabase
      .from("recommendations")
      .update({
        status: "complete",
        executive_summary: report.executiveSummary?.slice(0, 2_000) ?? null,
        recommended_entity_structure: report.entityRecommendation ?? null,
        entity_rationale: report.entityRationale?.slice(0, 1_000) ?? null,
        current_estimated_tax: report.currentEstimatedTax ?? null,
        optimized_estimated_tax: report.optimizedEstimatedTax ?? null,
        projected_annual_savings: report.projectedAnnualSavings ?? null,
        projected_10yr_savings: report.projected10YearSavings ?? null,
        savings_breakdown: report.savingsBreakdown ?? null,
        model_used: "claude-sonnet-4-6 (5-agent)",
        rag_chunks_used: finalState.ragChunks.length,
        law_version_date: report.lawVersionDate ?? new Date().toISOString().split("T")[0],
        raw_ai_response: JSON.stringify({
          agentLog: finalState.agentLog,
          errors: finalState.errors,
          totalTokensUsed: finalState.totalTokensUsed,
          headlineInsight: report.headlineInsight,
          scenarios: report.scenarios,
          implementationRoadmap: report.implementationRoadmap,
          urgentActions: report.urgentActions,
          totalRiskScore: report.totalRiskScore,
        }).slice(0, 20_000),
      })
      .eq("id", recommendationId);

    // 6. Insert approved strategies
    const approved = report.strategies.filter((s) => s.approvedForReport !== false);
    if (approved.length > 0) {
      const sorted = [...approved].sort(
        (a, b) => b.riskAdjustedSavings - a.riskAdjustedSavings
      );
      const rows = sorted.map((s, i) => ({
        recommendation_id: recommendationId,
        user_id: userId,
        category: s.category,
        title: s.name,
        description: s.actionItems?.join("; ").slice(0, 500) ?? "",
        detailed_explanation: s.savingsCalculation?.formula ?? null,
        irc_sections: s.ircSections ?? [],
        obbba_sections: s.obbaSections ?? [],
        state_law_refs: [],
        irs_publications: [],
        estimated_annual_savings: s.riskAdjustedSavings ?? s.estimatedAnnualSavings ?? 0,
        implementation_cost: s.implementationCost ?? 0,
        payback_period_months: s.implementationCost > 0 && s.estimatedAnnualSavings > 0
          ? Math.round((s.implementationCost / (s.estimatedAnnualSavings / 12)))
          : 0,
        priority: s.priority,
        complexity: s.complexity,
        timeline_days: s.timelineDays ?? 30,
        requires_attorney: s.requiresAttorney ?? false,
        requires_cpa: s.requiresCpa !== false,
        action_items: s.actionItems ?? [],
        user_status: "pending",
        sort_order: i,
      }));

      const { error: stratErr } = await supabase.from("strategies").insert(rows);
      if (stratErr) {
        console.error("[strategist] strategy insert error:", stratErr);
      }
    }

    console.log(
      `[strategist] complete: ${approved.length} strategies, ` +
      `$${report.projectedAnnualSavings?.toLocaleString() ?? "?"}/yr, ` +
      `${finalState.totalTokensUsed} tokens, ${finalState.errors.length} errors`
    );

    return Response.json({
      ok: true,
      recommendationId,
      strategiesCount: approved.length,
      ragChunks: finalState.ragChunks.length,
      totalTokensUsed: finalState.totalTokensUsed,
      errors: finalState.errors,
    });

  } catch (err) {
    console.error("[strategist] fatal:", err);
    await supabase
      .from("recommendations")
      .update({ status: "outdated" })
      .eq("id", recommendationId)
      .catch(() => {});
    return Response.json({ error: "Internal error" }, { status: 500 });
  }
}
