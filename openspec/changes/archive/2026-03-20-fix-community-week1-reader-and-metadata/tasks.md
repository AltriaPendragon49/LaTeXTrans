## 1. Scope Confirmation
- [x] 1.1 Confirm title/authors/abstract/preview are Week 1 commitments rather than Day 6+ features.
- [x] 1.2 Keep Day 6-10 interaction, notification, moderation, and hot-feed scope unchanged.

## 2. TDD
- [x] 2.1 Add failing backend tests for arXiv metadata hydration on submit/detail.
- [x] 2.2 Add failing backend tests for preview asset recovery from completed outputs.
- [x] 2.3 Add failing backend tests for translated abstract recovery when output contains a translated abstract.

## 3. Implementation
- [x] 3.1 Restore arXiv metadata population for new paper submit and lazy repair for old paper detail reads.
- [x] 3.2 Restore readable HTML preview recovery for completed community papers.
- [x] 3.3 Restore detail payload normalization so completed assets win over stale fallback metadata.

## 4. Validation
- [x] 4.1 Run `openspec validate fix-community-week1-reader-and-metadata --strict --no-interactive`.
- [x] 4.2 Run targeted backend tests covering submit, detail, preview, and Week 1 main path.
- [x] 4.3 Write a short delivery note with the acceptance checklist.

## 5. Reader Optimization Round 2
- [x] 5.1 Add failing tests for rich reader blocks and stale translated-abstract repair.
- [x] 5.2 Upgrade preview generation to semantic HTML lists, tables, references, and inline image figures when source assets exist.
- [x] 5.3 Improve detail-page abstract repair so stale English placeholders can be replaced from completed translation output.
- [x] 5.4 Re-run real browser validation on local sample papers and sync the delivery note with observed results.

## 6. Reader Interaction Foundation
- [x] 6.1 Add failing tests for KaTeX-compatible block math rendering and stable section/block anchors.
- [x] 6.2 Replace ignored `<pre>` math wrappers with reader-safe block math containers and expand frontend KaTeX delimiters for LaTeX environments.
- [x] 6.3 Emit stable `data-section-id` and `data-block-id` anchors across the generated HTML reader blocks.
- [x] 6.4 Re-run browser validation to confirm block math renders and anchors exist in the live DOM.

## 7. Reader Fidelity Round 3
- [x] 7.1 Add failing tests for PDF-backed figure rasterization and inline command/prose cleanup.
- [x] 7.2 Render local PDF figure assets inline when the runtime can rasterize them.
- [x] 7.3 Normalize inline LaTeX command examples so prose no longer leaks helper wrappers and raw command noise.
- [x] 7.4 Re-run browser validation against local sample papers and compare remaining gaps with AlphaXiv.

## 8. Reader Fidelity Round 4
- [x] 8.1 Add failing tests for detail-page download handoff and subsection/command-block rendering.
- [x] 8.2 Make detail-page translated PDF downloads resolve against the API origin and recover missing translated assets from completed outputs.
- [x] 8.3 Render subsection walkthroughs and centered command examples as rich HTML reader blocks instead of raw LaTeX dumps.
- [x] 8.4 Re-run browser validation on live sample papers for download behavior and the “system deployment / experiment setup” sections.

## 9. Reader Fidelity Round 5
- [x] 9.1 Add failing tests for complex result tables, clickable publication links, and aligned display equations.
- [x] 9.2 Normalize `multirow` / `multicolumn` / `resizebox`-style LaTeX tables into readable HTML tables.
- [x] 9.3 Convert normalized URL text and footnote-style publication links into clickable anchors in the HTML reader.
- [x] 9.4 Re-run browser validation on live sample papers for tables, links, and equation rendering quality.

## 10. Reader Fidelity Round 6
- [x] 10.1 Add failing tests for nested subheading cleanup and detail-page split reader/workspace layout.
- [x] 10.2 Normalize `\paragraph{}` / `\subsection{}` nesting, `algorithm*` blocks, `\textsubscript{}` tables, and other inline command residue into reader-safe HTML.
- [x] 10.3 Refactor `PaperDetail` into a fixed-height split layout with an internal-scroll HTML reader pane, a right-side workspace pane, and metadata/actions moved below.
- [x] 10.4 Re-run browser validation on the live Week 1 route, confirm no raw `\paragraph` / `\PARR` / `\hdashline` / `\textsubscript` / algorithm markers remain, and pass `npm run i18n:check`.

## 11. Reader Fidelity Round 7
- [x] 11.1 Add failing tests for dominant reader sizing, single-render math presentation, malformed inline-math cleanup, and scholarly column-mode fallback.
- [x] 11.2 Import the full KaTeX stylesheet and remove duplicate raw formula presentation so rendered math appears once.
- [x] 11.3 Expand backend cleanup for malformed inline math in captions/prose and add a scholarly HTML column fallback for wide-screen reading.
- [x] 11.4 Re-run browser validation on the affected live papers and confirm the reader now dominates the layout, broken `$s_c^{2D` text is gone, and wide-screen paper flow is closer to AlphaXiv.

## 12. Reader Fidelity Round 8
- [x] 12.1 Add failing tests for multiline equation stitching, figure-caption formatting cleanup, bibliography command cleanup, and root-scrollbar containment.
- [x] 12.2 Repair preview generation so split display equations, figure captions like `\textbf{...}`, and bibliography helpers such as `\newblock`, `\emph`, and `\natexlab` render as readable scholarly prose instead of raw LaTeX.
- [x] 12.3 Remove the reader-wide horizontal scrollbar while preserving local overflow for figures and tables, and continue refining the paper-like desktop layout toward an AlphaXiv-style reading surface.
- [x] 12.4 Re-run browser validation on the affected live papers, confirm the second paper no longer leaks the reported equation/caption/reference artifacts, and confirm only local figure/table scrollers remain.

## 13. Reader Fidelity Round 9
- [x] 13.1 Add failing tests for bibliography cross-reference linking, richer detail-header metadata, translated-PDF unavailability messaging, and reader table expansion affordances.
- [x] 13.2 Preserve section / figure / bibliography targets in preview HTML, add external bibliography links, and stop stale section labels from being downgraded to block-only anchors.
- [x] 13.3 Move detail metadata into the header chip row, disable repeat translation for completed papers, surface a friendly translated-PDF failure message, and add reader-side table expansion plus internal anchor scrolling.
- [x] 13.4 Re-run targeted backend/frontend validation, pass `npm run i18n:check`, and spot-check the live detail route for header/action behavior.
