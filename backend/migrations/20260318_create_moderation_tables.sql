create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  target_type text not null check (target_type in ('paper', 'comment')),
  target_id uuid not null,
  reason_code text not null,
  reason_text text null,
  reported_by uuid not null references auth.users (id) on delete cascade,
  status text not null default 'open' check (status in ('open', 'resolved', 'dismissed')),
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create index if not exists reports_status_created_at_idx
  on public.reports (status, created_at desc);

create index if not exists reports_reported_by_idx
  on public.reports (reported_by);

create table if not exists public.moderation_actions (
  id uuid primary key default gen_random_uuid(),
  report_id uuid null references public.reports (id) on delete set null,
  target_type text not null check (target_type in ('paper', 'comment', 'user')),
  target_id uuid not null,
  action_type text not null check (action_type in ('hide', 'unhide', 'ban_user', 'dismiss_report', 'resolve_report')),
  action_note text null,
  acted_by uuid not null references auth.users (id),
  created_at timestamp with time zone not null default now()
);

create index if not exists moderation_actions_report_id_idx
  on public.moderation_actions (report_id);

create index if not exists moderation_actions_acted_by_idx
  on public.moderation_actions (acted_by);

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  type text not null,
  title text not null,
  body text not null,
  payload jsonb not null default '{}'::jsonb,
  read_at timestamp with time zone null,
  created_at timestamp with time zone not null default now()
);

create index if not exists notifications_user_created_at_idx
  on public.notifications (user_id, created_at desc);

create table if not exists public.user_roles (
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('admin', 'moderator')),
  granted_by uuid null references auth.users (id),
  created_at timestamp with time zone not null default now(),
  primary key (user_id, role)
);

create index if not exists user_roles_granted_by_idx
  on public.user_roles (granted_by);

create table if not exists public.user_bans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  ban_reason text not null,
  expires_at timestamp with time zone null,
  created_by uuid not null references auth.users (id),
  created_at timestamp with time zone not null default now()
);

create index if not exists user_bans_user_id_idx
  on public.user_bans (user_id);

create or replace function public.current_user_is_admin()
returns boolean
language sql
security definer
stable
set search_path = ''
as $$
  select exists (
    select 1
    from public.user_roles
    where user_id = (select auth.uid())
      and role = any (array['admin', 'moderator'])
  );
$$;

revoke all on function public.current_user_is_admin() from public;
grant execute on function public.current_user_is_admin() to authenticated;

create or replace function public.current_user_is_banned()
returns boolean
language sql
security definer
stable
set search_path = ''
as $$
  select exists (
    select 1
    from public.user_bans
    where user_id = (select auth.uid())
      and (expires_at is null or expires_at > now())
  );
$$;

revoke all on function public.current_user_is_banned() from public;
grant execute on function public.current_user_is_banned() to authenticated;

alter table public.reports enable row level security;
alter table public.moderation_actions enable row level security;
alter table public.notifications enable row level security;
alter table public.user_roles enable row level security;
alter table public.user_bans enable row level security;

drop policy if exists reports_select_own on public.reports;
create policy reports_select_own
  on public.reports
  for select
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = reported_by
  );

drop policy if exists reports_insert_own on public.reports;
create policy reports_insert_own
  on public.reports
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = reported_by
    and not (select public.current_user_is_banned())
  );

drop policy if exists reports_admin_select_all on public.reports;
create policy reports_admin_select_all
  on public.reports
  for select
  to authenticated
  using ((select public.current_user_is_admin()));

drop policy if exists reports_admin_update_all on public.reports;
create policy reports_admin_update_all
  on public.reports
  for update
  to authenticated
  using ((select public.current_user_is_admin()))
  with check ((select public.current_user_is_admin()));

drop policy if exists moderation_actions_admin_all on public.moderation_actions;
create policy moderation_actions_admin_all
  on public.moderation_actions
  for all
  to authenticated
  using ((select public.current_user_is_admin()))
  with check ((select public.current_user_is_admin()));

drop policy if exists notifications_select_own on public.notifications;
create policy notifications_select_own
  on public.notifications
  for select
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists notifications_update_read_at_own on public.notifications;
create policy notifications_update_read_at_own
  on public.notifications
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

drop policy if exists user_roles_select_own on public.user_roles;
create policy user_roles_select_own
  on public.user_roles
  for select
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists user_roles_admin_manage_all on public.user_roles;
create policy user_roles_admin_manage_all
  on public.user_roles
  for all
  to authenticated
  using ((select public.current_user_is_admin()))
  with check ((select public.current_user_is_admin()));

drop policy if exists user_bans_admin_manage_all on public.user_bans;
create policy user_bans_admin_manage_all
  on public.user_bans
  for all
  to authenticated
  using ((select public.current_user_is_admin()))
  with check ((select public.current_user_is_admin()));

drop policy if exists papers_admin_read_all on public.papers;
create policy papers_admin_read_all
  on public.papers
  for select
  to authenticated
  using ((select public.current_user_is_admin()));

drop policy if exists papers_admin_update_all on public.papers;
create policy papers_admin_update_all
  on public.papers
  for update
  to authenticated
  using ((select public.current_user_is_admin()))
  with check ((select public.current_user_is_admin()));

drop policy if exists comments_admin_read_all on public.comments;
create policy comments_admin_read_all
  on public.comments
  for select
  to authenticated
  using ((select public.current_user_is_admin()));

drop policy if exists comments_admin_update_all on public.comments;
create policy comments_admin_update_all
  on public.comments
  for update
  to authenticated
  using ((select public.current_user_is_admin()))
  with check ((select public.current_user_is_admin()));

drop policy if exists comments_insert_own on public.comments;
create policy comments_insert_own
  on public.comments
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
    and not (select public.current_user_is_banned())
  );

drop policy if exists paper_likes_insert_own on public.paper_likes;
create policy paper_likes_insert_own
  on public.paper_likes
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
    and not (select public.current_user_is_banned())
  );

drop policy if exists paper_favorites_insert_own on public.paper_favorites;
create policy paper_favorites_insert_own
  on public.paper_favorites
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
    and not (select public.current_user_is_banned())
  );
