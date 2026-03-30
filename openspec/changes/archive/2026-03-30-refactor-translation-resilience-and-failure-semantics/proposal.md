# Change: Community Agent Resilience Bridge (Scoped)

## Why
The original proposal covered a broad translation-resilience refactor, but only the community-agent resilience bridge work has been implemented. This scoped change keeps OpenSpec history accurate and archives only completed behavior.

## What Changes
- Add bounded retry/backoff for community-agent reasoning provider calls on transient HTTP/network failures.
- Add deterministic title-to-arXiv bridge fallback to import/reuse papers, read paper context, and auto-start translation when translated output is missing.
- Ensure conversation runs only send conversation-scoped `paper_id` context and never leak paper ids from other conversations.
- Add and refresh automated tests for the above behavior.

## Impact
- Affected specs:
  - `community-agent-assistant`
  - `web-ui`
- Affected code:
  - `backend/app/services/community_agent/orchestrator.py`
  - `backend/tests/unit/test_community_agent_reasoning_retries.py`
  - `frontend/src/pages/CommunityConversation.tsx`
  - `frontend/src/pages/CommunityConversation.test.tsx`
  - `frontend/src/pages/CommunityFeed.agent-first.test.tsx`
- Consumer impact:
  - Community conversation requests now keep paper context scoped to the active thread.
  - Agent fallback behavior is more deterministic under transient provider failures.
