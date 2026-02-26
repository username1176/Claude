"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { step1Schema, type Step1Data } from "@/lib/schemas/questionnaire";
import { useQuestionnaireStore } from "@/store/questionnaire";
import { StepLayout } from "../StepLayout";
import { FormField, FormSelect, NumberInput } from "../FormField";
import { Input } from "@/components/ui/input";
import { useRouter } from "next/navigation";
import { useSaveProgress } from "@/hooks/useSaveProgress";

const STAGE_OPTIONS = [
  { value: "idea", label: "Idea / Pre-revenue" },
  { value: "startup", label: "Startup (< $250K revenue)" },
  { value: "growth", label: "Growth ($250K–$2M revenue)" },
  { value: "established", label: "Established ($2M–$10M revenue)" },
  { value: "mature", label: "Mature ($10M+ revenue)" },
];

const ENTITY_OPTIONS = [
  { value: "sole_prop", label: "Sole Proprietorship" },
  { value: "llc_single", label: "Single-Member LLC" },
  { value: "llc_multi", label: "Multi-Member LLC" },
  { value: "llc_scorp", label: "LLC taxed as S-Corp" },
  { value: "scorp", label: "S-Corporation" },
  { value: "ccorp", label: "C-Corporation" },
  { value: "partnership", label: "Partnership" },
  { value: "none", label: "No entity yet" },
];

const INDUSTRY_OPTIONS = [
  { value: "tech_software", label: "Technology / Software" },
  { value: "consulting", label: "Consulting / Professional Services" },
  { value: "real_estate", label: "Real Estate" },
  { value: "healthcare", label: "Healthcare / Medical" },
  { value: "ecommerce", label: "E-commerce / Retail" },
  { value: "finance", label: "Finance / Accounting" },
  { value: "legal", label: "Legal Services" },
  { value: "construction", label: "Construction / Trades" },
  { value: "media_creative", label: "Media / Creative / Marketing" },
  { value: "food_hospitality", label: "Food & Hospitality" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "agriculture", label: "Agriculture" },
  { value: "nonprofit", label: "Nonprofit" },
  { value: "other", label: "Other" },
];

export function Step1() {
  const router = useRouter();
  const store = useQuestionnaireStore();
  const { saveProgress } = useSaveProgress();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<Step1Data>({
    resolver: zodResolver(step1Schema),
    defaultValues: {
      businessName: store.step1.businessName ?? "",
      businessStage: store.step1.businessStage,
      industry: store.step1.industry ?? "",
      entityTypeCurrent: store.step1.entityTypeCurrent ?? "",
      yearBusinessFounded: store.step1.yearBusinessFounded ?? undefined,
    },
  });

  async function onSubmit(data: Step1Data) {
    store.setStep1(data);
    store.setCurrentStep(2);
    await saveProgress({ step: 1, stepData: data });
    router.push("/questionnaire/2");
  }

  return (
    <StepLayout
      currentStep={1}
      highestStepReached={store.highestStepReached}
      title="Tell us about your business"
      description="This helps us identify the right entity structure and strategies for your stage."
      onNext={handleSubmit(onSubmit)}
      isSaving={store.isSaving}
      lastSavedAt={store.lastSavedAt}
      onStepClick={(s) => router.push(`/questionnaire/${s}`)}
    >
      <FormField label="Business name" htmlFor="businessName" required error={errors.businessName?.message}>
        <Input
          id="businessName"
          placeholder="Acme Consulting LLC"
          {...register("businessName")}
        />
      </FormField>

      <FormField label="Business stage" htmlFor="businessStage" required error={errors.businessStage?.message}>
        <FormSelect
          id="businessStage"
          value={watch("businessStage")}
          onChange={(v) => setValue("businessStage", v as Step1Data["businessStage"], { shouldValidate: true })}
          options={STAGE_OPTIONS}
          placeholder="Select stage…"
        />
      </FormField>

      <FormField label="Industry" htmlFor="industry" required error={errors.industry?.message}>
        <FormSelect
          id="industry"
          value={watch("industry")}
          onChange={(v) => setValue("industry", v, { shouldValidate: true })}
          options={INDUSTRY_OPTIONS}
          placeholder="Select industry…"
        />
      </FormField>

      <FormField
        label="Current entity type"
        htmlFor="entityTypeCurrent"
        required
        error={errors.entityTypeCurrent?.message}
        hint="Select your current legal structure (or 'No entity yet' if you haven't formed one)"
      >
        <FormSelect
          id="entityTypeCurrent"
          value={watch("entityTypeCurrent")}
          onChange={(v) => setValue("entityTypeCurrent", v, { shouldValidate: true })}
          options={ENTITY_OPTIONS}
          placeholder="Select entity type…"
        />
      </FormField>

      <FormField
        label="Year business founded"
        htmlFor="yearBusinessFounded"
        error={errors.yearBusinessFounded?.message}
        hint="Leave blank if not yet founded. Important for QSBS qualification."
      >
        <NumberInput
          id="yearBusinessFounded"
          value={watch("yearBusinessFounded") ?? null}
          onChange={(v) => setValue("yearBusinessFounded", v ?? undefined)}
          placeholder={String(new Date().getFullYear())}
          min={1900}
          max={new Date().getFullYear()}
        />
      </FormField>
    </StepLayout>
  );
}
