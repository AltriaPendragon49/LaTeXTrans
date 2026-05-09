## Context
The backend already persists community paper assets and task outputs to COS in object-storage mode, but several hot paths still proxy large objects through the API process. arXiv source archive and original PDF downloads also currently originate from arXiv directly, which is the observed bottleneck during high-concurrency curation.

## Goals
- Route arXiv source archive and original PDF retrieval through COS mirror-origin raw cache.
- Let explicit downloads and thumbnail reads use COS signed URLs where browser behavior is stable.
- Keep iframe PDF preview stable by serving object-storage-backed PDFs through first-party Range-capable inline proxy responses.
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
- Proxy iframe PDF preview routes through the backend with Range forwarding when the source PDF is object-storage-backed, because the current COS default public domain can force `Content-Disposition: attachment`.
- Keep explicit download routes as signed COS redirects when available, where attachment disposition is desired and backend byte proxying would waste bandwidth.
- Generate thumbnails on the backend once, persist the PNG to COS, then redirect future thumbnail requests to COS.

## Risks / Trade-offs
- If COS mirror-origin rules are missing, signed raw-cache URLs may return 404/5xx. Mitigation: keep direct arXiv fallback in backend download paths and make raw cache opt-in.
- COS default-domain browser PDF reads can return `x-cos-force-download: true` and force `Content-Disposition: attachment`, which breaks iframe preview. Mitigation: keep iframe preview on first-party Range proxy responses while still using COS signed redirects for explicit downloads and lightweight assets.
- First-party PDF preview still consumes backend bandwidth. Mitigation: forward Range requests instead of buffering full files, and keep direct COS redirects for explicit downloads.
- Shared raw-cache `source_pdf` assets are not paper-owned objects. Mitigation: paper deletion removes database references and paper-owned artifacts, while shared arXiv cache remains reusable.

## Migration Plan
1. Add backend configuration for raw arXiv COS cache.
2. Configure COS mirror-origin rules for the production bucket prefixes.
3. Deploy backend code with raw cache disabled by default.
4. Enable raw cache in production env after COS rules are verified.
5. Run representative curation/read checks and confirm iframe PDF preview returns first-party inline Range responses while explicit downloads redirect to COS.

## Rollback
- Disable `ARXIV_RAW_CACHE_ENABLED` to restore direct arXiv backend downloads.
- Revert PDF preview proxying to direct COS redirects only if a future COS custom domain is approved and verified for inline iframe preview.
- Existing COS durable assets remain valid because canonical generated artifact paths are unchanged.
