"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Save, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProgressBar } from "./ProgressBar";
import { TOTAL_STEPS } from "@/lib/schemas/questionnaire";
import { cn } from "@/lib/utils";

interface StepLayoutProps {
  currentStep: number;
  highestStepReached: number;
  title: string;
  description: string;
  children: React.ReactNode;
  onNext: () => void;
  onBack?: () => void;
  isSubmitting?: boolean;
  isSaving?: boolean;
  lastSavedAt?: string | null;
  nextLabel?: string;
  canProceed?: boolean;
  onStepClick?: (step: number) => void;
}

export function StepLayout({
  currentStep,
  highestStepReached,
  title,
  description,
  children,
  onNext,
  onBack,
  isSubmitting = false,
  isSaving = false,
  lastSavedAt,
  nextLabel,
  canProceed = true,
  onStepClick,
}: StepLayoutProps) {
  const router = useRouter();
  const isLastStep = currentStep === TOTAL_STEPS;

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else if (currentStep > 1) {
      router.push(`/questionnaire/${currentStep - 1}`);
    } else {
      router.push("/dashboard");
    }
  };

  const formattedSaveTime = lastSavedAt
    ? new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" }).format(
        new Date(lastSavedAt)
      )
    : null;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <button
            type="button"
            onClick={handleBack}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {currentStep === 1 ? "Dashboard" : "Back"}
          </button>

          {/* Auto-save indicator */}
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            {isSaving ? (
              <>
                <Save className="h-3 w-3 animate-pulse text-emerald-400" />
                <span className="text-emerald-400">Saving…</span>
              </>
            ) : formattedSaveTime ? (
              <>
                <Clock className="h-3 w-3" />
                <span>Saved at {formattedSaveTime}</span>
              </>
            ) : null}
          </div>
        </div>

        {/* Progress bar */}
        <ProgressBar
          currentStep={currentStep}
          highestStepReached={highestStepReached}
          onStepClick={onStepClick}
        />
      </div>

      {/* Step card */}
      <div className="glass-card rounded-2xl p-6 md:p-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-white">{title}</h2>
          <p className="text-slate-400 mt-1 text-sm leading-relaxed">{description}</p>
        </div>

        {/* Form content */}
        <div className="space-y-5">{children}</div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={handleBack}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          {currentStep === 1 ? "Dashboard" : "Back"}
        </Button>

        <div className="flex items-center gap-3">
          {/* Step counter */}
          <span className="text-xs text-slate-500">
            {currentStep}/{TOTAL_STEPS}
          </span>

          <Button
            onClick={onNext}
            disabled={!canProceed || isSubmitting}
            loading={isSubmitting}
            variant="gradient"
            className={cn("gap-2", isLastStep && "glow-emerald")}
          >
            {nextLabel ?? (isLastStep ? "Generate My Tax Plan" : "Continue")}
            {!isLastStep && <ArrowRight className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
