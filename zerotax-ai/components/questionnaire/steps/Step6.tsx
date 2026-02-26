"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { step6Schema, type Step6Data } from "@/lib/schemas/questionnaire";
import { useQuestionnaireStore } from "@/store/questionnaire";
import { StepLayout } from "../StepLayout";
import { FormField, CheckboxCard, NumberInput } from "../FormField";
import { useRouter } from "next/navigation";
import { useSaveProgress } from "@/hooks/useSaveProgress";
import { cn } from "@/lib/utils";
import {
  TrendingDown,
  Shield,
  Heart,
  LogOut,
  PiggyBank,
  Users,
  Clock,
} from "lucide-react";

const GOALS = [
  {
    key: "goalMinimizeTaxes" as const,
    label: "Minimize taxes now",
    description: "Immediate tax reduction through deductions, credits, and entity structure",
    icon: TrendingDown,
  },
  {
    key: "goalAssetProtection" as const,
    label: "Protect assets from lawsuits",
    description: "Holding companies, charging order protection, DAPTs",
    icon: Shield,
  },
  {
    key: "goalEstatePlanning" as const,
    label: "Estate & legacy planning",
    description: "Trusts, wealth transfer, minimizing estate taxes",
    icon: Heart,
  },
  {
    key: "goalExitStrategy" as const,
    label: "Exit / sale optimization",
    description: "QSBS, installment sales, ESOP, step-up in basis strategies",
    icon: LogOut,
  },
  {
    key: "goalRetirementPlanning" as const,
    label: "Maximize retirement savings",
    description: "Solo 401(k), defined benefit plan, backdoor Roth",
    icon: PiggyBank,
  },
  {
    key: "goalHireFamily" as const,
    label: "Employ family members",
    description: "Tax-free wages to children, spousal retirement accounts",
    icon: Users,
  },
];

const HORIZON_OPTIONS = [
  { value: "immediate", label: "Immediate (implement now)", desc: "Focus on quick wins for this tax year" },
  { value: "1_year", label: "1 year", desc: "Short-term planning with implementation flexibility" },
  { value: "3_year", label: "3 years", desc: "Mid-term restructuring and retirement buildout" },
  { value: "5_plus", label: "5+ years", desc: "Long-term wealth building and estate planning" },
];

export function Step6() {
  const router = useRouter();
  const store = useQuestionnaireStore();
  const { saveProgress } = useSaveProgress();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { handleSubmit, watch, setValue, formState: { errors } } = useForm<Step6Data>({
    resolver: zodResolver(step6Schema) as any,
    defaultValues: {
      goalMinimizeTaxes: store.step6.goalMinimizeTaxes ?? true,
      goalAssetProtection: store.step6.goalAssetProtection ?? false,
      goalEstatePlanning: store.step6.goalEstatePlanning ?? false,
      goalExitStrategy: store.step6.goalExitStrategy ?? false,
      goalRetirementPlanning: store.step6.goalRetirementPlanning ?? true,
      goalHireFamily: store.step6.goalHireFamily ?? false,
      planningHorizon: store.step6.planningHorizon,
      exitTimelineYears: store.step6.exitTimelineYears ?? undefined,
    },
  });

  async function onSubmit(data: Step6Data) {
    store.setStep6(data);
    store.setCurrentStep(7);
    await saveProgress({ step: 6, stepData: data });
    router.push("/questionnaire/7");
  }

  const planningHorizon = watch("planningHorizon");
  const goalExit = watch("goalExitStrategy");
  const selectedGoalsCount = GOALS.filter((g) => watch(g.key)).length;

  return (
    <StepLayout
      currentStep={6}
      highestStepReached={store.highestStepReached}
      title="Goals & priorities"
      description="Select everything that matters to you — the AI will prioritize strategies accordingly."
      onNext={handleSubmit(onSubmit)}
      isSaving={store.isSaving}
      lastSavedAt={store.lastSavedAt}
      onStepClick={(s) => router.push(`/questionnaire/${s}`)}
    >
      {/* Goals */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium text-white">What are your financial goals?</p>
          {selectedGoalsCount > 0 && (
            <span className="text-xs text-emerald-400">{selectedGoalsCount} selected</span>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {GOALS.map((goal) => (
            <CheckboxCard
              key={goal.key}
              id={goal.key}
              label={goal.label}
              description={goal.description}
              checked={watch(goal.key) ?? false}
              onChange={(checked) => setValue(goal.key, checked)}
              icon={goal.icon}
            />
          ))}
        </div>
      </div>

      {/* Planning horizon */}
      <div className="border-t border-white/5 pt-5">
        <FormField
          label="Planning horizon"
          htmlFor="planningHorizon"
          required
          error={errors.planningHorizon?.message}
          hint="How far out should we optimize your tax strategy?"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {HORIZON_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setValue("planningHorizon", opt.value as Step6Data["planningHorizon"], { shouldValidate: true })}
                className={cn(
                  "text-left rounded-xl border p-3.5 transition-all",
                  planningHorizon === opt.value
                    ? "border-emerald-500/50 bg-emerald-950/20"
                    : "border-white/10 bg-white/[0.02] hover:border-white/20"
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div
                    className={cn(
                      "w-4 h-4 rounded-full border-2 flex items-center justify-center",
                      planningHorizon === opt.value
                        ? "border-emerald-500 bg-emerald-500"
                        : "border-white/20"
                    )}
                  >
                    {planningHorizon === opt.value && (
                      <div className="w-1.5 h-1.5 rounded-full bg-white" />
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-sm font-medium",
                      planningHorizon === opt.value ? "text-emerald-400" : "text-white"
                    )}
                  >
                    {opt.label}
                  </span>
                </div>
                <p className="text-xs text-slate-500 pl-6">{opt.desc}</p>
              </button>
            ))}
          </div>
        </FormField>
      </div>

      {/* Exit timeline (conditional) */}
      {goalExit && (
        <FormField
          label="Target exit timeline (years)"
          htmlFor="exitTimelineYears"
          error={errors.exitTimelineYears?.message}
          hint="When do you plan to sell or exit? Important for QSBS holding period and installment sale planning."
        >
          <div className="relative">
            <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <NumberInput
              id="exitTimelineYears"
              value={watch("exitTimelineYears") ?? null}
              onChange={(v) => setValue("exitTimelineYears", v ?? undefined)}
              placeholder="5"
              min={0}
              max={50}
              className="pl-10"
            />
          </div>
        </FormField>
      )}

      {/* Readiness callout */}
      {selectedGoalsCount > 0 && planningHorizon && (
        <div className="rounded-lg bg-emerald-950/30 border border-emerald-500/20 p-3">
          <p className="text-xs text-emerald-400">
            <span className="font-semibold">Almost done!</span> Click Continue to review your answers,
            then we&apos;ll run our AI analysis — usually takes 15–30 seconds.
          </p>
        </div>
      )}
    </StepLayout>
  );
}
