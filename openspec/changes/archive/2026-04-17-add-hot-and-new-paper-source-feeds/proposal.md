# Change: add hot, new, and core paper source feeds

## Why
The repository needs a reusable paper-source export workflow that can support both daily paper intake and a smaller, higher-value evergreen paper pool without creating duplicate translation work.

## What Changes
- Extend the export workflow to support reusable source modes for `hot-top-n`, `hot-new-24h`, and `new-24h`
- Add a `core-pool` mode that builds a roughly 4000-paper pretranslation seed set from multiple public impact signals instead of a single hot feed
- Store outputs under `backend/arxiv_id/` with stable subdirectories for `all_hot`, `daily_hot`, and `daily_new`
- Add a stable `backend/arxiv_id/core_pool/` output target for the evergreen seed set
- Export both Markdown and JSON artifacts, creating missing directories automatically
- Define de-duplication and scheduling rules so `hot` papers always take priority over `new` papers for translation
- Preserve duplicate papers for ranking and display purposes without requesting a second translation when a paper was already translated from another source
- Make the evergreen pool approximate real category distribution while preserving at least 50 papers for each included major category

## Impact
- Affected specs: `paper-source-feed-export`
- Affected code: `scripts/export_alphaxiv_catalog.py`, `backend/arxiv_id/`
