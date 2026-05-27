-- Add hot_score column to papers for hot ranking sort
set @col_exists = 0;
select count(*) into @col_exists
from information_schema.columns
where table_schema = database()
  and table_name = 'papers'
  and column_name = 'hot_score';

set @sql = if(@col_exists = 0,
    'alter table papers add column hot_score double null after view_count',
    'select ''column hot_score already exists'' as msg');
prepare stmt from @sql;
execute stmt;
deallocate prepare stmt;

-- Create index if not exists
set @idx_exists = 0;
select count(*) into @idx_exists
from information_schema.statistics
where table_schema = database()
  and table_name = 'papers'
  and index_name = 'idx_papers_hot_score_desc';

set @sql2 = if(@idx_exists = 0,
    'create index idx_papers_hot_score_desc on papers (hot_score desc)',
    'select ''index idx_papers_hot_score_desc already exists'' as msg');
prepare stmt2 from @sql2;
execute stmt2;
deallocate prepare stmt2;
