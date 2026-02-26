// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Knowledge Update API Route
// GET  → called by Vercel Cron every 24 h (requires Authorization: Bearer CRON_SECRET)
// POST → manual trigger or seed ingest (same auth check)
// ─────────────────────────────────────────────────────────────────────────────

import { NextResponse, type NextRequest } from "next/server";
import { KnowledgeUpdater } from "@/lib/knowledge-updater";

// Allow Vercel Cron to run for up to 5 minutes
export const maxDuration = 300;

function authorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false;
  return req.headers.get("authorization") === `Bearer ${secret}`;
}

/** Vercel Cron trigger */
export async function GET(req: NextRequest) {
  if (!authorized(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    const updater = new KnowledgeUpdater();
    const result = await updater.run("cron");
    return NextResponse.json(result);
  } catch (err) {
    console.error("[knowledge/update GET]", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}

/** Manual trigger (admin / development) */
export async function POST(req: NextRequest) {
  if (!authorized(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    const body = (await req.json().catch(() => ({}))) as {
      action?: string;
      triggeredBy?: string;
    };
    const updater = new KnowledgeUpdater();

    if (body.action === "seed") {
      const result = await updater.ingestSeedData();
      return NextResponse.json({ ok: true, ...result });
    }

    const result = await updater.run(body.triggeredBy ?? "manual");
    return NextResponse.json(result);
  } catch (err) {
    console.error("[knowledge/update POST]", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
