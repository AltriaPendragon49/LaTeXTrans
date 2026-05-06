create table if not exists user_daily_quotas (
  user_id varchar(64) not null,
  quota_type varchar(64) not null,
  quota_date date not null,
  limit_count int not null,
  used_count int not null default 0,
  created_at datetime not null,
  updated_at datetime not null,
  primary key (user_id, quota_type, quota_date),
  key idx_user_daily_quotas_date_type (quota_date, quota_type),
  constraint chk_user_daily_quotas_nonnegative
    check (used_count >= 0 and limit_count >= 0),
  constraint fk_user_daily_quotas_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

create table if not exists niutrans_balance_snapshots (
  user_id varchar(64) not null,
  unused_num_integral int null,
  status varchar(32) not null,
  source varchar(32) not null,
  fetched_at datetime null,
  updated_at datetime not null,
  primary key (user_id),
  constraint fk_niutrans_balance_snapshots_user_id
    foreign key (user_id) references users(id)
    on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;
