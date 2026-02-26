"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { step4Schema, type Step4Data } from "@/lib/schemas/questionnaire";
import { useQuestionnaireStore } from "@/store/questionnaire";
import { StepLayout } from "../StepLayout";
import { FormField, CurrencyInput, YesNoToggle, NumberInput } from "../FormField";
import { useRouter } from "next/navigation";
import { useSaveProgress } from "@/hooks/useSaveProgress";

export function Step4() {
  const router = useRouter();
  const store = useQuestionnaireStore();
  const { saveProgress } = useSaveProgress();

  const { handleSubmit, watch, setValue, formState: { errors } } = useForm<Step4Data>({
    resolver: zodResolver(step4Schema),
    defaultValues: {
      marriedFilingJointly: store.step4.marriedFilingJointly ?? undefined,
      spouseWorks: store.step4.spouseWorks ?? undefined,
      spouseIncome: store.step4.spouseIncome ?? undefined,
      childrenCount: store.step4.childrenCount ?? undefined,
      familyInBusiness: store.step4.familyInBusiness ?? undefined,
    },
  });

  async function onSubmit(data: Step4Data) {
    store.setStep4(data);
    store.setCurrentStep(5);
    await saveProgress({ step: 4, stepData: data });
    router.push("/questionnaire/5");
  }

  const isMarried = watch("marriedFilingJointly");
  const spouseWorks = watch("spouseWorks");
  const hasKids = (watch("childrenCount") ?? 0) > 0;
  const familyInBusiness = watch("familyInBusiness");

  return (
    <StepLayout
      currentStep={4}
      highestStepReached={store.highestStepReached}
      title="Family & personal"
      description="Family structure unlocks powerful strategies: HireMySpouse, 529 plans, dependent care, and SLAT trusts."
      onNext={handleSubmit(onSubmit)}
      isSaving={store.isSaving}
      lastSavedAt={store.lastSavedAt}
      onStepClick={(s) => router.push(`/questionnaire/${s}`)}
    >
      {/* Married? */}
      <FormField
        label="Married filing jointly?"
        htmlFor="marriedFilingJointly"
        error={errors.marriedFilingJointly?.message}
      >
        <YesNoToggle
          id="marriedFilingJointly"
          value={isMarried ?? null}
          onChange={(v) => setValue("marriedFilingJointly", v)}
        />
      </FormField>

      {/* Spouse employment */}
      {isMarried && (
        <>
          <FormField
            label="Does your spouse work?"
            htmlFor="spouseWorks"
            error={errors.spouseWorks?.message}
          >
            <YesNoToggle
              id="spouseWorks"
              value={spouseWorks ?? null}
              onChange={(v) => setValue("spouseWorks", v)}
            />
          </FormField>

          {spouseWorks && (
            <FormField
              label="Spouse annual income"
              htmlFor="spouseIncome"
              error={errors.spouseIncome?.message}
              hint="Affects backdoor Roth eligibility, Social Security optimization, and SLAT strategies"
            >
              <CurrencyInput
                id="spouseIncome"
                value={watch("spouseIncome")}
                onChange={(v) => setValue("spouseIncome", v ?? undefined)}
                placeholder="75,000"
              />
            </FormField>
          )}

          {!spouseWorks && spouseWorks !== undefined && (
            <div className="rounded-lg bg-emerald-950/30 border border-emerald-500/20 p-3">
              <p className="text-xs text-emerald-400">
                <span className="font-semibold">Spousal IRA opportunity:</span> A non-working spouse qualifies
                for a Spousal IRA ($7,000/yr). The AI will include this in your retirement analysis.
              </p>
            </div>
          )}
        </>
      )}

      {/* Children */}
      <FormField
        label="Number of dependent children"
        htmlFor="childrenCount"
        error={errors.childrenCount?.message}
        hint="Under age 18 (or 24 if full-time student)"
      >
        <NumberInput
          id="childrenCount"
          value={watch("childrenCount") ?? null}
          onChange={(v) => setValue("childrenCount", v ?? undefined)}
          placeholder="0"
          min={0}
          max={20}
        />
      </FormField>

      {hasKids && (
        <div className="rounded-lg bg-blue-950/30 border border-blue-500/20 p-3">
          <p className="text-xs text-blue-400">
            <span className="font-semibold">Child tax strategies unlocked:</span> 529 superfunding ($90K lump sum),
            employing children in your business (FICA-exempt under 18), dependent care FSA, and education credits.
          </p>
        </div>
      )}

      {/* Family in business */}
      <FormField
        label="Do you employ family members in your business?"
        htmlFor="familyInBusiness"
        error={errors.familyInBusiness?.message}
        hint="Or would you like to? Hiring family members is a powerful deduction strategy."
      >
        <YesNoToggle
          id="familyInBusiness"
          value={familyInBusiness ?? null}
          onChange={(v) => setValue("familyInBusiness", v)}
        />
      </FormField>

      {familyInBusiness && (
        <div className="rounded-lg bg-emerald-950/30 border border-emerald-500/20 p-3">
          <p className="text-xs text-emerald-400">
            <span className="font-semibold">Family employment strategies:</span> Children under 18 in a sole prop/LLC
            pay no FICA. Spouses in the business unlock additional retirement accounts. All wages are deductible.
          </p>
        </div>
      )}
    </StepLayout>
  );
}
