import { AlertTriangle } from "lucide-react";

export function DisclaimerBanner() {
  return (
    <div className="bg-yellow-950/40 border-b border-yellow-500/20 px-4 py-2">
      <div className="max-w-7xl mx-auto flex items-center gap-2 text-xs text-yellow-400/80">
        <AlertTriangle className="h-3 w-3 shrink-0" />
        <span>
          <strong>Not legal or tax advice.</strong> ZeroTax AI provides educational information only.
          Always consult a licensed CPA, tax attorney, or enrolled agent before implementing any strategy.
        </span>
      </div>
    </div>
  );
}
