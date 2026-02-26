// The old step-based flow (/questionnaire/1 through /questionnaire/7) has been
// replaced by the adaptive wizard at /questionnaire. All step URLs now redirect.

import { redirect } from "next/navigation";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default async function QuestionnaireStepPage(_props: {
  params: Promise<{ step: string }>;
}) {
  redirect("/questionnaire");
}

export const dynamic = "force-dynamic";
