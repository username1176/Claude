import Link from "next/link";
import { ArrowRight, CheckCircle2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import type { Database } from "@/types/database.types";

type Profile = Database["public"]["Tables"]["profiles"]["Row"];

const FEATURES_FREE = [
  "1 AI tax analysis",
  "Full IRC-cited recommendations",
  "Exact dollar savings calculation",
  "Implementation checklist",
];

const FEATURES_PREMIUM = [
  "Unlimited AI analyses",
  "PDF report download",
  "Real-time law updates (daily RAG)",
  "Unlimited follow-up AI chat",
  "Attorney referral network",
  "Multi-state strategy analysis",
  "Estate planning deep-dive",
  "Priority support",
];

export default async function BillingPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profileData } = await supabase
    .from("profiles")
    .select("subscription_tier, subscription_status")
    .eq("id", user.id)
    .single();

  const profile = profileData as Pick<Profile, "subscription_tier" | "subscription_status"> | null;

  const isPremium =
    profile?.subscription_tier === "premium" ||
    profile?.subscription_tier === "enterprise";

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-white">Billing & Plan</h1>
        <p className="text-slate-400 mt-1">Upgrade to unlock the full power of ZeroTax AI.</p>
      </div>

      {isPremium && (
        <Card glass className="border-emerald-500/30">
          <CardContent className="p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <div className="text-sm font-semibold text-emerald-400">Premium Active</div>
              <div className="text-xs text-slate-500">You have full access to all ZeroTax AI features</div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <Card glass className={isPremium ? "opacity-60" : ""}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Free Plan</CardTitle>
              {!isPremium && <Badge variant="info">Current</Badge>}
            </div>
            <div className="text-3xl font-bold text-white">$0</div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {FEATURES_FREE.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-slate-400">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card className="border-emerald-500/30 bg-gradient-to-b from-emerald-950/20 to-transparent rounded-xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Premium Plan</CardTitle>
              <Badge variant="default">
                <Zap className="h-3 w-3 mr-1" />
                Most Popular
              </Badge>
            </div>
            <div>
              <span className="text-3xl font-bold text-white">$49</span>
              <span className="text-slate-400 text-sm">/mo</span>
            </div>
            <p className="text-xs text-slate-500">7-day free trial · Cancel anytime</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {FEATURES_PREMIUM.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-white">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            {!isPremium && (
              <Button variant="gradient" className="w-full" size="lg" asChild>
                <Link href="/api/stripe/create-checkout">
                  Start Free Trial
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-slate-600 text-center">
        Stripe integration coming in Prompt 9. ZeroTax AI is not a law firm or accounting firm.
      </p>
    </div>
  );
}
