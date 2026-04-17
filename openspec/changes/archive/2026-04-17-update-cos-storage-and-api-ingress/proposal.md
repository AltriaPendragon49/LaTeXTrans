# Change: Move production assets to COS and restore stable API ingress

## Why
Production currently shows browser-facing failures even when the backend has already generated community paper assets successfully. External clients intermittently fail against `https://api.latextrans.online` during connection setup, while the same origin remains healthy from the server itself. In parallel, production still treats local disk as the canonical source for runtime and community paper assets, which makes the deployment stateful, keeps large files on the server, and amplifies fragile read paths such as oversized paper-detail payloads.

## What Changes
- Route the production API through a Cloudflare-managed ingress path instead of relying on direct public browser access to the CVM origin TLS endpoint.
- Introduce a storage abstraction that supports `local_disk` and Tencent COS, with production using COS as the canonical store and local disk only as a temporary cache.
- Upload runtime artifacts and community paper assets to COS, then clear the production cache after successful persistence.
- Keep local development fully supported without COS by falling back to the existing on-disk storage layout.
- Change public paper-reading APIs so detail payloads stay lightweight and asset delivery can resolve through object storage instead of requiring large inlined payloads or permanent origin files.

## Impact
- Affected specs:
  - `deployment-infra`
  - `community-paper-library-storage`
  - `community-public-read-experience`
  - `web-api`
- Affected code:
  - `backend/app/core/config.py`
  - `backend/app/services/paper_service.py`
  - `backend/app/api/routes/papers.py`
  - `backend/app/api/routes/download.py`
  - deployment scripts and production environment configuration
