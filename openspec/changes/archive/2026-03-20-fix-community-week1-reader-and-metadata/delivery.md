# Community Week 1 Reader + Metadata Fix Delivery

## What changed
- Restored arXiv metadata enrichment on submit and added lazy repair on detail reads, so Week 1 papers can recover `title`, `authors`, `categories`, `abstract_raw`, and `abstract_translated` from persisted outputs.
- Kept preview recovery active for completed papers and expanded it to rebuild from disk when runtime task memory or stale asset rows are missing.
- Upgraded preview generation from raw LaTeX fallback blocks to richer HTML blocks: semantic lists, semantic tables, bibliography lists, inline figures, PDF-backed figure rasterization, stable reader anchors, and clickable publication links.
- Added cleanup passes for split display equations, nested `\paragraph{}` / `\subsection{}` chains, `algorithm*` environments, `\textsubscript{}` tables, `\hdashline`, `\multirow`, malformed captions, bibliography helper commands, and dangling inline math so they no longer leak into the live DOM.
- Bumped the preview payload to `reader-v12`, extended stale-preview detection, and fixed the detail-route bridge so old `preview_html` assets are withheld and regenerated instead of being inlined into the page shell.
- Refactored `frontend/src/pages/PaperDetail.tsx` into a larger split reading layout: the HTML reader lives in a fixed-height pane with its own scroll bar, the reader pane takes the dominant share of the top workspace, and the right-side workspace pane remains available for future notes / agent workflows.
- Updated `frontend/src/components/community/PaperPreviewReader.tsx` so block and inline math are pre-rendered into KaTeX HTML before injection, avoiding runtime timing gaps and removing the remaining raw-math presentation.
- Shifted the reader surface toward a wider AlphaXiv-style single-column article flow while preserving local overflow for wide figures and tables.

## Effect
- Completed papers become readable again even when the `preview_html` asset row or translated abstract field is stale, as long as translation outputs still exist on disk.
- The HTML reader is materially closer to an AlphaXiv-style native reading experience: text, figures, math, links, captions, references, and benchmark tables render as article content instead of raw LaTeX fragments.
- Broken residue such as raw `\textbf{...}`, `\newblock`, `\natexlab`, dangling `$s_c^{2D`, visible `\cite{...}` fragments in captions, `\paragraph{}`, `\PARR{}`, `\hdashline`, `\textsubscript{}`, `\KwData`, and `\For{}` no longer survives into the validated visible DOM.
- Long papers no longer stretch the entire detail page vertically just to keep the reader open; the reader stays inside an embedded scrollable pane while metadata and action cards remain reachable below.
- The detail page keeps the structural foundation needed for later highlights / notes / agent features: stable block anchors remain in place and the workspace pane is reserved without destabilizing the reader.

## Round 9 addendum
- Moved the paper’s social + source metadata into the header chip row so source badges, views, likes, favorites, comments, translated inclusion time, and the original arXiv URL live together directly below the title block.
- Tightened detail actions so completed papers no longer invite redundant translation restarts, while translated-PDF download failures now surface a friendly message instead of the raw backend detail.
- Extended reader linking so bibliography entries expose external lookup URLs and internal section / figure / bibliography references survive normalization instead of collapsing into raw LaTeX residue.
- Added a larger table reading surface in the embedded HTML reader and covered both the expand affordance and internal anchor scrolling with targeted frontend tests.

## Automated validation
- `python -m pytest backend/tests/unit/test_paper_preview_service.py -q`
- `cd frontend && npm test -- --run src/components/community/PaperPreviewReader.test.tsx src/pages/PaperDetail.test.tsx`
- `openspec validate fix-community-week1-reader-and-metadata --strict --no-interactive`
- `cd frontend && npm run i18n:check`

## Browser validation
- Validated the live route `http://127.0.0.1:5173/paper/f41f12e6-9e02-4585-831c-c34037fdd637` against a local frontend on `5173` and patched backend on `9001`.
- Confirmed the completed-paper route now serves refreshed `reader-v12` HTML and renders the translated article inside a dedicated scroll viewport instead of showing the empty preview fallback.
- Confirmed the top reader/workspace split exists in the live DOM, the reader pane dominates the top grid, and the viewport no longer exposes a competing root horizontal scrollbar.
- Confirmed local table overflow still works via the table scroller while the reader viewport itself remains horizontally contained.
- Confirmed visible DOM residue checks return zero matches for raw `\textbf{...}`, `\newblock`, `\natexlab`, dangling `$s_c^{2D`, and broken caption/reference artifacts.
- Confirmed captions like `PPNeSF 架构示意图。` and bibliography text like `TensoRF: Tensorial Radiance Fields. In ECCV, 2022a.` render as normal readable prose.
- Confirmed KaTeX now renders both block and inline math in the live reader, with `.katex` nodes present in the page DOM.

## Acceptance checklist
- Open `/paper/:paperId` for an arXiv-backed paper with stale metadata and confirm title, authors, categories, and abstract are repaired on detail load.
- Open `/paper/:paperId` for a completed paper whose translated output exists and confirm the HTML reader renders article content instead of the empty preview fallback.
- Confirm the reader no longer exposes raw `\paragraph{}`, `\PARR{}`, `\textbf{...}`, `\newblock`, `\natexlab`, `\hdashline`, `\textsubscript`, dangling `$s_c^{2D`, or visible `\cite{...}` caption residue.
- Confirm semantic lists, semantic tables, inline figures, clickable publication links, and KaTeX-rendered inline plus display math appear in the reader when source assets exist.
- Confirm the detail page keeps the reader inside a fixed-height internal-scroll pane, shows a dominant reader/workspace split, and keeps metadata plus action cards reachable below.
- Confirm the detail header now centralizes source metadata plus the original paper URL, completed papers disable redundant translation, and translated-PDF download failures surface the friendly user-facing message.

## Browser addendum
- Confirmed on the shared local route that the header now renders the consolidated metadata chip row and that completed papers show the `Translate` action disabled while preview and download remain available.
- Verified through targeted reader tests that table figures expose an expand affordance and internal `#...` links scroll within the embedded reader viewport.
- Observed one shared-dev-server caveat during spot-checking: the long-running local `5173` instance reflected the header/action changes immediately, but did not visibly pick up the freshly injected table toolbar / reader enhancer without a clean frontend restart. The source changes and targeted tests are green; restart the local frontend before final UX sign-off if that shared dev instance appears stale.
