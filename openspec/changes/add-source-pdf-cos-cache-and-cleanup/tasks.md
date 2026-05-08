## 1. Source PDF COS Asset
- [x] 1.1 Add `source_pdf` asset handling to community paper asset serialization/resolution.
- [x] 1.2 Persist original arXiv PDF to COS during successful admin curation publish.
- [x] 1.3 Make source PDF preview/download prefer `source_pdf` before source archive or live arXiv fallback.
- [x] 1.4 Add dry-run-first backfill script for existing published arXiv papers missing `source_pdf`.
- [x] 1.5 Add unit tests for source PDF persistence, route resolution priority, and backfill planning.

## 2. Local Residue Cleanup
- [x] 2.1 Add dry-run-first cleanup/audit script for stale COS-mode local residue.
- [x] 2.2 Add strict path, mode, and age guards so cleanup cannot delete unrelated files.
- [x] 2.3 Add tests for cleanup candidate selection and refusal cases.
- [x] 2.4 Update `backend/file.md` for new backend scripts or materially changed responsibilities.

## 3. Validation
- [x] 3.1 Run targeted unit tests.
- [x] 3.2 Run `openspec validate add-source-pdf-cos-cache-and-cleanup --strict --no-interactive`.
- [ ] 3.3 Deploy code to production and restart backend/worker with COS mode preserved.
- [ ] 3.4 Run cleanup dry-run report on production and review candidates before any execute mode.

## 4. Production Acceptance
- [ ] 4.1 Authenticate as admin `1593120349@qq.com` without exposing credentials in logs or final output.
- [ ] 4.2 Start admin curation for `2407.12818` and `2407.01489`.
- [ ] 4.3 Verify both curation runs publish successfully or record actionable failure cause if external translation/arXiv dependencies fail.
- [ ] 4.4 Verify both published papers have COS-backed `source_pdf`, `source_archive`, `preview_html`, and `translated_pdf` assets where applicable.
- [ ] 4.5 Verify source PDF preview/download, translated PDF, preview HTML, detail, and list routes work after local durable roots remain clean.
- [ ] 4.6 Capture final production DB/COS/storage cleanup audit evidence.
