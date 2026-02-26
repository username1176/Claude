import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppSidebar } from "@/components/shared/AppSidebar";
import { DisclaimerBanner } from "@/components/shared/DisclaimerBanner";
import { MobileNav } from "@/components/shared/MobileNav";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "#050d1a" }}>
      <DisclaimerBanner />
      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar */}
        <div className="hidden lg:flex">
          <AppSidebar profile={profile} />
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col min-w-0 overflow-auto">
          {/* Mobile top nav */}
          <MobileNav profile={profile} />

          {/* Page content */}
          <main className="flex-1 p-6 lg:p-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
