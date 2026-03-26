# Walkthrough: Community Agent Streaming Foundation Hardening

This walkthrough summarizes what was delivered in `refactor-community-agent-openclaw-streaming-foundation`, with emphasis on streaming behavior, restart cleanup, and archive readiness.

## 1. Runtime foundation changes

- Split prompt skills from executable tools.
- Added dedicated skill prompt assembly and visibility rules.
- Added tool registry modules for community search, paper import, paper context read, translation handoff, and external search.
- Refactored orchestrator flow into planner/tool phase plus final streaming answer phase.

Primary implementation files:
- `backend/app/services/community_agent/orchestrator.py`
- `backend/app/services/community_agent/skills_runtime.py`
- `backend/app/services/community_agent/tools/base.py`
- `backend/app/services/community_agent/tools/community_search.py`
- `backend/app/services/community_agent/tools/import_arxiv_paper.py`
- `backend/app/services/community_agent/tools/read_paper_context.py`
- `backend/app/services/community_agent/tools/start_translation_kernel.py`

## 2. Async run lifecycle and authenticated SSE

- Added async run creation with accepted payload (`run_id`, `stream_url`, `result_url`).
- Converted run event endpoint to authenticated SSE.
- Added stable ordered stream events (`status`, `assistant_delta`, `tool_start`, `tool_result`, `citation`, `action`, `complete`).
- Added missing-run boundary handling so unknown `run_id` is returned as controlled failure (`404` pre-check; `failed` stream event fallback).

Primary implementation files:
- `backend/app/api/routes/community_agent.py`
- `backend/app/services/community_agent_service.py`

Primary tests:
- `backend/tests/unit/test_community_agent_runs_api.py`
- `backend/tests/unit/test_community_agent_streaming_foundation.py`

## 3. Non-blocking translation handoff

- Translation kickoff no longer terminates the current conversational answer.
- Runtime can provide immediate grounded first answer using available metadata while translation runs in background.
- Action payload (`paper_id`, `task_id`) remains available for UI navigation and progress linking.

Primary implementation files:
- `backend/app/services/community_agent/orchestrator.py`
- `backend/app/services/community_agent/skills/start_translation_kernel.py`

Primary tests:
- `backend/tests/unit/test_community_agent_service.py`
- `backend/tests/unit/test_community_agent_runtime.py`
- `backend/tests/unit/test_community_agent_streaming_foundation.py`

## 4. Frontend streaming conversation and workspace updates

- Added authenticated fetch-based SSE stream consumption.
- Assistant message now renders incrementally token-by-token in conversation.
- Tool traces, citations, and action metadata hydrate during the same stream.
- Reader workspace and sidebar behavior aligned with post-acceptance UX tasks.

Primary implementation files:
- `frontend/src/lib/community-api.ts`
- `frontend/src/pages/CommunityConversation.tsx`
- `frontend/src/pages/CommunityFeed.tsx`
- `frontend/src/components/community/PaperDetailWorkspace.tsx`
- `frontend/src/components/app-sidebar.tsx`
- `frontend/src/layout.tsx`

Primary tests:
- `frontend/src/pages/CommunityConversation.test.tsx`
- `frontend/src/pages/PaperDetail.reader-first.test.tsx`
- `frontend/src/pages/PaperDetail.test.tsx`

## 5. Restart cleanup and admin reconciliation

- Startup/admin cleanup now purges non-success community-paper artifacts across related Supabase tables and local artifacts.
- Added authenticated admin endpoint for manual reconciliation.
- Translation interruption handling now persists controlled terminal state for restart interruption paths.

Primary implementation files:
- `backend/app/main.py`
- `backend/app/api/routes/translate.py`
- `backend/app/services/paper_service.py`

Primary tests:
- `backend/tests/unit/test_restart_recovery_cleanup.py`
- `backend/tests/unit/test_admin_cleanup_api.py`

## 6. Validation status

Required archive-gate commands are tracked and executed as part of this pre-archive pass:
- OpenSpec strict validate for this change.
- Targeted backend unit test suite for community-agent foundation.
- Targeted frontend tests.
- Frontend production build.

A final `openspec archive ...` is only valid after deployment and after the branch is narrowed to this change content only.
