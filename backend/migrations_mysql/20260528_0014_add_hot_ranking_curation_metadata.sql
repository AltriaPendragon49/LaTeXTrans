-- Persist hot-ranking intake metadata on admin curation jobs
set @col_exists = 0;
select count(*) into @col_exists
from information_schema.columns
where table_schema = database()
  and table_name = 'community_curation_jobs'
  and column_name = 'source_family';

set @sql = if(@col_exists = 0,
    'alter table community_curation_jobs add column source_family varchar(64) null after artifact_storage_backend',
    'select ''column source_family already exists'' as msg');
prepare stmt from @sql;
execute stmt;
deallocate prepare stmt;

set @col_exists = 0;
select count(*) into @col_exists
from information_schema.columns
where table_schema = database()
  and table_name = 'community_curation_jobs'
  and column_name = 'hot_score';

set @sql = if(@col_exists = 0,
    'alter table community_curation_jobs add column hot_score double null after source_family',
    'select ''column hot_score already exists'' as msg');
prepare stmt from @sql;
execute stmt;
deallocate prepare stmt;

set @col_exists = 0;
select count(*) into @col_exists
from information_schema.columns
where table_schema = database()
  and table_name = 'community_curation_jobs'
  and column_name = 'score_breakdown';

set @sql = if(@col_exists = 0,
    'alter table community_curation_jobs add column score_breakdown json null after hot_score',
    'select ''column score_breakdown already exists'' as msg');
prepare stmt from @sql;
execute stmt;
deallocate prepare stmt;

set @idx_exists = 0;
select count(*) into @idx_exists
from information_schema.statistics
where table_schema = database()
  and table_name = 'community_curation_jobs'
  and index_name = 'idx_curation_jobs_source_family_hot_score';

set @sql = if(@idx_exists = 0,
    'create index idx_curation_jobs_source_family_hot_score on community_curation_jobs (source_family, hot_score)',
    'select ''index idx_curation_jobs_source_family_hot_score already exists'' as msg');
prepare stmt from @sql;
execute stmt;
deallocate prepare stmt;
