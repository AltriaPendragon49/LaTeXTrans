create table if not exists users (
  id varchar(64) not null,
  external_provider varchar(32) not null,
  external_user_id varchar(128) not null,
  email varchar(255) null,
  display_name varchar(255) null,
  token_version int not null default 1,
  status varchar(32) not null default 'active',
  created_at datetime not null,
  updated_at datetime not null,
  primary key (id),
  unique key uq_users_provider_external (external_provider, external_user_id),
  key idx_users_status_created (status, created_at)
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists user_roles (
  user_id varchar(64) not null,
  role varchar(64) not null,
  created_at datetime not null,
  primary key (user_id, role),
  key idx_user_roles_role (role),
  constraint fk_user_roles_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists auth_sessions (
  id varchar(64) not null,
  user_id varchar(64) not null,
  status varchar(32) not null default 'active',
  issued_at datetime not null,
  expires_at datetime not null,
  revoked_at datetime null,
  last_seen_at datetime null,
  client_ip varchar(64) null,
  user_agent varchar(512) null,
  primary key (id),
  key idx_auth_sessions_user_status (user_id, status),
  key idx_auth_sessions_expires_at (expires_at),
  constraint fk_auth_sessions_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists user_settings (
  user_id varchar(64) not null,
  default_source_language varchar(16) not null default 'en',
  default_target_language varchar(16) not null default 'zh',
  translation_mode varchar(32) not null default 'full',
  compile_strategy varchar(32) not null default 'auto',
  translation_model varchar(128) null,
  generate_glossary tinyint(1) not null default 1,
  use_author_api tinyint(1) not null default 1,
  custom_base_url text null,
  custom_api_key_encrypted text null,
  default_formatting json null,
  updated_at datetime not null,
  primary key (user_id),
  constraint fk_user_settings_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists translation_tasks (
  task_id varchar(64) not null,
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
  generate_glossary tinyint(1) not null default 1,
  use_author_api tinyint(1) not null default 1,
  email_notification tinyint(1) not null default 0,
  created_at datetime not null,
  completed_at datetime null,
  primary key (task_id),
  key idx_translation_tasks_user_created (user_id, created_at),
  key idx_translation_tasks_status_created (status, created_at),
  key idx_translation_tasks_arxiv_hash (arxiv_id, config_hash),
  constraint fk_translation_tasks_user_id
    foreign key (user_id) references users(id)
    on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists papers (
  id varchar(64) not null,
  created_by varchar(64) null,
  source varchar(32) not null,
  arxiv_id varchar(64) null,
  title text not null,
  authors json null,
  categories json null,
  abstract_raw text null,
  abstract_translated text null,
  visibility varchar(32) not null,
  status varchar(32) not null,
  community_status varchar(32) not null,
  trans_status varchar(32) not null,
  trans_latest_task_id varchar(64) null,
  trans_latest_asset_pdf_id varchar(255) null,
  community_selected_task_id varchar(64) null,
  community_selected_asset_id varchar(255) null,
  like_count int not null default 0,
  favorite_count int not null default 0,
  comment_count int not null default 0,
  view_count int not null default 0,
  download_count int not null default 0,
  official_published_at datetime null,
  created_at datetime not null,
  updated_at datetime not null,
  primary key (id),
  unique key uq_papers_arxiv_id (arxiv_id),
  key idx_papers_visibility_status_created (visibility, status, created_at),
  key idx_papers_trans_status_created (trans_status, created_at),
  key idx_papers_created_by (created_by),
  constraint fk_papers_created_by_user_id
    foreign key (created_by) references users(id)
    on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists paper_assets (
  id varchar(128) not null,
  paper_id varchar(64) not null,
  task_id varchar(64) null,
  asset_type varchar(32) not null,
  storage_backend varchar(32) not null,
  file_path text not null,
  file_name varchar(255) not null,
  mime_type varchar(255) not null,
  is_latest tinyint(1) not null default 1,
  created_at datetime not null,
  primary key (id),
  key idx_paper_assets_paper_type_latest (paper_id, asset_type, is_latest, created_at),
  key idx_paper_assets_task_id (task_id),
  constraint fk_paper_assets_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade,
  constraint fk_paper_assets_task_id
    foreign key (task_id) references translation_tasks(task_id)
    on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists paper_likes (
  paper_id varchar(64) not null,
  user_id varchar(64) not null,
  created_at datetime not null default current_timestamp,
  primary key (paper_id, user_id),
  key idx_paper_likes_user_id_paper_id (user_id, paper_id),
  constraint fk_paper_likes_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade,
  constraint fk_paper_likes_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists paper_favorites (
  paper_id varchar(64) not null,
  user_id varchar(64) not null,
  created_at datetime not null default current_timestamp,
  primary key (paper_id, user_id),
  key idx_paper_favorites_user_id_paper_id (user_id, paper_id),
  constraint fk_paper_favorites_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade,
  constraint fk_paper_favorites_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists comments (
  id varchar(64) not null,
  paper_id varchar(64) not null,
  user_id varchar(64) null,
  parent_id varchar(64) null,
  content text null,
  status varchar(32) not null default 'visible',
  created_at datetime not null default current_timestamp,
  updated_at datetime not null default current_timestamp,
  primary key (id),
  key idx_comments_paper_created (paper_id, created_at),
  key idx_comments_user_id (user_id),
  key idx_comments_parent_id (parent_id),
  constraint fk_comments_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade,
  constraint fk_comments_user_id
    foreign key (user_id) references users(id)
    on delete set null,
  constraint fk_comments_parent_id
    foreign key (parent_id) references comments(id)
    on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists reports (
  id varchar(64) not null,
  target_type varchar(32) not null,
  target_id varchar(64) not null,
  paper_id varchar(64) null,
  comment_id varchar(64) null,
  reported_by varchar(64) null,
  reason_code varchar(64) null,
  detail text null,
  status varchar(32) not null default 'open',
  created_at datetime not null,
  updated_at datetime not null,
  primary key (id),
  key idx_reports_target_status_created (target_type, target_id, status, created_at),
  key idx_reports_reported_by_created (reported_by, created_at),
  constraint fk_reports_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade,
  constraint fk_reports_comment_id
    foreign key (comment_id) references comments(id)
    on delete cascade,
  constraint fk_reports_reported_by_user_id
    foreign key (reported_by) references users(id)
    on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists moderation_actions (
  id varchar(64) not null,
  report_id varchar(64) not null,
  actor_user_id varchar(64) null,
  action_type varchar(32) not null,
  note text null,
  created_at datetime not null,
  primary key (id),
  key idx_moderation_actions_report_id_created (report_id, created_at),
  key idx_moderation_actions_actor_created (actor_user_id, created_at),
  constraint fk_moderation_actions_report_id
    foreign key (report_id) references reports(id)
    on delete cascade,
  constraint fk_moderation_actions_actor_user_id
    foreign key (actor_user_id) references users(id)
    on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists community_agent_conversations (
  conversation_id varchar(64) not null,
  user_id varchar(64) not null,
  title varchar(255) not null default 'New chat',
  created_at datetime not null,
  updated_at datetime not null,
  turns json not null,
  primary key (conversation_id, user_id),
  key idx_community_agent_conversations_user_updated (user_id, updated_at),
  constraint fk_community_agent_conversations_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists community_agent_runs (
  run_id varchar(64) not null,
  user_id varchar(64) null,
  conversation_id varchar(64) null,
  status varchar(32) not null default 'queued',
  intent varchar(64) not null default 'answer',
  mode varchar(32) not null default 'chat',
  message text null,
  summary text null,
  error text null,
  report json null,
  created_at datetime not null,
  updated_at datetime not null,
  completed_at datetime null,
  primary key (run_id),
  key idx_community_agent_runs_user_updated (user_id, updated_at),
  key idx_community_agent_runs_conversation_updated (conversation_id, updated_at),
  constraint fk_community_agent_runs_user_id
    foreign key (user_id) references users(id)
    on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists community_agent_events (
  id bigint not null auto_increment,
  run_id varchar(64) not null,
  sequence_no int not null,
  event_type varchar(32) not null,
  payload json not null,
  created_at datetime not null,
  primary key (id),
  unique key uq_community_agent_events_run_sequence (run_id, sequence_no),
  key idx_community_agent_events_run_created (run_id, created_at),
  constraint fk_community_agent_events_run_id
    foreign key (run_id) references community_agent_runs(run_id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;
