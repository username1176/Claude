"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { step5Schema, type Step5Data } from "@/lib/schemas/questionnaire";
import { useQuestionnaireStore } from "@/store/questionnaire";
import { StepLayout } from "../StepLayout";
import { FormField, CurrencyInput, YesNoToggle } from "../FormField";
import { useRouter } from "next/navigation";
import { useSaveProgress } from "@/hooks/useSaveProgress";
import { formatCurrency } from "@/lib/utils";

export function Step5() {
  const router = useRouter();
  const store = useQuestionnaireStore();
  const { saveProgress } = useSaveProgress();

  const { handleSubmit, watch, setValue, formState: { errors } } = useForm<Step5Data>({
    resolver: zodResolver(step5Schema),
    defaultValues: {
      realEstateValue: store.step5.realEstateValue ?? undefined,
      businessAssetsValue: store.step5.businessAssetsValue ?? undefined,
      investmentPortfolio: store.step5.investmentPortfolio ?? undefined,
      retirementAccounts: store.step5.retirementAccounts ?? undefined,
      totalNetWorth: store.step5.totalNetWorth ?? undefined,
      hasQsbsStock: store.step5.hasQsbsStock ?? undefined,
    },
  });

  async function onSubmit(data: Step5Data) {
    store.setStep5(data);
    store.setCurrentStep(6);
    await saveProgress({ step: 5, stepData: data });
    router.push("/questionnaire/6");
  }

  // Auto-calculate total net worth
  const realestate = watch("realEstateValue") ?? 0;
  const bizAssets = watch("businessAssetsValue") ?? 0;
  const investments = watch("investmentPortfolio") ?? 0;
  const retirement = watch("retirementAccounts") ?? 0;
  const estimatedNetWorth = realestate + bizAssets + investments + retirement;

  // Estate tax threshold (2025: $15M with OBBBA)
  const ESTATE_THRESHOLD = 15_000_000;
  const netWorth = watch("totalNetWorth") ?? estimatedNetWorth;
  const nearEstateThreshold = netWorth > ESTATE_THRESHOLD * 0.5;

  const hasQsbs = watch("hasQsbsStock");

  return (
    <StepLayout
      currentStep={5}
      highestStepReached={store.highestStepReached}
      title="Assets & wealth"
      description="Asset data enables estate planning analysis, depreciation strategies, and wealth transfer optimization."
      onNext={handleSubmit(onSubmit)}
      isSaving={store.isSaving}
      lastSavedAt={store.lastSavedAt}
      onStepClick={(s) => router.push(`/questionnaire/${s}`)}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField
          label="Real estate value"
          htmlFor="realEstateValue"
          error={errors.realEstateValue?.message}
          hint="Total FMV of all real property owned"
        >
          <CurrencyInput
            id="realEstateValue"
            value={watch("realEstateValue")}
            onChange={(v) => setValue("realEstateValue", v ?? undefined)}
            placeholder="0"
          />
        </FormField>

        <FormField
          label="Business assets value"
          htmlFor="businessAssetsValue"
          error={errors.businessAssetsValue?.message}
          hint="Equipment, vehicles, IP, goodwill"
        >
          <CurrencyInput
            id="businessAssetsValue"
            value={watch("businessAssetsValue")}
            onChange={(v) => setValue("businessAssetsValue", v ?? undefined)}
            placeholder="0"
          />
        </FormField>

        <FormField
          label="Investment portfolio"
          htmlFor="investmentPortfolio"
          error={errors.investmentPortfolio?.message}
          hint="Brokerage accounts, stocks, ETFs (non-retirement)"
        >
          <CurrencyInput
            id="investmentPortfolio"
            value={watch("investmentPortfolio")}
            onChange={(v) => setValue("investmentPortfolio", v ?? undefined)}
            placeholder="0"
          />
        </FormField>

        <FormField
          label="Retirement accounts"
          htmlFor="retirementAccounts"
          error={errors.retirementAccounts?.message}
          hint="401k, IRA, SEP-IRA, Defined Benefit total"
        >
          <CurrencyInput
            id="retirementAccounts"
            value={watch("retirementAccounts")}
            onChange={(v) => setValue("retirementAccounts", v ?? undefined)}
            placeholder="0"
          />
        </FormField>
      </div>

      {/* Estimated total */}
      {estimatedNetWorth > 0 && (
        <div className="rounded-lg bg-white/[0.03] border border-white/10 p-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">Estimated total (from above)</span>
          <span className="text-sm font-bold text-white">{formatCurrency(estimatedNetWorth)}</span>
        </div>
      )}

      <FormField
        label="Total net worth (your estimate)"
        htmlFor="totalNetWorth"
        error={errors.totalNetWorth?.message}
        hint="Include all assets minus liabilities. Leave blank to use calculated estimate above."
      >
        <CurrencyInput
          id="totalNetWorth"
          value={watch("totalNetWorth")}
          onChange={(v) => setValue("totalNetWorth", v ?? undefined)}
          placeholder={estimatedNetWorth > 0 ? String(estimatedNetWorth) : "0"}
        />
      </FormField>

      {/* Estate planning alert */}
      {nearEstateThreshold && (
        <div className="rounded-lg bg-yellow-950/30 border border-yellow-500/20 p-3">
          <p className="text-xs text-yellow-400">
            <span className="font-semibold">Estate planning strategies unlocked</span> — with net worth above
            {formatCurrency(ESTATE_THRESHOLD * 0.5)}, strategies like SLATs, GRATs, ILITs, and dynasty trusts
            can protect your wealth from estate taxes. The current exemption is {formatCurrency(ESTATE_THRESHOLD)} per person (OBBBA 2025).
          </p>
        </div>
      )}

      {/* QSBS */}
      <FormField
        label="Do you hold Qualified Small Business Stock (QSBS)?"
        htmlFor="hasQsbsStock"
        hint="C-Corp stock acquired at original issuance, held 5+ years. Potentially $15M tax-free under IRC §1202 (OBBBA 2025)."
        error={errors.hasQsbsStock?.message}
      >
        <YesNoToggle
          id="hasQsbsStock"
          value={hasQsbs ?? null}
          onChange={(v) => setValue("hasQsbsStock", v)}
        />
      </FormField>

      {hasQsbs && (
        <div className="rounded-lg bg-emerald-950/30 border border-emerald-500/20 p-3">
          <p className="text-xs text-emerald-400">
            <span className="font-semibold">QSBS analysis included</span> — the AI will analyze your IRC §1202 exclusion
            eligibility and calculate your potential tax-free gain (up to $15M per taxpayer under OBBBA 2025, or 10x
            basis, whichever is greater).
          </p>
        </div>
      )}
    </StepLayout>
  );
}
