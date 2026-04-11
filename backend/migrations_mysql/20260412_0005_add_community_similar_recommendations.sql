create table if not exists community_similar_recommendations (
  paper_id varchar(64) not null,
  position int not null,
  arxiv_id varchar(64) null,
  title varchar(1024) not null,
  abstract mediumtext not null,
  arxiv_url text not null,
  community_paper_id varchar(64) null,
  link_type varchar(32) not null,
  updated_at datetime not null,
  primary key (paper_id, position),
  key idx_community_similar_recommendations_paper_updated (paper_id, updated_at),
  constraint fk_community_similar_recommendations_paper_id
    foreign key (paper_id) references papers(id)
    on delete cascade
);
