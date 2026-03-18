create or replace function public.increment_paper_view_count(target_paper_id uuid)
returns table (view_count integer)
language plpgsql
security definer
set search_path = ''
as $$
begin
  return query
  update public.papers
  set view_count = public.papers.view_count + 1,
      updated_at = now()
  where public.papers.id = target_paper_id
    and public.papers.visibility = 'public'
    and public.papers.status <> 'removed'
  returning public.papers.view_count;
end;
$$;

revoke all on function public.increment_paper_view_count(uuid) from public;
grant execute on function public.increment_paper_view_count(uuid) to anon;
grant execute on function public.increment_paper_view_count(uuid) to authenticated;
grant execute on function public.increment_paper_view_count(uuid) to service_role;
