// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Recommendation Detail Page
// Full tax plan: executive summary, entity recommendation, savings projections,
// strategies with IRC citations, and action item checklists.
// ─────────────────────────────────────────────────────────────────────────────

import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingDown,
  Building2,
  Target,
  BookOpen,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Gavel,
  Calculator,
} from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils";
import { GeneratingBanner } from "@/components/recommendations/GeneratingBanner";

export const dynamic = "force-dynamic";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Recommendation {
  id: string;
  title: string;
  status: "draft" | "complete" | "outdated" | "archived";
  created_at: string;
  executive_summary: string | null;
  recommended_entity_structure: string | null;
  entity_rationale: string | null;
  current_estimated_tax: number | null;
  optimized_estimated_tax: number | null;
  projected_annual_savings: number | null;
  projected_10yr_savings: number | null;
  savings_breakdown: Record<string, number> | null;
  law_version_date: string | null;
  rag_chunks_used: number | null;
  model_used: string;
}

interface Strategy {
  id: string;
  category: string;
  title: string;
  description: string;
  detailed_explanation: string | null;
  irc_sections: string[] | null;
  obbba_sections: string[] | null;
  state_law_refs: string[] | null;
  irs_publications: string[] | null;
  estimated_annual_savings: number | null;
  implementation_cost: number | null;
  payback_period_months: number | null;
  priority: "critical" | "high" | "medium" | "low";
  complexity: "simple" | "medium" | "complex" | "attorney_required";
  timeline_days: number | null;
  requires_attorney: boolean;
  requires_cpa: boolean;
  action_items: string[] | null;
  sort_order: number;
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent = false,
  icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
  icon: React.ElementType;
}) {
  return (
    <div
      className={cn(
        "rounded-xl p-4 border",
        accent
          ? "bg-emerald-950/30 border-emerald-500/20"
          : "bg-white/[0.03] border-white/10"
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon
          className={cn(
            "h-4 w-4",
            accent ? "text-emerald-400" : "text-slate-400"
          )}
        />
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <div
        className={cn(
          "text-xl font-bold",
          accent ? "text-emerald-400" : "text-white"
        )}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-slate-600 mt-0.5">{sub}</div>}
    </div>
  );
}

// ─── Priority badge ───────────────────────────────────────────────────────────

function PriorityBadge({ priority }: { priority: Strategy["priority"] }) {
  const map = {
    critical: "bg-red-950/40 text-red-400 border-red-500/20",
    high: "bg-orange-950/40 text-orange-400 border-orange-500/20",
    medium: "bg-amber-950/40 text-amber-400 border-amber-500/20",
    low: "bg-slate-800/60 text-slate-500 border-slate-700/30",
  };
  return (
    <span
      className={cn(
        "text-xs font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wide",
        map[priority]
      )}
    >
      {priority}
    </span>
  );
}

// ─── Strategy Card ────────────────────────────────────────────────────────────

function StrategyCard({ s, idx }: { s: Strategy; idx: number }) {
  const citations = [
    ...(s.irc_sections ?? []).map((c) => `IRC §${c}`),
    ...(s.obbba_sections ?? []).map((c) => `OBBBA §${c}`),
    ...(s.irs_publications ?? []).map((c) => `IRS Pub. ${c}`),
  ];

  const complexityLabel = {
    simple: "Simple",
    medium: "Moderate",
    complex: "Complex",
    attorney_required: "Attorney Required",
  }[s.complexity];

  return (
    <div className="glass-card rounded-xl p-5 md:p-6">
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <span className="text-xs font-bold text-slate-600 flex-shrink-0 mt-1 w-5 text-right">
          {idx + 1}.
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-white">{s.title}</h3>
            <PriorityBadge priority={s.priority} />
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {s.description}
          </p>
        </div>
      </div>

      {/* Key numbers */}
      <div className="flex flex-wrap gap-4 mb-4 pl-8">
        {s.estimated_annual_savings != null &&
          s.estimated_annual_savings > 0 && (
            <div>
              <div className="text-xs text-slate-600">Annual Savings</div>
              <div className="text-sm font-bold text-emerald-400">
                {formatCurrency(s.estimated_annual_savings)}
              </div>
            </div>
          )}
        {s.implementation_cost != null && s.implementation_cost > 0 && (
          <div>
            <div className="text-xs text-slate-600">Impl. Cost</div>
            <div className="text-sm font-semibold text-white">
              {formatCurrency(s.implementation_cost)}
            </div>
          </div>
        )}
        {s.timeline_days != null && (
          <div>
            <div className="text-xs text-slate-600">Timeline</div>
            <div className="text-sm font-semibold text-white">
              {s.timeline_days < 30
                ? `${s.timeline_days}d`
                : `${Math.round(s.timeline_days / 30)}mo`}
            </div>
          </div>
        )}
      </div>

      {/* Detailed explanation */}
      {s.detailed_explanation && (
        <div className="pl-8 mb-4">
          <p className="text-xs text-slate-400 leading-relaxed">
            {s.detailed_explanation}
          </p>
        </div>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div className="pl-8 flex flex-wrap gap-1.5 mb-4">
          {citations.map((c, i) => (
            <span
              key={i}
              className="text-xs px-2 py-0.5 rounded-md bg-blue-950/30 text-blue-400 border border-blue-500/15 font-mono"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Meta */}
      <div className="pl-8 flex flex-wrap gap-3 text-xs text-slate-600 mb-4">
        <span>{complexityLabel}</span>
        {s.requires_attorney && (
          <span className="flex items-center gap-1 text-amber-500/70">
            <Gavel className="h-3 w-3" />
            Attorney required
          </span>
        )}
        {s.requires_cpa && (
          <span className="flex items-center gap-1">
            <Calculator className="h-3 w-3" />
            CPA required
          </span>
        )}
      </div>

      {/* Action items */}
      {s.action_items && s.action_items.length > 0 && (
        <details className="pl-8">
          <summary className="text-xs font-medium text-slate-500 cursor-pointer hover:text-slate-300 transition-colors flex items-center gap-1 select-none">
            <ChevronDown className="h-3.5 w-3.5" />
            Implementation steps ({s.action_items.length})
          </summary>
          <ol className="mt-2.5 space-y-1.5">
            {s.action_items.map((step, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-emerald-500 text-xs font-bold flex-shrink-0 mt-0.5">
                  {i + 1}.
                </span>
                <span className="text-xs text-slate-400 leading-relaxed">
                  {step}
                </span>
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

// ─── Savings Breakdown ────────────────────────────────────────────────────────

function SavingsBreakdown({
  breakdown,
  total,
}: {
  breakdown: Record<string, number>;
  total: number;
}) {
  const entries = Object.entries(breakdown)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a);

  if (entries.length === 0) return null;

  const labels: Record<string, string> = {
    entity_restructuring: "Entity Restructuring",
    retirement_plans: "Retirement Plans",
    qbi_deduction: "QBI Deduction",
    depreciation: "Depreciation",
    family_employment: "Family Employment",
    asset_protection: "Asset Protection",
    other: "Other Strategies",
  };

  return (
    <div className="glass-card rounded-2xl p-5 md:p-6">
      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        <TrendingDown className="h-4 w-4 text-emerald-400" />
        Savings breakdown
      </h3>
      <div className="space-y-3">
        {entries.map(([key, val]) => {
          const pct = total > 0 ? (val / total) * 100 : 0;
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-400">
                  {labels[key] ?? key}
                </span>
                <span className="text-xs font-semibold text-white">
                  {formatCurrency(val)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-emerald-500/70 transition-all"
                  style={{ width: `${Math.min(pct, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function RecommendationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const db = supabase as any;

  const { data: rec } = await db
    .from("recommendations")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!rec) notFound();

  const recommendation = rec as Recommendation;

  // If still generating, show a banner page
  if (recommendation.status === "draft") {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <Link
          href="/recommendations"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to plans
        </Link>
        <GeneratingBanner recommendationId={id} />
      </div>
    );
  }

  if (recommendation.status === "outdated") {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <Link
          href="/recommendations"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to plans
        </Link>
        <div className="glass-card rounded-2xl p-8 text-center">
          <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-white mb-2">
            Generation Failed
          </h2>
          <p className="text-sm text-slate-400 mb-5">
            There was an error generating this plan. Please try again.
          </p>
          <Link
            href="/questionnaire"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition-colors"
          >
            Start new questionnaire
          </Link>
        </div>
      </div>
    );
  }

  // Fetch strategies
  const { data: strategiesData } = await db
    .from("strategies")
    .select("*")
    .eq("recommendation_id", id)
    .order("sort_order", { ascending: true });

  const strategies = (strategiesData ?? []) as Strategy[];

  const createdDate = new Date(recommendation.created_at).toLocaleDateString(
    "en-US",
    { month: "long", day: "numeric", year: "numeric" }
  );

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* Back link */}
      <Link
        href="/recommendations"
        className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to plans
      </Link>

      {/* Header */}
      <div className="glass-card rounded-2xl p-6 md:p-8">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-white">
              {recommendation.title}
            </h1>
            <p className="text-xs text-slate-600 mt-1">
              Generated {createdDate}
              {recommendation.law_version_date &&
                ` · Law version: ${recommendation.law_version_date}`}
              {recommendation.rag_chunks_used != null &&
                recommendation.rag_chunks_used > 0 &&
                ` · ${recommendation.rag_chunks_used} tax docs cited`}
            </p>
          </div>
          <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
        </div>

        {recommendation.executive_summary && (
          <p className="text-sm text-slate-300 leading-relaxed">
            {recommendation.executive_summary}
          </p>
        )}
      </div>

      {/* Entity recommendation */}
      {recommendation.recommended_entity_structure && (
        <div className="glass-card rounded-2xl p-5 md:p-6">
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-slate-400" />
            Recommended Entity Structure
          </h2>
          <p className="text-base font-bold text-white mb-2">
            {recommendation.recommended_entity_structure}
          </p>
          {recommendation.entity_rationale && (
            <p className="text-xs text-slate-400 leading-relaxed">
              {recommendation.entity_rationale}
            </p>
          )}
        </div>
      )}

      {/* Tax stats grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Current Tax Burden"
          value={
            recommendation.current_estimated_tax != null
              ? formatCurrency(recommendation.current_estimated_tax)
              : "—"
          }
          sub="Estimated annual"
          icon={Target}
        />
        <StatCard
          label="Optimized Tax Burden"
          value={
            recommendation.optimized_estimated_tax != null
              ? formatCurrency(recommendation.optimized_estimated_tax)
              : "—"
          }
          sub="After top strategies"
          icon={TrendingDown}
        />
        <StatCard
          label="Annual Savings"
          value={
            recommendation.projected_annual_savings != null
              ? formatCurrency(recommendation.projected_annual_savings)
              : "—"
          }
          sub="Conservative estimate"
          icon={TrendingDown}
          accent
        />
        <StatCard
          label="10-Year Savings"
          value={
            recommendation.projected_10yr_savings != null
              ? formatCurrency(recommendation.projected_10yr_savings)
              : "—"
          }
          sub="Non-compounded"
          icon={Clock}
          accent
        />
      </div>

      {/* Savings breakdown */}
      {recommendation.savings_breakdown &&
        recommendation.projected_annual_savings != null && (
          <SavingsBreakdown
            breakdown={
              recommendation.savings_breakdown as Record<string, number>
            }
            total={recommendation.projected_annual_savings}
          />
        )}

      {/* Strategies */}
      {strategies.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-slate-400" />
            {strategies.length} Tax Strategies — Ranked by Savings
          </h2>
          {strategies.map((s, i) => (
            <StrategyCard key={s.id} s={s} idx={i} />
          ))}
        </div>
      )}

      {/* Disclaimer */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-950/20 border border-amber-500/10">
        <AlertTriangle className="h-4 w-4 text-amber-500/70 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-slate-500 leading-relaxed">
          ZeroTax AI provides educational information only. Nothing here
          constitutes legal, tax, or financial advice. All strategies require
          review by a qualified CPA or tax attorney before implementation.
          Tax laws change frequently — verify current law before acting.
          Law version date: {recommendation.law_version_date ?? "current"}.
        </p>
      </div>
    </div>
  );
}
