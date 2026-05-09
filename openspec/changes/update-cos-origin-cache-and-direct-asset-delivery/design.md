## Context
The backend already persists community paper assets and task outputs to COS in object-storage mode, but several hot paths still proxy large objects through the API process. arXiv source archive and original PDF downloads also currently originate from arXiv directly, which is the observed bottleneck during high-concurrency curation.

## Goals
- Route arXiv source archive and original PDF retrieval through COS mirror-origin raw cache.
- Let browsers read object-storage-backed PDFs and thumbnails directly from COS signed URLs.
- Keep backend local disk usage limited to runtime materialization for parsing, compiling, thumbnail generation, and upload staging.
- Preserve existing local-disk behavior and current API route contracts.

## Non-Goals
- Rework source HTML/image delivery in this change. arXiv HTML is lighter and has a more complex relative-asset signing problem.
- Change authentication, paper visibility, curation queue semantics, or LLM/compile concurrency.
- Require raw COS secrets in code or responses.

## Decisions
- Add a small `arxiv_raw_cache` service that owns raw-cache enablement checks, object key construction, and signed URL generation.
- Use raw-cache object keys under an optional configurable prefix, defaulting to root-level `pdf/<arxiv_id>.pdf` and `e-print/<arxiv_id>` paths so COS mirror-origin can map object keys directly to arXiv paths.
- In COS mode, `source_pdf` assets for arXiv papers may point at the shared raw-cache PDF object instead of forcing a paper-owned duplicate copy.
- Redirect PDF preview/read routes to signed COS URLs when available; keep local file serving and arXiv proxy fallbacks for non-COS or unconfigured deployments.
- Generate thumbnails on the backend once, persist the PNG to COS, then redirect future thumbnail requests to COS.

## Risks / Trade-offs
- If COS mirror-origin rules are missing, signed raw-cache URLs may return 404/5xx. Mitigation: keep direct arXiv fallback in backend download paths and make raw cache opt-in.
- Browser PDF direct reads depend on COS Range behavior and CORS/response headers. Mitigation: configure COS for GET/HEAD/Range use and verify with real PDF iframe/API checks.
- Shared raw-cache `source_pdf` assets are not paper-owned objects. Mitigation: paper deletion removes database references and paper-owned artifacts, while shared arXiv cache remains reusable.

## Migration Plan
1. Add backend configuration for raw arXiv COS cache.
2. Configure COS mirror-origin rules for the production bucket prefixes.
3. Deploy backend code with raw cache disabled by default.
4. Enable raw cache in production env after COS rules are verified.
5. Run representative curation/read checks and confirm public PDF routes redirect instead of streaming through backend.

## Rollback
- Disable `ARXIV_RAW_CACHE_ENABLED` to restore direct arXiv backend downloads.
- Revert PDF preview redirects to existing proxy behavior if a client/browser issue is observed.
- Existing COS durable assets remain valid because canonical generated artifact paths are unchanged.
