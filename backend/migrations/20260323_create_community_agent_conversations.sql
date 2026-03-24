create table if not exists public.community_agent_conversations (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  conversation_id text not null,
  title text not null default 'New chat',
  turns jsonb not null default '[]'::jsonb,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  primary key (user_id, conversation_id),
  constraint community_agent_conversations_title_not_blank
    check (char_length(btrim(title)) > 0),
  constraint community_agent_conversations_turns_is_array
    check (jsonb_typeof(turns) = 'array')
);

create index if not exists community_agent_conversations_user_updated_idx
  on public.community_agent_conversations (user_id, updated_at desc);

alter table public.community_agent_conversations enable row level security;

drop policy if exists community_agent_conversations_select_own on public.community_agent_conversations;
create policy community_agent_conversations_select_own
  on public.community_agent_conversations
  for select
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists community_agent_conversations_insert_own on public.community_agent_conversations;
create policy community_agent_conversations_insert_own
  on public.community_agent_conversations
  for insert
  to authenticated
  with check (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );

drop policy if exists community_agent_conversations_update_own on public.community_agent_conversations;
create policy community_agent_conversations_update_own
  on public.community_agent_conversations
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

drop policy if exists community_agent_conversations_delete_own on public.community_agent_conversations;
create policy community_agent_conversations_delete_own
  on public.community_agent_conversations
  for delete
  to authenticated
  using (
    (select auth.uid()) is not null
    and (select auth.uid()) = user_id
  );
