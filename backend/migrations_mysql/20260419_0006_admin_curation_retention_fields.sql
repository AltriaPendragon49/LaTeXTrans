set @has_terminal_task_status := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'community_curation_jobs'
    and column_name = 'terminal_task_status'
);
set @ddl := if(
  @has_terminal_task_status = 0,
  'alter table community_curation_jobs add column terminal_task_status varchar(32) null after status',
  'select 1'
);
prepare stmt from @ddl;
execute stmt;
deallocate prepare stmt;

set @has_failed_artifact_path := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'community_curation_jobs'
    and column_name = 'failed_artifact_path'
);
set @ddl := if(
  @has_failed_artifact_path = 0,
  'alter table community_curation_jobs add column failed_artifact_path text null after error',
  'select 1'
);
prepare stmt from @ddl;
execute stmt;
deallocate prepare stmt;

set @has_artifact_storage_backend := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'community_curation_jobs'
    and column_name = 'artifact_storage_backend'
);
set @ddl := if(
  @has_artifact_storage_backend = 0,
  'alter table community_curation_jobs add column artifact_storage_backend varchar(32) null after failed_artifact_path',
  'select 1'
);
prepare stmt from @ddl;
execute stmt;
deallocate prepare stmt;

set @has_published_paper_id := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'community_curation_jobs'
    and column_name = 'published_paper_id'
);
set @ddl := if(
  @has_published_paper_id = 0,
  'alter table community_curation_jobs add column published_paper_id varchar(64) null after paper_id',
  'select 1'
);
prepare stmt from @ddl;
execute stmt;
deallocate prepare stmt;
