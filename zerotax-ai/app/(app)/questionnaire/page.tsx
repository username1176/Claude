// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Questionnaire Entry Point (updated)
// Replaces the old multi-step redirect logic with the adaptive wizard.
// Server component: verifies auth, then hands off to the client-side wizard.
// Equivalent to the updated app.py in the Streamlit version.
// ─────────────────────────────────────────────────────────────────────────────

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AdaptiveWizard } from "@/components/questionnaire/AdaptiveWizard";

export default async function QuestionnairePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Hand off to the client-side adaptive wizard.
  // All question flow, branching, and state management happens client-side.
  return <AdaptiveWizard userId={user.id} />;
}

export const dynamic = "force-dynamic";
