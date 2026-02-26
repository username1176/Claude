"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { step3Schema, type Step3Data } from "@/lib/schemas/questionnaire";
import { useQuestionnaireStore } from "@/store/questionnaire";
import { StepLayout } from "../StepLayout";
import { FormField, FormSelect, NumberInput, StateMultiSelect } from "../FormField";
import { useRouter } from "next/navigation";
import { useSaveProgress } from "@/hooks/useSaveProgress";
import { US_STATES } from "@/lib/utils";
import { AlertCircle } from "lucide-react";

export function Step3() {
  const router = useRouter();
  const store = useQuestionnaireStore();
  const { saveProgress } = useSaveProgress();

  const { handleSubmit, watch, setValue, formState: { errors } } = useForm<Step3Data>({
    resolver: zodResolver(step3Schema),
    defaultValues: {
      stateOfFormation: store.step3.stateOfFormation ?? "",
      statesOperating: store.step3.statesOperating ?? [],
      numOwners: store.step3.numOwners ?? undefined,
    },
  });

  async function onSubmit(data: Step3Data) {
    store.setStep3(data);
    store.setCurrentStep(4);
    await saveProgress({ step: 3, stepData: data });
    router.push("/questionnaire/4");
  }

  const stateOptions = US_STATES.map((s) => ({ value: s.value, label: s.label }));
  const formationState = watch("stateOfFormation");
  const operatingStates = watch("statesOperating") ?? [];

  // Highlight favorable formation states for asset protection
  const favorableStates = ["WY", "DE", "NV", "SD", "AK"];
  const isInFavorableState = favorableStates.includes(formationState);

  return (
    <StepLayout
      currentStep={3}
      highestStepReached={store.highestStepReached}
      title="Location & structure"
      description="State taxes and formation jurisdiction significantly impact your optimal strategy."
      onNext={handleSubmit(onSubmit)}
      isSaving={store.isSaving}
      lastSavedAt={store.lastSavedAt}
      onStepClick={(s) => router.push(`/questionnaire/${s}`)}
    >
      <FormField
        label="State of formation"
        htmlFor="stateOfFormation"
        required
        error={errors.stateOfFormation?.message}
        hint="Where your business entity is legally registered"
      >
        <FormSelect
          id="stateOfFormation"
          value={formationState}
          onChange={(v) => setValue("stateOfFormation", v, { shouldValidate: true })}
          options={stateOptions}
          placeholder="Select state…"
        />
      </FormField>

      {/* State insight */}
      {formationState && (
        <div
          className={`rounded-lg p-3 text-xs ${
            isInFavorableState
              ? "bg-emerald-950/30 border border-emerald-500/20 text-emerald-400"
              : "bg-blue-950/30 border border-blue-500/20 text-blue-400"
          }`}
        >
          {isInFavorableState ? (
            <>
              <span className="font-semibold">{formationState} is excellent for asset protection</span> — strong
              charging order protection, favorable LLC laws, and no state income tax (WY/NV/SD).
            </>
          ) : (
            <>
              <span className="font-semibold">AI will analyze</span> whether a Wyoming or Delaware holding
              company structure could benefit your {formationState}-based business.
            </>
          )}
        </div>
      )}

      <FormField
        label="States where you operate"
        htmlFor="statesOperating"
        required
        error={errors.statesOperating?.message}
        hint="Select all states where you have nexus (employees, offices, significant customers)"
      >
        <StateMultiSelect
          selected={operatingStates}
          onChange={(states) => setValue("statesOperating", states, { shouldValidate: true })}
        />
        {operatingStates.length > 0 && (
          <p className="text-xs text-slate-500 mt-2">
            {operatingStates.length} state{operatingStates.length !== 1 ? "s" : ""} selected: {operatingStates.join(", ")}
          </p>
        )}
      </FormField>

      {/* Multi-state warning */}
      {operatingStates.length > 3 && (
        <div className="rounded-lg bg-yellow-950/30 border border-yellow-500/20 p-3 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-yellow-400 shrink-0 mt-0.5" />
          <p className="text-xs text-yellow-400">
            Multi-state operations trigger nexus issues. Our AI will identify PTE (pass-through entity) election
            opportunities and state apportionment strategies for each state.
          </p>
        </div>
      )}

      <FormField
        label="Number of owners / partners"
        htmlFor="numOwners"
        error={errors.numOwners?.message}
        hint="Total equity owners (including yourself)"
      >
        <NumberInput
          id="numOwners"
          value={watch("numOwners") ?? null}
          onChange={(v) => setValue("numOwners", v ?? undefined)}
          placeholder="1"
          min={1}
          max={999}
        />
      </FormField>
    </StepLayout>
  );
}
