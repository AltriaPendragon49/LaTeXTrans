create table if not exists public.paper_likes (
  paper_id uuid not null references public.papers (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamp with time zone not null default now(),
  primary key (paper_id, user_id)
);

create index if not exists paper_likes_user_id_idx
  on public.paper_likes (user_id);

create table if not exists public.paper_favorites (
  paper_id uuid not null references public.papers (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamp with time zone not null default now(),
  primary key (paper_id, user_id)
);

create index if not exists paper_favorites_user_id_idx
  on public.paper_favorites (user_id);

create table if not exists public.comments (
  id uuid primary key default gen_random_uuid(),
  paper_id uuid not null references public.papers (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  parent_id uuid null references public.comments (id) on delete cascade,
  content text not null,
  status text not null default 'visible' check (status in ('visible', 'hidden', 'deleted')),
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create index if not exists comments_paper_created_at_idx
  on public.comments (paper_id, created_at asc);

create index if not exists comments_user_id_idx
  on public.comments (user_id);

alter table public.paper_likes enable row level security;
alter table public.paper_favorites enable row level security;
alter table public.comments enable row level security;

drop policy if exists paper_likes_select_own on public.paper_likes;
create policy paper_likes_select_own
  on public.paper_likes
  for select
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists paper_likes_insert_own on public.paper_likes;
create policy paper_likes_insert_own
  on public.paper_likes
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists paper_likes_delete_own on public.paper_likes;
create policy paper_likes_delete_own
  on public.paper_likes
  for delete
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists paper_favorites_select_own on public.paper_favorites;
create policy paper_favorites_select_own
  on public.paper_favorites
  for select
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists paper_favorites_insert_own on public.paper_favorites;
create policy paper_favorites_insert_own
  on public.paper_favorites
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists paper_favorites_delete_own on public.paper_favorites;
create policy paper_favorites_delete_own
  on public.paper_favorites
  for delete
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists comments_public_read on public.comments;
create policy comments_public_read
  on public.comments
  for select
  to anon, authenticated
  using (
    status = 'visible'
    and exists (
      select 1
      from public.papers
      where public.papers.id = comments.paper_id
        and public.papers.visibility = 'public'
        and public.papers.status <> 'removed'
    )
  );

drop policy if exists comments_insert_own on public.comments;
create policy comments_insert_own
  on public.comments
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists comments_update_own on public.comments;
create policy comments_update_own
  on public.comments
  for update
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  )
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists comments_delete_own on public.comments;
create policy comments_delete_own
  on public.comments
  for delete
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );
