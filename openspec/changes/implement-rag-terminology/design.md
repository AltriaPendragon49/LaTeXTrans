# Design: Adaptive Advanced RAG Terminology Architecture

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Translation Request                        │
│                  (LaTeX section/env/caption)                  │
└──────────────────┬───────────────────────────────────────────┘
                   │
          ┌────────▼────────┐
          │ Stage 1: Query   │
          │ Transformation   │
          │ (extract plain   │
          │  text + keywords)│
          └────────┬─────────┘
                   │
       ┌───────────┼───────────┐
       │                       │
┌──────▼──────┐         ┌──────▼──────┐
│ Vector      │         │ Keyword     │
│ Search      │         │ Search      │
│ (pgvector + │         │ (tsvector + │
│  NVIDIA     │         │  ts_rank)   │
│  Embeddings)│         │             │
└──────┬──────┘         └──────┬──────┘
       │                       │
       └───────────┬───────────┘
                   │
          ┌────────▼────────┐
          │ Stage 2: Merge  │
          │ Candidate Pool  │
          └────────┬────────┘
                   │
          ┌────────▼─────────┐
          │ Stage 3: Cross-  │
          │ Encoder Reranking│
          │ (NVIDIA NIM      │
          │  Rerank API)     │
          └────────┬─────────┘
                   │
          ┌────────▼─────────┐
          │ Top-N Golden     │
          │ Context Injection│
          │ <Glossary> block │
          └────────┬─────────┘
                   │
          ┌────────▼─────────┐
          │ LLM Translation  │
          │ with constrained │
          │ terminology      │
          └──────────────────┘
```

## 1. Storage Backend (Supabase pgvector)

### Terminology Table Schema
```sql
CREATE TABLE glossary_terms (
  id SERIAL PRIMARY KEY,
  source_term TEXT NOT NULL,         -- English term
  target_term TEXT NOT NULL,         -- Translated term (e.g. Chinese)
  domain TEXT DEFAULT 'general',     -- e.g. 'cs.AI', 'physics', 'math'
  source TEXT DEFAULT 'system',      -- 'system' | 'user' | 'auto_extracted'
  user_id UUID REFERENCES auth.users(id),  -- NULL for system terms
  embedding VECTOR(1024),           -- NVIDIA NIM embedding dimension
  status TEXT DEFAULT 'approved',   -- 'approved' | 'pending_review'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Full-text search index column
  source_term_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', source_term)) STORED
);

-- Vector similarity index (HNSW for fast ANN)
CREATE INDEX idx_glossary_embedding ON glossary_terms 
  USING hnsw (embedding vector_cosine_ops);

-- Full-text search index
CREATE INDEX idx_glossary_tsv ON glossary_terms 
  USING gin (source_term_tsv);

-- Priority lookup index
CREATE INDEX idx_glossary_source_user ON glossary_terms (source, user_id);
```

### Prioritization Logic
- **User-defined terms** (`source = 'user'` AND `user_id` matches) → highest priority
- **System default terms** (`source = 'system'`) → baseline
- **Auto-extracted terms** (`source = 'auto_extracted'`, `status = 'pending_review'`) → excluded from retrieval until approved

## 2. Embedding Service (NVIDIA NIM)

- **API Endpoint**: `https://integrate.api.nvidia.com/v1/embeddings`
- **Model**: `nvidia/nv-embedqa-1b-v2` (1024 dimensions, multilingual, optimized for retrieval QA)
- **Authentication**: Same `nvapi-*` API key as existing LLM service
- **Integration**: Direct HTTP call via `aiohttp` (consistent with existing `_request_llm_for_trans`)

```python
# Embedding request format (OpenAI-compatible)
payload = {
    "model": "nvidia/nv-embedqa-1b-v2",
    "input": ["transformer architecture", "attention mechanism"],
    "input_type": "query",  # or "passage" for stored terms
    "encoding_format": "float"
}
```

## 3. Three-Stage RAG Retrieval Pipeline

### Stage 1: Query Transformation
- Input: Raw LaTeX content from section/env/caption
- Process: `_extract_text_from_tex()` → plain text → LLM extracts key terminology phrases
- Output: List of query terms (e.g., `["attention mechanism", "transformer", "self-supervised learning"]`)

### Stage 2: Hybrid Retrieval (Dual-Path)

**Path A – Vector Search (Semantic)**:
```sql
-- Supabase RPC function
CREATE FUNCTION match_terms(
  query_embedding VECTOR(1024),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 20,
  p_user_id UUID DEFAULT NULL
)
RETURNS TABLE (id INT, source_term TEXT, target_term TEXT, similarity FLOAT, source TEXT)
AS $$
  SELECT id, source_term, target_term, 
         1 - (embedding <=> query_embedding) AS similarity,
         source
  FROM glossary_terms
  WHERE embedding <=> query_embedding < 1 - match_threshold
    AND status = 'approved'
    AND (user_id IS NULL OR user_id = p_user_id)
  ORDER BY embedding <=> query_embedding ASC
  LIMIT match_count;
$$ LANGUAGE sql;
```

**Path B – Keyword Search (Exact/Phrase)**:
```sql
CREATE FUNCTION search_terms_keyword(
  query TEXT,
  match_count INT DEFAULT 20,
  p_user_id UUID DEFAULT NULL
)
RETURNS TABLE (id INT, source_term TEXT, target_term TEXT, rank FLOAT, source TEXT)
AS $$
  SELECT id, source_term, target_term,
         ts_rank(source_term_tsv, plainto_tsquery('english', query)) AS rank,
         source
  FROM glossary_terms
  WHERE source_term_tsv @@ plainto_tsquery('english', query)
    AND status = 'approved'
    AND (user_id IS NULL OR user_id = p_user_id)
  ORDER BY rank DESC
  LIMIT match_count;
$$ LANGUAGE sql;
```

**Merge**: Union results from both paths, deduplicate by `id`, combine scores.

### Stage 3: Cross-Encoder Re-ranking

- **API**: NVIDIA NIM Reranking (`https://integrate.api.nvidia.com/v1/ranking`)
- **Model**: `nvidia/nv-rerankqa-mistral-4b-v3`
- **Input**: Query text + candidate term pairs
- **Output**: Re-ranked list with relevance scores
- Select **Top-N** (default N=10) terms for injection

```python
# Reranking request format
payload = {
    "model": "nvidia/nv-rerankqa-mistral-4b-v3",
    "query": {"text": "the transformer architecture uses multi-head attention"},
    "passages": [
        {"text": "transformer → 变换器"},
        {"text": "attention mechanism → 注意力机制"},
        ...
    ]
}
```

## 4. Prompt Injection

Retrieved and re-ranked terms are injected into the system prompt:
```
<Glossary>
When translating, you MUST strictly use the following glossary.
User-defined terms (highest priority):
  - "field" → "域"
System terms:
  - "attention mechanism" → "注意力机制"
  - "transformer" → "Transformer"
  - "self-supervised learning" → "自监督学习"
</Glossary>
```

## 5. Terminology Auto-Extraction & Approval Workflow

### 5.1 Extraction Phase (During Translation)

After each section translates, `_extract_terminology_from_translation()` produces new `{source_term, target_term}` pairs. These are **appended** to a local JSON file:

**File**: `backend/data/pending_terms.json`
```json
[
  {
    "source_term": "attention mechanism",
    "target_term": "注意力机制",
    "domain": "cs.AI",
    "extracted_from_task": "task-abc123",
    "extracted_at": "2026-02-24T21:00:00+08:00",
    "status": "pending"
  },
  {
    "source_term": "wrong term",
    "target_term": "错误翻译",
    "domain": "general",
    "extracted_from_task": "task-def456",
    "extracted_at": "2026-02-24T20:30:00+08:00",
    "status": "rejected"
  }
]
```

### 5.2 Admin Review Phase (Via API)

Endpoints in `backend/app/api/routes/terminology.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/terminology/pending` | GET | List all entries in `pending_terms.json` with `status == "pending"` |
| `/api/terminology/approve` | POST | Set `status = "approved"` for specified term entries |
| `/api/terminology/reject` | POST | Set `status = "rejected"` for specified term entries |

These endpoints only modify the `status` field in `pending_terms.json`. **No database writes happen at review time** — this keeps the review fast and offline-safe.

### 5.3 Startup Processing Phase (Backend Restart)

On **every backend restart**, after orphaned-task cleanup completes, a new `_process_pending_terms()` function runs as part of `startup_event()` in `main.py`:

```
startup_event()
  ├─ Initialize TaskQueue
  ├─ Start cleanup_loop (orphaned tasks)
  └─ _process_pending_terms()     ← NEW
       ├─ Read pending_terms.json
       ├─ If empty or no decided entries → skip (log info)
       ├─ For each entry with status == "approved":
       │   ├─ Generate embedding via NVIDIA NIM API
       │   ├─ Insert into Supabase glossary_terms (status='approved', source='auto_extracted')
       │   └─ Remove from JSON
       ├─ For each entry with status == "rejected":
       │   └─ Remove from JSON
       ├─ Entries with status == "pending" → remain in JSON
       └─ Write updated JSON back to file
```

**Pseudocode**:
```python
async def _process_pending_terms():
    """Process approved/rejected terms on startup."""
    json_path = Path(settings.data_dir) / "pending_terms.json"
    
    if not json_path.exists():
        logger.info("[TermSync] No pending_terms.json found, skipping.")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        terms = json.load(f)
    
    if not terms:
        logger.info("[TermSync] pending_terms.json is empty, skipping.")
        return
    
    approved = [t for t in terms if t["status"] == "approved"]
    rejected = [t for t in terms if t["status"] == "rejected"]
    pending  = [t for t in terms if t["status"] == "pending"]
    
    if not approved and not rejected:
        logger.info(f"[TermSync] {len(pending)} pending terms, none decided yet. Skipping.")
        return
    
    # Process approved terms → generate embeddings and insert to Supabase
    if approved:
        from backend.app.services.rag.embedding_service import NvidiaEmbeddingService
        embedding_svc = NvidiaEmbeddingService()
        
        source_texts = [t["source_term"] for t in approved]
        embeddings = await embedding_svc.embed_batch(source_texts, input_type="passage")
        
        client = get_glossary_store_client()
        for term, emb in zip(approved, embeddings):
            client.table("glossary_terms").insert({
                "source_term": term["source_term"],
                "target_term": term["target_term"],
                "domain": term.get("domain", "general"),
                "source": "auto_extracted",
                "embedding": emb,
                "status": "approved"
            }).execute()
        
        logger.info(f"[TermSync] Inserted {len(approved)} approved term(s) into glossary.")
    
    # Rejected terms → just log
    if rejected:
        logger.info(f"[TermSync] Removed {len(rejected)} rejected term(s).")
    
    # Write back only pending terms
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    logger.info(f"[TermSync] {len(pending)} term(s) still pending review.")
```

### 5.4 Workflow Diagram

```
Translation completes
       │
       ▼
  Extract terms
  (LLM-based)
       │
       ▼
  Append to pending_terms.json
  (status: "pending")
       │
       ▼
  Admin reviews via API ──────────────┬─────────────────┐
  (GET /api/terminology/pending)      │                 │
       │                              │                 │
  POST /approve                 POST /reject       (no action)
  (status→"approved")          (status→"rejected")  (stays "pending")
       │                              │                 │
       ▼                              ▼                 ▼
  ─── Backend Restart ───────────────────────────────────────
       │
       ▼
  _process_pending_terms()
       │
       ├─ approved → embed + insert Supabase → remove from JSON
       ├─ rejected → remove from JSON
       └─ pending → keep in JSON for next review
```

## 6. Graceful Degradation

If RAG retrieval fails (network error, API timeout, empty results):
- **Fallback to existing CSV-based term dictionary** (`build_term_dict()`)
- Log warning but do not block translation
- Ensure zero negative impact on existing translation quality

If startup term processing fails (NVIDIA/Supabase unavailable):
- Log error, keep `pending_terms.json` unchanged
- Terms remain pending until next successful restart
