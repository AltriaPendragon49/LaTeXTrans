## 1. OpenSpec
- [x] 1.1 Add proposal, tasks, and design for `refactor-community-agent-openclaw-streaming-foundation`
- [x] 1.2 Add delta specs for `community-agent-assistant`, `web-api`, and `web-ui`
- [x] 1.3 Validate with `openspec validate refactor-community-agent-openclaw-streaming-foundation --strict --no-interactive`

## 2. Backend runtime foundation
- [x] 2.1 Split prompt skills from executable tools in `backend/app/services/community_agent/`
- [x] 2.2 Add skill prompt loader and runtime selection rules
- [x] 2.3 Add tool registry and migrate existing paper-domain tool implementations
- [x] 2.4 Refactor orchestrator into plan/tools/final-stream phases
- [x] 2.5 Remove `compose_academic_answer` from the primary answer path

## 3. Streaming run lifecycle
- [x] 3.1 Add async run creation mode with accepted response payload
- [x] 3.2 Convert `/runs/{run_id}/events` into authenticated live SSE
- [x] 3.3 Add ordered stream events for assistant deltas, tool lifecycle, citations, actions, and completion
- [x] 3.4 Preserve final run snapshot retrieval via `/runs/{run_id}`

## 4. Non-blocking translation handoff
- [x] 4.1 Change translation handoff so it does not terminate the current answer
- [x] 4.2 Add immediate grounded first-answer path from raw metadata/abstract evidence
- [x] 4.3 Emit translation task/action metadata during the same streamed answer

## 5. Frontend streaming conversation
- [x] 5.1 Add authenticated SSE/fetch-stream client for community agent runs
- [x] 5.2 Render running assistant turns token by token in `CommunityConversation`
- [x] 5.3 Hydrate citations, tool trace, and actions incrementally
- [x] 5.4 Persist final assistant turn after stream completion
- [x] 5.5 Keep external search toggle behavior unchanged

## 6. Tests
- [x] 6.1 Add backend tests for skill prompt loading and tool registry separation
- [x] 6.2 Add backend tests for async accepted runs and live stream event ordering
- [x] 6.3 Add backend tests for non-blocking translation handoff and immediate first answer
- [x] 6.4 Add frontend tests for streaming chat rendering and metadata hydration
- [x] 6.5 Add acceptance coverage for Chinese-language streaming and auth-protected stream access

## 7. Post-acceptance robustness
- [x] 7.1 Refine `PaperDetailWorkspace.tsx` reader panel height to `h-[calc(140dvh-160px)]`
- [x] 7.2 Remove duplicate streaming-thinking panel and legacy `tool_trace` badges in `CommunityConversation.tsx`
- [x] 7.3 Add startup/admin cleanup flow that purges non-success papers and related artifacts
- [x] 7.4 Refactor workspace sidebar to default collapsed (`defaultOpen={false}`) and move `SidebarTrigger` to `AppSidebar`
- [x] 7.5 Add `POST /api/admin/cleanup` endpoint for manual reconciliation

## 8. Restart recovery hardening follow-up
- [x] 8.1 Purge non-success community papers from related Supabase tables plus local artifacts
- [x] 8.2 Add TDD coverage for cleanup scope (`comments`, `reports`, `moderation_actions`, `paper_assets`, reactions, and translation artifacts)
- [x] 8.3 Fail interrupted in-flight translation tasks (`queued`/`pending`/`processing`) on restart
- [x] 8.4 Handle `asyncio.CancelledError` in translation runtime and persist terminal failed state
- [x] 8.5 Validate failover with browser acceptance and Supabase verification
- [x] 8.6 Bridge explicit arXiv-id and exact-title lookup hits to translation start when translated version is missing
- [x] 8.7 Add title-only miss fallback (`resolve arXiv -> import -> auto-translate`) and cover with unit tests

## 9. Fixture hygiene
- [x] 9.1 Remove unrelated community-paper fixture records (success/failed test artifacts) from Supabase and local storage

## Evidence map for completed items
- 1.1 Evidence: `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/proposal.md`, `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/design.md`, `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/tasks.md`.
- 1.2 Evidence: `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/specs/community-agent-assistant/spec.md`, `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/specs/web-api/spec.md`, `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/specs/web-ui/spec.md`.
- 1.3 Evidence: strict validate command recorded and rerun in this archive-gate pass.
- 2.1 Evidence: skill/tool separation under `backend/app/services/community_agent/skills/` and `backend/app/services/community_agent/tools/`.
- 2.2 Evidence: `backend/app/services/community_agent/skills_runtime.py`; tests in `backend/tests/unit/test_community_agent_skill_runtime.py`.
- 2.3 Evidence: `backend/app/services/community_agent/tools/base.py` and registry exports in `backend/app/services/community_agent/tools/__init__.py`.
- 2.4 Evidence: planner + final-stream orchestration in `backend/app/services/community_agent/orchestrator.py`.
- 2.5 Evidence: excluded from runtime-visible skills in `backend/app/services/community_agent/skills_runtime.py`; test assertion in `backend/tests/unit/test_community_agent_skill_runtime.py`.
- 3.1 Evidence: async accepted mode in `backend/app/services/community_agent_service.py` and `backend/app/api/routes/community_agent.py`; tests in `backend/tests/unit/test_community_agent_runs_api.py`.
- 3.2 Evidence: authenticated SSE route in `backend/app/api/routes/community_agent.py`; auth-gate tests in `backend/tests/unit/test_community_agent_runs_api.py`.
- 3.3 Evidence: ordered stream event publishing in `backend/app/services/community_agent_service.py`; ordering tests in `backend/tests/unit/test_community_agent_streaming_foundation.py`.
- 3.4 Evidence: run snapshot retrieval in `backend/app/api/routes/community_agent.py` + `backend/app/services/community_agent_service.py`.
- 4.1 Evidence: non-terminal translation handoff flow in `backend/app/services/community_agent/orchestrator.py`; behavior tests in `backend/tests/unit/test_community_agent_streaming_foundation.py`.
- 4.2 Evidence: first-answer grounding fallback in `backend/app/services/community_agent/orchestrator.py`; tests in `backend/tests/unit/test_community_agent_runtime.py`.
- 4.3 Evidence: translation action metadata emission in `backend/app/services/community_agent/orchestrator.py`; tests in `backend/tests/unit/test_community_agent_service.py`.
- 5.1 Evidence: authenticated fetch-stream client in `frontend/src/lib/community-api.ts`.
- 5.2 Evidence: incremental render state in `frontend/src/pages/CommunityConversation.tsx`.
- 5.3 Evidence: stream metadata hydration handlers in `frontend/src/pages/CommunityConversation.tsx`.
- 5.4 Evidence: final turn persistence in `frontend/src/pages/CommunityConversation.tsx`.
- 5.5 Evidence: toggle pass-through in `frontend/src/pages/CommunityFeed.tsx` and `frontend/src/pages/CommunityConversation.tsx`.
- 6.1 Evidence: `backend/tests/unit/test_community_agent_skill_runtime.py`.
- 6.2 Evidence: `backend/tests/unit/test_community_agent_streaming_foundation.py`, `backend/tests/unit/test_community_agent_runs_api.py`.
- 6.3 Evidence: `backend/tests/unit/test_community_agent_runtime.py`, `backend/tests/unit/test_community_agent_streaming_foundation.py`.
- 6.4 Evidence: `frontend/src/pages/CommunityConversation.test.tsx`.
- 6.5 Evidence: acceptance notes and walkthrough plus authenticated stream tests (`backend/tests/unit/test_community_agent_runs_api.py`).
- 7.1 Evidence: `frontend/src/components/community/PaperDetailWorkspace.tsx`, `frontend/src/pages/PaperDetail.reader-first.test.tsx`.
- 7.2 Evidence: legacy panel cleanup in `frontend/src/pages/CommunityConversation.tsx` (single streaming-thinking panel path).
- 7.3 Evidence: cleanup orchestration in `backend/app/main.py`; coverage in `backend/tests/unit/test_restart_recovery_cleanup.py`.
- 7.4 Evidence: `frontend/src/layout.tsx` (`defaultOpen={false}`) and `frontend/src/components/app-sidebar.tsx` (`SidebarTrigger` in sidebar header).
- 7.5 Evidence: `POST /api/admin/cleanup` in `backend/app/main.py`; tests in `backend/tests/unit/test_admin_cleanup_api.py`.
- 8.1 Evidence: purge coverage logic in `backend/app/main.py`; tests in `backend/tests/unit/test_restart_recovery_cleanup.py`.
- 8.2 Evidence: cleanup TDD cases in `backend/tests/unit/test_restart_recovery_cleanup.py`.
- 8.3 Evidence: interrupted-task failover in `backend/app/main.py`; tests in `backend/tests/unit/test_restart_recovery_cleanup.py`.
- 8.4 Evidence: `CancelledError` handling in `backend/app/api/routes/translate.py`; tests in `backend/tests/unit/test_restart_recovery_cleanup.py`.
- 8.5 Evidence: acceptance verification recorded in `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/walkthrough.md`.
- 8.6 Evidence: explicit id/title bridge logic and tests in `backend/tests/unit/test_community_agent_service.py`.
- 8.7 Evidence: title-only fallback flow and tests in `backend/tests/unit/test_community_agent_service.py`.
- 9.1 Evidence: fixture cleanup summary in `openspec/changes/refactor-community-agent-openclaw-streaming-foundation/walkthrough.md`.
