create table if not exists community_structured_insights (
  paper_id varchar(64) not null,
  section_key varchar(64) not null,
  summary_en text null,
  summary_zh text null,
  bullets_en json null,
  bullets_zh json null,
  body_en mediumtext null,
  body_zh mediumtext null,
  status varchar(32) not null,
  updated_at datetime not null,
  primary key (paper_id, section_key),
  constraint fk_community_structured_insights_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade
);

create table if not exists community_curation_jobs (
  job_id varchar(64) not null primary key,
  batch_id varchar(64) not null,
  paper_id varchar(64) not null,
  source_type varchar(32) not null,
  arxiv_id varchar(64) null,
  original_filename varchar(512) null,
  source_path text null,
  task_id varchar(64) null,
  source_language varchar(16) not null,
  target_language varchar(16) not null,
  status varchar(32) not null,
  error text null,
  created_by varchar(64) not null,
  created_at datetime not null,
  updated_at datetime not null,
  key idx_community_curation_jobs_batch_created (batch_id, created_at),
  key idx_community_curation_jobs_status_created (status, created_at),
  key idx_community_curation_jobs_paper_created (paper_id, created_at)
);

create table if not exists community_delete_jobs (
  job_id varchar(64) not null primary key,
  paper_id varchar(64) not null,
  status varchar(32) not null,
  attempt_count int not null default 0,
  last_error text null,
  created_by varchar(64) not null,
  created_at datetime not null,
  updated_at datetime not null,
  key idx_community_delete_jobs_status_created (status, created_at),
  key idx_community_delete_jobs_paper_created (paper_id, created_at)
);
