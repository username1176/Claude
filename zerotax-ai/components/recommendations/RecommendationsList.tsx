"use client";

// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Recommendations List (client component)
// Polls every 4 s while any recommendation is in "draft" status.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Loader2,
  TrendingDown,
  CheckCircle2,
  Clock,
  AlertCircle,
  ArrowRight,
  BookOpen,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RecSummary {
  id: string;
  title: string;
  status: "draft" | "complete" | "outdated" | "archived";
  created_at: string;
  projected_annual_savings: number | null;
  executive_summary: string | null;
  recommended_entity_structure: string | null;
  law_version_date: string | null;
  rag_chunks_used: number | null;
}

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: RecSummary["status"] }) {
  const map = {
    draft: {
      label: "Generating…",
      cls: "bg-amber-950/40 text-amber-400 border-amber-500/20",
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
    },
    complete: {
      label: "Ready",
      cls: "bg-emerald-950/40 text-emerald-400 border-emerald-500/20",
      icon: <CheckCircle2 className="h-3 w-3" />,
    },
    outdated: {
      label: "Failed",
      cls: "bg-red-950/40 text-red-400 border-red-500/20",
      icon: <AlertCircle className="h-3 w-3" />,
    },
    archived: {
      label: "Archived",
      cls: "bg-slate-800/60 text-slate-500 border-slate-700/30",
      icon: <Clock className="h-3 w-3" />,
    },
  };
  const { label, cls, icon } = map[status] ?? map.archived;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border",
        cls
      )}
    >
      {icon}
      {label}
    </span>
  );
}

// ─── Single recommendation card ───────────────────────────────────────────────

function RecCard({ rec }: { rec: RecSummary }) {
  const date = new Date(rec.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="glass-card rounded-2xl p-5 md:p-6 hover:border-white/10 transition-colors group">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white truncate">
            {rec.title}
          </h3>
          <p className="text-xs text-slate-600 mt-0.5">{date}</p>
        </div>
        <StatusBadge status={rec.status} />
      </div>

      {rec.status === "draft" && (
        <div className="flex items-center gap-2 text-xs text-amber-400/70 mb-3">
          <Sparkles className="h-3.5 w-3.5" />
          Claude is analyzing your profile and retrieving tax law documents…
        </div>
      )}

      {rec.status === "complete" && (
        <>
          {rec.projected_annual_savings != null &&
            rec.projected_annual_savings > 0 && (
              <div className="flex items-center gap-2 mb-3">
                <TrendingDown className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                <span className="text-base font-bold text-emerald-400">
                  {formatCurrency(rec.projected_annual_savings)}/yr
                </span>
                <span className="text-xs text-slate-500">
                  estimated savings
                </span>
              </div>
            )}

          {rec.executive_summary && (
            <p className="text-xs text-slate-400 leading-relaxed line-clamp-2 mb-3">
              {rec.executive_summary}
            </p>
          )}

          <div className="flex items-center gap-4 text-xs text-slate-600">
            {rec.recommended_entity_structure && (
              <span>→ {rec.recommended_entity_structure}</span>
            )}
            {rec.rag_chunks_used != null && rec.rag_chunks_used > 0 && (
              <span className="flex items-center gap-1">
                <BookOpen className="h-3 w-3" />
                {rec.rag_chunks_used} docs cited
              </span>
            )}
          </div>
        </>
      )}

      {rec.status === "outdated" && (
        <p className="text-xs text-red-400/70">
          Generation failed. Try creating a new plan.
        </p>
      )}

      {rec.status === "complete" && (
        <div className="mt-4">
          <Link
            href={`/recommendations/${rec.id}`}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors group-hover:gap-2"
          >
            View full plan
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>
      )}
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="glass-card rounded-2xl p-10 text-center">
      <div className="text-4xl mb-3">🏰</div>
      <h2 className="text-lg font-semibold text-white mb-2">
        No plans yet
      </h2>
      <p className="text-sm text-slate-400 mb-5 max-w-xs mx-auto">
        Complete the questionnaire to generate your personalized Zero-Tax
        Fortress Plan.
      </p>
      <Link
        href="/questionnaire"
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition-colors"
      >
        <Sparkles className="h-4 w-4" />
        Start Questionnaire
      </Link>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function RecommendationsList({
  initialItems,
  userId,
}: {
  initialItems: RecSummary[];
  userId: string;
}) {
  const [items, setItems] = useState<RecSummary[]>(initialItems);

  const hasDraft = items.some((r) => r.status === "draft");

  const refresh = useCallback(async () => {
    const supabase = createClient();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data } = await (supabase as any)
      .from("recommendations")
      .select(
        "id, title, status, created_at, projected_annual_savings, " +
          "executive_summary, recommended_entity_structure, law_version_date, " +
          "rag_chunks_used"
      )
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(20);
    if (data) setItems(data as RecSummary[]);
  }, [userId]);

  // Poll every 4 s while a draft recommendation exists
  useEffect(() => {
    if (!hasDraft) return;
    const id = setInterval(refresh, 4_000);
    return () => clearInterval(id);
  }, [hasDraft, refresh]);

  if (items.length === 0) return <EmptyState />;

  return (
    <div className="space-y-3">
      {items.map((rec) => (
        <RecCard key={rec.id} rec={rec} />
      ))}
    </div>
  );
}
