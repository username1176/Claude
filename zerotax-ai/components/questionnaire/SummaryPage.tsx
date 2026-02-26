"use client";

// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Summary Page
// Shown after all adaptive questions are answered. Displays the full profile
// summary, estimated strategies, and the "Generate My Zero-Tax Fortress Plan"
// CTA that triggers the AI recommendation engine.
// ─────────────────────────────────────────────────────────────────────────────

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  Shield,
  TrendingDown,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Loader2,
} from "lucide-react";
import {
  estimateStrategies,
  mapAnswersToDb,
  STAGE_LABELS,
  ENTITY_LABELS,
  ASSET_LABELS,
  HORIZON_LABELS,
  RISK_LABELS,
  EXIT_LABELS,
  COUNTRY_LABELS,
  GOAL_LABELS,
} from "@/lib/question-engine";
import { useAdaptiveStore } from "@/store/adaptive-questionnaire";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils";
import { US_STATES } from "@/lib/utils";

// ─── Helper: look up state label from code ────────────────────────────────────

function stateLabel(code: string): string {
  return US_STATES.find((s) => s.value === code)?.label ?? code;
}

// ─── Summary Row ──────────────────────────────────────────────────────────────

function SummaryRow({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string | null | undefined;
  highlight?: boolean;
}) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-4 py-2.5 border-b border-white/5 last:border-0">
      <span className="text-xs text-slate-500 flex-shrink-0 pt-0.5">{label}</span>
      <span
        className={cn(
          "text-sm text-right font-medium",
          highlight ? "text-emerald-400" : "text-slate-200"
        )}
      >
        {value}
      </span>
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sublabel,
  icon: Icon,
  accent = false,
}: {
  label: string;
  value: string;
  sublabel?: string;
  icon: React.ElementType;
  accent?: boolean;
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
      {sublabel && (
        <div className="text-xs text-slate-600 mt-0.5">{sublabel}</div>
      )}
    </div>
  );
}

// ─── Main SummaryPage ─────────────────────────────────────────────────────────

export function SummaryPage() {
  const store = useAdaptiveStore();
  const router = useRouter();
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const answers = store.answers;
  const estimate = estimateStrategies(answers);

  // ── Build summary sections ─────────────────────────────────────────────────
  const goals = (answers.goals as string[]) ?? [];

  const savingsText =
    estimate.annualSavingsMin > 0
      ? `${formatCurrency(estimate.annualSavingsMin)} – ${formatCurrency(estimate.annualSavingsMax)}/yr`
      : "Based on your profile";

  // ── Handle Generate click ──────────────────────────────────────────────────
  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await fetch("/api/questionnaire/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          businessId: store.businessId,
          questionnaireId: store.questionnaireId,
          data: mapAnswersToDb(answers),
        }),
      });

      if (!res.ok) {
        const json = (await res.json()) as { error?: string };
        throw new Error(json.error ?? "Submission failed");
      }

      const json = (await res.json()) as {
        businessId: string;
        questionnaireId: string;
        recommendationId: string | null;
      };

      if (json.businessId) store.setBusinessId(json.businessId);
      if (json.questionnaireId) store.setQuestionnaireId(json.questionnaireId);
      if (json.recommendationId) store.setRecommendationId(json.recommendationId);

      router.push("/recommendations");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-slide-up pb-12">
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <div className="glass-card rounded-2xl p-7 md:p-9 text-center relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative">
          <div className="text-5xl mb-3">🎯</div>
          <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
            Your Zero-Tax Profile is{" "}
            <span className="gradient-text">Ready</span>
          </h1>
          <p className="text-slate-400 text-sm max-w-md mx-auto leading-relaxed">
            Based on your answers, our AI has identified{" "}
            <span className="text-white font-semibold">
              {estimate.strategyCount} legal tax strategies
            </span>{" "}
            tailored to your exact situation.
          </p>
        </div>
      </div>

      {/* ── Stats Grid ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Potential Annual Savings"
          value={savingsText}
          sublabel="Conservative estimate"
          icon={TrendingDown}
          accent
        />
        <StatCard
          label="Strategies Identified"
          value={`${estimate.strategyCount} strategies`}
          sublabel="Personalized to your profile"
          icon={Sparkles}
        />
      </div>

      {/* ── Strategy Highlights ───────────────────────────────────────────── */}
      {estimate.highlights.length > 0 && (
        <div className="glass-card rounded-2xl p-5 md:p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-emerald-400" />
            Top strategies we identified for you
          </h3>
          <ul className="space-y-2.5">
            {estimate.highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-3">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-slate-300 leading-snug">{h}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Profile Summary ───────────────────────────────────────────────── */}
      <div className="glass-card rounded-2xl p-5 md:p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Shield className="h-4 w-4 text-slate-400" />
          Your profile summary
        </h3>

        {/* Location & Business */}
        <div className="mb-4">
          <p className="text-xs font-medium text-slate-600 uppercase tracking-wider mb-2">
            Location & Business
          </p>
          <SummaryRow
            label="Country"
            value={COUNTRY_LABELS[answers.country as string]}
          />
          <SummaryRow
            label="State"
            value={answers.state ? stateLabel(answers.state as string) : null}
          />
          <SummaryRow
            label="Business stage"
            value={STAGE_LABELS[answers.business_stage as string]}
          />
        </div>

        {/* Structure & Revenue */}
        <div className="mb-4">
          <p className="text-xs font-medium text-slate-600 uppercase tracking-wider mb-2">
            Structure & Revenue
          </p>
          <SummaryRow
            label="Entity type"
            value={ENTITY_LABELS[answers.entity_type as string]}
            highlight={["sole_prop", "single_llc", "multi_llc"].includes(
              answers.entity_type as string
            )}
          />
          <SummaryRow
            label="Annual revenue"
            value={
              answers.annual_revenue
                ? formatCurrency(Number(answers.annual_revenue))
                : null
            }
          />
          <SummaryRow
            label="Annual profit"
            value={
              answers.annual_profit
                ? formatCurrency(Number(answers.annual_profit))
                : null
            }
          />
          <SummaryRow
            label="W-2 wages paid"
            value={
              answers.w2_wages
                ? formatCurrency(Number(answers.w2_wages))
                : null
            }
          />
        </div>

        {/* Assets */}
        <div className="mb-4">
          <p className="text-xs font-medium text-slate-600 uppercase tracking-wider mb-2">
            Assets & Wealth
          </p>
          <SummaryRow
            label="Total assets"
            value={ASSET_LABELS[answers.total_assets as string]}
            highlight={["500k_1m", "1m_5m", "over_5m"].includes(
              answers.total_assets as string
            )}
          />
          <SummaryRow
            label="Real estate"
            value={
              answers.real_estate
                ? formatCurrency(Number(answers.real_estate))
                : null
            }
          />
          <SummaryRow
            label="QSBS eligible"
            value={
              answers.has_qsbs !== undefined
                ? answers.has_qsbs
                  ? "Yes ✅"
                  : "No"
                : null
            }
          />
        </div>

        {/* Family */}
        <div className="mb-4">
          <p className="text-xs font-medium text-slate-600 uppercase tracking-wider mb-2">
            Family
          </p>
          <SummaryRow
            label="Married / partner"
            value={
              answers.married !== undefined
                ? answers.married
                  ? "Yes"
                  : "No"
                : null
            }
          />
          <SummaryRow
            label="Children"
            value={
              answers.children_count
                ? (
                    {
                      "0": "None",
                      "1": "1 child",
                      "2": "2 children",
                      "3": "3 children",
                      "4_plus": "4 or more",
                    } as Record<string, string>
                  )[answers.children_count as string]
                : null
            }
          />
        </div>

        {/* Goals & Strategy */}
        <div>
          <p className="text-xs font-medium text-slate-600 uppercase tracking-wider mb-2">
            Goals & Strategy
          </p>
          {goals.length > 0 && (
            <SummaryRow
              label="Goals"
              value={goals.map((g) => GOAL_LABELS[g]).join(", ")}
            />
          )}
          <SummaryRow
            label="Risk tolerance"
            value={RISK_LABELS[answers.risk_tolerance as string]}
          />
          <SummaryRow
            label="Planning horizon"
            value={HORIZON_LABELS[answers.planning_horizon as string]}
          />
          <SummaryRow
            label="Exit timeline"
            value={
              answers.exit_timeline
                ? EXIT_LABELS[answers.exit_timeline as string]
                : null
            }
          />
        </div>
      </div>

      {/* ── Error ─────────────────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-red-950/30 border border-red-500/20 text-sm text-red-300">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* ── Primary CTA ───────────────────────────────────────────────────── */}
      <button
        onClick={handleGenerate}
        disabled={isGenerating}
        className={cn(
          "w-full py-5 rounded-2xl font-bold text-lg transition-all duration-300 flex items-center justify-center gap-3",
          isGenerating
            ? "bg-emerald-800/50 text-emerald-300 cursor-not-allowed"
            : "bg-emerald-600 hover:bg-emerald-500 text-white glow-emerald hover:scale-[1.02] active:scale-100"
        )}
      >
        {isGenerating ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            Generating your plan…
          </>
        ) : (
          <>
            🏰 Generate My Zero-Tax Fortress Plan
            <ArrowRight className="h-5 w-5" />
          </>
        )}
      </button>

      {/* ── What happens next ─────────────────────────────────────────────── */}
      <div className="glass-card rounded-xl p-5">
        <p className="text-xs font-semibold text-slate-400 mb-3">
          What happens when you click Generate:
        </p>
        <ul className="space-y-2">
          {[
            "Claude AI analyzes your profile against 10,000+ pages of tax law",
            "Our RAG engine retrieves the most relevant IRC sections and IRS publications",
            "We generate a personalized strategy ranked by estimated annual savings",
            "Your plan is ready in seconds — no email required",
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-2.5">
              <span className="text-emerald-500 text-xs font-bold flex-shrink-0 mt-0.5">
                {i + 1}.
              </span>
              <span className="text-xs text-slate-400 leading-relaxed">
                {step}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* ── Disclaimer ────────────────────────────────────────────────────── */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-950/20 border border-amber-500/10">
        <AlertTriangle className="h-4 w-4 text-amber-500/70 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-slate-500 leading-relaxed">
          ZeroTax AI provides educational information only. Nothing here
          constitutes legal, tax, or financial advice. All strategies require
          review by a qualified CPA or tax attorney before implementation.
          Tax laws change frequently — verify current law before acting.
        </p>
      </div>

      {/* ── Start Over ────────────────────────────────────────────────────── */}
      <div className="text-center">
        <button
          onClick={() => store.reset()}
          className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-400 transition-colors mx-auto"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Start over with different answers
        </button>
      </div>
    </div>
  );
}
