# Processing Page Balance Design

## Context
The translation processing page currently feels visually unstable on desktop. The content well is too narrow for the available shell width, the left status column is underweighted, and the log panel reads like a tall isolated pillar instead of part of one coherent workbench.

## Goal
Rebalance the `/processing` page so it feels like a stable translation workbench:

- keep live logs as the primary visual area
- make the task status column substantial enough to support the layout
- widen the page so the shell and content proportions feel intentional
- preserve existing task copy, state handling, and responsive behavior

## Approved Direction
Use a log-led workbench layout.

- Widen the page container beyond the current `max-w-5xl`
- Rework the main split into a desktop two-column layout close to `5 : 7`
- Keep the right live-log panel dominant, but tie its height and padding to the left column so the page feels balanced
- Consolidate the left column into a stronger summary stack: task timeline card plus current-status summary card
- Re-align the page header so the title block and cancel/download actions share a cleaner horizontal rhythm

## Constraints
- No new product capability
- No changes to task polling or translation logic
- Avoid introducing new localized strings for this visual pass
- Preserve mobile stacking and existing completion / failure states

## Testing
- Add a regression-oriented page test that verifies the workbench structure renders
- Run the focused processing page test and a production build after implementation

## Self Review
- No placeholders remain
- Scope is limited to the processing page layout and its supporting log container
- Design keeps existing behavior while changing visual proportions only
