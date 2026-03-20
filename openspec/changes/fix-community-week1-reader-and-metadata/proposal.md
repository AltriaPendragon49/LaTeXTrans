# Why
- Week 1 already promises a readable paper detail experience with title, authors, abstract, and preview/download.
- Current runtime behavior still leaves some arXiv-backed papers without metadata and some completed papers without a recoverable HTML reader.
- A dedicated fix change keeps the applied Day 5 history intact while restoring the already-promised Week 1 behavior.

## What Changes
- Restore arXiv metadata hydration for title, authors, categories, and source abstract on new and previously-created community papers.
- Restore HTML reader availability for completed papers by recovering missing preview assets from task outputs when possible.
- Restore translated abstract visibility when completed outputs contain a usable translated abstract.
- Upgrade the HTML reader so block math is renderable by the current KaTeX auto-render setup instead of being trapped inside ignored `<pre>` tags.
- Add stable section- and block-level HTML anchors so future highlighting, notes, and agent-on-selection flows have durable DOM attachment points.

## Impact
- Modifies `community-paper-discovery-ui`.
- Modifies `community-paper-intake-api`.
- Depends on `add-community-day-05-week1-e2e-stabilization`.
