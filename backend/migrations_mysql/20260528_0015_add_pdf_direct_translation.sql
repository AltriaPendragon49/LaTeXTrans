-- Add encrypted apikey column to users for PDF direct translation signing
alter table users
  add column encrypted_apikey text null after display_name;

-- Add unused_num_page to niutrans_balance_snapshots
alter table niutrans_balance_snapshots
  add column unused_num_page int null after unused_num_integral;

-- PDF direct translation tasks
create table if not exists pdf_direct_tasks (
  id varchar(64) not null,
  user_id varchar(64) not null,
  upstream_file_no varchar(128) not null,
  file_name varchar(512) not null,
  file_size_kb int null,
  page_num int null,
  progress double null,
  trans_status int not null default 101,
  trans_failure_cause text null,
  trans_failure_code int null,
  cos_artifact_key varchar(1024) null,
  status varchar(32) not null default 'active',
  created_at datetime not null,
  updated_at datetime not null,
  completed_at datetime null,
  primary key (id),
  key idx_pdf_direct_tasks_user_created (user_id, created_at),
  key idx_pdf_direct_tasks_upstream_file_no (upstream_file_no),
  key idx_pdf_direct_tasks_status (status, trans_status),
  constraint fk_pdf_direct_tasks_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;
