## Context
A full frontend structural and visual rebuild was requested from Stitch design sources, covering Community Feed, Community Conversation, Paper Detail, and Tools Hub.

## Goals / Non-Goals
- Goals:
  - Match approved Stitch layout intent across desktop/mobile breakpoints.
  - Preserve existing backend/API compatibility and workflow continuity.
  - Keep existing translation and agent flows functional after layout replacement.
- Non-Goals:
  - Backend API/schema redesign.
  - Non-UI feature expansion unrelated to rebuild scope.

## Decisions
- Reuse existing state/data hooks while replacing core page composition and shell layout.
- Prioritize route continuity and interaction parity before visual polishing extras.
- Keep operational settings/actions discoverable via sidebar + Tools Hub partition.

## Risks / Trade-offs
- Risk: regressions in routing or workflow transitions during structural replacement.
  - Mitigation: targeted UI tests and acceptance walkthroughs.
- Risk: component-level style collisions during migration.
  - Mitigation: rebuild-first approach for primary pages and shell containers.

## Migration Plan
1. Replace shell + key page layouts with Stitch-aligned structures.
2. Reconnect existing data/state actions to new UI composition.
3. Verify translation, agent, and reading workflows end-to-end.
4. Archive once acceptance checks pass.
