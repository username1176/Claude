import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function ReportsPage() {
  return (
    <div className="max-w-2xl mx-auto">
      <Card glass className="text-center">
        <CardContent className="py-16 space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-blue-900/50 border border-blue-500/30 flex items-center justify-center mx-auto">
            <FileText className="h-8 w-8 text-blue-400" />
          </div>
          <h1 className="text-3xl font-bold text-white">PDF Reports</h1>
          <p className="text-slate-400 text-lg">
            Coming in Prompt 7 — Generate professional PDF tax plans with your strategies,
            IRC citations, and savings breakdown.
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
