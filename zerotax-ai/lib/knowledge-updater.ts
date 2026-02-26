// ─────────────────────────────────────────────────────────────────────────────
// ZeroTax AI — Knowledge Updater  (equivalent to update_knowledge.py)
// Fetches RSS feeds → Claude Haiku summarizes → OpenAI embeds → Supabase upsert.
// Designed to run on Vercel Cron (maxDuration=300) or locally via API route.
// ─────────────────────────────────────────────────────────────────────────────

import { createHash } from "crypto";
import Anthropic from "@anthropic-ai/sdk";
import { createAdminClient } from "@/lib/supabase/admin";
import { embed, batchEmbed } from "@/lib/tax-rag";
import { ACTIVE_SOURCES, type FeedSource } from "@/knowledge_base/sources";
import {
  SUMMARIZE_SYSTEM_PROMPT,
  SUMMARIZE_USER_PROMPT,
} from "@/knowledge_base/prompts";
import {
  FEDERAL_SEED_CHUNKS,
  type SeedChunk,
} from "@/knowledge_base/seed/federal-core";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RssItem {
  title: string;
  description: string;
  link: string;
  pubDate: string | null;
}

interface SummarizedChunk {
  title: string;
  content: string;
  source_type: string;
  jurisdiction: string;
  effective_date: string | null;
  document_number: string | null;
  irc_sections: string[];
  impact_score: number;
  needs_review: boolean;
  review_reason: string | null;
  key_changes: string[];
}

export interface RunResult {
  logId: string;
  status: "complete" | "failed" | "partial";
  sourcesAttempted: number;
  sourcesOk: number;
  chunksAdded: number;
  chunksSkipped: number;
  chunksUpdated: number;
  errors: string[];
  flaggedForReview: string[];
}

interface Counters {
  sourcesAttempted: number;
  sourcesOk: number;
  chunksAdded: number;
  chunksSkipped: number;
  chunksUpdated: number;
  errors: string[];
  flaggedForReview: string[];
  sourcesProcessed: Array<{
    id: string;
    items: number;
    added: number;
    errors: number;
  }>;
}

// ─── KnowledgeUpdater ─────────────────────────────────────────────────────────

export class KnowledgeUpdater {
  private anthropic: Anthropic;
  private logId: string | null = null;
  private counters: Counters;
  private lastClaudeMs = 0;
  private lastEmbedMs = 0;

  // Rate limits — stay within API quotas
  private readonly CLAUDE_INTERVAL_MS = 1_500; // 1.5 s between Haiku calls
  private readonly EMBED_INTERVAL_MS = 500;    // 0.5 s between embed calls

  constructor() {
    if (!process.env.ANTHROPIC_API_KEY) {
      throw new Error("ANTHROPIC_API_KEY not set");
    }
    this.anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    this.counters = this.freshCounters();
  }

  private freshCounters(): Counters {
    return {
      sourcesAttempted: 0,
      sourcesOk: 0,
      chunksAdded: 0,
      chunksSkipped: 0,
      chunksUpdated: 0,
      errors: [],
      flaggedForReview: [],
      sourcesProcessed: [],
    };
  }

  // ── Public run method ──────────────────────────────────────────────────────

  async run(triggeredBy = "scheduled"): Promise<RunResult> {
    this.counters = this.freshCounters();
    this.logId = await this.createLog(triggeredBy);
    console.log(`[knowledge-updater] Run started. log=${this.logId}`);

    // Process sources sequentially to respect rate limits
    for (const source of ACTIVE_SOURCES) {
      await this.processSource(source);
    }

    const ok = this.counters.sourcesOk;
    const total = this.counters.sourcesAttempted;
    const finalStatus: RunResult["status"] =
      ok === 0 ? "failed" : ok < total ? "partial" : "complete";

    await this.finalizeLog(finalStatus);

    return {
      logId: this.logId!,
      status: finalStatus,
      sourcesAttempted: total,
      sourcesOk: ok,
      chunksAdded: this.counters.chunksAdded,
      chunksSkipped: this.counters.chunksSkipped,
      chunksUpdated: this.counters.chunksUpdated,
      errors: this.counters.errors,
      flaggedForReview: this.counters.flaggedForReview,
    };
  }

  // ── Source processing ──────────────────────────────────────────────────────

  private async processSource(source: FeedSource): Promise<void> {
    this.counters.sourcesAttempted++;
    const sourceResult = { id: source.id, items: 0, added: 0, errors: 0 };

    try {
      const xml = await this.fetchFeed(source.url);
      const items = this.parseRssFeed(xml);
      sourceResult.items = items.length;
      console.log(`[knowledge-updater] ${source.id}: ${items.length} items`);

      for (const item of items) {
        if (!item.link) continue;
        try {
          const result = await this.processItem(item, source);
          if (result === "added") {
            sourceResult.added++;
            this.counters.chunksAdded++;
          } else if (result === "updated") {
            sourceResult.added++;
            this.counters.chunksUpdated++;
          } else {
            this.counters.chunksSkipped++;
          }
        } catch (e) {
          sourceResult.errors++;
          const msg = e instanceof Error ? e.message : String(e);
          console.error(`[knowledge-updater] item (${source.id}):`, msg);
        }
      }

      // Record source fetch timestamp
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const supabase = createAdminClient() as any;
      await supabase.from("knowledge_base_sources").upsert(
        {
          url: source.url,
          source_type: source.source_type,
          last_fetched_at: new Date().toISOString(),
          chunk_count: sourceResult.added,
        },
        { onConflict: "url" }
      );

      this.counters.sourcesOk++;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      this.counters.errors.push(`${source.id}: ${msg}`);
      console.error(`[knowledge-updater] source (${source.id}):`, msg);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const supabase = createAdminClient() as any;
      await supabase.from("knowledge_base_sources").upsert(
        {
          url: source.url,
          source_type: source.source_type,
          error_count: 1,
          last_error: msg,
        },
        { onConflict: "url" }
      );
    }

    this.counters.sourcesProcessed.push(sourceResult);
  }

  // ── Process individual RSS item ────────────────────────────────────────────

  private async processItem(
    item: RssItem,
    source: FeedSource
  ): Promise<"added" | "updated" | "skipped"> {
    // Dedup by source URL
    const isDupe = await this.checkDuplicate(item.link);
    if (isDupe) return "skipped";

    // Summarize via Claude Haiku
    const summarized = await this.summarizeItem(
      item.title,
      item.description,
      source,
      item.link
    );
    // Discard non-tax content (impact_score < 0 signals irrelevant item)
    if (!summarized || summarized.impact_score < 0) return "skipped";

    // Auto-flag if score meets source threshold
    if (summarized.impact_score >= source.impact_threshold) {
      summarized.needs_review = true;
      if (!summarized.review_reason) {
        summarized.review_reason = `Impact score ${summarized.impact_score} ≥ source threshold ${source.impact_threshold}`;
      }
    }
    if (summarized.needs_review) {
      this.counters.flaggedForReview.push(
        `${summarized.title} (score:${summarized.impact_score})`
      );
    }

    // Content-hash dedup (exact duplicate text, different URL)
    const hash = this.sha256(summarized.content);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAdminClient() as any;
    const { data: existing } = await supabase
      .from("knowledge_base")
      .select("id")
      .eq("content_hash", hash)
      .maybeSingle();
    if (existing) return "skipped";

    // Embed
    await this.rateLimit("embed");
    const embedding = await embed(summarized.content);
    this.lastEmbedMs = Date.now();

    // Insert knowledge base chunk
    const { error } = await supabase.from("knowledge_base").insert({
      title: summarized.title,
      content: summarized.content,
      content_tokens: Math.round(summarized.content.length / 4),
      source_type: summarized.source_type,
      document_number: summarized.document_number,
      jurisdiction: summarized.jurisdiction,
      effective_date: summarized.effective_date,
      url: item.link,
      embedding,
      content_hash: hash,
      impact_score: summarized.impact_score,
      needs_review: summarized.needs_review,
      ingested_at: new Date().toISOString(),
    });

    if (error) throw new Error(`DB insert: ${error.message}`);

    // Mark URL as processed in sources table
    await supabase.from("knowledge_base_sources").upsert(
      {
        url: item.link,
        source_type: source.source_type,
        document_title: summarized.title,
        document_number: summarized.document_number,
        last_fetched_at: new Date().toISOString(),
        needs_review: summarized.needs_review,
        review_reason: summarized.review_reason,
        content_fingerprint: hash,
      },
      { onConflict: "url" }
    );

    return "added";
  }

  // ── Dedup check ────────────────────────────────────────────────────────────

  private async checkDuplicate(url: string): Promise<boolean> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAdminClient() as any;
    const { data } = await supabase
      .from("knowledge_base_sources")
      .select("id")
      .eq("url", url)
      .maybeSingle();
    return !!data;
  }

  // ── Claude Haiku summarizer ────────────────────────────────────────────────

  private async summarizeItem(
    title: string,
    content: string,
    source: FeedSource,
    url: string
  ): Promise<SummarizedChunk | null> {
    const today = new Date().toISOString().split("T")[0];
    const userPrompt = SUMMARIZE_USER_PROMPT
      .replace("{TITLE}", title)
      .replace("{CONTENT}", content.slice(0, 6_000))
      .replace(/{SOURCE_TYPE}/g, source.source_type)
      .replace("{URL}", url)
      .replace("{TODAY}", today);

    await this.rateLimit("claude");

    try {
      const response = await this.anthropic.messages.create({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1024,
        system: SUMMARIZE_SYSTEM_PROMPT,
        messages: [{ role: "user", content: userPrompt }],
      });
      this.lastClaudeMs = Date.now();

      const text =
        response.content[0].type === "text" ? response.content[0].text : "";

      // Extract JSON (Claude Haiku occasionally wraps in fences)
      const clean = text.includes("{")
        ? text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1)
        : text;

      return JSON.parse(clean) as SummarizedChunk;
    } catch (e) {
      console.error("[knowledge-updater] summarize error:", e);
      return null;
    }
  }

  // ── Rate limiter ───────────────────────────────────────────────────────────

  private async rateLimit(type: "claude" | "embed"): Promise<void> {
    const now = Date.now();
    if (type === "claude") {
      const wait = this.CLAUDE_INTERVAL_MS - (now - this.lastClaudeMs);
      if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    } else {
      const wait = this.EMBED_INTERVAL_MS - (now - this.lastEmbedMs);
      if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    }
  }

  // ── RSS feed fetcher ───────────────────────────────────────────────────────

  private async fetchFeed(url: string): Promise<string> {
    const res = await fetch(url, {
      headers: {
        "User-Agent": "ZeroTax-AI/1.0 (+https://zerotax.ai)",
        Accept: "application/rss+xml, application/xml, text/xml, */*",
      },
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} from ${url}`);
    return res.text();
  }

  // ── Lightweight RSS parser (no external deps) ──────────────────────────────

  private parseRssFeed(xml: string): RssItem[] {
    const items: RssItem[] = [];
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let m: RegExpExecArray | null;
    while ((m = itemRegex.exec(xml)) !== null) {
      const block = m[1];
      items.push({
        title: this.extractTag(block, "title"),
        description: this.extractTag(block, "description"),
        link: this.extractTag(block, "link"),
        pubDate: this.extractTag(block, "pubDate") || null,
      });
    }
    return items.filter((i) => i.title && i.link);
  }

  /** Extract text from an XML tag, stripping CDATA and HTML. */
  private extractTag(block: string, tag: string): string {
    const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i");
    const m = re.exec(block);
    if (!m) return "";
    let val = m[1].trim();
    const cdata = /^<!\[CDATA\[([\s\S]*?)\]\]>/.exec(val);
    if (cdata) val = cdata[1].trim();
    // Strip remaining HTML tags
    return val.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  }

  // ── Seed data ingestion ────────────────────────────────────────────────────

  /**
   * Ingests FEDERAL_SEED_CHUNKS on first run.
   * Uses batchEmbed for efficiency; skips existing chunks by content_hash.
   */
  async ingestSeedData(): Promise<{ added: number; skipped: number }> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAdminClient() as any;
    let added = 0;
    let skipped = 0;

    const hashes = FEDERAL_SEED_CHUNKS.map((c) => this.sha256(c.content));

    // Check which hashes already exist in DB
    const { data: existing } = await supabase
      .from("knowledge_base")
      .select("content_hash")
      .in("content_hash", hashes);

    const existingSet = new Set<string>(
      (existing ?? []).map((r: { content_hash: string }) => r.content_hash)
    );

    const toEmbed: SeedChunk[] = [];
    const toEmbedHashes: string[] = [];
    const toEmbedTexts: string[] = [];

    FEDERAL_SEED_CHUNKS.forEach((chunk, i) => {
      if (existingSet.has(hashes[i])) {
        skipped++;
      } else {
        toEmbed.push(chunk);
        toEmbedHashes.push(hashes[i]);
        toEmbedTexts.push(chunk.content);
      }
    });

    if (toEmbed.length === 0) {
      console.log("[knowledge-updater] seed: all chunks already present");
      return { added: 0, skipped };
    }

    // Batch embed all new seed chunks
    const embeddings = await batchEmbed(toEmbedTexts);

    for (let i = 0; i < toEmbed.length; i++) {
      const chunk = toEmbed[i];
      const { error } = await supabase.from("knowledge_base").insert({
        title: chunk.title,
        content: chunk.content,
        content_tokens: Math.round(chunk.content.length / 4),
        source_type: chunk.source_type,
        document_title: chunk.document_title,
        document_number: chunk.document_number,
        jurisdiction: chunk.jurisdiction ?? "federal",
        effective_date: chunk.effective_date,
        url: chunk.url,
        embedding: embeddings[i],
        content_hash: toEmbedHashes[i],
        impact_score: chunk.impact_score,
        needs_review: false,
        ingested_at: new Date().toISOString(),
      });
      if (!error) {
        added++;
      } else {
        console.error("[knowledge-updater] seed insert error:", error.message);
      }
    }

    console.log(`[knowledge-updater] seed: added=${added} skipped=${skipped}`);
    return { added, skipped };
  }

  // ── Run log helpers ────────────────────────────────────────────────────────

  private async createLog(triggeredBy: string): Promise<string> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAdminClient() as any;
    const { data } = await supabase
      .from("knowledge_update_log")
      .insert({
        run_type: "scheduled",
        triggered_by: triggeredBy,
        status: "running",
        started_at: new Date().toISOString(),
      })
      .select("id")
      .single();
    return (data?.id as string) ?? "unknown";
  }

  private async finalizeLog(status: string): Promise<void> {
    if (!this.logId || this.logId === "unknown") return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAdminClient() as any;
    await supabase
      .from("knowledge_update_log")
      .update({
        status,
        completed_at: new Date().toISOString(),
        sources_attempted: this.counters.sourcesAttempted,
        sources_ok: this.counters.sourcesOk,
        chunks_added: this.counters.chunksAdded,
        chunks_skipped: this.counters.chunksSkipped,
        chunks_updated: this.counters.chunksUpdated,
        sources_processed: this.counters.sourcesProcessed,
        errors: this.counters.errors,
        flagged_for_review: this.counters.flaggedForReview,
      })
      .eq("id", this.logId);
  }

  // ── Utility ────────────────────────────────────────────────────────────────

  private sha256(text: string): string {
    return createHash("sha256").update(text, "utf8").digest("hex");
  }
}
