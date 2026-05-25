# community-public-read-experience Specification

## Purpose
TBD - created by archiving change add-community-public-read-experience-foundation. Update Purpose after archive.
## Requirements
### Requirement: Public paper reading is preview-ready before normal reader access
The public paper reading experience SHALL continue trying to expose translated reading artifacts when translated section outputs or translated PDFs exist, even if compilation fails.

#### Scenario: Failed task still has translated section outputs
- **WHEN** a translation task ends in a compile-related terminal failure but translated section outputs remain available
- **THEN** the system SHALL still attempt to generate translated HTML preview from those outputs
- **AND** the detail page SHALL be allowed to surface that translated HTML as a readable state.

#### Scenario: Failed task still has a translated PDF
- **WHEN** a translation task fails but a translated PDF artifact exists
- **THEN** the system SHALL preserve that translated PDF as a readable fallback
- **AND** the detail page SHALL present it as a degraded translated mode rather than as total translated unavailability.

### Requirement: Public paper detail avoids a user-visible metadata-to-preview waterfall
The system SHALL provide a first-read contract that keeps paper detail bootstrap lightweight while still making translated reading assets immediately discoverable for normal users.

#### Scenario: Open a paper detail page that has a ready preview
- **WHEN** a user navigates to a paper detail route for a preview-ready paper
- **THEN** the system SHALL deliver metadata, reader state, and reader asset locators without embedding large multi-megabyte preview bodies directly in the main detail payload
- **AND** the page SHALL be able to begin rendering normal reading flow without a visibly serialized metadata request followed by a second blocking preview-discovery step.

#### Scenario: Navigate to a paper detail page whose reader is still warming
- **WHEN** a user opens a paper detail route for a paper whose preview is not yet reader-ready
- **THEN** the page SHALL communicate that the reader is warming or unavailable
- **AND** the non-reader metadata SHALL still render without pretending that full reading is immediately ready.

### Requirement: Public HTML reading prioritizes a paper-like reading surface
The system SHALL prefer a sanitized local reader presentation for English arXiv HTML before falling back to PDF or external source links. This layout will be governed directly by the Stitch Maximized Reader design paradigm.

#### Scenario: arXiv HTML is available
- **WHEN** the paper has an arXiv HTML source
- **THEN** the system SHALL prefer rendering sanitized article content inside the local reader shell shaped by the Maximized Reader constraints
- **AND** it SHALL remove or demote non-reader chrome that does not help the community reading experience.

#### Scenario: English HTML is unavailable
- **WHEN** the paper does not have usable English HTML content
- **THEN** the detail page SHALL fall back to a stored `source_pdf` asset before live arXiv PDF retrieval
- **AND** the reader SHALL keep the paper readable inside the community flow.

#### Scenario: Stored source PDF is available
- **WHEN** a public community paper has a latest `source_pdf` asset
- **THEN** source PDF preview and download routes SHALL resolve that asset through the configured storage backend
- **AND** normal reader access SHALL NOT depend on live arXiv PDF download for that paper.

### Requirement: Public math and caption rendering avoids duplicate or malformed formula output
The system SHALL prefer a single readable math presentation and SHALL not leak broken inline-math fragments or raw LaTeX source commands into prose, captions, tables, or fallback blocks.

#### Scenario: Display math is already renderable in the HTML reader
- **WHEN** a block formula is rendered through the HTML reader math pipeline
- **THEN** the page SHALL show one readable formula presentation
- **AND** it SHALL not leave a second raw horizontal text transcription beside or below the rendered formula.

#### Scenario: A caption or prose fragment contains malformed inline math
- **WHEN** preview generation encounters an unmatched or truncated inline-math fragment such as a dangling `$...`
- **THEN** the reader SHALL repair or remove that malformed fragment from visible prose
- **AND** the page SHALL not expose visibly broken math like `$s_c^{2D`.

#### Scenario: Scholarly formulas or references were split by translation artifacts
- **WHEN** preview generation encounters a display equation, figure caption, or bibliography entry that still contains raw helper commands or is split into multiple broken textual fragments
- **THEN** the reader SHALL normalize those fragments into one readable scholarly presentation
- **AND** it SHALL not expose raw helpers such as `\textbf{}`, `\newblock`, `\natexlab`, or visibly duplicated formula text beside the rendered equation.

#### Scenario: Unknown LaTeX command blocks are not shown as raw source
- **WHEN** preview generation encounters an unsupported environment or command block whose body is primarily raw TeX source
- **THEN** the reader SHALL replace that block with a reader-safe omission note
- **AND** it SHALL not expose raw snippets such as `\begin{tabular}`, `\includegraphics`, or custom macro command text directly in the reading surface.

### Requirement: Public community deployments support a cold-start content floor
The system SHALL continue to support seeded or newly imported English-readable papers before Chinese output is ready.

#### Scenario: Imported English papers remain readable before translation
- **WHEN** a public paper only has English-readable artifacts
- **THEN** the detail page SHALL keep that English reading path usable
- **AND** translation status SHALL not remove English readability while Chinese output is still missing or degraded.

### Requirement: Public-read performance is measurable and cache-aware
The system SHALL expose enough operational signals and cache behavior to verify that public reading readiness is improving.

#### Scenario: Measure homepage and paper read readiness
- **WHEN** the system serves public homepage, detail, or preview traffic
- **THEN** operators SHALL have measurable readiness signals for first-screen discovery and preview-read availability
- **AND** the implementation SHALL document the intended cache behavior for those public-read paths.

### Requirement: Reader state upgrades use soft feedback instead of abrupt page replacement
The system SHALL surface completion and failure as soft experience feedback rather than abrupt hard refreshes or dead-end error pages whenever a readable fallback still exists.

#### Scenario: Chinese reader becomes ready while the user is on the detail page
- **WHEN** a user is viewing an English-readable paper and the Chinese reader becomes ready
- **THEN** the page SHALL surface a lightweight completion message
- **AND** the reader area SHALL present the change as a soft upgrade rather than a disorienting full-page replacement.

#### Scenario: Translation fails but readable output still exists
- **WHEN** Chinese generation fails but English or translated fallback reading still exists
- **THEN** the page SHALL explain that generation degraded
- **AND** it SHALL keep the best available readable mode visible instead of collapsing into a fatal error page.

### Requirement: Reader exposes explicit source and translated mode control

The public reader SHALL let users intentionally switch between English-source and translated reading whenever both modes are available, while operating inside the new community-first application shell.

#### Scenario: Both English and translated readers exist
- **WHEN** a paper has both source-readable and translated-readable modes
- **THEN** the detail page SHALL expose explicit mode switches for `英文`, `译文 PDF`, `译文 HTML`, and `中英双栏对照` in that order whenever the underlying assets for those modes are available
- **AND** changing modes SHALL preserve the existing reader-first shell instead of leaving the paper detail workflow

#### Scenario: Reader remains available to anonymous users
- **WHEN** an unauthenticated user opens a paper detail page
- **THEN** the detail route SHALL remain readable inside the community shell
- **AND** login SHALL not be required merely to consume public reading content

### Requirement: Prewarmed readable assets are immediately usable by the reader
The public and community reading experience SHALL immediately use prewarmed readable assets from the content pool when they already exist, instead of acting like the paper still needs to be translated live.

#### Scenario: Paper detail opens for a prewarmed translated paper
- **WHEN** a user opens a paper whose translated reader or translated preview was already produced by the content pool
- **THEN** the detail page SHALL use that translated-readable state immediately
- **AND** it SHALL not force the user through a fresh translation-start path for the same paper.

#### Scenario: Public translated PDF reads use a ready delivery asset
- **WHEN** a user opens or downloads a translated PDF for a public community paper
- **THEN** the public read path SHALL resolve an already-prepared canonical translated PDF delivery asset
- **AND** it SHALL not perform user-visible leading-blank-page trimming, heavy asset recovery, or full object-storage materialization before beginning delivery.

### Requirement: Reader-side math hydration has a safe fallback path
The system SHALL keep display math readable even if client-side enhancement hydration partially fails.

#### Scenario: Enhancement pipeline fails but math blocks exist
- **WHEN** the reader receives preview HTML containing `.paper-preview__math-block` nodes and enhancement hydration throws or leaves those blocks unrendered
- **THEN** the client SHALL apply a fallback math renderer for those blocks
- **AND** the paper detail reading flow SHALL remain readable without requiring a full page reload.

### Requirement: Source HTML reading avoids duplicated paper header content
The public paper detail reader SHALL avoid repeating the paper title and author list inside the rendered source HTML body when that content is already presented in the page chrome.

#### Scenario: Render source HTML with a repeated title/author lead block
- **WHEN** the source HTML body begins with a title-and-author block that duplicates the visible paper metadata already shown by the page shell
- **THEN** the reader SHALL remove that leading duplicated block from the rendered HTML body
- **AND** it SHALL preserve the remaining article content structure.

### Requirement: Paper detail uses a coordinated dual-pane copilot workspace

The web UI SHALL present paper detail as a coordinated dual-pane workspace with a reading-dominant pane and a persistent paper-scoped support pane, integrated into the new editorial application shell.

#### Scenario: Desktop paper detail keeps both panes visible
- **WHEN** the user opens the paper detail page on a desktop-width viewport
- **THEN** the reader SHALL remain the dominant pane
- **AND** the support pane SHALL stay visible without visually displacing the reader from its primary role

#### Scenario: Shell redesign does not reduce paper-detail capability
- **WHEN** the paper detail page is migrated into the new community-first shell
- **THEN** translated mode controls, insights, similar-paper support, and reader-first behavior SHALL remain available
- **AND** the redesign SHALL not reduce current paper-detail functionality

### Requirement: Paper detail toolbar stays minimal and reader-first
The public paper detail route SHALL present a thin single-row toolbar that preserves reader controls and core actions without keeping title, author, status, and other metadata blocks permanently visible above the reading surface.

#### Scenario: Reader opens with a minimal toolbar
- **WHEN** a user opens a paper detail page
- **THEN** the sticky toolbar SHALL keep the back action pinned to the far left edge of the row
- **AND** the reader mode switch SHALL remain available in a lightweight rectangular control near the center of the row
- **AND** the route SHALL not render the previous expandable metadata banner, title block, category chips, status pills, or inline publication row above the reader.

#### Scenario: Toolbar actions stay independent and compact
- **WHEN** the toolbar renders its paper actions
- **THEN** it SHALL display four independent icon actions in this order: favorite, translated-PDF download, paper info, and share
- **AND** those actions SHALL not be wrapped inside a larger rounded capsule container
- **AND** the download action SHALL continue downloading the translated PDF when that asset is available.

#### Scenario: Paper metadata is available on demand
- **WHEN** the user activates the info action
- **THEN** the page SHALL reveal a card-style metadata panel for the current paper
- **AND** that panel SHALL surface core paper information such as title, authors, publication time, categories, and external identifiers or links when available
- **AND** closing the panel SHALL return the user to the unchanged reading layout.

#### Scenario: Share copies the current paper detail URL
- **WHEN** the user activates the share action
- **THEN** the page SHALL copy the current paper detail URL to the clipboard
- **AND** it SHALL provide lightweight feedback without navigating away from the paper.

### Requirement: Narrow-screen reading defaults to translated single-column mode
The public paper-reading experience SHALL default narrow/mobile viewports to a translated-first single-column reading presentation whenever translated reading assets are available.

#### Scenario: Mobile paper detail opens with translated reading available
- **WHEN** a user opens a paper detail page on a narrow/mobile viewport
- **AND** translated reading content is available
- **THEN** the reader SHALL default to a single-column translated presentation
- **AND** the UI SHALL not default to a side-by-side bilingual or dual-pane reading layout

#### Scenario: Mobile paper detail falls back when translated reading is unavailable
- **WHEN** a user opens a paper detail page on a narrow/mobile viewport
- **AND** translated reading content is not available
- **THEN** the page SHALL fall back to the best available readable source mode
- **AND** it SHALL keep the single-column mobile reading structure

### Requirement: Narrow-screen reading support uses explicit secondary surfaces
The public paper-reading experience SHALL move mobile secondary reading-support content into explicit toggles instead of keeping desktop-persistent support panes visible beside the reader.

#### Scenario: Mobile paper detail exposes support content
- **WHEN** a user needs insights, similar papers, paper metadata, or other reading-support content on a narrow/mobile viewport
- **THEN** the page SHALL expose that support content through explicit tabs, drawers, sheets, or collapsible regions
- **AND** those secondary surfaces SHALL not crowd the default single-column reader

#### Scenario: Mobile preview route opens on a narrow screen
- **WHEN** a user opens the preview route on a narrow/mobile viewport
- **THEN** the preview SHALL default to a single-document translated reading view
- **AND** alternate source or comparison views SHALL remain available through explicit user switching rather than simultaneous side-by-side rendering

### Requirement: Public PDF delivery balances stable iframe preview and COS direct downloads
The public reader SHALL use first-party Range-capable inline proxy responses for object-storage-backed PDF iframe previews, while explicit downloads SHALL continue to use signed COS redirects whenever available.

#### Scenario: Community translated PDF preview proxies COS with inline Range support
- **WHEN** a public community paper has an object-storage-backed translated PDF asset
- **THEN** `GET /api/papers/{paper_id}/translated-pdf` SHALL stream the signed COS object through the backend as an inline PDF response
- **AND** it SHALL forward browser `Range` requests upstream and preserve relevant `206 Partial Content`, `Accept-Ranges`, and `Content-Range` headers.

#### Scenario: Community source PDF preview proxies COS with inline Range support
- **WHEN** a public community paper resolves an object-storage-backed source PDF asset or raw-cache source PDF URL
- **THEN** `GET /api/papers/{paper_id}/source-pdf` SHALL stream the signed COS object through the backend as an inline PDF response
- **AND** it SHALL forward browser `Range` requests upstream and preserve relevant `206 Partial Content`, `Accept-Ranges`, and `Content-Range` headers.

#### Scenario: Ordinary task PDF preview proxies COS with inline Range support
- **WHEN** an ordinary completed translation task has an object-storage output manifest with a translated PDF
- **THEN** `GET /api/preview/{task_id}/pdf` SHALL stream the signed COS object through the backend as an inline PDF response
- **AND** it SHALL forward browser `Range` requests upstream and preserve relevant `206 Partial Content`, `Accept-Ranges`, and `Content-Range` headers
- **AND** local-disk deployments SHALL continue to serve the local PDF file as before.

#### Scenario: Explicit PDF downloads redirect to COS
- **WHEN** a public community paper or ordinary task has an object-storage-backed PDF available for explicit download
- **THEN** the download route SHALL redirect to a signed COS URL with attachment disposition when available
- **AND** the backend SHALL NOT proxy explicit download byte streams unless COS delivery is unavailable.

### Requirement: Public feed thumbnails are warm-cache friendly
Public paper thumbnails MUST be available from cache whenever a previously warmed public paper appears on the homepage.

#### Scenario: Paper becomes publicly readable
- **WHEN** a paper transitions into a public readable state with source or translated PDF preview assets
- **THEN** the backend MUST schedule thumbnail cache warmup for the relevant public preview assets
- **AND** subsequent homepage thumbnail requests SHOULD reuse the cached rasterized image when it already exists.

