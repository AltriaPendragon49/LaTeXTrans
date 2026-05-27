# Change: Update hot ranking source aggregation

## Why
The current community `hot` feed is only an alias for internal view-count sorting, which is useful after papers are published but does not explain which recent arXiv papers are broadly worth reading or translating. We need a simpler, auditable hot-ranking workflow that uses public evidence, publication-date filters, and time decay so the homepage can keep surfacing recently hot papers without becoming a copy of any single external leaderboard.

## What Changes
- Add a time-windowed hot-ranking source workflow that exports ranked arXiv candidates for `3d`, `7d`, `30d`, `90d`, and `all` windows.
- Define a compact evidence model based on attention, authority, implementation, and local engagement signals.
- Apply a window-specific time-decay factor so recent papers can outrank older papers with similar raw evidence.
- Require every ranked candidate to include score breakdowns, source evidence, freshness metadata, and operator-readable selection reasons.
- Extend the community discovery UI contract so the `Hot` feed can be filtered by publication-date window through a left-side filter icon, anchored popover, active date pill, and mobile-safe sheet behavior.
- Define how ranked hot candidates feed later admin curation or content-pool prewarm work without automatically translating unapproved papers.
- Add a daily scheduled cron task on the Worker process that refreshes hot rankings, compares against the existing community catalog, auto-starts admin-curation translation for new top-ranked papers that are not yet translated or queued, and writes a daily intake summary (Markdown) with score breakdowns and intake reasons for each paper.

## Impact
- Affected specs: `paper-source-feed-export`, `community-paper-discovery-ui`, `community-content-pool-foundation`
- Affected code: future work may add `scripts/export_hot_ranking.py`, `backend/app/services/hot_ranking_service.py`, extend `backend/app/main.py` Worker periodic tasks, `backend/app/core/config.py` cron parameters, backend feed/ranking services, Redis feed indexes, community feed API parameters, frontend community feed controls, and admin/content-pool candidate tooling.
- No implementation is included in this change proposal.
