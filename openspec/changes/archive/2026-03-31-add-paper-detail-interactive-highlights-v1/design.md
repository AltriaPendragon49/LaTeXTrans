# Design: Interactive Highlights and Toolbar

In the Paper Detail page, selection context is a core user action. To avoid the selection being "discarded" immediately after an AI call, we use the `CSS Custom Highlight API`.

## State Architecture
- `annotations`: Array of `{ id, range, color, note, ... }`.
- `readerSelection`: A special "active draft" annotation tied to the mouse selection.

## Rendering
A single `useEffect` iterates over both `annotations` and `readerSelection` every time the state changes, registering ranges into `CSS.highlights`. This is more performant than adding wrapping `<span>` tags for each highlight.

To avoid visual loss in long documents and nested scrollers:
- highlight ranges are revalidated on every recompute (`hasPersistableRange` + text fallback rebuild);
- absolute overlay rects are recalculated each frame trigger and rendered as fallback;
- recompute is triggered by:
  - reader root scroll;
  - nested translated preview viewport scroll (`paper-preview-viewport`);
  - panel/document scroll capture;
  - viewport resize.

## Toolbar Design
The toolbar is fixed-positioned based on the selection's bounding box.
It uses a solid white background with high-contrast text for readability.
Color circles are implemented with `highlight` names matching `::highlight(paper-annotation-<color>)`.
Interaction model:
- click color => immediate highlight persistence;
- no separate `Highlight` button;
- keep `取消高亮` as explicit undo;
- outside click dismisses toolbar without silently deleting persisted highlights.

## API Integration
The "Ask AI" button in the toolbar directly updates the `agentContext` state, which the side chat panel listens to. It also prepopulates the `agentInput` if a note was typed in the toolbar.
