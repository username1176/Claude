import Link from "next/link";
import { TrendingDown } from "lucide-react";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "#050d1a" }}>
      <DisclaimerBanner />

      {/* Top bar */}
      <div className="border-b border-white/5 bg-[#050d1a]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
              <TrendingDown className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-white">ZeroTax AI</span>
          </Link>
        </div>
      </div>

      {/* Auth content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="absolute inset-0 dot-grid opacity-30 pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-emerald-900/10 blur-[100px] pointer-events-none" />
        <div className="relative z-10 w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  );
}
