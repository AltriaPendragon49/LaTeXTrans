# community-paper-discovery-ui Specification

## Purpose
TBD - created by archiving change add-community-day-03-feed-and-paper-detail-shell. Update Purpose after archive.
## Requirements
### Requirement: Community feed homepage route
The system SHALL expose the community Feed as the primary web homepage and present it as a research-discovery surface rather than a translation form.

#### Scenario: Open the product homepage
- **WHEN** a user navigates to `/`
- **THEN** the system SHALL render the community Feed homepage shell
- **AND** the page SHALL visually prioritize browseable community papers over translation inputs
- **AND** the design SHALL follow a restrained dark research-reading direction inspired by alphaXiv without reproducing alphaXiv branding or navigation structure.

#### Scenario: Homepage first-screen discovery is ready without an empty boot gap
- **WHEN** a user opens the public homepage on a normal healthy deployment
- **THEN** the system SHALL provide first-screen discovery content through an initial-document payload, equivalent bootstrap data, or another non-empty first-load strategy
- **AND** the page SHALL NOT depend on a fully blank client-only boot path before any paper discovery content can appear.

#### Scenario: Initial homepage load is not delayed by search debounce
- **WHEN** the homepage performs its first public feed load for the current route
- **THEN** the system SHALL request or apply the initial feed payload immediately
- **AND** typing-oriented search debounce SHALL only apply to subsequent user query refinement.

### Requirement: Feed sort and browse shell
The community homepage SHALL provide the MVP browse controls needed to inspect official-first community content.

#### Scenario: Switch feed views
- **WHEN** a user changes between `latest`, `translated`, and `hot`
- **THEN** the system SHALL request the matching community paper list from the Day 2 API
- **AND** the Feed SHALL render loading, empty, and error states without falling back to local mock data.

#### Scenario: Surface official-first guidance
- **WHEN** the Feed homepage renders
- **THEN** the page SHALL communicate that official community content is prioritized
- **AND** fallback user content SHALL appear as a lower-priority community state rather than a peer official source.
- **AND** the page SHALL rely on spacing, grouping, and restrained status emphasis rather than broad accent-colored panels.

### Requirement: Paper card content contract
Each Feed result SHALL render as a dense paper discovery card that helps the viewer decide whether to inspect the paper in detail.

#### Scenario: Render a paper card
- **WHEN** the Feed receives a community paper item
- **THEN** the card SHALL show community status, translation status, title, author summary, category summary, timing, counters, and selected asset summary
- **AND** official papers SHALL be visually distinguishable from user fallback papers.

### Requirement: Paper detail shell contract
The system SHALL provide a dedicated paper detail shell that defaults to the community-selected version of a paper.

#### Scenario: Open a paper detail page
- **WHEN** a user navigates to `/paper/:paperId`
- **THEN** the page SHALL load the paper detail from the Day 2 API
- **AND** it SHALL render title, authors, abstract, status badges, counters, source metadata, and community-selected task/asset references
- **AND** it SHALL record a paper view without blocking the detail render if the view counter call fails.

#### Scenario: Recover readable detail content for completed papers
- **WHEN** a completed community paper has translated output on disk but its `preview_html` asset is missing or stale
- **THEN** the detail/preview path SHALL recover a readable HTML preview from the completed output when possible
- **AND** the page SHALL not collapse into an empty reader state merely because the preview asset row was missing.

#### Scenario: Render a reader-first preview instead of raw LaTeX dumps
- **WHEN** the system generates or refreshes `preview_html` for a completed community paper
- **THEN** it SHALL strip document-shell LaTeX noise such as `\begin{document}`, `\maketitle`, labels, and stale placeholders
- **AND** it SHALL downgrade figures and tables into readable callouts rather than exposing raw environment source whenever rich rendering is unavailable.

#### Scenario: Render display math in a KaTeX-compatible reader structure
- **WHEN** the system generates or refreshes `preview_html` containing block math environments such as `equation`, `align`, or `\[...\]`
- **THEN** it SHALL emit those blocks in a structure that the current HTML reader can pass through KaTeX auto-render
- **AND** it SHALL not trap renderable block math inside tags ignored by KaTeX auto-render such as `<pre>`.

#### Scenario: Emit stable anchors for future notes and highlights
- **WHEN** the system generates or refreshes `preview_html` for a completed community paper
- **THEN** each rendered section SHALL expose a stable `data-section-id`
- **AND** each reader block SHALL expose a stable `data-block-id`
- **AND** those anchors SHALL be present on paragraph-like, math, figure, table, and list blocks so future selection persistence can target them.

#### Scenario: Render PDF-backed figures inline when local source assets exist
- **WHEN** a figure in the selected community paper source references a local PDF asset and the runtime has a usable PDF rasterization tool
- **THEN** the HTML reader SHALL rasterize that figure into an inline image instead of always collapsing to a “view PDF version” placeholder
- **AND** the fallback note SHALL only remain for figures that still cannot be rasterized.

#### Scenario: Render inline LaTeX command examples readably inside prose
- **WHEN** translated prose contains inline command examples such as `\texttt{...}`, `\textbackslash`, or wrapped command snippets inside helper environments like `CJK`
- **THEN** the HTML reader SHALL normalize those snippets into readable inline code-like presentation
- **AND** it SHALL avoid exposing raw helper wrappers such as `\begin{CJK}...\end{CJK}` in normal article prose unless no safer normalization is possible.

#### Scenario: Render subsection command-line walkthroughs as rich reader blocks
- **WHEN** translated paper content contains nested heading commands such as `\subsection{...}` or centered command-line examples using environments like `center` plus font switches such as `\ttfamily`
- **THEN** the HTML reader SHALL render those walkthroughs as readable subheadings and command/example blocks rather than collapsing the whole chunk into raw LaTeX `<pre>` output
- **AND** it SHALL avoid exposing raw wrapper commands such as `\subsection`, `\begin{center}`, or `\ttfamily` when a safe HTML representation is available.

#### Scenario: Detail-page download opens a usable translated PDF URL
- **WHEN** a user clicks download from the paper detail page for a completed community paper
- **THEN** the client SHALL open a download URL that resolves against the API origin rather than assuming the frontend origin can serve `/api/papers/...`
- **AND** the backend SHALL recover the translated PDF asset from completed task output when the database asset row is stale or missing but the file still exists on disk.

#### Scenario: Render complex LaTeX result tables as readable HTML tables
- **WHEN** translated paper content contains `table` / `tabular` structures that use wrappers such as `resizebox`, `multirow`, `multicolumn`, `cmidrule`, `toprule`, or repeated column groups
- **THEN** the HTML reader SHALL normalize those constructs into a readable HTML table instead of exposing raw LaTeX control sequences inside the rendered cells
- **AND** captions such as benchmark/result summaries SHALL remain attached to the rendered table figure.

#### Scenario: Render publication/demo URLs as clickable links
- **WHEN** translated prose contains publication links encoded as `\url{...}`, `\href{...}{...}`, footnote URL text, or normalized textual forms such as `[<https://...>]`
- **THEN** the HTML reader SHALL emit clickable anchors for those URLs
- **AND** the visible prose SHALL no longer expose raw angle-bracket URL wrappers when a safe anchor representation is available.

#### Scenario: Preserve aligned display equations as math blocks
- **WHEN** translated paper content contains aligned display equations and surrounding explanatory prose such as parameter descriptions
- **THEN** the HTML reader SHALL keep the equation itself in a KaTeX-renderable block structure
- **AND** it SHALL avoid collapsing the equation into duplicated plain-text glyph streams when a math-environment representation is available.

#### Scenario: Repair missing Week 1 metadata for arXiv-backed papers
- **WHEN** an arXiv-backed paper detail is opened with missing title, authors, categories, or abstract
- **THEN** the system SHALL hydrate the missing metadata from the arXiv source of truth
- **AND** the detail page SHALL stop showing placeholder metadata once that hydration succeeds.

### Requirement: Disabled action-slot contract
The Day 3 detail page SHALL visually reserve the future action positions needed by later changes without exposing active controls yet.

#### Scenario: Show future action positions
- **WHEN** the detail page renders
- **THEN** the page SHALL display translation, preview, download, like, favorite, comment, and report action slots
- **AND** all action slots SHALL be disabled in Day 3
- **AND** the UI SHALL explain that those actions are coming in later changes.

### Requirement: Translation workspace relocation compatibility
The old translation workspace SHALL remain available after the homepage moves to the community Feed.

#### Scenario: Open the translation workspace
- **WHEN** a user navigates to `/translate`
- **THEN** the system SHALL render the existing translation Dashboard experience
- **AND** shared navigation SHALL expose both `Community` and `New Translation` as first-level destinations.

