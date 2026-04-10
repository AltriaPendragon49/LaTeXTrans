## Context
- Paper detail currently has high-quality interactions in HTML reader mode, while translated PDF mode is primarily a viewing path.
- Existing reader interactions are DOM-range/anchor driven and assume HTML structure.
- We need translated PDF mode to reach interaction parity without regressing current HTML behavior.

## Goals / Non-Goals
- Goals:
  - Enable translated-PDF in-reader selection context for copilot grounding.
  - Bring highlight/note/jump behavior in translated-PDF mode to parity level with HTML mode.
  - Ensure API contracts expose stable metadata for PDF location and navigation.
- Non-Goals:
  - Do not redesign the entire paper-detail visual layout in this change.
  - Do not change non-paper global conversation routing behavior.
  - Do not require first-iteration collaborative annotations unless explicitly chosen.

## Confirmed Decisions
- Decision 1: Rendering engine for translated PDF
  - Adopt an interactive PDF rendering layer to support deterministic selection/highlight/navigation.

- Decision 2: Locator mapping source
  - Use persisted locator mapping generated during asset preparation.

- Decision 3: Annotation persistence
  - Use local/session state in first iteration.

- Decision 4: Rollout
  - Ship full translated-PDF parity in a single release.

- Decision 5: Unresolved locator fallback UX
  - Auto-switch to translated HTML mode when translated-PDF locator resolution fails.

- Decision 6: First-release platform scope
  - Desktop-first parity in first release; mobile uses compatibility fallback behavior.

## Risks / Trade-offs
- Runtime-only locator matching can produce unstable jumps on long equations/tables and multi-column pages.
- Full parity without staged rollout increases regression risk for existing HTML reader interactions.
- Server-side annotation persistence in v1 increases schema/API complexity and testing surface.

## Migration Plan
1. Ship API metadata and reader contract upgrades behind compatibility-safe fields.
2. Implement translated-PDF interactive reader (selection, Ask AI, highlight, notes, navigation) in the same release branch.
3. Add fallback handling for unresolved locators.
4. Run cross-mode regression (source/html/translated_pdf) and release only when full parity acceptance passes.

## Open Questions
- None
