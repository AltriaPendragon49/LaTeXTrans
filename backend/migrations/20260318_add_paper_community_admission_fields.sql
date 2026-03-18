alter table public.papers
add column if not exists community_status text not null default 'user_fallback'
  check (community_status in ('official', 'user_fallback'));

alter table public.papers
add column if not exists community_selected_task_id text;

alter table public.papers
add column if not exists community_selected_asset_id uuid;

alter table public.papers
add column if not exists official_published_at timestamp with time zone;

create index if not exists papers_community_status_created_at_idx
  on public.papers (community_status, created_at desc);

create index if not exists papers_official_published_at_idx
  on public.papers (official_published_at desc)
  where official_published_at is not null;
