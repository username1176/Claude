"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardList,
  Lightbulb,
  FileText,
  CreditCard,
  User,
  TrendingDown,
  LogOut,
  ChevronRight,
  Sparkles,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import { Badge } from "@/components/ui/badge";
import type { Database } from "@/types/database.types";

type Profile = Database["public"]["Tables"]["profiles"]["Row"];

interface NavItem {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  badge?: string;
  premiumOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/questionnaire", icon: ClipboardList, label: "Tax Questionnaire" },
  { href: "/recommendations", icon: Lightbulb, label: "Recommendations" },
  { href: "/reports", icon: FileText, label: "PDF Reports", premiumOnly: true },
  { href: "/billing", icon: CreditCard, label: "Billing" },
  { href: "/profile", icon: User, label: "Profile" },
];

interface AppSidebarProps {
  profile: Profile | null;
}

export function AppSidebar({ profile }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  const isPremium =
    profile?.subscription_tier === "premium" ||
    profile?.subscription_tier === "enterprise";

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  const initials = profile?.full_name
    ? profile.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : profile?.email?.slice(0, 2).toUpperCase() ?? "??";

  return (
    <aside className="flex flex-col w-64 min-h-screen border-r border-white/5 bg-[#060d1b]">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/5">
        <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-900/50">
          <TrendingDown className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="text-base font-bold text-white">ZeroTax AI</div>
          <div className="text-xs text-slate-500">Tax Optimizer</div>
        </div>
      </div>

      {/* Plan badge */}
      {!isPremium && (
        <div className="mx-4 mt-4">
          <Link
            href="/billing"
            className="flex items-center justify-between rounded-lg bg-gradient-to-r from-emerald-950/60 to-indigo-950/60 border border-emerald-500/20 px-3 py-2.5 hover:border-emerald-500/40 transition-colors group"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              <div>
                <div className="text-xs font-semibold text-emerald-400">Free Plan</div>
                <div className="text-[10px] text-slate-500">Upgrade for PDF + RAG</div>
              </div>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
          </Link>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          const isLocked = item.premiumOnly && !isPremium;

          return (
            <Link
              key={item.href}
              href={isLocked ? "/billing" : item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150 group",
                isActive
                  ? "bg-emerald-900/40 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-white"
              )}
            >
              <item.icon
                className={cn(
                  "h-4 w-4 shrink-0 transition-colors",
                  isActive ? "text-emerald-400" : "text-slate-500 group-hover:text-white"
                )}
              />
              <span className="flex-1">{item.label}</span>
              {isLocked && (
                <Lock className="h-3 w-3 text-slate-600" />
              )}
              {item.badge && (
                <Badge variant="default" className="text-[10px] h-4 px-1.5">
                  {item.badge}
                </Badge>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Law update indicator */}
      <div className="mx-4 mb-3">
        <div className="rounded-lg bg-blue-950/30 border border-blue-500/20 px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-xs text-blue-400 font-medium">Laws updated today</span>
          </div>
          <p className="text-[10px] text-slate-600 mt-0.5">
            OBBBA 2025 · IRS Pub 535 · 47 state bulletins
          </p>
        </div>
      </div>

      {/* User section */}
      <div className="border-t border-white/5 px-3 py-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-emerald-900/60 border border-emerald-500/30 flex items-center justify-center text-xs font-bold text-emerald-400 shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">
              {profile?.full_name ?? "User"}
            </div>
            <div className="text-xs text-slate-500 truncate">{profile?.email}</div>
          </div>
          <button
            onClick={handleSignOut}
            className="p-1.5 rounded-md text-slate-500 hover:text-red-400 hover:bg-red-950/30 transition-colors"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
