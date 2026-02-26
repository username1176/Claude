import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

function toSnakeCase(data: Record<string, unknown>): Record<string, unknown> {
  const map: Record<string, string> = {
    businessStage: "business_stage",
    industry: "industry",
    entityTypeCurrent: "entity_type_current",
    yearBusinessFounded: "year_business_founded",
    annualRevenue: "annual_revenue",
    annualProfit: "annual_profit",
    w2WagesPaid: "w2_wages_paid",
    ownerDraws: "owner_draws",
    reasonableSalary: "reasonable_salary",
    otherIncome: "other_income",
    otherIncomeType: "other_income_type",
    stateOfFormation: "state_of_formation",
    statesOperating: "states_operating",
    numOwners: "num_owners",
    marriedFilingJointly: "married_filing_jointly",
    spouseWorks: "spouse_works",
    spouseIncome: "spouse_income",
    childrenCount: "children_count",
    familyInBusiness: "family_in_business",
    realEstateValue: "real_estate_value",
    businessAssetsValue: "business_assets_value",
    investmentPortfolio: "investment_portfolio",
    retirementAccounts: "retirement_accounts",
    totalNetWorth: "total_net_worth",
    hasQsbsStock: "has_qsbs_stock",
    goalMinimizeTaxes: "goal_minimize_taxes",
    goalAssetProtection: "goal_asset_protection",
    goalEstatePlanning: "goal_estate_planning",
    goalExitStrategy: "goal_exit_strategy",
    goalRetirementPlanning: "goal_retirement_planning",
    goalHireFamily: "goal_hire_family",
    planningHorizon: "planning_horizon",
    exitTimelineYears: "exit_timeline_years",
  };
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(data)) {
    if (map[k]) result[map[k]] = v;
  }
  return result;
}

export async function POST(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const body = await req.json() as {
      step: number;
      businessId: string | null;
      questionnaireId: string | null;
      allData: Record<string, unknown>;
    };
    const { step, businessId, questionnaireId, allData } = body;

    // 1. Ensure business
    let bizId = businessId;
    if (!bizId) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: biz, error } = await (supabase as any)
        .from("businesses")
        .insert({ user_id: user.id, name: allData.businessName ?? null, is_active: true })
        .select("id")
        .single();
      if (error || !biz) return NextResponse.json({ error: "Failed to create business" }, { status: 500 });
      bizId = (biz as { id: string }).id;
    } else if (allData.businessName) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (supabase as any)
        .from("businesses")
        .update({ name: allData.businessName })
        .eq("id", bizId);
    }

    // 2. Upsert questionnaire
    const dbData = toSnakeCase(allData);
    let qId = questionnaireId;

    if (!qId) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: q, error } = await (supabase as any)
        .from("questionnaire_responses")
        .insert({ business_id: bizId, user_id: user.id, step_completed: step, ...dbData })
        .select("id")
        .single();
      if (error || !q) return NextResponse.json({ error: "Failed to create questionnaire" }, { status: 500 });
      qId = (q as { id: string }).id;
    } else {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (supabase as any)
        .from("questionnaire_responses")
        .update({ step_completed: step, ...dbData })
        .eq("id", qId);
    }

    return NextResponse.json({ businessId: bizId, questionnaireId: qId });
  } catch (err) {
    console.error("[questionnaire/save]", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
