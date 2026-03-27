## Context
A full frontend structural and visual rebuild is requested based on 4 newly confirmed Stitch design screens.

## Goals / Non-Goals
- Goals: Match the Stitch design specifications exactly. Ensure responsive behavior across Maximized Reader and Compact Feed states. Maintain existing Backend API compatibility.
- Non-Goals: Refactoring the backend API; changing the foundational database schema, changing the core Vite setup unless necessary.

## Decisions
- Decision: Re-use the existing state management paradigms (stores/api) but heavily refactor or replace Layout components leveraging the new Stitch HTML/CSS DOM structures as the source of truth for the views.
- Alternatives considered: Iteratively migrating old components. Decided against it because a full rebuild locally avoids complicated CSS class namespace collisions and structurally ensures pixel-perfect fidelity with the fresh Stitch specification.

## Risks / Trade-offs
- Risk: Breaking existing user workflows or dropping SSE UI states during the Reactivity refactoring.
- Mitigation: Detailed E2E tests and manual functional workflow reviews after implementing the core layouts to guarantee all previously functional requirements remain intact.

## Migration Plan
The CSS will be updated concurrently with component templates. Developers will handle feature toggling locally until the full UI matches. When deployed, users will just see the improved shell. No structural data changes exist on the backend.
