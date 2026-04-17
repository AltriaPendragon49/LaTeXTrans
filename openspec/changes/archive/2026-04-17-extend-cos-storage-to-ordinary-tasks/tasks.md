## 1. Specification
- [x] 1.1 Add delta specs for ordinary-task COS-backed upload/output persistence and API delivery semantics
- [x] 1.2 Validate the OpenSpec change in strict mode

## 2. Implementation
- [x] 2.1 Add ordinary-task storage helpers for syncing task sources/outputs between local runtime cache and COS
- [x] 2.2 Update upload and arXiv ingestion flows to persist ordinary-task sources to COS in object-storage mode
- [x] 2.3 Update translation and output-reuse flows to hydrate from COS, persist terminal outputs back to COS, and clean local cache
- [x] 2.4 Update ordinary-task preview/download flows to use backend proxy for previews and signed URLs for downloads in object-storage mode
- [x] 2.5 Fix production COS hydration for object listings that include the configured `cos_base_prefix`
- [x] 2.6 Fix production `promptbox` environment translation to preserve source wrappers and avoid false structure-guard failures

## 3. Verification
- [x] 3.1 Add or update unit tests for ordinary-task object storage helpers and API behavior
- [x] 3.2 Run focused backend unit tests covering the new storage semantics
- [x] 3.3 Deploy the change to the Tencent Cloud production backend and verify health after restart
- [x] 3.4 Exercise the anonymous ordinary-task arXiv flow against `2503.12345` and verify COS-backed source/output handling end-to-end
- [x] 3.5 Verify signed COS download delivery for ordinary-task translated PDF, translated source archive, and terminology CSV
