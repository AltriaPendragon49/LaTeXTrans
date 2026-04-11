# Change: Update Community Admin Curation Flow

## Why
The current community experience exposes costly public agent entry points, mixes public community publication with ordinary user translation workflows, and still treats the paper guide as a six-module structure whose content quality and module boundaries do not match the desired reading experience. The product now needs a cleaner split: community stays public and curated, tools stay usable for ordinary user translation, and the paper detail pane becomes a fixed five-module Chinese paper-guide system focused on reader understanding rather than schema-heavy structure.

## What Changes
- Replace the community homepage agent-first composer with an internal community-paper search surface while keeping the overall page layout silhouette stable.
- Replace the paper-detail right-side public copilot pane with five fixed Chinese paper-guide modules generated from translated paper content and stored as reader-facing Chinese-only text content.
- Add an admin-only sidebar entry and new community curation page for single and batch intake via `arXiv ID` and TeX-containing archives.
- Require admin curation runs to complete ingestion, translation, metadata preparation, and five-module paper-guide generation before the paper becomes publicly visible in the community.
- Keep the paper-guide pipeline content-first: the system owns module structure, the model only writes Chinese正文, each module generates independently, and every module has fallback so publication is never blocked by a single generation failure.
- Stop ordinary authenticated translation tools from auto-publishing results into the community library.
- Add admin-only hard delete for community papers, removing local database rows and local filesystem assets.
- Hide homepage, sidebar, and detail-page public agent entry points without deleting the retained community-agent routes or runtime services.

## Impact
- Affected specs:
  - `community-paper-discovery-ui`
  - `community-agent-assistant`
  - `community-paper-intake-api`
  - `community-paper-library-storage`
  - `web-api`
  - `community-admin-curation` (new)
  - `community-structured-insights` (new)
- Affected code:
  - frontend community homepage, paper-detail page, sidebar, and new admin curation page
  - backend paper intake/publish flows, admin APIs, metadata extraction, five-module guide generation, and hard-delete cleanup
