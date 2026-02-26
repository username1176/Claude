import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

// Redirect to step 1, or resume from the last saved step
export default async function QuestionnairePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // Check for in-progress questionnaire
  const { data: businesses } = await supabase
    .from("businesses")
    .select("id")
    .eq("user_id", user.id)
    .eq("is_active", true)
    .limit(1);

  if (businesses && businesses.length > 0) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: questionnaire } = await (supabase as any)
      .from("questionnaire_responses")
      .select("step_completed")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(1)
      .single() as { data: { step_completed: number } | null };

    if (questionnaire && questionnaire.step_completed > 0) {
      const resumeStep = Math.min(questionnaire.step_completed + 1, 7);
      redirect(`/questionnaire/${resumeStep}`);
    }
  }

  redirect("/questionnaire/1");
}
