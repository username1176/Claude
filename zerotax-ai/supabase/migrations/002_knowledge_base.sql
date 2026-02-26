-- ============================================================
-- Knowledge Base (RAG) — requires pgvector extension
-- ============================================================

-- Sources table (dedup tracking)
create table public.knowledge_base_sources (
  id              uuid primary key default uuid_generate_v4(),
  url             text unique not null,
  source_type     text not null,
  document_title  text,
  document_number text,
  last_fetched_at timestamptz,
  last_modified   text,
  chunk_count     integer default 0,
  is_active       boolean default true,
  created_at      timestamptz not null default now()
);

-- Knowledge base chunks with embeddings
create table public.knowledge_base (
  id              uuid primary key default uuid_generate_v4(),
  source_id       uuid references public.knowledge_base_sources(id) on delete set null,

  title           text not null,
  content         text not null,
  content_tokens  integer,

  source_type     text not null check (source_type in (
    'irs_publication', 'irc_section', 'obbba', 'revenue_ruling',
    'tax_court', 'state_bulletin', 'treasury_reg', 'cca', 'plr'
  )),
  document_title  text,
  document_number text,
  jurisdiction    text,
  effective_date  date,
  url             text,

  -- 1536 dims for OpenAI text-embedding-3-small
  embedding       vector(1536),

  ingested_at     timestamptz not null default now(),
  expires_at      timestamptz,
  created_at      timestamptz not null default now()
);

-- Indexes
create index on public.knowledge_base(source_type);
create index on public.knowledge_base(jurisdiction);

-- IVFFlat index for fast approximate nearest neighbor search
-- Tune lists = sqrt(expected_rows). Start with 100 for ~10K rows.
create index on public.knowledge_base
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- ============================================================
-- RPC function for similarity search
-- ============================================================
create or replace function match_knowledge_base(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_jurisdiction text default null
)
returns table (
  id uuid,
  title text,
  content text,
  source_type text,
  document_title text,
  document_number text,
  jurisdiction text,
  url text,
  similarity float
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
    1 - (kb.embedding <=> query_embedding) as similarity
  from public.knowledge_base kb
  where
    (filter_jurisdiction is null or kb.jurisdiction = filter_jurisdiction or kb.jurisdiction = 'federal')
    and 1 - (kb.embedding <=> query_embedding) > match_threshold
  order by kb.embedding <=> query_embedding
  limit match_count;
$$;
