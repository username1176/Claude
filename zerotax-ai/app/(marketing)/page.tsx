import Link from "next/link";
import {
  ArrowRight,
  Shield,
  Zap,
  TrendingDown,
  CheckCircle2,
  Star,
  Building2,
  Calculator,
  FileText,
  Lock,
  ChevronRight,
  Sparkles,
  DollarSign,
  BarChart3,
  BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";

// ─── Hero Section ──────────────────────────────────────────────────────────────
function HeroSection() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-[#050d1a]" />
      <div className="absolute inset-0 dot-grid opacity-60" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-emerald-900/10 blur-[120px]" />
      <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full bg-indigo-900/10 blur-[100px]" />

      <div className="relative z-10 max-w-6xl mx-auto px-6 text-center">
        {/* Launch badge */}
        <div className="inline-flex items-center gap-2 bg-emerald-950/60 border border-emerald-500/30 rounded-full px-4 py-1.5 mb-8 text-sm text-emerald-400">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Powered by Claude AI · Updated for OBBBA 2025</span>
          <ChevronRight className="h-3 w-3 opacity-60" />
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-tight">
          <span className="text-white">Legally reduce your</span>
          <br />
          <span className="gradient-text">taxes to zero.</span>
        </h1>

        <p className="text-xl md:text-2xl text-slate-400 max-w-3xl mx-auto mb-10 leading-relaxed">
          AI-powered tax strategy that outperforms any human accountant.
          Get a personalized plan citing exact IRC sections, with projected savings
          calculated to the dollar — in minutes, not months.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <Button size="xl" variant="gradient" asChild className="glow-emerald">
            <Link href="/register">
              Get My Free Tax Plan
              <ArrowRight className="h-5 w-5" />
            </Link>
          </Button>
          <Button size="xl" variant="outline" asChild>
            <Link href="#how-it-works">
              See How It Works
            </Link>
          </Button>
        </div>

        {/* Social proof bar */}
        <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <div className="flex">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
              ))}
            </div>
            <span>4.9/5 from 2,100+ users</span>
          </div>
          <div className="h-4 w-px bg-white/10 hidden sm:block" />
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-400" />
            <span>$47M+ projected savings generated</span>
          </div>
          <div className="h-4 w-px bg-white/10 hidden sm:block" />
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-blue-400" />
            <span>SOC 2 compliant · Bank-grade security</span>
          </div>
        </div>
      </div>

      {/* Dashboard preview mockup */}
      <div className="relative z-10 w-full max-w-5xl mx-auto px-6 mt-16">
        <div className="glass-card rounded-2xl overflow-hidden border border-white/10 shadow-glass">
          {/* Fake browser chrome */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 bg-white/[0.02]">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/70" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
              <div className="w-3 h-3 rounded-full bg-green-500/70" />
            </div>
            <div className="flex-1 mx-4 bg-white/5 rounded-md h-6 flex items-center px-3 text-xs text-slate-500">
              zerotax.ai/dashboard
            </div>
          </div>

          {/* Dashboard content preview */}
          <div className="p-6 bg-[#070f1e]">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {[
                { label: "Projected Annual Savings", value: "$84,320", color: "emerald", icon: TrendingDown },
                { label: "10-Year Tax Savings", value: "$843,200", color: "purple", icon: BarChart3 },
                { label: "Strategies Identified", value: "12", color: "blue", icon: CheckCircle2 },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl border border-white/8 bg-white/[0.03] p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-500">{stat.label}</span>
                    <stat.icon className={`h-4 w-4 text-${stat.color}-400`} />
                  </div>
                  <div className={`text-2xl font-bold text-${stat.color}-400`}>{stat.value}</div>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              {[
                { title: "LLC → S-Corp Election", savings: "$22,400/yr", priority: "Critical", badge: "entity_structure" },
                { title: "Solo 401(k) + Defined Benefit Plan", savings: "$35,000/yr", priority: "Critical", badge: "retirement" },
                { title: "100% Bonus Depreciation (§168k)", savings: "$18,200/yr", priority: "High", badge: "depreciation" },
              ].map((strategy) => (
                <div
                  key={strategy.title}
                  className="flex items-center justify-between rounded-lg border border-white/8 bg-white/[0.02] px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${strategy.priority === "Critical" ? "bg-red-400" : "bg-yellow-400"}`} />
                    <div>
                      <div className="text-sm font-medium text-white">{strategy.title}</div>
                      <div className="text-xs text-slate-500">IRC §199A · OBBBA 2025</div>
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-emerald-400">{strategy.savings}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Stats Section ─────────────────────────────────────────────────────────────
function StatsSection() {
  const stats = [
    { value: "$2.3M", label: "Average lifetime tax savings for our users", sub: "vs. standard CPA advice" },
    { value: "15min", label: "Average time to complete questionnaire", sub: "and receive full AI report" },
    { value: "200+", label: "IRC sections and strategies in our database", sub: "updated daily via RAG" },
    { value: "99.7%", label: "Uptime SLA", sub: "enterprise-grade infrastructure" },
  ];

  return (
    <section className="py-20 border-y border-white/5 bg-[#060d1b]">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-4xl font-bold gradient-text mb-2">{stat.value}</div>
              <div className="text-sm text-white/80 font-medium mb-1">{stat.label}</div>
              <div className="text-xs text-slate-500">{stat.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── How It Works ──────────────────────────────────────────────────────────────
function HowItWorksSection() {
  const steps = [
    {
      number: "01",
      icon: FileText,
      title: "Answer 15 smart questions",
      description:
        "Our AI-guided questionnaire asks about your business stage, revenue, location, family, and goals — progressive disclosure means you only answer what's relevant.",
    },
    {
      number: "02",
      icon: Sparkles,
      title: "AI analyzes 200+ strategies",
      description:
        "Claude Opus searches our real-time legal database (IRS publications, OBBBA 2025, state tax bulletins) and calculates exact dollar savings for your specific situation.",
    },
    {
      number: "03",
      icon: BarChart3,
      title: "Get your personalized plan",
      description:
        "Receive a prioritized implementation checklist with IRC citations, projected savings breakdowns, and professional referrals — ready to hand to your CPA.",
    },
    {
      number: "04",
      icon: CheckCircle2,
      title: "Implement and track",
      description:
        "Mark strategies complete, chat with the AI about implementation details, download your PDF report, and get alerted when tax law changes affect your plan.",
    },
  ];

  return (
    <section id="how-it-works" className="py-24 bg-[#050d1a]">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <Badge className="mb-4">How It Works</Badge>
          <h2 className="text-4xl font-bold text-white mb-4">
            From zero to optimized in 15 minutes
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            No 6-month engagement. No $500/hr attorney fees to just get started.
            Get institutional-grade tax strategy in the time it takes to get coffee.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, i) => (
            <div key={step.number} className="relative">
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute top-8 left-full w-full h-px bg-gradient-to-r from-emerald-500/30 to-transparent z-10" />
              )}
              <div className="glass-card rounded-xl p-6 h-full">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center">
                    <step.icon className="h-5 w-5 text-emerald-400" />
                  </div>
                  <span className="text-3xl font-bold text-white/10">{step.number}</span>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Features Grid ─────────────────────────────────────────────────────────────
function FeaturesSection() {
  const features = [
    {
      icon: Zap,
      title: "OBBBA 2025 Ready",
      description:
        "Permanent QBI 20% deduction, 100% bonus depreciation, $15M estate exemption, enhanced QSBS up to $15M — all baked in.",
      color: "yellow",
    },
    {
      icon: BookOpen,
      title: "Real-Time Law RAG",
      description:
        "Daily cron pulls IRS publications, treasury regulations, and state bulletins into our vector database. Claude always reasons over current law.",
      color: "blue",
    },
    {
      icon: Calculator,
      title: "Exact Dollar Math",
      description:
        "We don't say 'save money' — we calculate your SE tax, QBI deduction, state PTE election, and retirement deductions to the exact dollar.",
      color: "emerald",
    },
    {
      icon: Building2,
      title: "Entity Structure AI",
      description:
        "LLC → S-Corp, C-Corp for QSBS, Wyoming holding company, Delaware DST — AI finds the optimal structure for your specific numbers.",
      color: "purple",
    },
    {
      icon: Shield,
      title: "Asset Protection Plans",
      description:
        "Domestic Asset Protection Trusts (SD/NV/AK), Series LLC, charging order analysis — protect your wealth alongside minimizing taxes.",
      color: "red",
    },
    {
      icon: TrendingDown,
      title: "Estate Planning AI",
      description:
        "SLATs, GRATs, IDGTs, dynasty trusts, 529 superfunding — use the $15M exemption before it's gone with AI-driven estate strategy.",
      color: "indigo",
    },
  ];

  const colorMap: Record<string, string> = {
    yellow: "text-yellow-400 bg-yellow-900/30 border-yellow-500/30",
    blue: "text-blue-400 bg-blue-900/30 border-blue-500/30",
    emerald: "text-emerald-400 bg-emerald-900/30 border-emerald-500/30",
    purple: "text-purple-400 bg-purple-900/30 border-purple-500/30",
    red: "text-red-400 bg-red-900/30 border-red-500/30",
    indigo: "text-indigo-400 bg-indigo-900/30 border-indigo-500/30",
  };

  return (
    <section className="py-24 bg-[#060d1b]">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <Badge className="mb-4">Features</Badge>
          <h2 className="text-4xl font-bold text-white mb-4">
            Everything a Big 4 partner knows.
            <br />
            <span className="gradient-text">Available to everyone.</span>
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Tax optimization used to require $50K+ in professional fees to access.
            ZeroTax AI democratizes institutional tax strategy.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div key={feature.title} className="glass-card rounded-xl p-6 hover:border-white/15 transition-colors group">
              <div className={`w-11 h-11 rounded-xl border flex items-center justify-center mb-4 ${colorMap[feature.color]}`}>
                <feature.icon className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-emerald-400 transition-colors">
                {feature.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Comparison Section ────────────────────────────────────────────────────────
function ComparisonSection() {
  const competitors = [
    { name: "ZeroTax AI", price: "$49/mo", irc: true, realTime: true, calcs: true, estate: true, rag: true, highlight: true },
    { name: "TurboTax Advisor", price: "$200+/hr", irc: false, realTime: false, calcs: false, estate: false, rag: false, highlight: false },
    { name: "TaxGPT", price: "$30/mo", irc: false, realTime: false, calcs: false, estate: false, rag: false, highlight: false },
    { name: "Human CPA", price: "$5K–$50K", irc: true, realTime: true, calcs: true, estate: false, rag: false, highlight: false },
  ];

  const cols = [
    { key: "price", label: "Price" },
    { key: "irc", label: "IRC Citations" },
    { key: "realTime", label: "Real-Time Law" },
    { key: "calcs", label: "Exact $ Math" },
    { key: "estate", label: "Estate Planning" },
    { key: "rag", label: "Daily Updates" },
  ];

  return (
    <section className="py-24 bg-[#050d1a]">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <Badge className="mb-4">Comparison</Badge>
          <h2 className="text-4xl font-bold text-white mb-4">
            Why ZeroTax AI beats everything else
          </h2>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-4 text-slate-400 font-medium">Tool</th>
                  {cols.map((col) => (
                    <th key={col.key} className="text-center p-4 text-slate-400 font-medium text-sm">
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {competitors.map((comp) => (
                  <tr
                    key={comp.name}
                    className={`border-b border-white/5 last:border-0 ${comp.highlight ? "bg-emerald-950/20" : ""}`}
                  >
                    <td className="p-4">
                      <span className={`font-semibold ${comp.highlight ? "text-emerald-400" : "text-white"}`}>
                        {comp.name}
                      </span>
                      {comp.highlight && (
                        <span className="ml-2 text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full px-2 py-0.5">
                          Best
                        </span>
                      )}
                    </td>
                    <td className={`p-4 text-center text-sm ${comp.highlight ? "text-emerald-400 font-bold" : "text-slate-400"}`}>
                      {comp.price}
                    </td>
                    {(["irc", "realTime", "calcs", "estate", "rag"] as const).map((key) => (
                      <td key={key} className="p-4 text-center">
                        {comp[key] ? (
                          <CheckCircle2 className="h-5 w-5 text-emerald-400 mx-auto" />
                        ) : (
                          <span className="text-slate-600 text-lg">×</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Testimonials ──────────────────────────────────────────────────────────────
function TestimonialsSection() {
  const testimonials = [
    {
      quote:
        "ZeroTax AI identified an S-Corp election I'd been putting off for years. The AI calculated exactly $27,400 in annual SE tax savings and gave me the exact steps. My CPA confirmed every single recommendation.",
      name: "Marcus T.",
      role: "SaaS Founder, $2.4M ARR",
      savings: "$27,400/yr saved",
    },
    {
      quote:
        "The QSBS analysis alone is worth 10x the subscription. The AI explained exactly why I needed a C-Corp structure, cited IRC §1202, and calculated my potential $15M tax-free exit. Mind-blowing.",
      name: "Sarah K.",
      role: "Biotech Startup CEO",
      savings: "$15M potential exclusion",
    },
    {
      quote:
        "I run 12 rental properties. ZeroTax AI found the real estate professional status loophole (IRC §469), cost segregation strategy, and short-term rental exception. Projected $68K in first-year savings.",
      name: "David R.",
      role: "Real Estate Investor",
      savings: "$68,000 first year",
    },
  ];

  return (
    <section className="py-24 bg-[#060d1b]">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <Badge className="mb-4">Testimonials</Badge>
          <h2 className="text-4xl font-bold text-white mb-4">
            Real savings. Real IRC citations.
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {testimonials.map((t) => (
            <div key={t.name} className="glass-card rounded-xl p-6 flex flex-col">
              <div className="flex mb-4">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                ))}
              </div>
              <p className="text-slate-300 text-sm leading-relaxed flex-1 mb-6">
                &ldquo;{t.quote}&rdquo;
              </p>
              <div className="border-t border-white/10 pt-4 flex items-center justify-between">
                <div>
                  <div className="text-white font-semibold text-sm">{t.name}</div>
                  <div className="text-slate-500 text-xs">{t.role}</div>
                </div>
                <Badge variant="default" className="text-xs">
                  {t.savings}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── CTA Section ───────────────────────────────────────────────────────────────
function CTASection() {
  return (
    <section className="py-24 bg-[#050d1a]">
      <div className="max-w-3xl mx-auto px-6 text-center">
        <div className="gradient-border rounded-2xl p-12">
          <div className="w-16 h-16 rounded-2xl bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center mx-auto mb-6">
            <TrendingDown className="h-8 w-8 text-emerald-400" />
          </div>
          <h2 className="text-4xl font-bold text-white mb-4">
            Stop overpaying taxes.
            <br />
            Start today — free.
          </h2>
          <p className="text-slate-400 text-lg mb-8">
            Free plan includes a full AI analysis. No credit card required.
            Upgrade to premium for PDF reports, real-time law updates, and unlimited follow-up chat.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="xl" variant="gradient" asChild className="glow-emerald">
              <Link href="/register">
                Get My Free Tax Plan
                <ArrowRight className="h-5 w-5" />
              </Link>
            </Button>
            <Button size="xl" variant="outline" asChild>
              <Link href="/pricing">View Pricing</Link>
            </Button>
          </div>
          <p className="text-xs text-slate-600 mt-6">
            ⚠️ For informational purposes only. Not legal or tax advice. Always consult a licensed professional.
          </p>
        </div>
      </div>
    </section>
  );
}

// ─── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="border-t border-white/5 bg-[#040b17] py-12">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
                <TrendingDown className="h-4 w-4 text-white" />
              </div>
              <span className="text-xl font-bold text-white">ZeroTax AI</span>
            </div>
            <p className="text-sm text-slate-500 max-w-xs leading-relaxed">
              AI-powered tax optimization platform for business owners. Updated daily for OBBBA 2025.
            </p>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link></li>
              <li><Link href="/register" className="hover:text-white transition-colors">Get Started</Link></li>
              <li><Link href="/login" className="hover:text-white transition-colors">Sign In</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Legal</h4>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
              <li><Link href="/disclaimer" className="hover:text-white transition-colors">AI Disclaimer</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-white/5 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            © 2026 ZeroTax AI LLC. All rights reserved.
          </p>
          <p className="text-xs text-slate-600 text-center max-w-xl">
            <strong className="text-slate-500">Disclaimer:</strong> ZeroTax AI provides AI-generated
            educational information only. Not legal, tax, or accounting advice. No attorney-client relationship
            is formed. Always consult a licensed CPA, tax attorney, or enrolled agent before implementing
            any tax strategy.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ─── Navbar ────────────────────────────────────────────────────────────────────
function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#050d1a]/80 backdrop-blur-xl">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
            <TrendingDown className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-bold text-white">ZeroTax AI</span>
        </Link>

        <div className="hidden md:flex items-center gap-6 text-sm text-slate-400">
          <Link href="#how-it-works" className="hover:text-white transition-colors">How It Works</Link>
          <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
          <Link href="/login" className="hover:text-white transition-colors">Sign In</Link>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/login">Sign In</Link>
          </Button>
          <Button variant="gradient" size="sm" asChild>
            <Link href="/register">
              Get Started Free
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </div>
    </nav>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen" style={{ backgroundColor: "#050d1a" }}>
      <DisclaimerBanner />
      <Navbar />
      <main className="pt-8">
        <HeroSection />
        <StatsSection />
        <HowItWorksSection />
        <FeaturesSection />
        <ComparisonSection />
        <TestimonialsSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
