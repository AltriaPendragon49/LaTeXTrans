# Implementation Tasks

## 1. OpenSpec Alignment
- [x] 1.1 Remove stale Supabase/pgvector assumptions from this change record.
- [x] 1.2 Validate the refreshed change with `openspec validate implement-rag-terminology --strict --no-interactive`.

## 2. Storage And Review Schema
- [ ] 2.1 Add MySQL migration for terminology terms, review fields, source metadata (including `provenance` JSON field), status, and keyword indexes.
- [ ] 2.2 Add optional embedding metadata fields for Milvus collection name, vector primary key, embedding model, and embedding status.
- [ ] 2.3 Implement repository methods for term creation, search, approval, rejection, provenance lookup, and embedding sync state.

## 3. Vector Store And Embeddings
- [ ] 3.1 Add Milvus configuration and connection wrapper with health/fallback behavior.
- [ ] 3.2 Implement embedding client using configured provider/model.
- [ ] 3.3 Upsert approved terms into Milvus and keep pending/rejected terms out of vector retrieval.
- [ ] 3.4 Add retry-safe handling for approved terms whose embedding or Milvus upsert fails.

## 4. RAG Retrieval Pipeline
- [ ] 4.1 Implement query transformation from LaTeX/plain text chunks to terminology queries.
- [ ] 4.2 **Implement BM25 keyword retrieval**: build in-memory BM25 index from approved terms using `rank_bm25`; score and rank candidates on each retrieval.
- [ ] 4.3 Implement MySQL exact/prefix retrieval as complement to BM25.
- [ ] 4.4 Implement Milvus vector retrieval for approved terms.
- [ ] 4.5 Merge and deduplicate BM25, MySQL exact, and vector candidates with source/user priority.
- [ ] 4.6 **Implement Cross-Encoder reranking**: score (chunk_text, candidate_term) pairs using `sentence-transformers` cross-encoder model; select Top-N.
- [ ] 4.7 Add graceful fallback: Cross-Encoder → BM25+vector score merge → keyword-only → skip RAG.
- [ ] 4.8 Format selected terms into a bounded `<Glossary>` prompt block.

## 5. Multi-Source Knowledge Base Ingestion
- [ ] 5.1 **CSV import**: implement CSV parser with row validation, duplicate detection, and batch insert as `source_type=imported`.
- [ ] 5.2 **BibTeX parsing**: implement BibTeX file parser to extract citation entries; use LLM to suggest term candidates with provenance metadata.
- [ ] 5.3 Add POST `/api/terminology/upload` endpoint accepting CSV and BibTeX files with size/content-type validation.
- [ ] 5.4 Store all ingested candidates in MySQL with `status=pending_review` and route them through the admin review workflow.

## 6. Translation Tool Integration
- [ ] 6.1 Add an explicit opt-in translation-tool configuration flag for RAG terminology.
- [ ] 6.2 Ensure default `origin_cli_parity` tasks remain byte/behavior compatible when the flag is absent or false.
- [ ] 6.3 Inject retrieved glossary terms only for opted-in translation-tool executions.
- [ ] 6.4 Persist matched/injected term metadata for UI display and evaluation.

## 7. Admin Review
- [ ] 7.1 Extract source-target terminology pairs after opted-in translations (auto-extraction).
- [ ] 7.2 Store extracted pairs in MySQL as `pending_review`.
- [ ] 7.3 Add admin endpoints to list, approve, reject, and inspect terminology candidates.
- [ ] 7.4 On approval, refresh BM25 index, generate embeddings, and upsert approved terms into Milvus.

## 8. Frontend
- [ ] 8.1 Add translation-tool UI control for optional RAG terminology.
- [ ] 8.2 Display matched/injected terms for completed RAG-enabled tasks.
- [ ] 8.3 Add or extend admin UI for pending terminology review.

## 9. Evaluation And Artifacts
- [ ] 9.1 **BLEU/ROUGE evaluation script**: implement script that computes sentence-level and document-level BLEU/ROUGE scores comparing baseline vs RAG-enabled outputs on the same source paper.
- [ ] 9.2 **Terminology consistency metric**: implement metric measuring the proportion of predefined key terms translated identically across all occurrences; per-term and aggregate rates.
- [ ] 9.3 **Evaluation report export**: generate structured JSON/CSV report with BLEU, ROUGE, and terminology consistency scores.
- [ ] 9.4 Prepare graduation-design evaluation artifacts: matched-term logs, score deltas, and qualitative comparison notes.

## 10. Tests
- [ ] 10.1 Add unit tests for repository status transitions and permission boundaries.
- [ ] 10.2 Add unit tests for BM25 index build, scoring, and refresh behavior.
- [ ] 10.3 Add unit tests for hybrid retrieval merge/deduplication and fallback behavior.
- [ ] 10.4 Add mocked tests for embedding, Milvus, Cross-Encoder reranking clients.
- [ ] 10.5 Add integration coverage for an opted-in translation-tool run that records matched terms.
