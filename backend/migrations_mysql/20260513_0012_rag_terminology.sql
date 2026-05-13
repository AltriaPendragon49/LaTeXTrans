-- RAG Terminology Management
-- Implements the "query transformation -> hybrid retrieval (BM25 + vector) -> Cross-Encoder reranking -> glossary injection" pipeline.
-- Terminology terms table with review workflow, provenance tracking, and embedding sync metadata.

create table if not exists terminology_terms (
    id                  varchar(64)  not null,
    source_term         varchar(512) not null,
    target_term         varchar(512) not null,
    source_lang         varchar(16)  not null default 'en',
    target_lang         varchar(16)  not null default 'zh',
    domain              varchar(128)          default null,
    -- source_type: system, user, imported, auto_extracted
    source_type         varchar(32)  not null default 'auto_extracted',
    -- status: pending_review, approved, rejected
    status              varchar(32)  not null default 'pending_review',
    owner_user_id       varchar(64)          default null,
    created_by_user_id  varchar(64)          default null,
    reviewed_by_user_id varchar(64)          default null,
    reviewed_at         datetime             default null,
    rejection_reason    varchar(1024)        default null,
    -- Link back to the translation task that produced this term
    extracted_from_task_id varchar(64)       default null,
    -- Provenance metadata (JSON): tracks source file, row number, BibTeX citation key, etc.
    -- Examples:
    --   {"source":"csv_import","file_name":"physics_terms.csv","row":42}
    --   {"source":"bibtex","citation_key":"brown2020","entry_type":"article"}
    provenance          json                 default null,
    -- Embedding sync metadata
    embedding_model     varchar(128)         default null,
    -- embedding_status: none, pending, ready, failed
    embedding_status    varchar(32)  not null default 'none',
    vector_collection   varchar(128)         default null,
    vector_term_id      varchar(128)         default null,
    created_at          datetime     not null,
    updated_at          datetime     not null,

    primary key (id),
    key idx_terminology_status_lang (status, source_lang, target_lang),
    key idx_terminology_status_domain (status, domain),
    key idx_terminology_owner_status (owner_user_id, status),
    key idx_terminology_review_queue (status, created_at),
    key idx_terminology_extracted_task (extracted_from_task_id),
    key idx_terminology_source_term (source_term(128)),
    key idx_terminology_embedding_status (embedding_status),
    constraint fk_terminology_terms_owner
        foreign key (owner_user_id) references users(id)
        on delete set null,
    constraint fk_terminology_terms_created_by
        foreign key (created_by_user_id) references users(id)
        on delete set null,
    constraint fk_terminology_terms_reviewed_by
        foreign key (reviewed_by_user_id) references users(id)
        on delete set null
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

-- Table to track RAG terminology evaluation runs for graduation-design reporting
create table if not exists terminology_evaluation_runs (
    id                  varchar(64)  not null,
    task_id             varchar(64)  not null,
    -- baseline_task_id: the same paper translated WITHOUT RAG terminology for comparison
    baseline_task_id    varchar(64)           default null,
    rag_enabled         tinyint(1)   not null default 1,
    -- Evaluation scores (JSON): {"bleu": 0.45, "rouge_l": 0.52, "term_consistency": 0.88}
    scores_json         json                  default null,
    -- Number of terms matched/injected during this run
    matched_term_count  int          not null default 0,
    injected_term_count int          not null default 0,
    created_at          datetime     not null,
    primary key (id),
    key idx_eval_task (task_id),
    key idx_eval_baseline (baseline_task_id),
    constraint fk_evaluation_runs_task
        foreign key (task_id) references translation_tasks(task_id)
        on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;

-- Table to record which terms were matched during a RAG-enabled translation chunk
create table if not exists terminology_match_log (
    id                  varchar(64)  not null,
    task_id             varchar(64)  not null,
    term_id             varchar(64)  not null,
    chunk_index         int          not null default 0,
    -- retrieval_source: bm25, vector, both
    retrieval_source    varchar(32)  not null default 'bm25',
    -- Whether this term was actually injected into the prompt
    was_injected        tinyint(1)   not null default 0,
    -- Cross-Encoder relevance score (if reranking was applied)
    rerank_score        float                default null,
    created_at          datetime     not null,
    primary key (id),
    key idx_match_log_task (task_id),
    key idx_match_log_term (term_id),
    constraint fk_match_log_task
        foreign key (task_id) references translation_tasks(task_id)
        on delete cascade,
    constraint fk_match_log_term
        foreign key (term_id) references terminology_terms(id)
        on delete cascade
) engine=innodb default charset=utf8mb4 collate=utf8mb4_unicode_ci;
