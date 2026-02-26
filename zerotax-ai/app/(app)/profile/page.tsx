import { redirect } from "next/navigation";
import { User, Mail, Calendar, Shield } from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Database } from "@/types/database.types";

type Profile = Database["public"]["Tables"]["profiles"]["Row"];

export default async function ProfilePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profileData } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  const profile = profileData as Profile | null;

  const tierVariant = (
    tier: string | undefined
  ): "outline" | "default" | "purple" => {
    if (tier === "premium") return "default";
    if (tier === "enterprise") return "purple";
    return "outline";
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-white">Profile</h1>
        <p className="text-slate-400 mt-1">Your account information</p>
      </div>

      <Card glass>
        <CardHeader>
          <CardTitle className="text-lg">Account Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 pb-4 border-b border-white/5">
            <div className="w-16 h-16 rounded-full bg-emerald-900/60 border border-emerald-500/30 flex items-center justify-center text-xl font-bold text-emerald-400">
              {profile?.full_name?.slice(0, 2).toUpperCase() ?? "??"}
            </div>
            <div>
              <div className="text-lg font-semibold text-white">
                {profile?.full_name ?? "No name set"}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={tierVariant(profile?.subscription_tier)}>
                  {profile?.subscription_tier ?? "free"} plan
                </Badge>
                <Badge variant={profile?.subscription_status === "active" ? "default" : "outline"}>
                  {profile?.subscription_status ?? "inactive"}
                </Badge>
              </div>
            </div>
          </div>

          {[
            { icon: User, label: "Full Name", value: profile?.full_name ?? "—" },
            { icon: Mail, label: "Email", value: profile?.email ?? "—" },
            {
              icon: Calendar,
              label: "Member Since",
              value: profile?.created_at
                ? new Date(profile.created_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })
                : "—",
            },
            { icon: Shield, label: "Account ID", value: user.id.slice(0, 8) + "..." },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-center gap-3 py-2">
              <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
                <Icon className="h-4 w-4 text-slate-400" />
              </div>
              <div className="flex-1">
                <div className="text-xs text-slate-500">{label}</div>
                <div className="text-sm text-white font-medium">{value}</div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <p className="text-xs text-slate-600 text-center">
        Profile editing coming in a future prompt.
      </p>
    </div>
  );
}
