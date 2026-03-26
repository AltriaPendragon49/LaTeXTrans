## Context
- The current `community_agent` runtime is a request-scoped single-agent runtime that already supports conversational tool calling, paper-aware context, and deterministic fallback.
- The existing `backend/app/services/community_agent/skills/contracts/*/SKILL.md` files currently act as tool contracts instead of OpenClaw-style instruction skills.
- The community conversation routes are protected by Bearer-token authentication, so the frontend cannot rely on anonymous browser `EventSource` connections for live streaming.

## Goals / Non-Goals
- Goals:
  - Align the meaning of `skill` with OpenClaw-style prompt skills.
  - Introduce true token-level streaming for the final assistant answer.
  - Make translation handoff a background action that does not terminate the current answer.
  - Make backend restart reconciliation deterministic so non-success community-paper state is fully removed and interrupted translations are failed/cleaned automatically.
  - Keep the community assistant a real paper-domain agent without turning the full LaTeX translation kernel into a generic agent runtime.
- Non-Goals:
  - Do not convert `backend/app/services/agents/` into a generic agent platform.
  - Do not introduce multi-agent delegation.
  - Do not implement an async content pool in this change.
  - Do not implement the dual-pane reading UI in this change.
  - Do not implement deep research mode in this change.

## Decisions
- Decision: Split prompt skills from executable tools.
  - Prompt skills remain under `backend/app/services/community_agent/skills/` and only describe when to use a capability, how to reason about it, and how to respond.
  - Executable tools move under `backend/app/services/community_agent/tools/` and define schemas, visibility rules, validation hooks, and execution logic in Python.
  - Alternatives considered:
    - Keep current `skills/contracts/*` as mixed tool-and-skill artifacts. Rejected because it preserves the current semantic mismatch with OpenClaw.
    - Convert everything into prompt-only skills without a dedicated tool registry. Rejected because tool validation and execution need a stable typed backend boundary.

- Decision: Introduce a dedicated skill prompt builder at `backend/app/services/community_agent/skills_runtime.py`.
  - It scans bundled skill packs, filters them by runtime context, builds a concise skill index, and injects selected skill bodies into the planner/final-answer prompts.
  - Default visibility rules:
    - always-visible skills are always injected
    - paper-aware skills are injected when a `paper_id` or paper context exists
    - external-search skills are injected only when `skill_toggles.external_search=true`
  - Alternatives considered:
    - Load every skill body every turn. Rejected because prompt growth would be unnecessary and unstable.
    - Add user-installed dynamic skills in this change. Rejected as out of scope for the foundational refactor.

- Decision: Use a two-phase LLM flow.
  - Phase 1 is non-streaming planner/tool-calling execution.
  - Phase 2 is a separate streaming final-answer request with `stream=True` and Markdown-friendly output.
  - This preserves stable tool-calling while enabling true token streaming.
  - Alternatives considered:
    - Single streaming call for both tool use and final answer. Rejected because authenticated backend streaming plus tool-call reliability would become significantly harder to stabilize.

- Decision: Make `start_translation_kernel` a non-blocking background handoff.
  - The tool still returns `task_id`, status, and action metadata immediately.
  - The runtime records the action and emits status updates, but it must continue the current answer instead of terminating the turn.
  - The final streamed answer prompt explicitly instructs the model to naturally mention that translation is running in the background when relevant.
  - Alternatives considered:
    - Keep the current terminal handoff behavior. Rejected because it breaks conversational continuity.
    - Hide translation status completely. Rejected because the UI still needs user-visible progress context.

- Decision: Use explicit fail-and-cleanup restart reconciliation.
  - Startup/admin reconciliation MUST fail interrupted in-flight tasks and purge community papers in non-success states (`not_started`, `queued`, `processing`, `failed`, `failed_compilation`, `structure_invalid`) while preserving successful papers.
  - Purge MUST delete all paper-related Supabase records that can still reference the failed paper, including `comments`, `reports`, `moderation_actions`, `paper_assets`, `paper_likes`, `paper_favorites`, related `translation_tasks`, and finally `papers`.
  - Purge MUST also delete local task artifacts for every purged task id plus the paper’s `community_papers/<paper_id>` folder.
  - Interrupted `translation_tasks` in `queued`, `pending`, or `processing` state MUST be marked `failed` on startup/admin cleanup and corresponding local artifacts MUST be cleaned.
  - Related `papers` rows in `queued`/`processing` MUST be updated to `failed` when their selected task is interrupted.
  - Triggered automatically on backend startup and via authenticated `POST /api/admin/cleanup` endpoint.

- Decision: Bridge explicit paper lookup to translation handoff.
  - When users explicitly query by arXiv id or exact paper title and the matched community paper is not translated-ready, runtime MUST bridge search hits to `read_paper_context` + `start_translation_kernel`.
  - When users issue a title-only query and community search has no hit, runtime MUST resolve arXiv id from title metadata and run `import_arxiv_paper` -> `read_paper_context` -> `start_translation_kernel` deterministically.
  - The bridge MUST run even when the planner already produced a direct conversational response, so translation startup does not depend on planner randomness.

- Decision: Refined Sidebar and Reader layout.
  - Sidebar starts in collapsed state (`defaultOpen={false}`) to maximize initial workspace.
  - Moved `SidebarTrigger` into the `AppSidebar` header for a consolidated control scheme.
  - Increased `PaperDetailWorkspace` reader panel height to `h-[calc(140dvh-160px)]` to allow immersive reading while maintaining page-level scrollability.

- Decision: Add a fast first-answer path when a paper has no translated abstract yet.
  - When a paper was newly imported or loaded and translated reader-ready content is unavailable, the runtime may ground an immediate answer on `title`, `abstract_raw`, and a lightweight preview translation or preview grounding helper.
  - This helper is internal and does not become a user-callable tool.
  - Alternatives considered:
    - Wait for the translation kernel to finish. Rejected because it would violate the non-blocking conversational goal.

- Decision: Use authenticated fetch-stream on the frontend instead of browser-native `EventSource`.
  - The backend still emits `text/event-stream`.
  - The frontend consumes the stream with authenticated `fetch`, `ReadableStream`, and an SSE frame parser so Bearer auth continues to work.
  - Alternatives considered:
    - Anonymous `EventSource`. Rejected because the route requires auth.
    - WebSockets. Rejected because SSE is sufficient for this one-way streaming foundation and fits the requested scope.

## Risks / Trade-offs
- Skill/tool separation changes the structure of `backend/app/services/community_agent/` and may require careful runtime migration.
- Live SSE introduces more backend/frontend coordination complexity than the current request/response model.
- Non-blocking translation handoff introduces more nuanced UI states because a single answer turn may now include both content deltas and background work status.
- The two-phase LLM design is slightly less “pure” than a single agent loop, but it significantly reduces tool-calling instability while enabling token streaming.
- Restart reconciliation now performs more startup work because it purges cloud-side paper artifacts and fails/cleans interrupted in-flight translations, but the cost is bounded to active/non-success community-paper rows.

## Migration Plan
1. Keep an explicit blocking execution mode as a compatibility and regression path.
2. Move the community conversation page to async streaming mode while preserving the existing result snapshot API.
3. Remove `compose_academic_answer` from the primary runtime path after the streaming final-answer phase is in place.
4. Migrate the current `skills/contracts/*` structure into prompt skills plus a dedicated tool registry.
5. Reconcile failed paper artifacts and fail/clean interrupted translation tasks during startup before serving traffic.

## Open Questions
- None for this change. Follow-up scope is deferred to future changes.
