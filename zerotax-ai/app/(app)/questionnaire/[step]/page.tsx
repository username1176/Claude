import { notFound, redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Step1 } from "@/components/questionnaire/steps/Step1";
import { Step2 } from "@/components/questionnaire/steps/Step2";
import { Step3 } from "@/components/questionnaire/steps/Step3";
import { Step4 } from "@/components/questionnaire/steps/Step4";
import { Step5 } from "@/components/questionnaire/steps/Step5";
import { Step6 } from "@/components/questionnaire/steps/Step6";
import { Step7 } from "@/components/questionnaire/steps/Step7";
import { TOTAL_STEPS } from "@/lib/schemas/questionnaire";

const STEP_COMPONENTS = {
  1: Step1,
  2: Step2,
  3: Step3,
  4: Step4,
  5: Step5,
  6: Step6,
  7: Step7,
} as const;

interface Props {
  params: Promise<{ step: string }>;
}

export default async function QuestionnaireStepPage({ params }: Props) {
  const { step: stepStr } = await params;
  const step = parseInt(stepStr, 10);

  // Validate step number
  if (isNaN(step) || step < 1 || step > TOTAL_STEPS) {
    notFound();
  }

  // Require auth
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const StepComponent = STEP_COMPONENTS[step as keyof typeof STEP_COMPONENTS];
  return <StepComponent />;
}

export function generateStaticParams() {
  return Array.from({ length: TOTAL_STEPS }, (_, i) => ({ step: String(i + 1) }));
}

export const dynamic = "force-dynamic";
