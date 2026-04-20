## 1. Spec and planning
- [x] 1.1 Validate the OpenSpec change and keep the modified repeated-curation requirements aligned with the approved “delete first, then recreate” behavior.

## 2. Backend duplicate-reset orchestration
- [x] 2.1 Add repository support for listing admin curation jobs by `arXiv ID` in created-order so the service can reset prior history deterministically.
- [x] 2.2 Add service helpers that cancel active matching curation workers, hard-delete any published paper for the duplicate `arXiv ID`, and delete failed/incomplete curation traces before reinserting a new job.
- [x] 2.3 Update admin arXiv batch submission to run the duplicate reset before job insertion and to assign a fresh `paper_id` after the reset succeeds.

## 3. Regression coverage and index maintenance
- [x] 3.1 Add unit tests that prove repeated admin arXiv intake deletes old completed and failed traces and then creates a new job with a new `paper_id`.
- [x] 3.2 Update `backend/file.md` for any backend responsibility changes introduced by the new reset helpers.
- [x] 3.3 Run focused backend tests plus `openspec validate update-admin-curation-repeat-arxiv-reset --strict --no-interactive`.
