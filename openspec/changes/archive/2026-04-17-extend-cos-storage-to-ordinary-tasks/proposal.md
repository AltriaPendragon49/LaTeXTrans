# Change: Extend COS storage to ordinary translation tasks

## Why
Ordinary translation tasks still treat `data/uploads` and `data/outputs` as long-lived local disk state, while community-paper assets already use COS. This creates split storage semantics, leaves historical runtime artifacts on the server, and blocks the desired deployment model where COS is the durable source of truth.

## What Changes
- Store ordinary task upload sources and translation outputs in COS when `STORAGE_BACKEND_MODE=cos`
- Keep local task files as temporary runtime cache only, and clear them after durable COS persistence
- Preserve existing API surface while changing ordinary-task download endpoints to signed COS delivery and keeping preview endpoints backend-proxied
- Add durable output manifest metadata so ordinary-task downloads and previews can resolve COS artifacts without relying on local disk
- Keep compatibility for local-disk mode and for history/task persistence records

## Impact
- Affected specs: `file-management`, `web-api`
- Affected code: ordinary task upload/arXiv/translate/download routes, task storage helpers, storage backend abstraction, task recovery logic, and related unit tests

## Production Validation Status
- Production backend was deployed and verified on Tencent Cloud during implementation
- Anonymous ordinary-task arXiv flow was exercised against `2503.12345`
- COS-backed source persistence, COS-backed source hydration, COS-backed output persistence, and signed download delivery were all verified end-to-end
- Follow-up production fixes were required for:
  - COS hydration when object listings returned keys prefixed by `cos_base_prefix`
  - `promptbox` environment wrapper preservation during translation
- After those fixes, the production task `2503.12345-0417-1724-59e5c4b4-29c3-4180-9af0-292f0b629f60` completed as `completed_with_warnings`
- Remaining issues observed on that paper are translation/compile quality problems in the translation kernel, not blockers for the COS storage migration itself
