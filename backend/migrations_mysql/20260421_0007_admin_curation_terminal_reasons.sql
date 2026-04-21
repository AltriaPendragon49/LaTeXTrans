set @has_terminal_reason := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'community_curation_jobs'
    and column_name = 'terminal_reason'
);
set @ddl := if(
  @has_terminal_reason = 0,
  'alter table community_curation_jobs add column terminal_reason varchar(64) null after terminal_task_status',
  'select 1'
);
prepare stmt from @ddl;
execute stmt;
deallocate prepare stmt;

set @has_timeout_reason := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'community_curation_jobs'
    and column_name = 'timeout_reason'
);
set @ddl := if(
  @has_timeout_reason = 0,
  'alter table community_curation_jobs add column timeout_reason varchar(64) null after terminal_reason',
  'select 1'
);
prepare stmt from @ddl;
execute stmt;
deallocate prepare stmt;
