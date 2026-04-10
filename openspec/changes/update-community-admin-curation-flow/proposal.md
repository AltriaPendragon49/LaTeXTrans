# Change: Update Community Admin Curation Flow

## Why
The current community experience exposes costly public agent entry points, mixes public community publication with ordinary user translation workflows, and lacks an admin-only curation path for producing complete community papers. The product now needs a cleaner split: community stays public and curated, tools stay usable for ordinary user translation, and only admin-managed complete papers enter the community library.

## What Changes
- Replace the community homepage agent-first composer with an internal community-paper search surface while keeping the overall page layout silhouette stable.
- Replace the paper-detail right-side public copilot pane with prepared structured paper insights (`Problem`, `Method`, `Key Idea`, `Experiment`, `Result`, `Limitation`) that follow the current reader language mode.
- Add an admin-only sidebar entry and new community curation page for single and batch intake via `arXiv ID` and TeX-containing archives.
- Require admin curation runs to complete ingestion, translation, metadata preparation, and structured insight generation before the paper becomes publicly visible in the community.
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
  - backend paper intake/publish flows, admin APIs, metadata extraction, structured insight generation, and hard-delete cleanup
