# Design: Optional RAG Terminology Tooling

## Context
The graduation-design materials define the RAG module as a three-stage process: query transformation, hybrid retrieval, reranking, and prompt injection. They also allow a dedicated vector database such as Milvus or pgvector and a keyword retrieval path such as BM25.

The current project context has changed since the original proposal:
- Supabase has been fully abandoned.
- Runtime persistence is MySQL/SQLite oriented, with MySQL as the server deployment target.
- The default production translation path is intentionally normalized to `origin_cli_parity`.
- Terminology generation is currently disabled by parity normalization for default tasks.

This design keeps the thesis RAG idea but moves it behind an explicit translation-tool option. It does not redefine the default production translation kernel.

## Goals
- Reuse the graduation-design "query -> hybrid retrieval -> rerank -> inject" architecture.
- Use MySQL as the source of truth for terminology metadata, review status, ownership, and audit fields.
- Use Milvus as the server-side vector database for approved terminology embeddings.
- Provide an administrator review flow for auto-extracted terminology.
- Keep default translation behavior unchanged unless the user explicitly enables RAG terminology.
- Provide enough matched-term evidence for UI display and graduation-design evaluation.

## Non-Goals
- Do not restore Supabase, pgvector RPC functions, or Supabase RLS policies.
- Do not force RAG terminology into every translation mode.
- Do not alter community/admin automated translation paths by default.
- Do not require Elasticsearch; BM25 is implemented via the `rank_bm25` Python library operating on in-memory indices built from MySQL approved terms.
- Do not require local GPU reranking service. Cross-Encoder reranking uses a CPU-friendly model (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`).
- Full PDF content ingestion is marked as post-graduation; BibTeX citation parsing is limited to extracting keyphrase-term candidates from `.bib` files, not full-text PDF RAG.

## Architecture

### Data Stores

MySQL is authoritative for terminology state:
- approved system terms
- user/imported terms
- auto-extracted pending terms
- review decisions
- vector sync metadata

Milvus stores embeddings for approved terms only. Pending and rejected terms MUST NOT participate in vector retrieval.

```
Translation Tool Request
  -> optional enable_rag_terminology
  -> Query Transformer
  -> MySQL Keyword Retriever
  -> Milvus Vector Retriever
  -> Candidate Merge
  -> Reranker
  -> <Glossary> Injection
  -> Translation Call
  -> Auto Term Extraction
  -> MySQL pending_review
  -> Admin Approval
  -> Embedding + Milvus Upsert
```

### MySQL Schema Shape

Use a MySQL migration under `backend/migrations_mysql/`.

`terminology_terms` should include at least:
- `id`
- `source_term`
- `target_term`
- `source_lang`
- `target_lang`
- `domain`
- `source_type`: `system`, `user`, `imported`, `auto_extracted`
- `status`: `pending_review`, `approved`, `rejected`
- `owner_user_id` nullable
- `created_by_user_id` nullable
- `reviewed_by_user_id` nullable
- `reviewed_at` nullable
- `rejection_reason` nullable
- `extracted_from_task_id` nullable
- `provenance` nullable — JSON field for source provenance metadata (e.g. `{"source": "bibtex", "citation_key": "brown2020", "entry_type": "article"}`, or `{"source": "csv_import", "file_name": "physics_terms.csv", "row": 42}`)
- `embedding_model` nullable
- `embedding_status`: `none`, `pending`, `ready`, `failed`
- `vector_collection` nullable
- `vector_term_id` nullable
- `created_at`
- `updated_at`

Indexes:
- status/language/domain filters for retrieval
- owner/status filters for user-specific terms
- keyword index for `source_term` and optionally `target_term`
- review queue index for `status`, `created_at`

The first implementation may store embeddings only in Milvus. MySQL stores vector sync metadata, not the vector payload, unless a later migration needs embedding backup.

### Retrieval Pipeline

Stage 1: Query Transformation
- Extract plain text from LaTeX content using existing safe text extraction helpers.
- Build terminology queries from the current chunk, with a deterministic fallback that uses noun/phrase heuristics or the raw chunk when LLM query extraction fails.

Stage 2: Hybrid Retrieval (BM25 + Vector)
- **BM25 keyword path**: Build an in-memory BM25 index from approved terms (source_term text). Tokenize the query and score against the BM25 index on every retrieval call. The index is rebuilt when terms are approved/rejected or on a configurable refresh interval. This provides proper TF-IDF scoring without Elasticsearch.
- **MySQL exact path**: Retrieve approved terms by exact phrase and prefix matching as a complement to BM25.
- **Milvus vector path**: Retrieve semantically related approved terms by embedding similarity.
- Results from all three paths are merged and deduplicated by MySQL term id.
- User/imported terms outrank system terms when conflicts exist.

Stage 3: Cross-Encoder Reranking
- Rerank merged candidates against the current chunk using a Cross-Encoder model (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`).
- The Cross-Encoder scores each (chunk_text, candidate_source_term) pair with a relevance score.
- Keep Top-N terms, bounded by configuration.
- If Cross-Encoder reranking fails or is unavailable, fall back to a configurable lightweight reranker (LLM scoring) or merged retrieval score with priority ordering.

Stage 4: Prompt Injection
- Format selected terms as a compact `<Glossary>` block.
- Inject only for `enable_rag_terminology=true`.
- Keep the block bounded so it cannot dominate the model context.

### Multi-Source Knowledge Base Ingestion

The system ingests terminology from three external sources (in addition to manual system entry):

1. **CSV Import** (`source_type=imported`):
   - Accept CSV files with columns: `source_term`, `target_term`, `source_lang`, `target_lang`, `domain` (optional).
   - Validate row format, detect duplicates by (source_term, target_term, language pair).
   - All imported rows enter MySQL with `status=pending_review`.
   - API endpoint: `POST /api/terminology/upload` with file size and content type validation.

2. **BibTeX Citation Parsing** (`source_type=auto_extracted` with provenance):
   - Parse `.bib` files to extract citation keys and entry metadata.
   - Use LLM to suggest source-term/target-term candidates from citation title and abstract context (when available via arXiv API).
   - Store extracted candidates with `provenance={"source":"bibtex","citation_key":"...","entry_type":"..."}`.
   - These candidates enter the same `pending_review` workflow.

3. **Post-Translation Auto-Extraction** (`source_type=auto_extracted`):
   - After opted-in translation chunks complete, compare source/target segments to extract terminology pairs.
   - Store with `extracted_from_task_id` linking back to the translation task.
   - Enter `pending_review` workflow.

All ingested terms converge into the same MySQL review workflow (approve → embed → upsert to Milvus).

### Admin Review

Auto-extracted terminology is stored directly in MySQL as `pending_review`.

Admin actions:
- approve: mark approved, generate embedding, upsert into Milvus
- reject: mark rejected and exclude from retrieval
- inspect/list: filter by status, language pair, domain, source type, and task id

Approval must be idempotent. If embedding or Milvus upsert fails after approval, the term remains approved with `embedding_status='failed'` or `pending`, and keyword retrieval may still use it.

### API Boundaries

Routes should stay thin and delegate business logic to services/repositories.

Candidate API surface:
- `GET /api/terminology/terms`
- `POST /api/terminology/upload`
- `GET /api/terminology/pending`
- `POST /api/terminology/{term_id}/approve`
- `POST /api/terminology/{term_id}/reject`
- `GET /api/terminology/tasks/{task_id}/matches`

Admin review endpoints MUST require admin authentication. User-uploaded term endpoints MUST validate ownership and file size/content type.

### Configuration

Add explicit configuration, all disabled or conservative by default:
- `RAG_TERMINOLOGY_ENABLED=false`
- `RAG_TERMINOLOGY_TOP_N=10`
- `RAG_TERMINOLOGY_MILVUS_URI`
- `RAG_TERMINOLOGY_COLLECTION=terminology_terms`
- `RAG_TERMINOLOGY_EMBEDDING_MODEL`
- `RAG_TERMINOLOGY_RERANK_MODEL`

The translation tool flag is separate from server capability. If the server capability is disabled, user opt-in should be ignored gracefully with a visible but non-fatal status.

## Error Handling
- If query transformation fails, use deterministic plain-text fallback.
- If Milvus is unavailable, use MySQL keyword retrieval only.
- If MySQL retrieval fails, skip RAG for that chunk and continue translation.
- If reranking fails, use merged retrieval scores.
- If glossary injection would exceed context budget, reduce Top-N.
- If auto-extraction fails, log and continue; the translation result remains valid.

## Security
- Admin review endpoints require admin authorization.
- User uploads are size-limited and parsed as CSV/JSON only.
- Term text is treated as user input and must not be logged with secrets or injected into SQL through string concatenation.
- Query and insert/update operations must use parameterized repository methods.
- Matched-term logs should include term ids and safe text snippets only.

## Testing
- Repository tests for create/list/approve/reject transitions.
- BM25 index build/refresh/score unit tests.
- Retrieval tests for BM25/vector/keyword merge and user priority.
- Fallback tests for Milvus, embedding, Cross-Encoder rerank, and extraction failures.
- Route tests for admin-only review actions.
- Integration test for an opted-in translation-tool execution that records matched terms.
- Evaluation script or fixture comparing baseline vs RAG-enabled terminology consistency for graduation-design reporting.

## Evaluation Methodology
The graduation-design evaluation requires quantitative comparison between baseline and RAG-enabled translation.

### BLEU / ROUGE
- BLEU (BiLingual Evaluation Understudy): n-gram precision-based metric for translation quality.
- ROUGE (Recall-Oriented Understudy for Gisting Evaluation): recall-oriented metric.
- Compute both at sentence and document level for baseline and RAG outputs on the same source paper.
- Report delta = RAG_score - baseline_score.

### Terminology Consistency Metric
- Define a set of N key terms for the test domain (e.g. computer science: "self-attention", "convolutional layer", "backpropagation").
- For each key term, count how many times it appears in the RAG-enabled translation output as an exact target-language match to its canonical translation.
- Per-term consistency = (correct occurrences) / (total occurrences).
- Aggregate consistency = mean of per-term consistency across all N key terms.
- Compare against the same metric computed on the baseline output.

### Evaluation Artifacts
- Structured JSON/CSV report with all scores.
- Matched-term injection logs from RAG runs for qualitative analysis.
- Per-chunk comparison of glossary presence and term usage.

## Migration Plan
1. Update OpenSpec to remove stale Supabase design.
2. Add MySQL schema and repository.
3. Add Milvus and embedding wrappers behind config.
4. Add multi-source ingestion (CSV import, BibTeX parsing).
5. Add BM25 keyword retrieval, Cross-Encoder reranking, and retrieval/reranking/prompt formatting services.
6. Add opt-in translation-tool integration.
7. Add auto-extraction and admin review.
8. Add evaluation scripts and artifacts.
9. Add UI and graduation-design evaluation deliverables.

## Risks And Trade-offs
- Milvus adds one more server component. This is acceptable because the graduation-design方案 already allowed a vector database and MySQL alone is not a strong vector retrieval engine.
- Reranking can add latency. Keep Top-N and candidate counts bounded and allow reranking fallback.
- Optional RAG can drift from default parity output. This is intentional only for explicit opt-in tasks and must be measurable through matched-term logs.
- PDF/BibTeX RAG would expand scope. Keep first implementation focused on terminology entries and review workflow.
