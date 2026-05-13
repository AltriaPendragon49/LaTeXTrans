# Change: Update hot ranking source aggregation

## Why
The current community `hot` feed is only an alias for internal view-count sorting, which is useful after papers are published but does not provide a scientifically grounded way to discover which new arXiv papers should be translated and promoted. We need a multi-source, auditable ranking workflow that combines platform momentum, scholarly impact, reproducibility signals, and publication-window filters before operators choose papers for admin curation.

## What Changes
- Add a time-windowed hot-ranking source workflow that exports ranked arXiv candidates for `3d`, `7d`, `30d`, `90d`, and `all` windows.
- Define a tiered external source policy covering alphaXiv, arXiv, OpenAlex, Semantic Scholar, Hugging Face Papers, GitHub/Papers-with-Code style code signals, OpenReview, and excluded or low-confidence sources.
- Require every ranked candidate to include score breakdowns, source evidence, freshness metadata, confidence, and operator-readable selection reasons.
- Extend the community discovery UI contract so the `Hot` feed can be filtered by publication-date window through a left-side filter icon, anchored popover, active date pill, and mobile-safe sheet behavior.
- Define how ranked hot candidates feed later admin curation or content-pool prewarm work without automatically translating unapproved papers.

## Impact
- Affected specs: `paper-source-feed-export`, `community-paper-discovery-ui`, `community-content-pool-foundation`
- Affected code: future work may touch `scripts/export_alphaxiv_catalog.py`, backend feed/ranking services, Redis feed indexes, community feed API parameters, frontend community feed controls, and admin/content-pool candidate tooling.
- No implementation is included in this change proposal.
