create table if not exists public.papers (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('upload', 'arxiv')),
  arxiv_id text null,
  title text not null,
  authors jsonb not null default '[]'::jsonb,
  categories text[] not null default '{}'::text[],
  abstract_raw text null,
  abstract_translated text null,
  visibility text not null default 'public' check (visibility in ('public', 'hidden')),
  status text not null default 'draft' check (status in ('draft', 'published', 'removed')),
  trans_status text not null default 'not_started' check (trans_status in ('not_started', 'queued', 'processing', 'completed', 'failed')),
  created_by uuid null references auth.users (id),
  trans_latest_task_id text null,
  trans_latest_asset_pdf_id uuid null,
  like_count integer not null default 0 check (like_count >= 0),
  favorite_count integer not null default 0 check (favorite_count >= 0),
  comment_count integer not null default 0 check (comment_count >= 0),
  view_count integer not null default 0 check (view_count >= 0),
  download_count integer not null default 0 check (download_count >= 0),
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create unique index if not exists papers_arxiv_id_unique_idx
  on public.papers (arxiv_id)
  where arxiv_id is not null;

create index if not exists papers_created_at_desc_idx
  on public.papers (created_at desc);

create index if not exists papers_visibility_status_created_at_idx
  on public.papers (visibility, status, created_at desc);

create index if not exists papers_trans_status_created_at_idx
  on public.papers (trans_status, created_at desc);

create index if not exists papers_created_by_idx
  on public.papers (created_by);

create table if not exists public.paper_assets (
  id uuid primary key default gen_random_uuid(),
  paper_id uuid not null references public.papers (id) on delete cascade,
  task_id text null,
  asset_type text not null check (asset_type in ('source_archive', 'translated_pdf', 'preview_pdf', 'preview_html')),
  storage_backend text not null check (storage_backend in ('local_disk', 'object_storage')),
  file_path text not null,
  file_name text not null,
  mime_type text not null,
  is_latest boolean not null default false,
  created_at timestamp with time zone not null default now()
);

create index if not exists paper_assets_paper_id_idx
  on public.paper_assets (paper_id);

create index if not exists paper_assets_paper_latest_idx
  on public.paper_assets (paper_id, is_latest);

alter table public.papers enable row level security;
alter table public.paper_assets enable row level security;

drop policy if exists papers_public_read on public.papers;
create policy papers_public_read
  on public.papers
  for select
  to anon, authenticated
  using (
    visibility = 'public'
    and status <> 'removed'
  );
