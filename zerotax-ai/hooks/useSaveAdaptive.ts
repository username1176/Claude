"use client";

// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Adaptive Save Hook
// Fires answers to /api/questionnaire/save after each question.
// Uses the existing route (no new API endpoint needed) — just maps adaptive
// answers to the expected camelCase format via mapAnswersToDb().
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback } from "react";
import { useAdaptiveStore } from "@/store/adaptive-questionnaire";
import { mapAnswersToDb, type Answers } from "@/lib/question-engine";

export function useSaveAdaptive() {
  const store = useAdaptiveStore();

  /**
   * Fire-and-forget save. Silently fails on network error —
   * Zustand + localStorage is the source of truth.
   */
  const save = useCallback(
    async (answers: Answers) => {
      store.setIsSaving(true);
      try {
        const res = await fetch("/api/questionnaire/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            step: Object.keys(answers).length,
            businessId: store.businessId,
            questionnaireId: store.questionnaireId,
            // allData is the camelCase format the save route expects
            allData: mapAnswersToDb(answers),
          }),
        });

        if (res.ok) {
          const json = (await res.json()) as {
            businessId: string;
            questionnaireId: string;
          };
          if (json.businessId && !store.businessId) {
            store.setBusinessId(json.businessId);
          }
          if (json.questionnaireId && !store.questionnaireId) {
            store.setQuestionnaireId(json.questionnaireId);
          }
          store.setLastSavedAt(new Date().toISOString());
        }
      } catch {
        // Silently fail — Zustand/localStorage holds all answers
      } finally {
        store.setIsSaving(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [store.businessId, store.questionnaireId]
  );

  return { save };
}
