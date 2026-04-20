# Change: Reset duplicate admin arXiv curation before re-import

## Why
The current admin arXiv curation flow reuses the existing canonical `paper_id` when the same `arXiv ID` is curated again. That keeps old job history, assets, and task records mixed with the new run, which makes operator history hard to reason about and can leave stale records attached to the next intake attempt.

## What Changes
- Detect duplicate admin arXiv curation at submission time when the same `arXiv ID` already has a canonical paper or prior curation history.
- Hard-delete the existing paper, assets, structured insights, similar recommendations, curation-job records, translation-task records, retained failed artifacts, and run-scoped local files before creating the new curation job.
- Cancel any in-flight in-memory admin curation worker for the duplicated `arXiv ID` before deletion so the old run cannot publish after cleanup.
- Create the replacement admin curation job with a fresh `paper_id` only after the pre-delete completes successfully.

## Impact
- Affected specs: `community-paper-intake-api`, `community-admin-curation`
- Affected code: `backend/app/services/paper_service.py`, `backend/app/repositories/community_paper_repository.py`, `backend/tests/unit/test_admin_curation_lifecycle.py`, `backend/file.md`
