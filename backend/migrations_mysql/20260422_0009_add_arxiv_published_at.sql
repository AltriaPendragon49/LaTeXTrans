set @ddl := (
  select if(
    exists(
      select 1
      from information_schema.columns
      where table_schema = database()
        and table_name = 'papers'
        and column_name = 'arxiv_published_at'
    ),
    'select 1',
    'alter table papers add column arxiv_published_at datetime null after official_published_at'
  )
);
prepare stmt from @ddl;
execute stmt;
deallocate prepare stmt;
