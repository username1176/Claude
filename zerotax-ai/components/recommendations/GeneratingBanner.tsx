"use client";

// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Generating Banner
// Shown on the recommendation detail page while status === "draft".
// Polls every 4 s then redirects to the same page when complete.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export function GeneratingBanner({
  recommendationId,
}: {
  recommendationId: string;
}) {
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();

    const id = setInterval(async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data } = await (supabase as any)
        .from("recommendations")
        .select("status")
        .eq("id", recommendationId)
        .single();

      if (data?.status && data.status !== "draft") {
        clearInterval(id);
        router.refresh();
      }
    }, 4_000);

    return () => clearInterval(id);
  }, [recommendationId, router]);

  const steps = [
    "Retrieving relevant IRC sections and IRS publications…",
    "Analyzing your financial profile against tax law…",
    "Calculating estimated savings for each strategy…",
    "Ranking strategies by annual savings potential…",
  ];

  return (
    <div className="glass-card rounded-2xl p-10 text-center">
      <div className="flex items-center justify-center gap-3 mb-6">
        <Loader2 className="h-8 w-8 text-emerald-400 animate-spin" />
        <Sparkles className="h-6 w-6 text-emerald-500/60" />
      </div>

      <h2 className="text-xl font-bold text-white mb-2">
        Building Your Tax Fortress Plan
      </h2>
      <p className="text-sm text-slate-400 mb-8 max-w-sm mx-auto">
        Claude is analyzing your profile against 10,000+ pages of tax law.
        This typically takes 30–60 seconds.
      </p>

      <ul className="space-y-2.5 text-left max-w-sm mx-auto">
        {steps.map((step, i) => (
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
  );
}
