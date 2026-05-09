## 1. OpenSpec
- [x] 1.1 Add proposal, design, tasks, and spec deltas.
- [x] 1.2 Validate the change with strict OpenSpec validation.

## 2. Backend Implementation
- [x] 2.1 Add raw arXiv COS cache configuration and helper service.
- [x] 2.2 Route arXiv source archive and source PDF downloads through raw cache when enabled, with existing direct arXiv fallback.
- [x] 2.3 Make object-storage-backed PDF preview/read routes redirect to signed COS URLs instead of proxying bytes.
- [x] 2.4 Persist generated paper thumbnails to COS and redirect thumbnail reads to signed COS URLs when object storage is active.
- [x] 2.5 Keep source-PDF publishing/backfill from forcing server-side arXiv download when raw cache can represent the source PDF asset.
- [x] 2.6 Update backend file index for any added production files.

## 3. Tests And Verification
- [x] 3.1 Add/update unit tests for raw-cache key/URL generation and fallback behavior.
- [x] 3.2 Add/update API tests for PDF preview redirects and source PDF delivery.
- [x] 3.3 Add/update thumbnail tests for COS persisted delivery.
- [x] 3.4 Run focused backend tests.
- [x] 3.5 Run real backend/browser-facing checks for representative PDF preview/download behavior.
