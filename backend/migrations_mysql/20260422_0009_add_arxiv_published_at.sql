alter table papers
  add column if not exists arxiv_published_at datetime null after official_published_at;
