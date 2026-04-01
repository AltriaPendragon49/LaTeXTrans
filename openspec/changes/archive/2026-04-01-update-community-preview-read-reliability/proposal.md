# Change: Update community preview read reliability

## Why
- The community HTML reader still surfaced raw LaTeX source in multiple real papers (`\\begin{...}`, command blocks, helper control commands), which broke reading flow.
- Existing preview availability heuristics could reject otherwise readable legacy preview assets, causing user-visible `Preview file not found` despite assets being present.
- List/detail state derivation could diverge when `source_archive` became newer than `preview_html`, making completed papers look failed in list views.
- Startup stale cleanup was too aggressive for public papers and risked deleting visible community content after restart.
- Supabase transient transport/timeout failures were not retried broadly enough, causing avoidable request failures.

## What Changes
- Hardened preview HTML generation sanitization for mixed LaTeX/text inputs, including display-math normalization, optional cite parsing, control-command residue stripping, and command-block suppression for unreadable source snippets.
- Added legacy preview read-time sanitization and fallback-serving path so existing readable preview assets are returned even when strict freshness or untranslated-zh heuristics reject regeneration paths.
- Updated paper list assembly to derive status from per-paper asset maps (by asset type) rather than a single latest asset timestamp, aligning list status with detail status.
- Adjusted startup stale cleanup guardrails to preserve public papers while still reconciling interrupted tasks and purging non-success private/removed content; added env toggle for purge execution.
- Expanded async DB retry wrapper to include broader transient HTTP transport/timeout exceptions with bounded backoff.
- Added frontend reader fallback math rendering for `.paper-preview__math-block` when enhancement pipeline fails or does not hydrate KaTeX.

## Impact
- Affected specs:
  - `community-public-read-experience`
  - `community-paper-translation-bridge`
  - `web-api`
  - `web-ui`
- Affected backend code:
  - `backend/app/services/paper_preview_service.py`
  - `backend/app/services/paper_service.py`
  - `backend/app/main.py`
- Affected frontend code:
  - `frontend/src/components/community/PaperPreviewReader.tsx`
- Verification coverage:
  - `backend/tests/unit/test_paper_preview_service.py`
  - `backend/tests/unit/test_papers_preview_bridge.py`
  - `backend/tests/unit/test_papers_list_detail_contract.py`
  - `backend/tests/unit/test_restart_recovery_cleanup.py`
  - `backend/tests/unit/test_community_public_read_experience.py`
  - `backend/tests/unit/test_paper_db_retry.py`
