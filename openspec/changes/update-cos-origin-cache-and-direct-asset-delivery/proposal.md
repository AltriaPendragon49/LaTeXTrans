# Change: Use COS origin cache and direct asset delivery for paper inputs and readers

## Why
Production arXiv intake and public PDF reading can still spend backend bandwidth on large PDF/source transfers even when COS is configured as durable storage. COS should absorb raw arXiv retrieval and browser-facing asset delivery so backend workers only materialize files locally when parsing, translating, compiling, or generating derived artifacts.

## What Changes
- Add a COS-backed arXiv raw cache for source archives and original PDFs.
- Prefer COS raw-cache URLs over direct arXiv URLs for backend source/PDF materialization.
- Deliver object-storage-backed paper PDFs and task preview PDFs by redirecting to signed COS URLs instead of proxying bytes through FastAPI.
- Persist generated paper thumbnail PNGs to COS and redirect browsers to signed COS URLs after the thumbnail exists.
- Keep local files as temporary runtime materialization only; generated artifacts still upload to the existing durable COS locations.

## Impact
- Affected specs: `file-management`, `community-paper-library-storage`, `community-public-read-experience`
- Affected code: backend storage abstraction, arXiv download utilities, paper service, paper/download routes, thumbnail service, source-PDF backfill path, focused backend tests
- Operational impact: production COS bucket needs mirror-origin rules for the configured arXiv raw-cache prefixes and CORS/response-header exposure suitable for browser PDF reads.
