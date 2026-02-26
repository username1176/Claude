import Link from "next/link";
import { ArrowRight, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function QuestionnairePage() {
  return (
    <div className="max-w-2xl mx-auto">
      <Card glass className="text-center">
        <CardContent className="py-16 space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-emerald-900/50 border border-emerald-500/30 flex items-center justify-center mx-auto">
            <ClipboardList className="h-8 w-8 text-emerald-400" />
          </div>
          <h1 className="text-3xl font-bold text-white">Tax Questionnaire</h1>
          <p className="text-slate-400 text-lg">
            Coming in Prompt 2 — Multi-step questionnaire with 7 steps, Zustand store,
            and full validation.
          </p>
          <Button variant="gradient" asChild>
            <Link href="/dashboard">
              Back to Dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
