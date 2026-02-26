-- ============================================================
-- ZeroTax AI — Knowledge Base Update Infrastructure
-- Migration 004: Adds versioning, dedup, review flags, and
-- update audit log to the existing knowledge_base tables.
-- ============================================================

-- ── Add versioning + dedup columns to knowledge_base ─────────────────────────
alter table public.knowledge_base
  add column if not exists content_hash   text,
  add column if not exists impact_score   integer not null default 0,
  add column if not exists needs_review   boolean not null default false,
  add column if not exists chunk_version  integer not null default 1;

comment on column public.knowledge_base.content_hash   is 'SHA-256 of content for duplicate detection';
comment on column public.knowledge_base.impact_score   is '0–10 score; ≥7 triggers human review flag';
comment on column public.knowledge_base.needs_review   is 'True if content should be reviewed by a human before surfacing';
comment on column public.knowledge_base.chunk_version  is 'Monotonically increases when content is updated; old versions kept for audit';

-- Index for fast dedup lookups
create index if not exists kb_content_hash_idx
  on public.knowledge_base(content_hash)
  where content_hash is not null;

-- ── Add review + fingerprint columns to knowledge_base_sources ───────────────
alter table public.knowledge_base_sources
  add column if not exists needs_review         boolean not null default false,
  add column if not exists review_reason        text,
  add column if not exists content_fingerprint  text,
  add column if not exists error_count          integer not null default 0,
  add column if not exists last_error           text;

-- ── Knowledge update run log ──────────────────────────────────────────────────
create table if not exists public.knowledge_update_log (
  id              uuid primary key default uuid_generate_v4(),
  run_type        text not null default 'scheduled'
                    check (run_type in ('scheduled', 'manual', 'seed', 'retry')),
  triggered_by    text,
  started_at      timestamptz not null default now(),
  completed_at    timestamptz,
  duration_ms     integer,

  -- Counters
  sources_attempted  integer not null default 0,
  sources_ok         integer not null default 0,
  chunks_fetched     integer not null default 0,
  chunks_added       integer not null default 0,
  chunks_skipped     integer not null default 0,
  chunks_updated     integer not null default 0,

  -- Detail arrays (stored as JSONB)
  sources_processed  jsonb not null default '[]',
  errors             jsonb not null default '[]',
  flagged_for_review jsonb not null default '[]',

  status  text not null default 'running'
            check (status in ('running', 'complete', 'failed', 'partial')),
  created_at  timestamptz not null default now()
);

create index if not exists kul_started_at_idx on public.knowledge_update_log(started_at desc);

comment on table public.knowledge_update_log is
  'Audit trail for every knowledge base update run (scheduled or manual).';

-- RLS: service role only (no direct user access)
alter table public.knowledge_update_log enable row level security;

create policy "service_role_only_update_log"
  on public.knowledge_update_log for all
  using (false)
  with check (false);

-- ── Replace match_knowledge_base RPC to include effective_date ───────────────
-- (Drop old, recreate with the new return column)
drop function if exists match_knowledge_base(vector(1536), float, int, text);

create or replace function match_knowledge_base(
  query_embedding   vector(1536),
  match_threshold   float,
  match_count       int,
  filter_jurisdiction text default null
)
returns table (
  id              uuid,
  title           text,
  content         text,
  source_type     text,
  document_title  text,
  document_number text,
  jurisdiction    text,
  url             text,
  effective_date  date,
  impact_score    integer,
  similarity      float
)
language sql stable
as $$
  select
    kb.id,
    kb.title,
    kb.content,
    kb.source_type,
    kb.document_title,
    kb.document_number,
    kb.jurisdiction,
    kb.url,
    kb.effective_date,
    kb.impact_score,
    1 - (kb.embedding <=> query_embedding) as similarity
  from public.knowledge_base kb
  where
    kb.embedding is not null
    and kb.needs_review = false
    and (kb.expires_at is null or kb.expires_at > now())
    and (
      filter_jurisdiction is null
      or kb.jurisdiction = filter_jurisdiction
      or kb.jurisdiction = 'federal'
    )
    and 1 - (kb.embedding <=> query_embedding) > match_threshold
  order by kb.embedding <=> query_embedding
  limit match_count;
$$;
