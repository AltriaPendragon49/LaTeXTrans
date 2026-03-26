# Change: Refactor community agent into an OpenClaw-style streaming foundation

## Why
- The current community agent is already a lightweight real agent, but its `skill` layer still behaves like executable tool contracts instead of OpenClaw-style instruction capability packs.
- The current conversational runtime returns natural answers, but it still does not provide true token-level streaming for the final assistant response.
- Translation handoff still interrupts conversational continuity and often collapses the turn into a terminal “translation started” style reply.
- Backend restart reconciliation is still incomplete: purgeable community-paper records are not fully removed from Supabase, and interrupted translation work can remain in a non-terminal state.
- We need to upgrade the foundation first so later changes can build an async content pool, dual-pane reading workspace, and deep research mode on top of a stronger runtime.

## What Changes
- Refactor the community agent skill system toward an OpenClaw-style model where `skill` only defines behavior guidance and tool registration/execution is managed separately.
- Upgrade the community agent run API to support authenticated SSE-based live streaming events.
- Change final answer generation to Markdown-friendly token streaming while preserving the existing paper-domain tool loop.
- Make translation handoff a background asynchronous action that does not terminate the current answer.
- Preserve citations, tool trace, provider state, actions, and saved conversations while introducing the new runtime foundation.
- Harden restart reconciliation so non-success community-paper artifacts (`not_started`, `queued`, `processing`, `failed`, `failed_compilation`, `structure_invalid`) are removed across local disk and all paper-related Supabase tables, while successful papers remain intact.
- Change restart handling for in-flight translation tasks to deterministic fail-and-cleanup semantics so interrupted work becomes terminal (`failed`) instead of staying stuck.
- Add deterministic paper-lookup bridging so explicit arXiv-id and exact-title queries both check existing translated community paper state and auto-start translation when missing.
- Add title-only fallback resolution (community miss -> arXiv title metadata match -> import -> translation start) so planner variance cannot skip translation kickoff.

## Impact
- Affected specs: `community-agent-assistant`, `web-api`, `web-ui`
- Affected backend:
  - `backend/app/services/community_agent/`
  - `backend/app/services/community_agent_service.py`
  - `backend/app/api/routes/community_agent.py`
  - `backend/app/api/routes/translate.py`
  - `backend/app/services/paper_service.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/main.py`
- Affected frontend:
  - `frontend/src/pages/CommunityConversation.tsx`
  - `frontend/src/lib/community-api.ts`
  - `frontend/src/types/community.ts`
- Follow-up changes required later:
  - async content pool
  - dual-pane reading workspace
  - deep research mode
