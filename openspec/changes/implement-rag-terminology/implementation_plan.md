# Implementation Plan: Adaptive Advanced RAG for Terminology Consistency

## Goal Description
Implement the three-stage RAG pipeline ("Query → Hybrid Retrieval → Re-ranking") from task plan §3.1, using Supabase pgvector for dual-path retrieval, NVIDIA NIM for embeddings and Cross-Encoder re-ranking, applied across all translation modes. This transforms terminology management from "post-translation observation" to "in-translation active constraint".

## User Review Required

> [!IMPORTANT]
> **NVIDIA NIM API Cost**: The embedding and reranking models use the same NVIDIA NIM free-tier API key. Embedding calls add ~2-5 API calls per section (batch term embeddings). Reranking adds ~1 call per section. This may affect rate limiting (current: 30 concurrent). Need to confirm free-tier limits cover this additional load.

> [!WARNING]
> **Breaking Change to `trans_mode` semantics**: Currently `trans_mode == 2` is the only mode with terminology support. This change makes ALL modes use RAG terminology. The old `trans_mode == 2` specific behavior (CSV-only terms) will be superseded. The `build_term_dict()` CSV path is retained as fallback only.

> [!IMPORTANT]
> **Cross-Encoder Reranking Latency**: The NVIDIA NIM reranking API call adds ~200-500ms per section. For a 30-section paper, this adds ~6-15 seconds total. This is a tradeoff for significantly better terminology precision. Do you accept this?

## Proposed Changes

### Database Schema (Supabase pgvector)

#### [NEW] Supabase Migration: `create_glossary_terms_table`
- Enable pgvector extension
- Create `glossary_terms` table with columns: `id`, `source_term`, `target_term`, `domain`, `source`, `user_id`, `embedding` (vector 1024), `status`, `source_term_tsv` (tsvector)
- Create HNSW index on embedding column for fast vector search
- Create GIN index on tsvector column for fast keyword search
- Create RPC functions: `match_terms()` for vector search, `search_terms_keyword()` for full-text search
- Seed system default terms from existing `terms/default.csv`

---

### Backend RAG Service Module

#### [NEW] `backend/app/services/rag/__init__.py`
- Package initialization

#### [NEW] `backend/app/services/rag/embedding_service.py`
- `NvidiaEmbeddingService` class
- `embed_text(text: str) -> List[float]`: Single text embedding via NVIDIA NIM API
- `embed_batch(texts: List[str]) -> List[List[float]]`: Batch embedding
- Config: reads `LLM_API_KEY` and constructs embedding URL (`integrate.api.nvidia.com/v1/embeddings`)
- Model: `nvidia/nv-embedqa-1b-v2` (1024 dims)

#### [NEW] `backend/app/services/rag/term_retriever.py`
- `TermRetriever` class
- `hybrid_search(query_text: str, user_id: Optional[str]) -> List[TermCandidate]`:
  1. Extract keywords from query text
  2. Generate query embedding via `NvidiaEmbeddingService`
  3. Execute vector search via Supabase RPC `match_terms()`
  4. Execute keyword search via Supabase RPC `search_terms_keyword()`
  5. Merge and deduplicate results
  6. Return candidate list

#### [NEW] `backend/app/services/rag/reranker.py`
- `NvidiaReranker` class
- `rerank(query: str, candidates: List[TermCandidate], top_n: int = 10) -> List[TermCandidate]`:
  1. Call NVIDIA NIM Reranking API (`integrate.api.nvidia.com/v1/ranking`)
  2. Model: `nvidia/nv-rerankqa-mistral-4b-v3`
  3. Sort by relevance score, return top N

#### [NEW] `backend/app/services/rag/rag_pipeline.py`
- `RAGTerminologyPipeline` class — orchestrates the full three-stage pipeline
- `retrieve_terms(latex_content: str, user_id: Optional[str]) -> Dict[str, str]`:
  1. Stage 1: Query Transformation (LaTeX → plain text → keywords)
  2. Stage 2: Hybrid Retrieval via `TermRetriever`
  3. Stage 3: Re-ranking via `NvidiaReranker`
  4. Return `{source_term: target_term}` dictionary
- `format_glossary_prompt(terms: Dict[str, str]) -> str`: Format as `<Glossary>` block
- Graceful degradation: on any failure, return empty dict (fallback to CSV)

---

### Backend Agent Integration

#### [MODIFY] `backend/app/services/agents/translator_agent.py`
- Add `RAGTerminologyPipeline` as instance attribute in `__init__`
- **Modify `_translate_section`**: Before LLM call in ALL modes (0, 1, 2, 3):
  1. Call `rag_pipeline.retrieve_terms(section["content"])` 
  2. If terms found: inject `<Glossary>` block into system prompt
  3. If empty: proceed without glossary (graceful degradation)
- **Modify `_translate_env`** and **`_translate_caption`**: Same pattern
- **Remove mode-2 specific term logic**: Consolidate into universal RAG path
- **Keep `build_term_dict()` as fallback**: If RAG fails, fall back to CSV terms
- **Modify `_extract_terminology_from_translation`**: Append new terms to local `data/pending_terms.json` with `status = 'pending'` (source_term, target_term, domain, task_id, timestamp)

---

### Backend API Endpoints

#### [NEW] `backend/app/api/routes/terminology.py`
- `POST /api/terminology/upload`: Upload CSV/JSON glossary → parse and insert into `glossary_terms` with embeddings
- `GET /api/terminology/pending`: List all entries from `data/pending_terms.json` with `status == "pending"`
- `POST /api/terminology/approve`: Accept `{indices: [0, 2, 5]}` body → mark those entries in JSON as `status = "approved"`
- `POST /api/terminology/reject`: Accept `{indices: [1, 3]}` body → mark those entries in JSON as `status = "rejected"`
- **Note**: Approve/Reject only modify JSON file status. Actual DB insertion happens at next backend restart.

#### [MODIFY] `backend/app/main.py`
- Add `_process_pending_terms()` async function to `startup_event()`
- Runs **after** orphaned-task cleanup completes
- Reads `data/pending_terms.json`:
  - `status == "approved"`: Generate embedding via NVIDIA NIM → insert into Supabase `glossary_terms` → remove from JSON
  - `status == "rejected"`: Remove from JSON
  - `status == "pending"`: Keep in JSON for next review cycle
- If no decided entries → skip silently
- On failure (API/DB error): log error, keep JSON unchanged, terms wait for next restart

---

### Configuration

#### [MODIFY] `backend/.env`
- Add `NVIDIA_EMBEDDING_MODEL=nvidia/nv-embedqa-1b-v2`
- Add `NVIDIA_RERANK_MODEL=nvidia/nv-rerankqa-mistral-4b-v3`
- Add `RAG_TOP_N=10` (number of terms to inject)
- Add `RAG_ENABLED=true` (feature flag for gradual rollout)

#### [MODIFY] `backend/requirements.txt`
- No new dependencies needed (already has `aiohttp`, `supabase`, existing Supabase client handles pgvector)

---

### Specification

#### [MODIFY] `specs/rag-terminology/spec.md`
- Add requirements for hybrid retrieval, cross-encoder reranking, graceful degradation, performance constraints

---

## Verification Plan

### Automated Tests

1. **Unit test: Embedding Service**
   - File: `backend/tests/test_rag_embedding.py`
   - Command: `cd d:\future\antigravity\LaTexTrans\backend && python -m pytest tests/test_rag_embedding.py -v`
   - Tests: API call format validation, response parsing, error handling

2. **Unit test: Term Retriever**
   - File: `backend/tests/test_rag_retriever.py`  
   - Command: `cd d:\future\antigravity\LaTexTrans\backend && python -m pytest tests/test_rag_retriever.py -v`
   - Tests: Hybrid search merge logic, deduplication, user priority over system terms

3. **Unit test: Reranker**
   - File: `backend/tests/test_rag_reranker.py`
   - Command: `cd d:\future\antigravity\LaTexTrans\backend && python -m pytest tests/test_rag_reranker.py -v`
   - Tests: API call format, top-N selection, graceful error handling

4. **Integration test: RAG Pipeline**
   - File: `backend/tests/test_rag_pipeline.py`
   - Command: `cd d:\future\antigravity\LaTexTrans\backend && python -m pytest tests/test_rag_pipeline.py -v`
   - Tests: End-to-end pipeline with mocked API calls, fallback behavior

### Manual Verification
1. **Translation with RAG**: Run a translation task on a known paper, check terminal logs for `<Glossary>` injection in prompts
2. **Term consistency**: Compare translation output with/without RAG for a paper with domain-specific terms (e.g., "attention mechanism" should consistently translate to "注意力机制")
3. **Fallback**: Disable RAG (`RAG_ENABLED=false`), confirm translation still works via CSV fallback
4. **User-suggested**: Deploy to staging and test with a real paper; user verifies terminology quality improvement
