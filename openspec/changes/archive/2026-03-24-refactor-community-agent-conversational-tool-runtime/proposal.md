# Why
- The current community paper agent is implemented as a planner/finalize state machine in `backend/app/services/community_agent/orchestrator.py`.
- That design forces the LLM to behave like a JSON-emitting workflow controller instead of a normal conversational assistant.
- The current user experience therefore looks like rendered summary cards rather than a real paper copilot that can chat naturally and invoke domain skills only when needed.
- We need an alphaXiv-like assistant: a general conversational agent that answers naturally, uses paper-domain tools opportunistically, preserves citations/actions/tool trace, and still supports robust fallbacks.

# What Changes
- Replace the slot/finalize orchestration loop with an OpenAI-compatible conversational tool-calling runtime.
- Keep the existing paper-domain skills (`community_search_papers`, `external_tavily_search`, `read_paper_context`, `import_arxiv_paper`, `start_translation_kernel`) as visible tools and remove `compose_academic_answer` from the required answer path.
- Return a natural assistant message as the primary run output, while preserving backward compatibility for existing `summary` consumers during the migration.
- Update the conversation UI so assistant turns render as normal chat messages instead of synthetic structured summary sections/cards.
- Preserve paper actions, citations, tool trace, language alignment, arXiv auto-import, and translation handoff behavior in the new runtime.
- Validate the change through TDD: backend unit tests, frontend unit tests, OpenSpec validation, and browser acceptance on local backend `9001` + frontend `5173`.

# Impact
- Affected backend runtime: `backend/app/services/community_agent/`
- Affected backend service/API: `backend/app/services/community_agent_service.py`, `backend/app/api/routes/community_agent.py`
- Affected frontend conversation UI: `frontend/src/pages/CommunityConversation.tsx`, `frontend/src/components/community/PaperDetailWorkspace.tsx`, related types/api clients/tests
- Affected specs: `community-agent-assistant`, `web-api`, `web-ui`
- This change supersedes the slot/finalize-centric assumptions introduced by `refactor-community-agent-skill-react-orchestrator`
