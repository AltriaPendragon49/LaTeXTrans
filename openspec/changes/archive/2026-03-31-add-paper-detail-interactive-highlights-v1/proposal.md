# Change: Add Paper Detail Interactive Highlights

## Why
Users need a way to persistently annotate papers with colorful highlights and notes to improve their research and reading efficiency. The current selection model is too transient.

## What Changes
- **Persistent Annotations**: Highlights remain visible and recoverable after selection changes, toolbar dismissal, and reader scrolling.
- **Selection Toolbar**: Floating toolbar uses a solid white panel, provides 7 available color entries for highlighting, note input, `Ask AI`, and `取消高亮`.
- **Direct Highlight Interaction**: Clicking a color immediately applies highlight without an extra confirm button.
- **Dismiss + Cancel Flow**: Clicking outside can dismiss the toolbar, while `取消高亮` explicitly removes the corresponding persisted highlight.
- **AI Context Enrichment**: Toolbar note and selected text are pushed into agent context when `Ask AI` is triggered.
- **Hybrid Rendering**: CSS Highlight API + overlay-rect fallback are kept in sync for robust visual persistence across nested scroll containers.

## Impact
- Affected specs: `highlights`
- Affected code:
  - `frontend/src/pages/PaperDetail.tsx`
  - `frontend/src/components/community/PaperDetailWorkspace.tsx`
  - `frontend/src/index.css`
  - `frontend/src/pages/PaperDetail.reader-first.test.tsx`
