# Change: Optional RAG Terminology Tooling

## Why
The graduation-design direction requires a RAG terminology module to improve academic terminology consistency, but the existing change proposal is stale: it depends on Supabase/pgvector, while the current project has moved to MySQL-backed runtime persistence and the production translation path is intentionally preserved as `origin_cli_parity`.

This change restarts the RAG terminology work as an opt-in translation-tool capability. It reuses the graduation-design architecture of "query transformation -> hybrid retrieval -> reranking -> prompt injection" while keeping the default production translation path unchanged.

## What Changes
- Replace all Supabase/pgvector/RPC terminology storage assumptions with MySQL as the review and metadata source of truth.
- Add Milvus as the optional vector retrieval database on the server for approved terminology embeddings.
- Add an explicit `enable_rag_terminology` style option for the translation tool; the feature is disabled by default and MUST NOT affect default `origin_cli_parity` tasks.
- Implement **multi-source knowledge base ingestion**:
  - CSV terminology table batch import (source type `imported`).
  - BibTeX citation parsing to extract keyphrase-term candidates (source type `auto_extracted` with citation provenance).
  - Auto-extraction from opted-in translation outputs (source type `auto_extracted`).
  - All sources funnel into the MySQL review workflow before entering retrieval.
- Implement a three-stage terminology RAG pipeline:
  - query transformation from LaTeX chunk text to terminology queries,
  - hybrid retrieval combining **BM25 keyword search** and Milvus vector search,
  - **Cross-Encoder reranking** and Top-N glossary injection.
- Persist auto-extracted and imported terminology candidates to MySQL with `pending_review` status, then expose admin approval and rejection flows.
- Keep graceful degradation: if embedding, Milvus, BM25 indexing, Cross-Encoder reranking, or retrieval fails, translation continues without RAG terminology enhancement.
- Record matched/injected terminology so the UI and graduation-design evaluation can compare RAG-enabled and baseline translation results.
- Provide **evaluation methodology** including BLEU/ROUGE scoring and terminology consistency metrics for graduation-design reporting.

## Impact
- Affected specs: `rag-terminology`
- Affected code:
  - `backend/migrations_mysql/` for terminology tables and indexes
  - `backend/app/repositories/` for MySQL terminology persistence
  - `backend/app/services/rag/` for embedding, retrieval (BM25 + vector), Cross-Encoder reranking, and prompt formatting
  - `backend/app/services/rag/knowledge_base/` for multi-source ingestion (CSV import, BibTeX parsing)
  - `backend/app/api/routes/` for terminology upload/review/admin endpoints
  - translation-tool configuration and execution paths that explicitly opt in to RAG terminology
  - frontend translation settings/admin terminology review UI, if implemented in this change
- Not affected:
  - default `origin_cli_parity` behavior
  - community/admin automated translation paths unless they explicitly opt in later through a separate approved change
  - Supabase, which is no longer part of this design
