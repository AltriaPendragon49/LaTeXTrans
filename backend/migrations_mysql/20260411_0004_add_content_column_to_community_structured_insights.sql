set @community_structured_insights_has_content := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'community_structured_insights'
    and column_name = 'content'
);

set @community_structured_insights_add_content_sql := if(
  @community_structured_insights_has_content = 0,
  'alter table community_structured_insights add column content mediumtext null after section_key',
  'select 1'
);

prepare community_structured_insights_add_content_stmt from @community_structured_insights_add_content_sql;
execute community_structured_insights_add_content_stmt;
deallocate prepare community_structured_insights_add_content_stmt;
