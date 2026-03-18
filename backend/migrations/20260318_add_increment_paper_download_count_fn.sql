create or replace function public.increment_paper_download_count(target_paper_id uuid)
returns table (download_count integer)
language plpgsql
security definer
set search_path = ''
as $$
begin
  return query
  update public.papers
  set download_count = public.papers.download_count + 1
  where public.papers.id = target_paper_id
    and public.papers.visibility = 'public'
    and public.papers.status <> 'removed'
  returning public.papers.download_count;
end;
$$;
