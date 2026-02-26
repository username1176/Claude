"use client";

import { cn } from "@/lib/utils";
import { CheckCircle2 } from "lucide-react";
import { TOTAL_STEPS } from "@/lib/schemas/questionnaire";

const STEP_LABELS = [
  "Business Profile",
  "Revenue",
  "Location",
  "Family",
  "Assets",
  "Goals",
  "Review",
];

interface ProgressBarProps {
  currentStep: number;
  highestStepReached: number;
  onStepClick?: (step: number) => void;
}

export function ProgressBar({ currentStep, highestStepReached, onStepClick }: ProgressBarProps) {
  return (
    <div className="w-full">
      {/* Step dots — desktop */}
      <div className="hidden md:flex items-center justify-between mb-2">
        {STEP_LABELS.map((label, idx) => {
          const step = idx + 1;
          const isCompleted = step < currentStep;
          const isCurrent = step === currentStep;
          const isAccessible = step <= highestStepReached;

          return (
            <div key={step} className="flex flex-col items-center flex-1">
              <div className="flex items-center w-full">
                {/* Connector line left */}
                <div
                  className={cn(
                    "flex-1 h-0.5 transition-colors",
                    idx === 0 ? "invisible" : "",
                    isCompleted || isCurrent ? "bg-emerald-500/60" : "bg-white/10"
                  )}
                />
                {/* Circle */}
                <button
                  type="button"
                  onClick={() => isAccessible && onStepClick?.(step)}
                  disabled={!isAccessible}
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-200 shrink-0",
                    isCompleted
                      ? "bg-emerald-600 text-white cursor-pointer hover:bg-emerald-500"
                      : isCurrent
                      ? "bg-emerald-600 text-white ring-2 ring-emerald-400/50 ring-offset-2 ring-offset-[#050d1a]"
                      : isAccessible
                      ? "bg-white/10 text-slate-400 hover:bg-white/20 cursor-pointer"
                      : "bg-white/5 text-slate-600 cursor-not-allowed"
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    step
                  )}
                </button>
                {/* Connector line right */}
                <div
                  className={cn(
                    "flex-1 h-0.5 transition-colors",
                    idx === TOTAL_STEPS - 1 ? "invisible" : "",
                    isCompleted ? "bg-emerald-500/60" : "bg-white/10"
                  )}
                />
              </div>
              <span
                className={cn(
                  "mt-1.5 text-[10px] text-center leading-tight max-w-[60px] transition-colors",
                  isCurrent ? "text-emerald-400 font-medium" : isCompleted ? "text-emerald-400/70" : "text-slate-600"
                )}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Mobile progress bar */}
      <div className="md:hidden space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">
            Step {currentStep} of {TOTAL_STEPS}:{" "}
            <span className="text-white font-medium">{STEP_LABELS[currentStep - 1]}</span>
          </span>
          <span className="text-emerald-400 font-medium">
            {Math.round(((currentStep - 1) / (TOTAL_STEPS - 1)) * 100)}%
          </span>
        </div>
        <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
            style={{ width: `${((currentStep - 1) / (TOTAL_STEPS - 1)) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
