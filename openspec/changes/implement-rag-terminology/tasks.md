# Implementation Tasks

1. [ ] **Database**: Create Supabase migration for `glossary_terms` table with pgvector + tsvector indexes and RPC functions
2. [ ] **Database**: Seed system default terms from existing `terms/default.csv` with NVIDIA embeddings
3. [ ] **Backend**: Implement `rag/embedding_service.py` — NVIDIA NIM Embedding API client
4. [ ] **Backend**: Implement `rag/term_retriever.py` — Hybrid search (vector + keyword) via Supabase
5. [ ] **Backend**: Implement `rag/reranker.py` — NVIDIA NIM Cross-Encoder Reranking API client
6. [ ] **Backend**: Implement `rag/rag_pipeline.py` — Three-stage pipeline orchestrator with fallback
7. [ ] **Backend**: Modify `TranslatorAgent._translate_section` — integrate RAG for all modes (0,1,2,3)
8. [ ] **Backend**: Modify `TranslatorAgent._translate_env` and `_translate_caption` — integrate RAG
9. [ ] **Backend**: Modify `_extract_terminology_from_translation` — append to `data/pending_terms.json` instead of memory
10. [ ] **Backend**: Add terminology management API routes (`/api/terminology/upload`, `/pending`, `/approve`, `/reject`) — JSON-based
11. [ ] **Backend**: Add `_process_pending_terms()` to `main.py:startup_event()` — startup entry processing (approved→embed+Supabase, rejected→delete)
12. [ ] **Config**: Update `.env` with embedding/rerank model configs, feature flag
13. [ ] **Tests**: Write unit tests for embedding, retriever, reranker, pipeline, startup term processing
14. [ ] **Integration**: End-to-end test with real paper translation
15. [ ] **Frontend**: Emit matched terms via WebSocket for terminology UI display
