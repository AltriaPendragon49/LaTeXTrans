## Context
- The current paper detail shell already emphasizes reading and keeps an agent workspace nearby, but it does not yet feel like an integrated copilot experience.
- The requested direction is closer to an alphaXiv-style study environment where reading and AI assistance share one workspace.
- The community detail page already has source and translated reading modes, plus agent citations and actions, but those pieces are not yet tied together with explicit anchors and synchronized layout behavior.

## Goals / Non-Goals
- Goals:
  - Make the paper detail page a reading-first dual-pane workspace.
  - Keep the AI copilot persistent and scoped to the current paper.
  - Let assistant citations and actions drive the reader to the relevant paper location.
  - Upgrade between source and translated reading modes softly rather than with abrupt full-page replacement.
- Non-Goals:
  - Do not redesign the homepage or feed in this change.
  - Do not introduce full document annotation or note-sharing systems.
  - Do not add deep research mode in this change.
  - Do not replace the existing standalone conversation workspace for non-paper-specific chats.

## Decisions
- Decision: Keep the paper detail route as the canonical reading workspace.
  - The dual-pane copilot experience lives on the paper detail route rather than opening a separate app shell.
  - The reader remains visually dominant and the copilot stays persistent on the same screen.

- Decision: Scope the copilot state to the active paper.
  - The side-panel copilot for a paper detail session is paper-scoped rather than globally floating across unrelated papers.
  - Moving to another paper starts a new paper-scoped copilot context unless an explicit same-paper conversation is reused.

- Decision: Use stable reader anchors as the linking primitive.
  - Readable paper sections, preview blocks, or rendered segments must expose stable `anchor_id` values.
  - Assistant citations and actions can target those anchors using API payload fields such as `paper_id` and `anchor_id`.
  - Clicking a citation or related action scrolls the reader to that anchor and highlights it.

- Decision: Treat translated readiness as a soft upgrade.
  - If the user is reading source content and translated HTML becomes ready, the UI shows a lightweight upgrade cue and can switch modes without a full route reload.
  - The reader shell, copilot pane, and active chat context remain intact during this upgrade.

- Decision: Use shared client state to coordinate the two panes.
  - The reader selection, active anchor, copilot metadata, and translation readiness state belong in a shared page-level store.
  - This avoids brittle prop-threading and enables scroll/highlight interactions to stay synchronized.

## Risks / Trade-offs
- Stable anchor generation requires a consistent reader segmentation strategy from backend to frontend.
- The dual-pane layout can become cramped on smaller screens if the responsive rules are not explicit.
- Overly aggressive automatic reader switching would feel disorienting; the upgrade behavior must stay soft and reversible.

## Migration Plan
1. Extend the API contracts for reader anchors and agent reference metadata.
2. Refactor the paper detail layout into a dual-pane shell while preserving the existing route.
3. Add anchor-driven reader interactions and soft translation-upgrade behavior.
4. Keep degraded and single-mode reading states valid even when dual-pane features are partially unavailable.

## Open Questions
- None for this change. Larger annotation and note-taking systems are deferred to later changes.
