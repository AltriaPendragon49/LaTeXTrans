# Proposal: Adaptive Advanced RAG for Terminology Consistency

## Problem Statement
The current translation system generates terminology tables post-translation (mode 2 only) and injects terms from static CSV files. This approach suffers from:
1. **Low recall**: Static CSV glossaries miss domain-specific terms not explicitly listed.
2. **Noise interference**: No relevance ranking means all matched terms are injected regardless of context relevance.
3. **Mode limitation**: Terminology enhancement is restricted to `trans_mode == 2`; modes 0, 1, 3 lack terminology support entirely.

## Proposed Solution
Implement a **three-stage RAG pipeline** ("Query → Hybrid Retrieval → Re-ranking") as specified in the initial task plan §3.1:

1. **Multi-source Knowledge Base**: Store terminology in Supabase PostgreSQL with pgvector for embeddings and tsvector for full-text search. Support ingestion of CSV terminology files and user-defined custom glossaries.
2. **Query Transformation & Hybrid Retrieval**:
   - **Query Transformation**: Use `_extract_text_from_tex` to convert LaTeX to plain text, then extract core terminology keywords via LLM.
   - **Dual-path Retrieval**: Execute **vector search** (Supabase pgvector via NVIDIA NIM embeddings) and **keyword search** (PostgreSQL full-text search / tsvector + BM25-like ranking) in parallel.
3. **Cross-Encoder Re-ranking & Injection**: Use NVIDIA NIM Reranking API to re-rank hybrid retrieval results, select Top-N "golden context" terms, and dynamically inject them into translation prompts as `<Glossary>` blocks.
4. **Universal Mode Enhancement**: Apply RAG terminology retrieval **across all translation modes** (0, 1, 2, 3), replacing the current mode-2-only restriction.
5. **Terminology Auto-Extraction**: After translation, extract new source→target term pairs and save to a pending review table in Supabase.

## Scope
- **Backend**: New `rag/` service module for embedding, retrieval, reranking. Modify `TranslatorAgent` to integrate RAG across all modes.
- **Database**: Supabase PostgreSQL with pgvector extension for terminology storage and vector search. Supabase MCP for schema management.
- **Embedding**: NVIDIA NIM Embedding API (`integrate.api.nvidia.com/v1/embeddings`) — same infrastructure as existing LLM API.
- **Reranking**: NVIDIA NIM Reranking API for Cross-Encoder based re-ranking.
- **Frontend**: Emit matched terms via existing WebSocket progress updates for display in terminology UI.
