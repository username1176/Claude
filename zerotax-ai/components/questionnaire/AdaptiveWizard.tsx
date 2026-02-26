"use client";

// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Adaptive Multi-Step Wizard
// Replaces the fixed 7-step flow with a smart 12–17 question adaptive engine.
// Equivalent to the updated app.py — this is the primary questionnaire UI.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect, useCallback } from "react";
import {
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  X,
  Clock,
  Save,
  CheckCircle2,
} from "lucide-react";
import {
  QUESTIONS,
  getNextQuestion,
  getProgress,
  type Answers,
  type Question,
  type QuestionType,
} from "@/lib/question-engine";
import { useAdaptiveStore } from "@/store/adaptive-questionnaire";
import { useSaveAdaptive } from "@/hooks/useSaveAdaptive";
import { SummaryPage } from "./SummaryPage";
import { cn } from "@/lib/utils";
import { US_STATES } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

// auto-advance types (click → immediately move to next question)
const AUTO_ADVANCE: QuestionType[] = ["select", "boolean"];

// ─── Input Sub-Components ─────────────────────────────────────────────────────

function SelectInput({
  question,
  onSelect,
}: {
  question: Question;
  onSelect: (value: string) => void;
}) {
  return (
    <div className="space-y-2.5">
      {question.options!.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onSelect(opt.value)}
          className="w-full flex items-center gap-4 px-5 py-4 rounded-xl border border-white/10 bg-white/[0.03] hover:border-emerald-500/60 hover:bg-emerald-950/20 text-left transition-all duration-200 group"
        >
          {opt.emoji && (
            <span className="text-2xl flex-shrink-0">{opt.emoji}</span>
          )}
          <div className="flex-1 min-w-0">
            <div className="font-medium text-white text-sm">{opt.label}</div>
            {opt.description && (
              <div className="text-xs text-slate-500 mt-0.5">
                {opt.description}
              </div>
            )}
          </div>
          <ChevronRight className="h-4 w-4 text-slate-600 group-hover:text-emerald-400 transition-colors flex-shrink-0" />
        </button>
      ))}
    </div>
  );
}

function BooleanInput({
  onSelect,
}: {
  question: Question;
  onSelect: (value: boolean) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <button
        onClick={() => onSelect(true)}
        className="flex flex-col items-center justify-center gap-3 p-8 rounded-xl border border-white/10 bg-white/[0.03] hover:border-emerald-500/60 hover:bg-emerald-950/20 transition-all duration-200 group"
      >
        <span className="text-4xl group-hover:scale-110 transition-transform">
          ✅
        </span>
        <span className="text-lg font-semibold text-white">Yes</span>
      </button>
      <button
        onClick={() => onSelect(false)}
        className="flex flex-col items-center justify-center gap-3 p-8 rounded-xl border border-white/10 bg-white/[0.03] hover:border-slate-400/40 hover:bg-white/5 transition-all duration-200 group"
      >
        <span className="text-4xl group-hover:scale-110 transition-transform">
          ❌
        </span>
        <span className="text-lg font-semibold text-white">No</span>
      </button>
    </div>
  );
}

function MultiSelectInput({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: unknown;
  onChange: (value: string[]) => void;
}) {
  const selected = (value as string[]) ?? [];

  const toggle = (v: string) => {
    onChange(
      selected.includes(v)
        ? selected.filter((s) => s !== v)
        : [...selected, v]
    );
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {question.options!.map((opt) => {
        const isSelected = selected.includes(opt.value);
        return (
          <button
            key={opt.value}
            onClick={() => toggle(opt.value)}
            className={cn(
              "flex items-start gap-3 p-4 rounded-xl border text-left transition-all duration-200",
              isSelected
                ? "border-emerald-500/60 bg-emerald-950/30 text-white"
                : "border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/20 hover:bg-white/5"
            )}
          >
            {opt.emoji && (
              <span className="text-xl flex-shrink-0 mt-0.5">{opt.emoji}</span>
            )}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm leading-tight">{opt.label}</div>
              {opt.description && (
                <div className="text-xs text-slate-500 mt-0.5">
                  {opt.description}
                </div>
              )}
            </div>
            <div
              className={cn(
                "h-5 w-5 rounded-full border flex items-center justify-center flex-shrink-0 mt-0.5 transition-all",
                isSelected
                  ? "border-emerald-500 bg-emerald-500"
                  : "border-white/20"
              )}
            >
              {isSelected && <CheckCircle2 className="h-3.5 w-3.5 text-white" />}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function CurrencyInput({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: unknown;
  onChange: (value: number | null) => void;
}) {
  const [raw, setRaw] = useState<string>(
    value !== null && value !== undefined ? String(value) : ""
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const stripped = e.target.value.replace(/[^0-9.]/g, "");
    setRaw(stripped);
    onChange(stripped ? Number(stripped) : null);
  };

  const formatted =
    raw && !isNaN(Number(raw))
      ? Number(raw).toLocaleString("en-US")
      : raw;

  return (
    <div className="space-y-3">
      <div className="relative">
        <span className="absolute left-5 top-1/2 -translate-y-1/2 text-2xl text-slate-400 font-light pointer-events-none">
          $
        </span>
        <input
          type="text"
          inputMode="numeric"
          value={raw}
          onChange={handleChange}
          placeholder={question.placeholder ?? "0"}
          className="w-full pl-11 pr-5 py-5 bg-white/5 border border-white/10 rounded-xl text-2xl text-white font-light placeholder-slate-600 focus:outline-none focus:border-emerald-500/60 focus:bg-emerald-950/10 transition-all"
          autoFocus
        />
      </div>
      {raw && formatted !== raw && (
        <p className="text-center text-sm text-slate-500">${formatted}</p>
      )}
    </div>
  );
}

function StateSelectInput({
  value,
  onChange,
}: {
  question: Question;
  value: unknown;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative">
      <select
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-emerald-500/60 focus:bg-emerald-950/10 transition-all appearance-none cursor-pointer text-sm"
        autoFocus
      >
        <option value="" className="bg-slate-900 text-slate-400">
          Select your state…
        </option>
        {US_STATES.map((s) => (
          <option key={s.value} value={s.value} className="bg-slate-900">
            {s.label}
          </option>
        ))}
      </select>
      <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none rotate-90" />
    </div>
  );
}

// ─── Question Input Router ────────────────────────────────────────────────────

function QuestionInput({
  question,
  value,
  onChange,
  onAutoAdvance,
}: {
  question: Question;
  value: unknown;
  onChange: (value: unknown) => void;
  onAutoAdvance: (value: unknown) => void;
}) {
  switch (question.type) {
    case "select":
      return (
        <SelectInput
          question={question}
          onSelect={(v) => onAutoAdvance(v)}
        />
      );
    case "boolean":
      return (
        <BooleanInput
          question={question}
          onSelect={(v) => onAutoAdvance(v)}
        />
      );
    case "multiselect":
      return (
        <MultiSelectInput
          question={question}
          value={value}
          onChange={(v) => onChange(v)}
        />
      );
    case "currency":
      return (
        <CurrencyInput
          question={question}
          value={value}
          onChange={(v) => onChange(v)}
        />
      );
    case "state_select":
      return (
        <StateSelectInput
          question={question}
          value={value}
          onChange={(v) => onChange(v)}
        />
      );
    default:
      return null;
  }
}

// ─── Tooltip Panel ────────────────────────────────────────────────────────────

function TooltipPanel({
  question,
  onClose,
}: {
  question: Question;
  onClose: () => void;
}) {
  return (
    <div className="mb-5 rounded-xl bg-emerald-950/40 border border-emerald-500/20 p-4 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-emerald-400 mb-1.5">
            💡 {question.tooltipTitle}
          </p>
          <p className="text-xs text-slate-300 leading-relaxed">
            {question.tooltip}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-white transition-colors flex-shrink-0"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ─── Progress Header ──────────────────────────────────────────────────────────

function ProgressHeader({
  answered,
  total,
  percent,
  onBack,
  canGoBack,
  isSaving,
  lastSavedAt,
}: {
  answered: number;
  total: number;
  percent: number;
  onBack: () => void;
  canGoBack: boolean;
  isSaving: boolean;
  lastSavedAt: string | null;
}) {
  const minsLeft = Math.max(1, Math.ceil((total - answered) * 0.22));

  const formattedSave = lastSavedAt
    ? new Intl.DateTimeFormat("en-US", {
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(lastSavedAt))
    : null;

  return (
    <div className="sticky top-0 z-20 bg-[#050d1a]/95 backdrop-blur-sm border-b border-white/5 px-4 py-3">
      <div className="max-w-2xl mx-auto">
        {/* Top row */}
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={onBack}
            disabled={!canGoBack}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors disabled:opacity-25 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </button>

          <span className="text-xs text-slate-500 font-medium">
            Question {answered + 1} of ~{total}
          </span>

          <div className="flex items-center gap-2">
            {isSaving ? (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <Save className="h-3 w-3 animate-pulse" />
                Saving…
              </span>
            ) : formattedSave ? (
              <span className="flex items-center gap-1 text-xs text-slate-600">
                <Clock className="h-3 w-3" />
                Saved {formattedSave}
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-slate-600">
                <Clock className="h-3 w-3" />
                ~{minsLeft} min left
              </span>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-700 to-emerald-400 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${Math.max(2, percent)}%` }}
          />
        </div>

        {/* Step dots */}
        <div className="flex items-center justify-between mt-2">
          {Array.from({ length: Math.min(total, 12) }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-1 rounded-full transition-all duration-500 flex-1 mx-0.5",
                i < answered
                  ? "bg-emerald-500"
                  : i === answered
                  ? "bg-emerald-700/60"
                  : "bg-white/5"
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main AdaptiveWizard Component ────────────────────────────────────────────

interface AdaptiveWizardProps {
  userId: string;
}

export function AdaptiveWizard({ userId: _userId }: AdaptiveWizardProps) {
  const store = useAdaptiveStore();
  const { save } = useSaveAdaptive();

  // Local state for the current question's input value
  const [localValue, setLocalValue] = useState<unknown>(null);
  const [tooltipOpen, setTooltipOpen] = useState(false);
  // Key changes to trigger CSS re-animation on question transition
  const [animKey, setAnimKey] = useState(0);

  // ── Derive current question from engine ──────────────────────────────────
  const currentQ = getNextQuestion(store.answers, store.history);
  const progress = getProgress(store.answers, store.history);

  // ── Sync local value when question changes ───────────────────────────────
  useEffect(() => {
    if (!currentQ) return;
    const existing = store.answers[currentQ.id];
    if (currentQ.type === "multiselect") {
      setLocalValue((existing as string[]) ?? []);
    } else {
      setLocalValue(existing ?? null);
    }
    setTooltipOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentQ?.id]);

  // ── Mark complete when all visible questions are answered ────────────────
  useEffect(() => {
    if (!currentQ && store.history.length > 0 && !store.isComplete) {
      store.complete();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentQ?.id, store.history.length]);

  // ── Advance to next question ─────────────────────────────────────────────
  const advance = useCallback(
    async (questionId: string, value: unknown) => {
      const newAnswers = { ...store.answers, [questionId]: value };
      store.setAnswer(questionId, value);
      setAnimKey((k) => k + 1);
      // Fire-and-forget background save
      void save(newAnswers);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [store.answers, store.history]
  );

  // ── Go back one question ─────────────────────────────────────────────────
  const handleBack = useCallback(() => {
    store.goBack();
    setAnimKey((k) => k + 1);
  }, [store]);

  // ── Render SummaryPage when done ─────────────────────────────────────────
  if (store.isComplete || (!currentQ && store.history.length > 0)) {
    return <SummaryPage />;
  }

  if (!currentQ) {
    // First load — show first question (engine returns Q1)
    const firstQ = QUESTIONS[0];
    if (!firstQ) return null;
  }

  // ── Determine if Continue button should be shown ─────────────────────────
  const needsContinue = !AUTO_ADVANCE.includes(currentQ!.type);

  const canContinue = (): boolean => {
    if (currentQ!.optional) return true;
    if (currentQ!.type === "multiselect") {
      return Array.isArray(localValue) && localValue.length > 0;
    }
    if (currentQ!.type === "currency") {
      // Allow 0 as valid, only block null/undefined
      return localValue !== null && localValue !== undefined;
    }
    return !!localValue;
  };

  const handleContinue = () => {
    if (!canContinue() && !currentQ!.optional) return;
    void advance(currentQ!.id, localValue);
  };

  const handleSkip = () => {
    void advance(currentQ!.id, null);
  };

  return (
    <div className="min-h-[calc(100vh-120px)] flex flex-col -mx-6 -my-6 lg:-mx-8 lg:-my-8">
      {/* ── Sticky Progress Header ─────────────────────────────────────── */}
      <ProgressHeader
        answered={progress.answered}
        total={progress.total}
        percent={progress.percent}
        onBack={handleBack}
        canGoBack={store.history.length > 0}
        isSaving={store.isSaving}
        lastSavedAt={store.lastSavedAt}
      />

      {/* ── Question Area ──────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <div
          key={animKey}
          className="w-full max-w-2xl animate-slide-up"
        >
          {/* Question Card */}
          <div className="glass-card rounded-2xl p-6 md:p-8">
            {/* Emoji + Text */}
            <div className="mb-6">
              <div className="text-5xl mb-4 leading-none">{currentQ!.emoji}</div>
              <h2 className="text-xl md:text-2xl font-semibold text-white leading-snug mb-1.5">
                {currentQ!.text}
              </h2>
              {currentQ!.subtitle && (
                <p className="text-sm text-slate-400 leading-relaxed">
                  {currentQ!.subtitle}
                </p>
              )}
            </div>

            {/* "Why we ask this" toggle */}
            <button
              onClick={() => setTooltipOpen((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-emerald-400/60 hover:text-emerald-400 mb-5 transition-colors"
            >
              <HelpCircle className="h-3.5 w-3.5" />
              {tooltipOpen ? "Hide explanation" : "Why we ask this"}
            </button>

            {/* Tooltip panel */}
            {tooltipOpen && (
              <TooltipPanel
                question={currentQ!}
                onClose={() => setTooltipOpen(false)}
              />
            )}

            {/* Input */}
            <QuestionInput
              question={currentQ!}
              value={localValue}
              onChange={setLocalValue}
              onAutoAdvance={(v) => void advance(currentQ!.id, v)}
            />
          </div>

          {/* ── Navigation (for non-auto-advance types) ──────────────── */}
          {needsContinue && (
            <div className="mt-4 flex items-center gap-3">
              {currentQ!.optional && (
                <button
                  onClick={handleSkip}
                  className="px-5 py-3 text-sm text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0"
                >
                  Skip
                </button>
              )}
              <button
                onClick={handleContinue}
                disabled={!canContinue() && !currentQ!.optional}
                className={cn(
                  "flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl font-medium text-sm transition-all duration-200",
                  canContinue()
                    ? "bg-emerald-600 hover:bg-emerald-500 text-white glow-emerald"
                    : "bg-white/5 text-slate-600 cursor-not-allowed"
                )}
              >
                Continue
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* Auto-advance hint for select/boolean */}
          {!needsContinue && (
            <p className="text-center text-xs text-slate-600 mt-4">
              Click an option to continue
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
