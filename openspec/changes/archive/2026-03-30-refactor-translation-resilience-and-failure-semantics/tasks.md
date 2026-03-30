## 1. Implementation
- [x] 1.1 Add bounded retry/backoff behavior for community-agent reasoning provider calls on transient HTTP/network failures.
- [x] 1.2 Add deterministic title-to-arXiv bridge fallback to import/read paper context and auto-start translation when translated content is missing.
- [x] 1.3 Ensure conversation runs only pass conversation-scoped `paper_id` context and never leak paper ids across conversations.

## 2. Verification
- [x] 2.1 Add/refresh backend unit tests for reasoning-provider retry behavior.
- [x] 2.2 Add/refresh frontend conversation tests for conversation-scoped `paper_id` propagation.
- [x] 2.3 Validate agent-first flow remains functional with updated run payload and bridge behavior.

## 3. Rollout Notes
- [x] 3.1 Scope reduced to completed community-agent bridge work only; unfinished translation-core resilience items were intentionally removed from this archive.
