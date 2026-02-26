"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  TrendingDown, Mail, Lock, User, ArrowRight, Eye, EyeOff,
  CheckCircle2, Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useSupabase } from "@/hooks/useSupabase";

const BENEFITS = [
  "Full AI tax analysis — free",
  "Personalized IRC-cited strategy",
  "Exact dollar savings calculations",
  "Updated for OBBBA 2025",
];

export default function RegisterPage() {
  const router = useRouter();
  const supabase = useSupabase();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      setLoading(false);
      return;
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName },
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    if (data.session) {
      router.push("/questionnaire");
      router.refresh();
    } else {
      setSuccess(true);
    }

    setLoading(false);
  }

  async function handleGoogleRegister() {
    setLoading(true);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?redirectTo=/questionnaire`,
      },
    });
    if (error) {
      setError(error.message);
      setLoading(false);
    }
  }

  if (success) {
    return (
      <Card glass className="animate-slide-up text-center">
        <CardContent className="pt-8 pb-8 space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center mx-auto">
            <CheckCircle2 className="h-8 w-8 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-bold text-white">Check your email</h2>
          <p className="text-slate-400 text-sm">
            We sent a confirmation link to{" "}
            <span className="text-white font-medium">{email}</span>.
            Click it to activate your account and start your free tax analysis.
          </p>
          <button onClick={() => setSuccess(false)} className="text-xs text-emerald-400 hover:underline">
            Try again
          </button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 justify-center">
        {BENEFITS.map((b) => (
          <div key={b} className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs text-emerald-400" style={{ background: "rgba(6,78,59,0.3)", border: "1px solid rgba(16,185,129,0.2)" }}>
            <Sparkles className="h-3 w-3" />{b}
          </div>
        ))}
      </div>

      <Card glass className="animate-slide-up">
        <CardHeader className="text-center pb-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4">
            <TrendingDown className="h-6 w-6 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Get your free tax plan</h1>
          <p className="text-sm text-slate-400 mt-1">No credit card required · Takes 15 minutes</p>
        </CardHeader>

        <CardContent className="space-y-4">
          <Button variant="outline" className="w-full h-11 gap-3" onClick={handleGoogleRegister} disabled={loading}>
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Continue with Google
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="px-2 text-slate-500" style={{ backgroundColor: "#0a1628" }}>or email</span>
            </div>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName">Full name</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <Input id="fullName" type="text" placeholder="Alex Johnson" value={fullName} onChange={(e) => setFullName(e.target.value)} className="pl-10" required autoComplete="name" />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <Input id="email" type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} className="pl-10" required autoComplete="email" />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <Input id="password" type={showPassword ? "text" : "password"} placeholder="Min. 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} className="pl-10 pr-10" required autoComplete="new-password" minLength={8} />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-lg p-3 text-sm text-red-400" style={{ background: "rgba(127,29,29,0.3)", border: "1px solid rgba(239,68,68,0.3)" }}>
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" size="lg" loading={loading}>
              Create Free Account <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <p className="text-center text-xs text-slate-600">
            By creating an account, you agree to our{" "}
            <Link href="/terms" className="text-slate-400 hover:text-white transition-colors">Terms</Link>
            {" "}and{" "}
            <Link href="/privacy" className="text-slate-400 hover:text-white transition-colors">Privacy Policy</Link>.
            ZeroTax AI is not a law firm or accounting firm.
          </p>

          <p className="text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link href="/login" className="text-emerald-400 hover:text-emerald-300 transition-colors font-medium">Sign in</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
