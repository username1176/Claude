import { NextResponse, type NextRequest } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function POST(req: NextRequest) {
  try {
    const { recommendationId } = (await req.json()) as { recommendationId?: string };
    if (!recommendationId) return NextResponse.json({ error: "recommendationId required" }, { status: 400 });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAdminClient() as any;
    await supabase.from("recommendations").update({ status: "draft" }).eq("id", recommendationId);

    return NextResponse.json({ ok: true, recommendationId });
  } catch (err) {
    console.error("[ai/recommend]", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
