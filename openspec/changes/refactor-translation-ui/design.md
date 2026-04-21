# Design: Seamless Workspace UX

## Principles
1. **Minimalism:** Use whitespace instead of borders to define sections.
2. **Seamless Navigation:** Eliminate 'card-in-card' nesting.
3. **Immersive Focus:** The main content should stretch to its bounds naturally and integrate visually with the sidebar background system.

## Trade-offs
- Removing obvious card boundaries might make certain grouped actions (like "Local Upload" drops) less confined; we compensate using subtle background color differences (`bg-[color:var(--px-shell-panel-strong)]` or `tone="glass"`) rather than distinct drop shadows and thick borders.
