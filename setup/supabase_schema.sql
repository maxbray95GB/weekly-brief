-- Weekly Brief Bot — Supabase Schema
-- Run this in your Supabase project's SQL editor (https://app.supabase.com → SQL Editor)
-- This sets up the table for storing weekly memory records.

-- Enable the pgvector extension for future semantic search
-- (may already be enabled — if you get an error, skip this line)
create extension if not exists vector;

-- Main memory table
create table if not exists weekly_memories (
  id           bigserial primary key,
  type         text not null,        -- 'person_interaction', 'learning', 'meeting', 'commitment'
  content      text not null,        -- The text content (searchable)
  metadata     jsonb default '{}',   -- Structured data (week, names, etc.)
  embedding    vector(1536),         -- For future semantic search (optional for now)
  created_at   timestamptz default now()
);

-- Index for fast text search
create index if not exists weekly_memories_content_idx 
  on weekly_memories using gin(to_tsvector('english', content));

-- Index for filtering by type
create index if not exists weekly_memories_type_idx 
  on weekly_memories (type);

-- Index for filtering by week (stored in metadata)
create index if not exists weekly_memories_week_idx 
  on weekly_memories ((metadata->>'week'));

-- Index for future vector similarity search
-- Uncomment when you have embeddings:
-- create index if not exists weekly_memories_embedding_idx 
--   on weekly_memories using ivfflat (embedding vector_cosine_ops);

-- Allow the anon key to read and write (needed for the bot)
alter table weekly_memories enable row level security;

create policy "Allow all operations for service role"
  on weekly_memories
  for all
  using (true)
  with check (true);

-- Helpful view: people you've interacted with most
create or replace view top_contacts as
  select
    metadata->>'name' as name,
    metadata->>'email' as email,
    metadata->>'company' as company,
    sum((metadata->>'interaction_count')::int) as total_interactions,
    max(metadata->>'week') as last_seen,
    min(metadata->>'week') as first_seen
  from weekly_memories
  where type = 'person_interaction'
    and metadata->>'email' != ''
  group by 
    metadata->>'name',
    metadata->>'email', 
    metadata->>'company'
  order by total_interactions desc;

-- Helpful view: open commitments
create or replace view open_commitments as
  select
    content,
    metadata->>'person' as person,
    metadata->>'direction' as direction,
    metadata->>'week' as week_created
  from weekly_memories
  where type = 'commitment'
    and metadata->>'status' = 'open'
  order by created_at desc;

