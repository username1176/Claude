// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Knowledge Base Status API
// Returns stats about the knowledge base and recent update runs.
// Used by the admin dashboard (future) and for debugging.
// ─────────────────────────────────────────────────────────────────────────────

import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function GET() {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAdminClient() as any;

    // Recent update runs (last 10)
    const { data: recentRuns } = await supabase
      .from("knowledge_update_log")
      .select(
        "id, run_type, triggered_by, started_at, completed_at, status, " +
        "chunks_added, chunks_skipped, chunks_updated, sources_ok, sources_attempted, " +
        "flagged_for_review"
      )
      .order("started_at", { ascending: false })
      .limit(10);

    // Total chunks
    const { count: totalChunks } = await supabase
      .from("knowledge_base")
      .select("*", { count: "exact", head: true });

    // Pending review count
    const { count: pendingReview } = await supabase
      .from("knowledge_base")
      .select("*", { count: "exact", head: true })
      .eq("needs_review", true);

    // Chunks by source_type
    const { data: bySourceType } = await supabase
      .from("knowledge_base")
      .select("source_type")
      .order("source_type");

    const sourceTypeCounts: Record<string, number> = {};
    for (const row of bySourceType ?? []) {
      const t = (row as { source_type: string }).source_type;
      sourceTypeCounts[t] = (sourceTypeCounts[t] ?? 0) + 1;
    }

    // Chunks by jurisdiction
    const { data: byJurisdiction } = await supabase
      .from("knowledge_base")
      .select("jurisdiction")
      .order("jurisdiction");

    const jurisdictionCounts: Record<string, number> = {};
    for (const row of byJurisdiction ?? []) {
      const j =
        (row as { jurisdiction: string | null }).jurisdiction ?? "unknown";
      jurisdictionCounts[j] = (jurisdictionCounts[j] ?? 0) + 1;
    }

    // Latest ingestion timestamp
    const { data: latest } = await supabase
      .from("knowledge_base")
      .select("ingested_at")
      .order("ingested_at", { ascending: false })
      .limit(1)
      .single();

    return NextResponse.json({
      totalChunks: totalChunks ?? 0,
      pendingReview: pendingReview ?? 0,
      lastIngestedAt: latest?.ingested_at ?? null,
      bySourceType: sourceTypeCounts,
      byJurisdiction: jurisdictionCounts,
      recentRuns: recentRuns ?? [],
    });
  } catch (err) {
    console.error("[knowledge/status]", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
