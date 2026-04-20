# Change: update translated PDF canonical delivery

## Why
Translated PDF reads are much slower and less reliable than source PDF reads because the public preview path can still recover assets, download full PDFs from object storage, and trim leading blank pages while the user is waiting. We need translated PDF delivery to feel like source PDF delivery without removing the mandatory blank-page trimming behavior.

## What Changes
- Move translated PDF leading-blank-page trimming out of the public read path and into canonical asset preparation.
- Treat the trimmed translated PDF as the canonical public delivery asset for community papers.
- Keep public translated PDF preview and download reads on a lightweight path that only resolves an already-prepared delivery asset.
- Add an operator backfill entry point so existing community papers can be upgraded in place without full re-curation.

## Impact
- Affected specs: `community-public-read-experience`, `community-paper-library-storage`
- Affected code: `backend/app/services/paper_service.py`, `backend/app/api/routes/papers.py`, `backend/app/repositories/community_paper_repository.py`, `backend/scripts/*`
