## 1. Ingress and Runtime Design
- [x] 1.1 Add production storage configuration for COS mode, cache directories, and object-key prefix conventions.
- [x] 1.2 Define the Cloudflare-managed API ingress cutover steps and production validation checklist.

## 2. Storage Backend Implementation
- [x] 2.1 Introduce a backend storage abstraction that supports `local_disk` and `cos`.
- [x] 2.2 Make runtime uploads, outputs, and community paper asset persistence backend-aware.
- [x] 2.3 Upload retained production artifacts to COS and delete local cache copies after successful persistence.
- [x] 2.4 Keep local development working without COS by preserving local-disk fallback behavior.

## 3. Community Read and Delivery Paths
- [x] 3.1 Update paper asset resolution for previews, downloads, and runtime recovery to support `object_storage`.
- [x] 3.2 Slim the paper-detail API so it returns lightweight reader bootstrap metadata and asset locators.
- [x] 3.3 Update frontend/community reader flows to load preview and PDF assets through the new delivery contract.

## 4. Verification
- [x] 4.1 Add or update unit/integration coverage for local-disk mode and COS mode.
- [x] 4.2 Verify admin curation, community homepage, paper detail, translated PDF, and delete/cleanup flows under object storage.
- [x] 4.3 Verify external browser access to `https://api.latextrans.online` after Cloudflare ingress cutover.
