"use client";

import { useCallback } from "react";
import { useQuestionnaireStore } from "@/store/questionnaire";

interface SaveProgressArgs {
  step: number;
  stepData: Record<string, unknown>;
}

export function useSaveProgress() {
  const store = useQuestionnaireStore();

  const saveProgress = useCallback(
    async ({ step, stepData }: SaveProgressArgs) => {
      store.setIsSaving(true);
      try {
        const response = await fetch("/api/questionnaire/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            step,
            businessId: store.businessId,
            questionnaireId: store.questionnaireId,
            data: stepData,
            // Send all accumulated data too
            allData: {
              ...store.step1,
              ...store.step2,
              ...store.step3,
              ...store.step4,
              ...store.step5,
              ...store.step6,
              ...stepData,
            },
          }),
        });

        if (response.ok) {
          const json = await response.json();
          if (json.businessId && !store.businessId) {
            store.setBusinessId(json.businessId);
          }
          if (json.questionnaireId && !store.questionnaireId) {
            store.setQuestionnaireId(json.questionnaireId);
          }
          store.setLastSavedAt(new Date().toISOString());
        }
      } catch {
        // Silently fail — progress is already in localStorage
      } finally {
        store.setIsSaving(false);
      }
    },
    [store]
  );

  return { saveProgress };
}
