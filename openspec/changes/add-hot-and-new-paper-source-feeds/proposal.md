# Change: add hot and new paper source feeds

## Why
The repository needs a reusable paper-source export workflow that can support both alphaXiv hot-paper intake and daily new-paper intake without creating duplicate translation work.

## What Changes
- Extend the export workflow to support reusable source modes for `hot-top-n`, `hot-new-24h`, and `new-24h`
- Store outputs under `backend/arxiv_id/` with stable subdirectories for `all_hot`, `daily_hot`, and `daily_new`
- Export both Markdown and JSON artifacts, creating missing directories automatically
- Define de-duplication and scheduling rules so `hot` papers always take priority over `new` papers for translation
- Preserve duplicate papers for ranking and display purposes without requesting a second translation when a paper was already translated from another source

## Impact
- Affected specs: `paper-source-feed-export`
- Affected code: `scripts/export_alphaxiv_catalog.py`, `backend/arxiv_id/`
