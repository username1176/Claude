import { redirect } from "next/navigation";
import Link from "next/link";
import {
  TrendingDown, ArrowRight, Lightbulb, ClipboardList,
  FileText, Zap, DollarSign, BarChart3, CheckCircle2, AlertCircle
} from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import type { Database } from "@/types/database.types";

type Profile = Database["public"]["Tables"]["profiles"]["Row"];
type Recommendation = Database["public"]["Tables"]["recommendations"]["Row"];

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const [{ data: profileData }, { data: businesses }, { data: recommendationsData }] =
    await Promise.all([
      supabase.from("profiles").select("*").eq("id", user.id).single(),
      supabase.from("businesses").select("id").eq("user_id", user.id).eq("is_active", true),
      supabase
        .from("recommendations")
        .select("*")
        .eq("user_id", user.id)
        .eq("status", "complete")
        .order("created_at", { ascending: false })
        .limit(3),
    ]);

  const profile = profileData as Profile | null;
  const recommendations = recommendationsData as Recommendation[] | null;
  const firstName = profile?.full_name?.split(" ")[0] ?? "there";
  const hasCompletedQuestionnaire = (businesses?.length ?? 0) > 0;

  const totalSavings = recommendations?.reduce(
    (sum, r) => sum + (r.projected_annual_savings ?? 0), 0
  ) ?? 0;
  const total10yr = recommendations?.reduce(
    (sum, r) => sum + (r.projected_10yr_savings ?? 0), 0
  ) ?? 0;

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-white">Welcome back, {firstName} 👋</h1>
        <p className="text-slate-400 mt-1">Your personalized tax optimization command center.</p>
      </div>

      {!hasCompletedQuestionnaire && (
        <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-r from-emerald-950/40 to-indigo-950/40 p-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-900/60 border border-emerald-500/30 flex items-center justify-center shrink-0">
                <Zap className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Start your tax analysis</h2>
                <p className="text-sm text-slate-400 mt-1 max-w-md">
                  Answer 15 quick questions about your business. Our AI will identify
                  every legal strategy to minimize your taxes — with exact dollar savings.
                </p>
              </div>
            </div>
            <Button variant="gradient" size="lg" asChild className="shrink-0">
              <Link href="/questionnaire">
                Start Questionnaire <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            {["Takes 15 minutes", "IRC citations included", "Exact dollar calculations", "Free to use"].map((item) => (
              <div key={item} className="flex items-center gap-1.5 text-xs text-emerald-400/80">
                <CheckCircle2 className="h-3 w-3" />{item}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Annual Tax Savings", value: totalSavings > 0 ? formatCurrency(totalSavings) : "–", sub: "Projected from strategies", Icon: TrendingDown, colorClass: "text-emerald-400", iconBg: "bg-emerald-900/40 border-emerald-500/20" },
          { label: "10-Year Savings", value: total10yr > 0 ? formatCurrency(total10yr) : "–", sub: "Compound benefit", Icon: BarChart3, colorClass: "text-purple-400", iconBg: "bg-purple-900/40 border-purple-500/20" },
          { label: "Recommendations", value: String(recommendations?.length ?? 0), sub: "AI-generated plans", Icon: Lightbulb, colorClass: "text-yellow-400", iconBg: "bg-yellow-900/40 border-yellow-500/20" },
          { label: "Plan Status", value: hasCompletedQuestionnaire ? "Active" : "Start Now", sub: hasCompletedQuestionnaire ? "Optimizing" : "No plan yet", Icon: hasCompletedQuestionnaire ? CheckCircle2 : AlertCircle, colorClass: hasCompletedQuestionnaire ? "text-blue-400" : "text-slate-400", iconBg: hasCompletedQuestionnaire ? "bg-blue-900/40 border-blue-500/20" : "bg-slate-900/40 border-slate-500/20" },
        ].map((stat) => (
          <Card key={stat.label} glass>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">{stat.label}</span>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${stat.iconBg}`}>
                  <stat.Icon className={`h-4 w-4 ${stat.colorClass}`} />
                </div>
              </div>
              <div className={`text-2xl font-bold ${stat.colorClass} mb-1`}>{stat.value}</div>
              <div className="text-xs text-slate-500">{stat.sub}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {(recommendations?.length ?? 0) > 0 ? (
        <Card glass>
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="text-lg">Recent Recommendations</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/recommendations">View all <ArrowRight className="h-3.5 w-3.5" /></Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {recommendations!.map((rec) => (
              <Link key={rec.id} href={`/recommendations/${rec.id}`}
                className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] p-4 hover:border-white/10 hover:bg-white/[0.04] transition-all group">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-emerald-900/40 border border-emerald-500/20 flex items-center justify-center">
                    <Lightbulb className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">{rec.title}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{rec.recommended_entity_structure ?? "Custom strategy"}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {rec.projected_annual_savings != null && (
                    <div className="text-right">
                      <div className="text-sm font-semibold text-emerald-400">{formatCurrency(rec.projected_annual_savings)}/yr</div>
                      <div className="text-xs text-slate-500">projected savings</div>
                    </div>
                  )}
                  <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      ) : (
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { href: "/questionnaire", Icon: ClipboardList, title: "Complete Questionnaire", desc: "Answer questions about your business, income, and goals", iconColor: "text-emerald-400", iconBg: "bg-emerald-900/40 border-emerald-500/20" },
            { href: "/recommendations", Icon: Lightbulb, title: "View Strategies", desc: "Browse AI-identified tax strategies for your situation", iconColor: "text-purple-400", iconBg: "bg-purple-900/40 border-purple-500/20" },
            { href: "/reports", Icon: FileText, title: "Generate PDF Report", desc: "Download a professional tax plan to share with your CPA", iconColor: "text-blue-400", iconBg: "bg-blue-900/40 border-blue-500/20" },
          ].map((card) => (
            <Link key={card.href} href={card.href} className="glass-card rounded-xl p-5 hover:border-white/15 transition-all group">
              <div className={`w-10 h-10 rounded-xl border flex items-center justify-center mb-3 ${card.iconBg}`}>
                <card.Icon className={`h-5 w-5 ${card.iconColor}`} />
              </div>
              <h3 className="text-sm font-semibold text-white group-hover:text-emerald-400 transition-colors mb-1">{card.title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{card.desc}</p>
            </Link>
          ))}
        </div>
      )}

      {profile?.subscription_tier === "free" && (
        <Card glass className="border-emerald-500/20">
          <CardContent className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center">
                <DollarSign className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Upgrade to Premium — $49/mo</div>
                <div className="text-xs text-slate-500 mt-0.5">Unlock PDF reports, real-time law updates, unlimited AI chat, and attorney referrals</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="default" className="text-xs whitespace-nowrap">7-day free trial</Badge>
              <Button variant="gradient" size="sm" asChild>
                <Link href="/billing">Upgrade <ArrowRight className="h-3.5 w-3.5" /></Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
