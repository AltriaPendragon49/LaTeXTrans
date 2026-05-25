# Implementation Plan: Optional RAG Terminology Tooling

This supporting plan mirrors `tasks.md` and exists only to explain implementation order. `tasks.md` remains the authoritative checklist.

## Phase 1: Data Foundation
- Add MySQL terminology tables and indexes.
- Add repository methods for status transitions and retrieval filters.
- Add admin-safe review operations.

## Phase 2: Vector Foundation
- Add Milvus configuration and connection wrapper.
- Add embedding client.
- Upsert approved terms into the Milvus collection.
- Keep MySQL as the source of truth and Milvus as a derived retrieval index.

## Phase 3: Retrieval Pipeline
- Query-transform LaTeX/plain text chunks.
- Retrieve keyword candidates from MySQL.
- Retrieve semantic candidates from Milvus.
- Merge, deduplicate, prioritize, rerank, and format Top-N glossary terms.

## Phase 4: Optional Translation Tool Integration
- Add an explicit RAG terminology toggle.
- Keep default translation behavior unchanged when the toggle is off.
- Inject glossary terms only when the toggle is on and retrieval succeeds.
- Record matched terms for UI and evaluation.
- Surface the personal glossary workspace in `tools-hub` and keep its data owner-scoped to the current user.

## Phase 5: Review And Evaluation
- Auto-extract terminology pairs from opted-in translation outputs.
- Store extracted pairs as `pending_review`.
- Add admin approval/rejection endpoints and UI.
- Add tests and graduation-design evaluation artifacts comparing baseline and RAG-enabled runs.

## Verification
- `openspec validate implement-rag-terminology --strict --no-interactive`
- Backend unit tests for repositories and RAG services.
- API route tests for auth and review transitions.
- Integration test for an opted-in RAG terminology translation-tool run.
