## Context
The current shell uses a sidebar-first desktop layout that remains visible on narrow screens. Community feed controls, paper detail actions, workflow workbenches, and admin history views all inherit that desktop assumption, which leads to cramped content width and overlapping interaction zones on mobile.

This change needs one consistent responsive model across the whole frontend rather than a series of isolated page patches. The user specifically approved:
- a 4-item mobile bottom navigation
- full-page mobile coverage including admin routes
- mobile default single-column translated reading

## Goals
- Provide one shared mobile shell pattern that applies across the frontend.
- Preserve desktop capability while making narrow-screen routes usable and conflict-free.
- Default paper reading and preview to translated single-column mode on mobile.
- Define responsive behavior by page family so implementation stays consistent.

## Non-Goals
- Re-architect desktop information architecture beyond the responsive shell boundary.
- Add new product capabilities unrelated to responsive behavior.
- Deliver full translated-PDF interaction parity on mobile beyond safe readable fallback behavior already allowed by existing specs.

## Decisions
- Decision: Use a mobile bottom navigation with exactly four primary destinations.
  - Rationale: It removes the narrow-screen left-rail width penalty and keeps first-level navigation in a thumb-reachable zone.
- Decision: Keep desktop sidebar behavior for larger viewports.
  - Rationale: Desktop information density and existing workflows benefit from the current rail model.
- Decision: Treat page responsiveness as page-family templates rather than per-page exceptions.
  - Rationale: This reduces drift and helps all current and future routes follow the same mobile rules.
- Decision: Default narrow-screen paper detail and preview to translated single-column presentation.
  - Rationale: The user explicitly approved translated-first single-column reading for mobile.
- Decision: Move secondary controls and support panes into explicit tabs, drawers, or collapsible regions on mobile.
  - Rationale: Persistent dual panes and dense action rows are the primary source of button conflict and cramped layouts.

## Page-family patterns
### Public browse pages
- Routes: `/`, `/tools`, `/favorites`, `/profile`, `/login`
- Mobile pattern: single-column scroll, compact top bar, bottom navigation, stacked search/filter/action areas

### Reading and preview pages
- Routes: `/paper/:paperId`, `/preview`
- Mobile pattern: single-column translated-first reader by default
- Secondary content: source view, insights, similar content, terminology, and auxiliary metadata move into explicit tabs, drawers, or collapsible sections

### Workflow pages
- Routes: `/translate`, `/processing`
- Mobile pattern: stacked workbench with primary task progression first, advanced configuration and logs below or behind expansion controls
- Primary action rule: start/continue/download controls stay visually obvious and thumb-reachable

### Workspace and admin pages
- Routes: `/workspace/history`, `/workspace/settings`, `/workspace/glossary`, `/admin/curation`, `/admin/curation/tasks`, `/agent`
- Mobile pattern: card lists, stacked forms, expandable details, drawer-style secondary navigation where needed
- Data-density rule: desktop tables and side rails degrade to cards and explicit expansion instead of horizontal squeeze

## Risks / Trade-offs
- Different navigation models between desktop and mobile increase layout branching.
  - Mitigation: centralize shell logic and page-family rules instead of scattering one-off breakpoints.
- Admin pages may need larger structural changes than public pages.
  - Mitigation: treat admin history and conversation as first-class members of the responsive rollout, not follow-up cleanup.
- Existing tests are likely desktop-oriented.
  - Mitigation: add route-level responsive expectations for the shared shell and representative pages in each family.

## Validation approach
- Verify shared shell behavior on narrow screens, including safe-area spacing and bottom-nav persistence.
- Verify paper detail and preview default to translated single-column mobile reading.
- Verify workflow pages keep primary actions reachable without action overlap.
- Verify history/admin pages switch from table compression to card/expansion behavior.

## Open Questions
- None remaining for this proposal. The user approved the navigation model, admin inclusion, responsive route-family approach, and translated-first mobile reading default.
