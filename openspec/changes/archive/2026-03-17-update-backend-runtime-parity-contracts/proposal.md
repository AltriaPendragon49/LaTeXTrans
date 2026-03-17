# Proposal: Update Backend Runtime Parity Contracts

## Description
Record the backend-side runtime, orchestration, compilation, and generic-text-environment recovery behavior that was implemented to align FastAPI task results with the extracted standalone CLI baseline.

## Motivation
- The backend code now contains a concrete set of parity fixes that are not fully reflected in active OpenSpec requirements.
- Recent fixes changed the effective source of truth for backend task execution: bounded task-level LLM concurrency, richer agent-config propagation, retry stagnation short-circuiting, CJK engine preference, and stronger abstract/generic-env recovery.
- Archived compiler/runtime proposals contain historical assumptions that no longer match the current backend behavior. The current code should be documented explicitly so future work does not regress toward those older assumptions.

## Scope
- Backend runtime configuration propagation from the web API into translation orchestration.
- Translation orchestration observability and retry-stagnation short-circuit behavior.
- Generic text environment recovery behavior for abstract-like blocks.
- CJK final-PDF engine selection behavior in tiered compilation.

## Non-Goals
- Introducing new user-facing API endpoints or request schema changes.
- Recording standalone CLI extraction architecture work already covered by `extract-standalone-cli-translation-core`.
- Changing fallback-model or terminology-RAG behavior covered by other active changes.

## Conflict Review
- Active changes `add-fallback-model` and `implement-rag-terminology` are orthogonal and do not describe runtime parity, compilation-engine selection, or env-recovery semantics.
- Archived changes around compiler evolution and multilingual compilation remain historical reference only. This change updates active specs to match the current backend implementation, including current CJK final-engine preference and retry/runtime behavior.

## Impact
- Updates the active specification set so backend behavior is no longer ambiguous.
- Gives future implementers an explicit contract for the fixes already merged into `backend/`.
