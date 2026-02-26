"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu, X, TrendingDown, LayoutDashboard, ClipboardList,
  Lightbulb, FileText, CreditCard, User, LogOut
} from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import type { Database } from "@/types/database.types";

type Profile = Database["public"]["Tables"]["profiles"]["Row"];

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/questionnaire", icon: ClipboardList, label: "Questionnaire" },
  { href: "/recommendations", icon: Lightbulb, label: "Recommendations" },
  { href: "/reports", icon: FileText, label: "Reports" },
  { href: "/billing", icon: CreditCard, label: "Billing" },
  { href: "/profile", icon: User, label: "Profile" },
];

export function MobileNav({ profile }: { profile: Profile | null }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <>
      {/* Top bar (mobile only) */}
      <div className="lg:hidden flex items-center justify-between px-4 h-14 border-b border-white/5 bg-[#060d1b]">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center">
            <TrendingDown className="h-4 w-4 text-white" />
          </div>
          <span className="text-base font-bold text-white">ZeroTax AI</span>
        </Link>
        <button
          onClick={() => setOpen(!open)}
          className="p-2 rounded-lg text-slate-400 hover:bg-white/5 transition-colors"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu overlay */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-50 bg-[#050d1a]/95 backdrop-blur-xl flex flex-col">
          <div className="flex items-center justify-between px-4 h-14 border-b border-white/5">
            <span className="text-base font-bold text-white">Menu</span>
            <button onClick={() => setOpen(false)} className="p-2 rounded-lg text-slate-400">
              <X className="h-5 w-5" />
            </button>
          </div>

          <nav className="flex-1 px-4 py-6 space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-4 py-3 text-base transition-colors",
                    isActive
                      ? "bg-emerald-900/40 text-emerald-400"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  )}
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-white/5 px-4 py-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-emerald-900/60 border border-emerald-500/30 flex items-center justify-center text-sm font-bold text-emerald-400">
                {profile?.full_name?.slice(0, 2).toUpperCase() ?? "??"}
              </div>
              <div>
                <div className="text-sm font-medium text-white">{profile?.full_name}</div>
                <div className="text-xs text-slate-500">{profile?.email}</div>
              </div>
            </div>
            <button
              onClick={handleSignOut}
              className="flex items-center gap-2 text-sm text-slate-400 hover:text-red-400 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
          </div>
        </div>
      )}
    </>
  );
}
