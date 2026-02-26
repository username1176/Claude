"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  Edit2,
  Building2,
  DollarSign,
  MapPin,
  Users,
  BarChart3,
  Target,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import { useQuestionnaireStore } from "@/store/questionnaire";
import { StepLayout } from "../StepLayout";
import { formatCurrency } from "@/lib/utils";
import Link from "next/link";

interface ReviewSectionProps {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  step: number;
  children: React.ReactNode;
}

function ReviewSection({ title, icon: Icon, step, children }: ReviewSectionProps) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-emerald-400" />
          <span className="text-sm font-semibold text-white">{title}</span>
        </div>
        <Link
          href={`/questionnaire/${step}`}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-emerald-400 transition-colors"
        >
          <Edit2 className="h-3 w-3" />
          Edit
        </Link>
      </div>
      <div className="px-4 py-3 space-y-2">{children}</div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string | number | boolean | null | undefined }) {
  if (value === null || value === undefined || value === "") return null;
  const displayValue =
    typeof value === "boolean"
      ? value ? "Yes" : "No"
      : typeof value === "number"
      ? isNaN(value) ? "—" : String(value)
      : String(value);

  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-xs text-white font-medium text-right max-w-[60%]">{displayValue}</span>
    </div>
  );
}

const ENTITY_LABELS: Record<string, string> = {
  sole_prop: "Sole Proprietorship",
  llc_single: "Single-Member LLC",
  llc_multi: "Multi-Member LLC",
  llc_scorp: "LLC taxed as S-Corp",
  scorp: "S-Corporation",
  ccorp: "C-Corporation",
  partnership: "Partnership",
  none: "No entity yet",
};

const HORIZON_LABELS: Record<string, string> = {
  immediate: "Immediate",
  "1_year": "1 year",
  "3_year": "3 years",
  "5_plus": "5+ years",
};

export function Step7() {
  const router = useRouter();
  const store = useQuestionnaireStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { step1, step2, step3, step4, step5, step6 } = store;

  const activeGoals = [
    step6.goalMinimizeTaxes && "Minimize taxes",
    step6.goalAssetProtection && "Asset protection",
    step6.goalEstatePlanning && "Estate planning",
    step6.goalExitStrategy && "Exit strategy",
    step6.goalRetirementPlanning && "Retirement planning",
    step6.goalHireFamily && "Employ family",
  ].filter(Boolean) as string[];

  async function handleSubmit() {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await fetch("/api/questionnaire/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          businessId: store.businessId,
          questionnaireId: store.questionnaireId,
          data: {
            ...step1,
            ...step2,
            ...step3,
            ...step4,
            ...step5,
            ...step6,
          },
        }),
      });

      const json = await response.json();

      if (!response.ok) {
        throw new Error(json.error ?? "Submission failed");
      }

      // Clear persisted store & redirect to recommendations
      const recommendationId = json.recommendationId;
      store.reset();
      router.push(
        recommendationId
          ? `/recommendations/${recommendationId}`
          : "/recommendations"
      );
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      setIsSubmitting(false);
    }
  }

  return (
    <StepLayout
      currentStep={7}
      highestStepReached={store.highestStepReached}
      title="Review your information"
      description="Confirm your details before we run the AI analysis. You can edit any section."
      onNext={handleSubmit}
      isSubmitting={isSubmitting}
      isSaving={store.isSaving}
      lastSavedAt={store.lastSavedAt}
      nextLabel="Generate My Tax Plan"
      onStepClick={(s) => router.push(`/questionnaire/${s}`)}
    >
      {/* Business profile */}
      <ReviewSection title="Business Profile" icon={Building2} step={1}>
        <ReviewRow label="Business name" value={step1.businessName} />
        <ReviewRow label="Stage" value={step1.businessStage} />
        <ReviewRow label="Industry" value={step1.industry} />
        <ReviewRow label="Current entity" value={ENTITY_LABELS[step1.entityTypeCurrent ?? ""] ?? step1.entityTypeCurrent} />
        <ReviewRow label="Year founded" value={step1.yearBusinessFounded} />
      </ReviewSection>

      {/* Revenue */}
      <ReviewSection title="Revenue & Compensation" icon={DollarSign} step={2}>
        <ReviewRow label="Annual revenue" value={step2.annualRevenue != null ? formatCurrency(step2.annualRevenue) : undefined} />
        <ReviewRow label="Annual profit" value={step2.annualProfit != null ? formatCurrency(step2.annualProfit) : undefined} />
        <ReviewRow label="W-2 wages paid" value={step2.w2WagesPaid != null ? formatCurrency(step2.w2WagesPaid) : undefined} />
        <ReviewRow label="Owner draws" value={step2.ownerDraws != null ? formatCurrency(step2.ownerDraws) : undefined} />
        <ReviewRow label="Reasonable salary" value={step2.reasonableSalary != null ? formatCurrency(step2.reasonableSalary) : undefined} />
        {step2.otherIncome && (
          <ReviewRow label="Other income" value={formatCurrency(step2.otherIncome)} />
        )}
      </ReviewSection>

      {/* Location */}
      <ReviewSection title="Location & Structure" icon={MapPin} step={3}>
        <ReviewRow label="State of formation" value={step3.stateOfFormation} />
        <ReviewRow
          label="Operating states"
          value={(step3.statesOperating ?? []).join(", ")}
        />
        <ReviewRow label="Number of owners" value={step3.numOwners} />
      </ReviewSection>

      {/* Family */}
      <ReviewSection title="Family & Personal" icon={Users} step={4}>
        <ReviewRow label="Married filing jointly" value={step4.marriedFilingJointly} />
        {step4.marriedFilingJointly && (
          <>
            <ReviewRow label="Spouse works" value={step4.spouseWorks} />
            {step4.spouseWorks && (
              <ReviewRow label="Spouse income" value={step4.spouseIncome != null ? formatCurrency(step4.spouseIncome) : undefined} />
            )}
          </>
        )}
        <ReviewRow label="Dependent children" value={step4.childrenCount} />
        <ReviewRow label="Family in business" value={step4.familyInBusiness} />
      </ReviewSection>

      {/* Assets */}
      <ReviewSection title="Assets & Wealth" icon={BarChart3} step={5}>
        {step5.realEstateValue != null && <ReviewRow label="Real estate" value={formatCurrency(step5.realEstateValue)} />}
        {step5.businessAssetsValue != null && <ReviewRow label="Business assets" value={formatCurrency(step5.businessAssetsValue)} />}
        {step5.investmentPortfolio != null && <ReviewRow label="Investment portfolio" value={formatCurrency(step5.investmentPortfolio)} />}
        {step5.retirementAccounts != null && <ReviewRow label="Retirement accounts" value={formatCurrency(step5.retirementAccounts)} />}
        {step5.totalNetWorth != null && <ReviewRow label="Total net worth" value={formatCurrency(step5.totalNetWorth)} />}
        <ReviewRow label="Holds QSBS stock" value={step5.hasQsbsStock} />
      </ReviewSection>

      {/* Goals */}
      <ReviewSection title="Goals & Planning" icon={Target} step={6}>
        <div className="flex flex-wrap gap-1.5 py-1">
          {activeGoals.map((goal) => (
            <span
              key={goal}
              className="text-xs bg-emerald-950/40 border border-emerald-500/20 text-emerald-400 rounded-full px-2.5 py-0.5"
            >
              {goal}
            </span>
          ))}
          {activeGoals.length === 0 && (
            <span className="text-xs text-slate-500">No goals selected</span>
          )}
        </div>
        <ReviewRow
          label="Planning horizon"
          value={HORIZON_LABELS[step6.planningHorizon ?? ""] ?? step6.planningHorizon}
        />
        {step6.exitTimelineYears != null && (
          <ReviewRow label="Exit timeline" value={`${step6.exitTimelineYears} years`} />
        )}
      </ReviewSection>

      {/* What happens next */}
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/10 p-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center shrink-0">
            <Sparkles className="h-4 w-4 text-emerald-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white mb-1">What happens next</p>
            <ul className="space-y-1 text-xs text-slate-400">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                Claude AI searches 200+ tax strategies in our legal database
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                Calculates exact dollar savings for your specific situation
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                Generates prioritized implementation plan with IRC citations
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                Ready in approximately 15–30 seconds
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-2 text-xs text-slate-600">
        <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-yellow-700" />
        <span>
          By submitting, you confirm this is for informational purposes only.
          ZeroTax AI is not a law firm, CPA firm, or financial advisor. Always consult a licensed
          professional before implementing any tax strategy.
        </span>
      </div>

      {submitError && (
        <div
          className="rounded-lg p-3 text-sm text-red-400"
          style={{ background: "rgba(127,29,29,0.3)", border: "1px solid rgba(239,68,68,0.3)" }}
        >
          {submitError}
        </div>
      )}
    </StepLayout>
  );
}
