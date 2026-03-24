# Why
- The current community agent in `backend/app/services/community_agent_service.py` still relies on regex intent detection and handwritten `if/else` routing.
- That implementation cannot express OpenClaw-style optional skill visibility, model-side query extraction, or a repairable ReAct loop with deterministic final output validation.
- The current external search integration is generic and opaque, while the new paper agent architecture requires a first-class Tavily-backed search skill with explicit request/response normalization.
- The current answer generation path lets the reasoning model produce the final long-form answer directly, which makes validation, consistency checks, and UI formatting less reliable.

# What Changes
- Replace regex intent routing with a typed skill-driven orchestration loop that exposes only visible skills to the planner model.
- Introduce a slot-based finalization contract so the model emits structured answer data and a deterministic formatter renders the user-visible summary.
- Add a generation skill (`compose_academic_answer`) so background explanation / answer synthesis becomes a traced skill step instead of an invisible reasoning side effect.
- Add validator checks for skill visibility, search query quality, intent/action consistency, and citation/action grounding, with one repair attempt before fallback.
- Migrate external search in the new agent path to Tavily-specific configuration and request handling.
- Extend the community agent API and launcher/workspace UI to carry a non-persistent `external_search` toggle.
- Detect the user's question language and steer planner/composer/fallback formatting so Chinese prompts naturally produce Chinese answers and status text.
- Strengthen paper-specific orchestration so arXiv-id questions auto-import missing papers into community, start translation when needed, and ground answers on the imported paper context.
- Upgrade preview HTML generation/rendering so the reading workspace preserves paper title/author metadata, shows figure assets and references reliably, and keeps scrolling isolated to the reader viewport instead of the whole page.
- Require authenticated agent conversations, persist conversation history in Supabase under the signed-in user, and support deleting saved conversations from the conversation workspace.

# Impact
- Affected backend API: `POST /api/community-agent/runs`
- Affected backend service: `backend/app/services/community_agent_service.py`
- New internal backend package: `backend/app/services/community_agent/`
- Affected frontend entry points: `frontend/src/pages/CommunityFeed.tsx`, `frontend/src/pages/CommunityConversation.tsx`
- Affected documentation/specs: `community-agent-assistant`, `web-api`, `web-ui`
- Affected backend API: authenticated community-agent conversation history endpoints
- Affected backend services: preview generation / paper import / translation handoff / conversation persistence
- Affected frontend entry points: `frontend/src/pages/PaperDetail.tsx`, `frontend/src/components/community/PaperDetailWorkspace.tsx`, `frontend/src/components/community/PaperPreviewReader.tsx`
- Affected storage/schema: Supabase conversation tables and RLS policies for user-owned community-agent histories
