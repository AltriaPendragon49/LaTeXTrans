set @users_has_login_identifier := (
  select count(*)
  from information_schema.columns
  where table_schema = database()
    and table_name = 'users'
    and column_name = 'login_identifier'
);

set @alter_users_add_login_identifier := if(
  @users_has_login_identifier = 0,
  'alter table users add column login_identifier varchar(255) null after external_user_id',
  'select 1'
);

prepare stmt from @alter_users_add_login_identifier;
execute stmt;
deallocate prepare stmt;
