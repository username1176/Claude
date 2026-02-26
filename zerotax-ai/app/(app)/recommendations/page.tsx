// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Recommendations List Page
// Shows all recommendations for the authenticated user.
// ─────────────────────────────────────────────────────────────────────────────

import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { RecommendationsList } from "@/components/recommendations/RecommendationsList";

export const dynamic = "force-dynamic";

export default async function RecommendationsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const db = supabase as any;

  const { data: recommendations } = await db
    .from("recommendations")
    .select(
      "id, title, status, created_at, projected_annual_savings, " +
        "executive_summary, recommended_entity_structure, law_version_date, " +
        "rag_chunks_used"
    )
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Your Tax Plans</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            AI-generated strategies ranked by estimated annual savings
          </p>
        </div>
        <Link
          href="/questionnaire"
          className="text-xs px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors"
        >
          + New Plan
        </Link>
      </div>

      <RecommendationsList
        initialItems={recommendations ?? []}
        userId={user.id}
      />
    </div>
  );
}
