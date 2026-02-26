import { z } from "zod";

// ─── Step 1 — Business Profile ────────────────────────────────────────────────
export const step1Schema = z.object({
  businessName: z.string().min(1, "Business name is required"),
  businessStage: z.enum(["idea", "startup", "growth", "established", "mature"], "Select a business stage"),
  industry: z.string().min(1, "Industry is required"),
  entityTypeCurrent: z.string().min(1, "Select your current entity type"),
  yearBusinessFounded: z.number().int().min(1900).max(new Date().getFullYear()).nullable().optional(),
});

export type Step1Data = z.infer<typeof step1Schema>;

// ─── Step 2 — Revenue & Compensation ─────────────────────────────────────────
export const step2Schema = z.object({
  annualRevenue: z.number().min(0, "Must be 0 or more").nullable().optional(),
  annualProfit: z.number().nullable().optional(),
  w2WagesPaid: z.number().min(0).nullable().optional(),
  ownerDraws: z.number().min(0).nullable().optional(),
  reasonableSalary: z.number().min(0).nullable().optional(),
  otherIncome: z.number().min(0).nullable().optional(),
  otherIncomeType: z.string().optional(),
});

export type Step2Data = z.infer<typeof step2Schema>;

// ─── Step 3 — Location & Structure ───────────────────────────────────────────
export const step3Schema = z.object({
  stateOfFormation: z.string().min(1, "Select state of formation"),
  statesOperating: z.array(z.string()).min(1, "Select at least one operating state"),
  numOwners: z.number().int().min(1).max(999).nullable().optional(),
});

export type Step3Data = z.infer<typeof step3Schema>;

// ─── Step 4 — Family & Personal ───────────────────────────────────────────────
export const step4Schema = z.object({
  marriedFilingJointly: z.boolean().nullable().optional(),
  spouseWorks: z.boolean().nullable().optional(),
  spouseIncome: z.number().min(0).nullable().optional(),
  childrenCount: z.number().int().min(0).max(99).nullable().optional(),
  familyInBusiness: z.boolean().nullable().optional(),
});

export type Step4Data = z.infer<typeof step4Schema>;

// ─── Step 5 — Assets & Wealth ─────────────────────────────────────────────────
export const step5Schema = z.object({
  realEstateValue: z.number().min(0).nullable().optional(),
  businessAssetsValue: z.number().min(0).nullable().optional(),
  investmentPortfolio: z.number().min(0).nullable().optional(),
  retirementAccounts: z.number().min(0).nullable().optional(),
  totalNetWorth: z.number().nullable().optional(),
  hasQsbsStock: z.boolean().nullable().optional(),
});

export type Step5Data = z.infer<typeof step5Schema>;

// ─── Step 6 — Goals & Planning ────────────────────────────────────────────────
export const step6Schema = z.object({
  goalMinimizeTaxes: z.boolean().default(false),
  goalAssetProtection: z.boolean().default(false),
  goalEstatePlanning: z.boolean().default(false),
  goalExitStrategy: z.boolean().default(false),
  goalRetirementPlanning: z.boolean().default(false),
  goalHireFamily: z.boolean().default(false),
  planningHorizon: z.enum(["immediate", "1_year", "3_year", "5_plus"], "Select a planning horizon"),
  exitTimelineYears: z.number().int().min(0).max(99).nullable().optional(),
});

export type Step6Data = z.infer<typeof step6Schema>;

// ─── Full questionnaire schema ────────────────────────────────────────────────
export const fullQuestionnaireSchema = step1Schema
  .merge(step2Schema)
  .merge(step3Schema)
  .merge(step4Schema)
  .merge(step5Schema)
  .merge(step6Schema);

export type FullQuestionnaireData = z.infer<typeof fullQuestionnaireSchema>;

// ─── Constants ────────────────────────────────────────────────────────────────
export const TOTAL_STEPS = 7;
