create table if not exists users (
  id varchar(64) primary key,
  external_provider varchar(32) not null,
  external_user_id varchar(64) not null,
  email varchar(255) null,
  display_name varchar(255) null,
  token_version int not null default 1,
  status varchar(32) not null default 'active',
  created_at datetime not null,
  updated_at datetime not null,
  unique key uq_users_provider_external (external_provider, external_user_id)
);

create table if not exists user_roles (
  user_id varchar(64) not null,
  role varchar(64) not null,
  created_at datetime not null,
  primary key (user_id, role),
  constraint fk_user_roles_user foreign key (user_id) references users(id)
);

create table if not exists auth_sessions (
  id varchar(64) primary key,
  user_id varchar(64) not null,
  status varchar(32) not null default 'active',
  issued_at datetime not null,
  expires_at datetime not null,
  revoked_at datetime null,
  last_seen_at datetime null,
  client_ip varchar(64) null,
  user_agent varchar(512) null,
  key idx_auth_sessions_user_status (user_id, status),
  constraint fk_auth_sessions_user foreign key (user_id) references users(id)
);

create table if not exists user_settings (
  user_id varchar(64) primary key,
  default_source_language varchar(16) not null default 'en',
  default_target_language varchar(16) not null default 'zh',
  translation_mode varchar(32) not null default 'full',
  compile_strategy varchar(32) not null default 'auto',
  translation_model varchar(128) null,
  generate_glossary boolean not null default true,
  use_author_api boolean not null default true,
  custom_base_url text null,
  custom_api_key_encrypted text null,
  default_formatting json null,
  updated_at datetime not null,
  constraint fk_user_settings_user foreign key (user_id) references users(id)
);

create table if not exists translation_tasks (
  task_id varchar(64) primary key,
  user_id varchar(64) null,
  source_type varchar(32) not null,
  arxiv_id varchar(64) null,
  status varchar(32) not null,
  stage varchar(64) null,
  progress int not null default 0,
  message text null,
  error text null,
  detail_code varchar(128) null,
  source_language varchar(16) not null,
  target_language varchar(16) not null,
  translation_mode varchar(32) not null,
  compile_strategy varchar(32) not null,
  translation_model varchar(128) null,
  config_hash varchar(128) null,
  source_path text null,
  output_path text null,
  formatting json null,
  generate_glossary boolean not null default true,
  use_author_api boolean not null default true,
  email_notification boolean not null default false,
  created_at datetime not null,
  completed_at datetime null,
  key idx_translation_tasks_user_created (user_id, created_at),
  key idx_translation_tasks_arxiv_hash (arxiv_id, config_hash),
  constraint fk_translation_tasks_user foreign key (user_id) references users(id)
);

create table if not exists papers (
  id varchar(64) primary key,
  created_by varchar(64) null,
  source varchar(32) not null,
  arxiv_id varchar(64) null,
  title text not null,
  authors json null,
  categories json null,
  abstract_raw text null,
  abstract_translated text null,
  visibility varchar(32) not null default 'public',
  status varchar(32) not null default 'published',
  community_status varchar(32) not null default 'official',
  trans_status varchar(32) not null default 'not_started',
  community_selected_task_id varchar(64) null,
  trans_latest_task_id varchar(64) null,
  official_published_at datetime null,
  view_count int not null default 0,
  download_count int not null default 0,
  created_at datetime not null,
  updated_at datetime not null,
  key idx_papers_visibility_status_created (visibility, status, created_at),
  unique key uq_papers_arxiv_id (arxiv_id)
);

create table if not exists paper_assets (
  id varchar(64) primary key,
  paper_id varchar(64) not null,
  task_id varchar(64) null,
  asset_type varchar(32) not null,
  storage_backend varchar(32) not null default 'local_disk',
  file_path text not null,
  file_name varchar(255) not null,
  mime_type varchar(255) not null,
  created_at datetime not null,
  key idx_paper_assets_paper_type (paper_id, asset_type),
  constraint fk_paper_assets_paper foreign key (paper_id) references papers(id)
);

create table if not exists community_conversations (
  id varchar(64) primary key,
  owner_user_id varchar(64) not null,
  title varchar(255) not null,
  created_at datetime not null,
  updated_at datetime not null,
  key idx_community_conversations_owner_updated (owner_user_id, updated_at),
  constraint fk_community_conversations_user foreign key (owner_user_id) references users(id)
);

create table if not exists community_conversation_turns (
  id varchar(64) primary key,
  conversation_id varchar(64) not null,
  sequence_no int not null,
  role varchar(32) not null,
  content longtext not null,
  status varchar(32) not null default 'completed',
  run_payload json null,
  error text null,
  created_at datetime not null,
  unique key uq_community_conversation_turns_sequence (conversation_id, sequence_no),
  constraint fk_community_conversation_turns_conversation foreign key (conversation_id) references community_conversations(id)
);

create table if not exists community_agent_runs (
  id varchar(64) primary key,
  owner_user_id varchar(64) not null,
  conversation_id varchar(64) null,
  status varchar(32) not null,
  mode varchar(32) not null default 'chat',
  intent varchar(64) null,
  message text null,
  summary text null,
  provider_state json null,
  action_payload json null,
  report_payload json null,
  created_at datetime not null,
  updated_at datetime not null,
  key idx_community_agent_runs_owner_updated (owner_user_id, updated_at),
  constraint fk_community_agent_runs_user foreign key (owner_user_id) references users(id),
  constraint fk_community_agent_runs_conversation foreign key (conversation_id) references community_conversations(id)
);

create table if not exists community_agent_events (
  id bigint auto_increment primary key,
  run_id varchar(64) not null,
  sequence_no int not null,
  event_type varchar(64) not null,
  payload json not null,
  created_at datetime not null,
  unique key uq_community_agent_events_sequence (run_id, sequence_no),
  constraint fk_community_agent_events_run foreign key (run_id) references community_agent_runs(id)
);
