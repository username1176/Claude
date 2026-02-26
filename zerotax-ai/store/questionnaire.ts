import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type {
  Step1Data,
  Step2Data,
  Step3Data,
  Step4Data,
  Step5Data,
  Step6Data,
} from "@/lib/schemas/questionnaire";

// ─── State shape ──────────────────────────────────────────────────────────────
export interface QuestionnaireState {
  // Persisted step data
  step1: Partial<Step1Data>;
  step2: Partial<Step2Data>;
  step3: Partial<Step3Data>;
  step4: Partial<Step4Data>;
  step5: Partial<Step5Data>;
  step6: Partial<Step6Data>;

  // Navigation & meta
  currentStep: number;
  highestStepReached: number;
  businessId: string | null;
  questionnaireId: string | null;
  lastSavedAt: string | null;
  isSaving: boolean;

  // Actions
  setStep1: (data: Partial<Step1Data>) => void;
  setStep2: (data: Partial<Step2Data>) => void;
  setStep3: (data: Partial<Step3Data>) => void;
  setStep4: (data: Partial<Step4Data>) => void;
  setStep5: (data: Partial<Step5Data>) => void;
  setStep6: (data: Partial<Step6Data>) => void;
  setCurrentStep: (step: number) => void;
  setBusinessId: (id: string) => void;
  setQuestionnaireId: (id: string) => void;
  setIsSaving: (saving: boolean) => void;
  setLastSavedAt: (ts: string) => void;
  reset: () => void;
  loadFromServer: (data: Partial<ServerQuestionnaireData>) => void;
}

// ─── Server-side data shape (from DB) ────────────────────────────────────────
export interface ServerQuestionnaireData {
  id: string;
  businessId: string;
  stepCompleted: number;
  businessName: string;
  businessStage: string;
  industry: string;
  entityTypeCurrent: string;
  yearBusinessFounded: number | null;
  annualRevenue: number | null;
  annualProfit: number | null;
  w2WagesPaid: number | null;
  ownerDraws: number | null;
  reasonableSalary: number | null;
  otherIncome: number | null;
  otherIncomeType: string | null;
  stateOfFormation: string;
  statesOperating: string[];
  numOwners: number | null;
  marriedFilingJointly: boolean | null;
  spouseWorks: boolean | null;
  spouseIncome: number | null;
  childrenCount: number | null;
  familyInBusiness: boolean | null;
  realEstateValue: number | null;
  businessAssetsValue: number | null;
  investmentPortfolio: number | null;
  retirementAccounts: number | null;
  totalNetWorth: number | null;
  hasQsbsStock: boolean | null;
  goalMinimizeTaxes: boolean;
  goalAssetProtection: boolean;
  goalEstatePlanning: boolean;
  goalExitStrategy: boolean;
  goalRetirementPlanning: boolean;
  goalHireFamily: boolean;
  planningHorizon: string;
  exitTimelineYears: number | null;
}

// ─── Initial state ────────────────────────────────────────────────────────────
const initialState = {
  step1: {} as Partial<Step1Data>,
  step2: {} as Partial<Step2Data>,
  step3: { statesOperating: [] } as Partial<Step3Data>,
  step4: {} as Partial<Step4Data>,
  step5: {} as Partial<Step5Data>,
  step6: {
    goalMinimizeTaxes: true,
    goalAssetProtection: false,
    goalEstatePlanning: false,
    goalExitStrategy: false,
    goalRetirementPlanning: true,
    goalHireFamily: false,
  } as Partial<Step6Data>,
  currentStep: 1,
  highestStepReached: 1,
  businessId: null,
  questionnaireId: null,
  lastSavedAt: null,
  isSaving: false,
};

// ─── Store ────────────────────────────────────────────────────────────────────
export const useQuestionnaireStore = create<QuestionnaireState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setStep1: (data) =>
        set((s) => ({ step1: { ...s.step1, ...data } })),

      setStep2: (data) =>
        set((s) => ({ step2: { ...s.step2, ...data } })),

      setStep3: (data) =>
        set((s) => ({ step3: { ...s.step3, ...data } })),

      setStep4: (data) =>
        set((s) => ({ step4: { ...s.step4, ...data } })),

      setStep5: (data) =>
        set((s) => ({ step5: { ...s.step5, ...data } })),

      setStep6: (data) =>
        set((s) => ({ step6: { ...s.step6, ...data } })),

      setCurrentStep: (step) =>
        set((s) => ({
          currentStep: step,
          highestStepReached: Math.max(s.highestStepReached, step),
        })),

      setBusinessId: (id) => set({ businessId: id }),
      setQuestionnaireId: (id) => set({ questionnaireId: id }),
      setIsSaving: (saving) => set({ isSaving: saving }),
      setLastSavedAt: (ts) => set({ lastSavedAt: ts }),

      reset: () => set(initialState),

      loadFromServer: (data) => {
        const s = get();
        set({
          questionnaireId: data.id ?? s.questionnaireId,
          businessId: data.businessId ?? s.businessId,
          currentStep: Math.min((data.stepCompleted ?? 0) + 1, 7),
          highestStepReached: data.stepCompleted ?? s.highestStepReached,
          step1: {
            businessName: data.businessName ?? "",
            businessStage: (data.businessStage as Step1Data["businessStage"]) ?? undefined,
            industry: data.industry ?? "",
            entityTypeCurrent: data.entityTypeCurrent ?? "",
            yearBusinessFounded: data.yearBusinessFounded ?? undefined,
          },
          step2: {
            annualRevenue: data.annualRevenue ?? undefined,
            annualProfit: data.annualProfit ?? undefined,
            w2WagesPaid: data.w2WagesPaid ?? undefined,
            ownerDraws: data.ownerDraws ?? undefined,
            reasonableSalary: data.reasonableSalary ?? undefined,
            otherIncome: data.otherIncome ?? undefined,
            otherIncomeType: data.otherIncomeType ?? undefined,
          },
          step3: {
            stateOfFormation: data.stateOfFormation ?? "",
            statesOperating: data.statesOperating ?? [],
            numOwners: data.numOwners ?? undefined,
          },
          step4: {
            marriedFilingJointly: data.marriedFilingJointly ?? undefined,
            spouseWorks: data.spouseWorks ?? undefined,
            spouseIncome: data.spouseIncome ?? undefined,
            childrenCount: data.childrenCount ?? undefined,
            familyInBusiness: data.familyInBusiness ?? undefined,
          },
          step5: {
            realEstateValue: data.realEstateValue ?? undefined,
            businessAssetsValue: data.businessAssetsValue ?? undefined,
            investmentPortfolio: data.investmentPortfolio ?? undefined,
            retirementAccounts: data.retirementAccounts ?? undefined,
            totalNetWorth: data.totalNetWorth ?? undefined,
            hasQsbsStock: data.hasQsbsStock ?? undefined,
          },
          step6: {
            goalMinimizeTaxes: data.goalMinimizeTaxes ?? true,
            goalAssetProtection: data.goalAssetProtection ?? false,
            goalEstatePlanning: data.goalEstatePlanning ?? false,
            goalExitStrategy: data.goalExitStrategy ?? false,
            goalRetirementPlanning: data.goalRetirementPlanning ?? true,
            goalHireFamily: data.goalHireFamily ?? false,
            planningHorizon: (data.planningHorizon as Step6Data["planningHorizon"]) ?? undefined,
            exitTimelineYears: data.exitTimelineYears ?? undefined,
          },
        });
      },
    }),
    {
      name: "zerotax-questionnaire",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? localStorage : ({
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        } as unknown as Storage)
      ),
      // Only persist data fields; skip isSaving
      partialize: (s) => ({
        step1: s.step1,
        step2: s.step2,
        step3: s.step3,
        step4: s.step4,
        step5: s.step5,
        step6: s.step6,
        currentStep: s.currentStep,
        highestStepReached: s.highestStepReached,
        businessId: s.businessId,
        questionnaireId: s.questionnaireId,
        lastSavedAt: s.lastSavedAt,
      }),
    }
  )
);
