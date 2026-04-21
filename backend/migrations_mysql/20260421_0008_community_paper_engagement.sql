create table if not exists favorite_folders (
  id varchar(64) not null,
  user_id varchar(64) not null,
  name varchar(255) not null,
  created_at datetime not null,
  updated_at datetime not null,
  primary key (id),
  unique key uq_favorite_folders_user_name (user_id, name),
  key idx_favorite_folders_user_updated (user_id, updated_at),
  constraint fk_favorite_folders_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists favorite_folder_papers (
  folder_id varchar(64) not null,
  paper_id varchar(64) not null,
  created_at datetime not null default current_timestamp,
  primary key (folder_id, paper_id),
  unique key uq_favorite_folder_papers_folder_paper (folder_id, paper_id),
  key idx_favorite_folder_papers_paper_id (paper_id),
  constraint fk_favorite_folder_papers_folder_id
    foreign key (folder_id) references favorite_folders(id)
    on delete cascade,
  constraint fk_favorite_folder_papers_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists paper_daily_views (
  paper_id varchar(64) not null,
  view_date date not null,
  principal_type varchar(16) not null,
  principal_key varchar(128) not null,
  created_at datetime not null default current_timestamp,
  primary key (paper_id, view_date, principal_type, principal_key),
  unique key uq_paper_daily_views_dedupe (paper_id, view_date, principal_type, principal_key),
  key idx_paper_daily_views_lookup (paper_id, view_date),
  constraint fk_paper_daily_views_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;
