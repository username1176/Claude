import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

function buildDbPayload(data: Record<string, unknown>): Record<string, unknown> {
  return {
    business_stage: data.businessStage,
    industry: data.industry,
    entity_type_current: data.entityTypeCurrent,
    year_business_founded: data.yearBusinessFounded,
    annual_revenue: data.annualRevenue,
    annual_profit: data.annualProfit,
    w2_wages_paid: data.w2WagesPaid,
    owner_draws: data.ownerDraws,
    reasonable_salary: data.reasonableSalary,
    other_income: data.otherIncome,
    other_income_type: data.otherIncomeType,
    state_of_formation: data.stateOfFormation,
    states_operating: data.statesOperating,
    num_owners: data.numOwners,
    married_filing_jointly: data.marriedFilingJointly,
    spouse_works: data.spouseWorks,
    spouse_income: data.spouseIncome,
    children_count: data.childrenCount,
    family_in_business: data.familyInBusiness,
    real_estate_value: data.realEstateValue,
    business_assets_value: data.businessAssetsValue,
    investment_portfolio: data.investmentPortfolio,
    retirement_accounts: data.retirementAccounts,
    total_net_worth: data.totalNetWorth,
    has_qsbs_stock: data.hasQsbsStock,
    goal_minimize_taxes: data.goalMinimizeTaxes ?? false,
    goal_asset_protection: data.goalAssetProtection ?? false,
    goal_estate_planning: data.goalEstatePlanning ?? false,
    goal_exit_strategy: data.goalExitStrategy ?? false,
    goal_retirement_planning: data.goalRetirementPlanning ?? false,
    goal_hire_family: data.goalHireFamily ?? false,
    planning_horizon: data.planningHorizon,
    exit_timeline_years: data.exitTimelineYears,
    step_completed: 6,
    completed_at: new Date().toISOString(),
  };
}

export async function POST(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const db = supabase as any;

    const body = await req.json() as {
      businessId: string | null;
      questionnaireId: string | null;
      data: Record<string, unknown>;
    };
    const { businessId, questionnaireId, data } = body;

    // 1. Ensure business
    let bizId = businessId;
    if (!bizId) {
      const { data: biz, error } = await db
        .from("businesses")
        .insert({ user_id: user.id, name: data.businessName ?? null, is_active: true })
        .select("id")
        .single();
      if (error || !biz) return NextResponse.json({ error: "Failed to create business" }, { status: 500 });
      bizId = biz.id as string;
    }

    // 2. Upsert questionnaire
    const dbPayload = buildDbPayload(data);
    let qId = questionnaireId;

    if (!qId) {
      const { data: q, error } = await db
        .from("questionnaire_responses")
        .insert({ business_id: bizId, user_id: user.id, ...dbPayload })
        .select("id")
        .single();
      if (error || !q) return NextResponse.json({ error: "Failed to save questionnaire" }, { status: 500 });
      qId = q.id as string;
    } else {
      await db
        .from("questionnaire_responses")
        .update(dbPayload)
        .eq("id", qId);
    }

    // 3. Create draft recommendation shell
    const { data: rec } = await db
      .from("recommendations")
      .insert({
        business_id: bizId,
        user_id: user.id,
        questionnaire_id: qId,
        title: `Tax Plan — ${String(data.businessName ?? "My Business")}`,
        status: "draft",
        model_used: "claude-sonnet-4-6",
        rag_chunks_used: 0,
      })
      .select("id")
      .single();

    // 4. Trigger async AI generation (fire-and-forget)
    if (rec?.id) {
      const baseUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
      fetch(`${baseUrl}/api/ai/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recommendationId: rec.id,
          questionnaireId: qId,
          businessId: bizId,
          userId: user.id,
        }),
      }).catch(() => {});
    }

    return NextResponse.json({
      businessId: bizId,
      questionnaireId: qId,
      recommendationId: rec?.id ?? null,
    });
  } catch (err) {
    console.error("[questionnaire/submit]", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
