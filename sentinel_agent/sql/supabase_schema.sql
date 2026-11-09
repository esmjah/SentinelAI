-- SentinelAI document index on Supabase (Postgres + pgvector).
-- Run once in the Supabase SQL editor. Embedding dimension 1536 = text-embedding-3-small.

create extension if not exists vector;

create table if not exists doc_chunks (
  chunk_id          text primary key,              -- DOC.<doc_id>.<revision>.<nn>, citable by the agent
  doc_id            text not null,
  revision          text not null,
  status            text not null check (status in ('active', 'superseded', 'withdrawn')),
  effective_from    date not null,
  superseded_by     text,
  doc_type          text not null,
  title             text not null,
  section           text,
  chunk_index       int  not null,
  content           text not null,                 -- context header + chunk body
  content_hash      text not null,
  token_count       int,
  classification    text not null default 'internal',
  trust             text not null default 'controlled',   -- controlled | semi-trusted | untrusted
  source            text,
  asserts           jsonb default '[]'::jsonb,      -- [{graph_id, value, unit}] values the text states
  numbers           jsonb default '[]'::jsonb,      -- numbers in the text, for the grounding gate
  injection_suspect boolean not null default false,
  injection_reasons jsonb default '[]'::jsonb,
  embedding         vector(1536) not null,
  fts               tsvector generated always as (to_tsvector('english', content)) stored,
  ingested_at       timestamptz not null default now()
);

create index if not exists doc_chunks_embedding_hnsw on doc_chunks using hnsw (embedding vector_cosine_ops);
create index if not exists doc_chunks_fts on doc_chunks using gin (fts);
create index if not exists doc_chunks_doc on doc_chunks (doc_id, revision);

create table if not exists index_manifest (
  id            bigserial primary key,
  index_version text not null,
  manifest      jsonb not null,
  created_at    timestamptz not null default now()
);

-- Restricted documents: no anonymous access. The agent uses the service key on the server side only.
alter table doc_chunks enable row level security;
alter table index_manifest enable row level security;
-- (No policies for anon/authenticated = no access. The service role bypasses RLS.)

-- Hybrid search: vector + full-text, fused with Reciprocal Rank Fusion; active revisions by default.
create or replace function hybrid_search(
  query_embedding    vector(1536),
  query_text         text,
  match_count        int     default 5,
  candidate_count    int     default 20,
  include_superseded boolean default false,
  as_of              date    default null,
  rrf_k              int     default 60
)
returns table (
  chunk_id text, doc_id text, revision text, status text, effective_from date, superseded_by text,
  doc_type text, title text, section text, chunk_index int, content text, content_hash text,
  classification text, trust text, source text, asserts jsonb, numbers jsonb,
  injection_suspect boolean, injection_reasons jsonb, score double precision,
  vector_rank bigint, keyword_rank bigint
)
language sql stable
as $$
  with eligible as (
    select * from doc_chunks d
    where (include_superseded or d.status = 'active')
      and (as_of is null or d.effective_from <= as_of)
  ),
  v as (
    select e.chunk_id, row_number() over (order by e.embedding <=> query_embedding) as r
    from eligible e order by e.embedding <=> query_embedding limit candidate_count
  ),
  k as (
    select e.chunk_id,
           row_number() over (order by ts_rank_cd(e.fts, websearch_to_tsquery('english', query_text)) desc) as r
    from eligible e
    where e.fts @@ websearch_to_tsquery('english', query_text)
    limit candidate_count
  ),
  fused as (
    select coalesce(v.chunk_id, k.chunk_id) as chunk_id,
           coalesce(1.0 / (rrf_k + v.r), 0) + coalesce(1.0 / (rrf_k + k.r), 0) as score,
           v.r as vector_rank, k.r as keyword_rank
    from v full outer join k on v.chunk_id = k.chunk_id
  )
  select d.chunk_id, d.doc_id, d.revision, d.status, d.effective_from, d.superseded_by, d.doc_type,
         d.title, d.section, d.chunk_index, d.content, d.content_hash, d.classification, d.trust,
         d.source, d.asserts, d.numbers, d.injection_suspect, d.injection_reasons,
         f.score, f.vector_rank, f.keyword_rank
  from fused f join doc_chunks d using (chunk_id)
  order by f.score desc
  limit match_count;
$$;
