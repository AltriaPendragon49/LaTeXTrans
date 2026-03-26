create table if not exists public.community_content_pool_candidates (
  id uuid primary key default gen_random_uuid(),
  arxiv_id text not null,
  source text not null default 'unknown',
  status text not null default 'discovered'
    check (status in ('discovered', 'running', 'translated_ready', 'failed')),
  score numeric null,
  metadata jsonb not null default '{}'::jsonb,
  paper_id uuid null references public.papers (id) on delete set null,
  last_error text null,
  last_stage text not null default 'discover',
  freshness timestamp with time zone null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create unique index if not exists community_content_pool_candidates_arxiv_id_idx
  on public.community_content_pool_candidates (arxiv_id);

create index if not exists community_content_pool_candidates_status_idx
  on public.community_content_pool_candidates (status, updated_at desc);

create table if not exists public.community_content_pool_jobs (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.community_content_pool_candidates (id) on delete cascade,
  paper_id uuid null references public.papers (id) on delete set null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'failed')),
  current_stage text not null default 'discover',
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 1 check (max_attempts >= 1),
  translated_ready boolean not null default false,
  started_at timestamp with time zone null,
  finished_at timestamp with time zone null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create index if not exists community_content_pool_jobs_status_idx
  on public.community_content_pool_jobs (status, updated_at desc);

create index if not exists community_content_pool_jobs_candidate_id_idx
  on public.community_content_pool_jobs (candidate_id, created_at desc);

create table if not exists public.community_content_pool_job_events (
  id bigserial primary key,
  job_id uuid not null references public.community_content_pool_jobs (id) on delete cascade,
  candidate_id uuid not null references public.community_content_pool_candidates (id) on delete cascade,
  stage text not null,
  status text not null,
  attempt integer not null default 0 check (attempt >= 0),
  error text null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamp with time zone not null default now()
);

create index if not exists community_content_pool_job_events_job_id_idx
  on public.community_content_pool_job_events (job_id, created_at desc);

create index if not exists community_content_pool_job_events_candidate_id_idx
  on public.community_content_pool_job_events (candidate_id, created_at desc);
