# Change: Update Frontend Theme to Lumina Blue

## Why
The current frontend uses a red-based color palette that resembles an "Apache-style" aesthetic. To provide a more professional, calm, and readable research environment, the user requested switching the overall frontend color tone to a blue-based theme ("Lumina Blue") extracted from the `stitch_text_document` UI mockups.

## What Changes
- Replace the `--primary` red colors in `index.css` with Lumina Blue (`#0037b0` in light mode, `#b7c4ff` in dark mode).
- Update background, surface, muted, and border variables in `index.css` to align with the Lumina Blue aesthetic (using cool grays/blues like `#faf8ff` instead of warm grays `#fcf9f8`).
- Update dark mode equivalents accordingly.
- **Paper Detail Optimization**: Metadata (title, authors, publish date) is extracted into a **sticky top header** to ensure visibility during scrolling, following `paper_detail_refined_header_hierarchy`.
- **Reading Area Highlight & Interaction**: Native text highlighting (via CSS `::highlight`). Right-click on selection triggers a context menu with "对这些内容提问", auto-filling the Agent prompt.
- **Agent panel interaction**: Default empty state suggestions (e.g., "总结这篇论文", "这一篇论文的核心是什么？") to guide the user.
- **Interactive PDF Previews**: Homepage cards now feature **functional PDF previews** using `<object>` tags with beautiful CSS-skeleton fallbacks to gracefully handle missing files (preventing ugly JSON errors).
- **Hover-Zoom**: PDF thumbnails support hover magnification where *only the specific hovered PDF* scales up, keeping the other stable.
- **Card Layout**: Conforms perfectly to `community_feed_document_focus_final`, implementing a left-text, right-thumbnail side-by-side flexible layout.
- **Native PDF Reading**: In Paper Detail, if a high-fidelity HTML preview is unavailable, translated PDFs are rendered directly via an embedded iframe to maintain a smooth reading experience.
- **Source Preview Performance**: Source preview now prefers existing local community-paper source PDFs before any remote arXiv fetch to avoid unnecessary repeated downloads.
- **Range-friendly Source Proxy**: Backend source-PDF proxy now forwards `Range` requests and returns `206` partial content when requested, enabling pdf.js chunked loading.
- **Card PDF First-Page Fit**: Community feed PDF thumbnails now render the first page with aspect-preserving fit (no clipping/cropping), for both original and translated previews.
- **Preview Stability**: `react-pdf` options are stabilized and source previews use fetch settings tuned for progressive loading.
- **Icon Rendering Fix**: Added Material Symbols Outlined font import in `index.html` to resolve raw text rendering issues (e.g., `local_fire_department`) in the community feed.
- **Translation Toggle Label**: Updated the abstract translation toggle button text to "切换语言(switch)" to clarify its purpose and prevent confusion with active translation processes.

## Impact
- Affected specs: `web-ui`
- Affected code:
  - `frontend/src/index.css`
  - `frontend/src/components/community/PaperCard.tsx`
  - `frontend/index.html`
  - `backend/app/api/routes/download.py`
