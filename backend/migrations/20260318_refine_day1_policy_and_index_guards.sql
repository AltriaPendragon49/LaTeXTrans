create index if not exists comments_parent_id_idx
  on public.comments (parent_id)
  where parent_id is not null;

create index if not exists user_bans_created_by_idx
  on public.user_bans (created_by);

drop policy if exists papers_public_read on public.papers;
drop policy if exists papers_admin_read_all on public.papers;

create policy papers_public_read_anon
  on public.papers
  for select
  to anon
  using (
    visibility = 'public'
    and status <> 'removed'
  );

create policy papers_select_authenticated
  on public.papers
  for select
  to authenticated
  using (
    (
      visibility = 'public'
      and status <> 'removed'
    )
    or (select public.current_user_is_admin())
  );

drop policy if exists comments_public_read on public.comments;
drop policy if exists comments_admin_read_all on public.comments;

create policy comments_public_read_anon
  on public.comments
  for select
  to anon
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

create policy comments_select_authenticated
  on public.comments
  for select
  to authenticated
  using (
    (
      status = 'visible'
      and exists (
        select 1
        from public.papers
        where public.papers.id = comments.paper_id
          and public.papers.visibility = 'public'
          and public.papers.status <> 'removed'
      )
    )
    or (select public.current_user_is_admin())
  );

drop policy if exists comments_update_own on public.comments;
drop policy if exists comments_admin_update_all on public.comments;

create policy comments_update_authenticated
  on public.comments
  for update
  to authenticated
  using (
    (
      (select auth.uid()) is not null
      and (select auth.uid()) = user_id
    )
    or (select public.current_user_is_admin())
  )
  with check (
    (
      (select auth.uid()) is not null
      and (select auth.uid()) = user_id
    )
    or (select public.current_user_is_admin())
  );

drop policy if exists reports_select_own on public.reports;
drop policy if exists reports_admin_select_all on public.reports;

create policy reports_select_authenticated
  on public.reports
  for select
  to authenticated
  using (
    (
      (select auth.uid()) is not null
      and (select auth.uid()) = reported_by
    )
    or (select public.current_user_is_admin())
  );

drop policy if exists user_roles_select_own on public.user_roles;
drop policy if exists user_roles_admin_manage_all on public.user_roles;

create policy user_roles_select_authenticated
  on public.user_roles
  for select
  to authenticated
  using (
    (
      (select auth.uid()) is not null
      and (select auth.uid()) = user_id
    )
    or (select public.current_user_is_admin())
  );

create policy user_roles_admin_insert_all
  on public.user_roles
  for insert
  to authenticated
  with check ((select public.current_user_is_admin()));

create policy user_roles_admin_update_all
  on public.user_roles
  for update
  to authenticated
  using ((select public.current_user_is_admin()))
  with check ((select public.current_user_is_admin()));

create policy user_roles_admin_delete_all
  on public.user_roles
  for delete
  to authenticated
  using ((select public.current_user_is_admin()));

drop policy if exists paper_assets_admin_read_all on public.paper_assets;
create policy paper_assets_admin_read_all
  on public.paper_assets
  for select
  to authenticated
  using ((select public.current_user_is_admin()));
