"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { step2Schema, type Step2Data } from "@/lib/schemas/questionnaire";
import { useQuestionnaireStore } from "@/store/questionnaire";
import { StepLayout } from "../StepLayout";
import { FormField, CurrencyInput, FormSelect } from "../FormField";
import { useRouter } from "next/navigation";
import { useSaveProgress } from "@/hooks/useSaveProgress";
import { useState } from "react";
import { Input } from "@/components/ui/input";

const OTHER_INCOME_OPTIONS = [
  { value: "w2_job", label: "W-2 from other employer" },
  { value: "rental", label: "Rental income" },
  { value: "dividends", label: "Dividends / interest" },
  { value: "capital_gains", label: "Capital gains" },
  { value: "crypto", label: "Crypto" },
  { value: "royalties", label: "Royalties" },
  { value: "other", label: "Other" },
];

export function Step2() {
  const router = useRouter();
  const store = useQuestionnaireStore();
  const { saveProgress } = useSaveProgress();
  const [showOtherIncome, setShowOtherIncome] = useState(
    (store.step2.otherIncome ?? 0) > 0
  );

  const { handleSubmit, watch, setValue, formState: { errors } } = useForm<Step2Data>({
    resolver: zodResolver(step2Schema),
    defaultValues: {
      annualRevenue: store.step2.annualRevenue ?? undefined,
      annualProfit: store.step2.annualProfit ?? undefined,
      w2WagesPaid: store.step2.w2WagesPaid ?? undefined,
      ownerDraws: store.step2.ownerDraws ?? undefined,
      reasonableSalary: store.step2.reasonableSalary ?? undefined,
      otherIncome: store.step2.otherIncome ?? undefined,
      otherIncomeType: store.step2.otherIncomeType ?? undefined,
    },
  });

  async function onSubmit(data: Step2Data) {
    store.setStep2(data);
    store.setCurrentStep(3);
    await saveProgress({ step: 2, stepData: data });
    router.push("/questionnaire/3");
  }

  const entityType = store.step1.entityTypeCurrent ?? "";
  const isSCorp = entityType.includes("scorp") || entityType.includes("s_corp");

  return (
    <StepLayout
      currentStep={2}
      highestStepReached={store.highestStepReached}
      title="Revenue & compensation"
      description="These numbers drive the core tax calculations — exact dollar savings depend on this data."
      onNext={handleSubmit(onSubmit)}
      isSaving={store.isSaving}
      lastSavedAt={store.lastSavedAt}
      onStepClick={(s) => router.push(`/questionnaire/${s}`)}
    >
      {/* Revenue row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField
          label="Annual gross revenue"
          htmlFor="annualRevenue"
          hint="Total business receipts before expenses"
          error={errors.annualRevenue?.message}
        >
          <CurrencyInput
            id="annualRevenue"
            value={watch("annualRevenue")}
            onChange={(v) => setValue("annualRevenue", v ?? undefined)}
            placeholder="250,000"
          />
        </FormField>

        <FormField
          label="Annual net profit"
          htmlFor="annualProfit"
          hint="After all business expenses, before owner pay"
          error={errors.annualProfit?.message}
        >
          <CurrencyInput
            id="annualProfit"
            value={watch("annualProfit")}
            onChange={(v) => setValue("annualProfit", v ?? undefined)}
            placeholder="120,000"
          />
        </FormField>
      </div>

      {/* Owner compensation */}
      <div className="border-t border-white/5 pt-5">
        <p className="text-sm font-medium text-white mb-3">Owner compensation</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField
            label="W-2 wages paid to yourself"
            htmlFor="w2WagesPaid"
            hint="If you're an S-Corp, enter your salary here"
            error={errors.w2WagesPaid?.message}
          >
            <CurrencyInput
              id="w2WagesPaid"
              value={watch("w2WagesPaid")}
              onChange={(v) => setValue("w2WagesPaid", v ?? undefined)}
              placeholder="0"
            />
          </FormField>

          <FormField
            label="Owner draws / distributions"
            htmlFor="ownerDraws"
            hint="Non-salary distributions from the business"
            error={errors.ownerDraws?.message}
          >
            <CurrencyInput
              id="ownerDraws"
              value={watch("ownerDraws")}
              onChange={(v) => setValue("ownerDraws", v ?? undefined)}
              placeholder="0"
            />
          </FormField>
        </div>

        {/* Reasonable salary — shown for non-S-Corps as suggestion field */}
        {!isSCorp && (
          <FormField
            label="Target 'reasonable salary' (estimated)"
            htmlFor="reasonableSalary"
            className="mt-4"
            hint="If you convert to S-Corp, what would a reasonable salary be for your role? Used to calculate SE tax savings."
            error={errors.reasonableSalary?.message}
          >
            <CurrencyInput
              id="reasonableSalary"
              value={watch("reasonableSalary")}
              onChange={(v) => setValue("reasonableSalary", v ?? undefined)}
              placeholder="80,000"
            />
          </FormField>
        )}
      </div>

      {/* Other income toggle */}
      <div className="border-t border-white/5 pt-5">
        <button
          type="button"
          onClick={() => setShowOtherIncome(!showOtherIncome)}
          className="flex items-center gap-2 text-sm text-emerald-400 hover:text-emerald-300 transition-colors"
        >
          <span className="w-4 h-4 rounded border border-emerald-500/50 flex items-center justify-center text-xs font-bold">
            {showOtherIncome ? "−" : "+"}
          </span>
          I have other significant income sources
        </button>

        {showOtherIncome && (
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField
              label="Other annual income"
              htmlFor="otherIncome"
              error={errors.otherIncome?.message}
            >
              <CurrencyInput
                id="otherIncome"
                value={watch("otherIncome")}
                onChange={(v) => setValue("otherIncome", v ?? undefined)}
                placeholder="0"
              />
            </FormField>

            <FormField
              label="Income type"
              htmlFor="otherIncomeType"
              error={errors.otherIncomeType?.message}
            >
              <FormSelect
                id="otherIncomeType"
                value={watch("otherIncomeType")}
                onChange={(v) => setValue("otherIncomeType", v)}
                options={OTHER_INCOME_OPTIONS}
                placeholder="Select type…"
              />
            </FormField>
          </div>
        )}
      </div>

      {/* Tax impact callout */}
      {(watch("annualRevenue") ?? 0) > 0 && (
        <div className="rounded-lg bg-emerald-950/30 border border-emerald-500/20 p-3">
          <p className="text-xs text-emerald-400">
            <span className="font-semibold">AI will calculate:</span> SE tax savings from S-Corp election,
            QBI 20% deduction eligibility, retirement contribution limits, and more — based on these numbers.
          </p>
        </div>
      )}
    </StepLayout>
  );
}
