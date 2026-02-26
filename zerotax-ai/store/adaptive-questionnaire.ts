// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Adaptive Questionnaire Store
// Zustand store with localStorage persistence for the adaptive wizard.
// Equivalent to st.session_state in the Streamlit version.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// ─── State Shape ──────────────────────────────────────────────────────────────

export interface AdaptiveStore {
  // All collected answers keyed by question ID
  answers: Record<string, unknown>;

  // Ordered list of question IDs that have been answered (navigation history)
  history: string[];

  // Supabase IDs (populated after first save)
  businessId: string | null;
  questionnaireId: string | null;
  recommendationId: string | null;

  // Wizard status
  isComplete: boolean;
  isSaving: boolean;
  lastSavedAt: string | null;

  // ── Actions ──────────────────────────────────────────────────────────────
  /** Record an answer and add the question to history */
  setAnswer: (questionId: string, value: unknown) => void;

  /** Go back one question (removes last entry from history) */
  goBack: () => void;

  /** Mark the wizard as complete */
  complete: () => void;

  setBusinessId: (id: string) => void;
  setQuestionnaireId: (id: string) => void;
  setRecommendationId: (id: string) => void;
  setIsSaving: (v: boolean) => void;
  setLastSavedAt: (ts: string) => void;

  /** Full reset — clears all data and history */
  reset: () => void;
}

// ─── Initial State ────────────────────────────────────────────────────────────

const initialState = {
  answers: {} as Record<string, unknown>,
  history: [] as string[],
  businessId: null,
  questionnaireId: null,
  recommendationId: null,
  isComplete: false,
  isSaving: false,
  lastSavedAt: null,
};

// ─── Store ────────────────────────────────────────────────────────────────────

export const useAdaptiveStore = create<AdaptiveStore>()(
  persist(
    (set) => ({
      ...initialState,

      setAnswer: (questionId, value) =>
        set((s) => ({
          answers: { ...s.answers, [questionId]: value },
          // Only add to history if not already there (handles re-answer from back)
          history: s.history.includes(questionId)
            ? s.history
            : [...s.history, questionId],
        })),

      goBack: () =>
        set((s) => ({
          history: s.history.slice(0, -1),
        })),

      complete: () => set({ isComplete: true }),

      setBusinessId: (id) => set({ businessId: id }),
      setQuestionnaireId: (id) => set({ questionnaireId: id }),
      setRecommendationId: (id) => set({ recommendationId: id }),
      setIsSaving: (v) => set({ isSaving: v }),
      setLastSavedAt: (ts) => set({ lastSavedAt: ts }),

      reset: () => set(initialState),
    }),
    {
      name: "zerotax-adaptive-v1",
      storage: createJSONStorage(() =>
        typeof window !== "undefined"
          ? localStorage
          : ({
              getItem: () => null,
              setItem: () => {},
              removeItem: () => {},
            } as unknown as Storage)
      ),
      // Persist everything except transient isSaving flag
      partialize: (s) => ({
        answers: s.answers,
        history: s.history,
        businessId: s.businessId,
        questionnaireId: s.questionnaireId,
        recommendationId: s.recommendationId,
        isComplete: s.isComplete,
        lastSavedAt: s.lastSavedAt,
      }),
    }
  )
);
