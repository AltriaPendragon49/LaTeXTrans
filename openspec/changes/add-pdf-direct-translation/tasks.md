## 1. Backend Contract
- [ ] 1.1 Add server-side NiuTrans document API configuration for `NIUTRANS_DOC_API_BASE_URL`, `NIUTRANS_DOC_API_APP_ID`, timeout, and feature-availability flag (`PDF_DIRECT_TRANSLATION_ENABLED`).
- [ ] 1.2 Implement auth string generation exactly as documented (sort non-empty params + apikey by ASCII name, MD5, omit authStr and file fields), with tests.
- [ ] 1.3 Extend `NiuTransAuthClient.fetch_user_info_balance` to also extract `apikey` and `unusedNumPage` from the `getUserInfo` response; store encrypted `apikey` in the `users` table (or a dedicated credentials table) during login.
- [ ] 1.4 Add `unused_num_page` column to `niutrans_balance_snapshots`; extend `TranslationQuotaService` and related repository to include `unusedNumPage` in PDF direct snapshots returned to the frontend.
- [ ] 1.5 Create `pdf_direct_tasks` table with columns: local task id, user id, upstream `fileNo`, file name, file size (KB), page count, progress (0.00–1.00), transStatus, transFailureCause, transFailureCode, COS artifact key, timestamps. Never store upstream tokens, apikeys, or auth strings.
- [ ] 1.6 Implement PDF direct translation service adapter for upload/page count, start, status, interrupt, and translated-PDF download — using product `appId` + user's stored `apikey` for signing.
- [ ] 1.7 On task completion (transStatus=105), download translated PDF from upstream and upload to COS under `{cos_base_prefix}/pdf-direct/{user_id}/{fileNo}/translated.pdf`; persist COS key.
- [ ] 1.8 Add first-party `/api/pdf-direct/*` routes with local-auth protection and stable product error codes covering: all documented upstream error codes, file validation errors, limit errors, rate-limit/busy errors, auth errors, not-found/expiry, page-count-pending, and timeout.
- [ ] 1.9 Ensure PDF direct translation is billed against the logged-in user's NiuTrans credits and never the local LaTeX daily quota.
- [ ] 1.10 Refresh the authenticated user's PDF direct credit snapshot (both `unusedNumIntegral` and `unusedNumPage`) after accepted or terminal PDF direct operations when feasible.
- [ ] 1.11 Return a stable insufficient-PDF-credit error with a `https://niutrans.com/` account-management URL when the user's credits are insufficient.
- [ ] 1.12 Return a stable `PDF_DIRECT_CREDENTIAL_UNAVAILABLE` error when the user's stored `apikey` is missing, prompting re-login.
- [ ] 1.13 Implement task timeout: mark tasks as failed if `transStatus=103` exceeds `pipeline_timeout_seconds`; handle upstream `expireTime` by transitioning to an expired terminal state.

## 2. Frontend Workflow
- [ ] 2.1 Rework the translation workspace to show `LaTeX 翻译` and `PDF 直译` as first-level options.
- [ ] 2.2 Wrap the existing `arXiv 编号`, `本地上传`, and `批量翻译` controls as second-level options under `LaTeX 翻译`.
- [ ] 2.3 Add the authenticated PDF direct workspace with PDF upload, page-count preview, fixed English-to-Chinese indication, start action, progress/status display, cancel action, and translated-PDF download.
- [ ] 2.4 Show uploaded-but-not-started tasks in the user's task list with a "start translation" action (transStatus=101 ready state).
- [ ] 2.5 Keep `dictNo`, `memoryNo`, and `realmCode` out of the first-release UI; use upstream default realm behavior instead.
- [ ] 2.6 Gate PDF direct translation for unauthenticated users with the existing local login flow.
- [ ] 2.7 Add an insufficient-credit reminder with an action that opens `https://niutrans.com/`.
- [ ] 2.8 Add a re-login prompt when the backend returns `PDF_DIRECT_CREDENTIAL_UNAVAILABLE`.
- [ ] 2.9 Display PDF direct credits (integral + page count) separately from local LaTeX quota in the account block and workspace header.
- [ ] 2.10 Add centralized i18n copy for the new UI, errors, quota messages, and accessibility labels.

## 3. Verification
- [ ] 3.1 Add backend unit tests for upstream adapter: request signing (sorted params, empty-field omission, MD5 output), status mapping, and error code mapping for all documented upstream codes.
- [ ] 3.2 Add backend route tests for auth gating, upload validation, quota independence, cancellation, download delivery, COS caching, credential-missing rejection, and task timeout/expiry with mocked upstream responses.
- [ ] 3.3 Add backend unit tests for `apikey` encryption-at-rest, `unusedNumPage` snapshot persistence, and `pdf_direct_tasks` CRUD operations.
- [ ] 3.4 Add frontend component/store tests for first-level/second-level option behavior, PDF direct state transitions (ready→processing→completed/canceled/failed/expired), and re-login prompt.
- [ ] 3.5 Run frontend typecheck/tests and backend targeted tests.
- [ ] 3.6 Manually verify a mocked end-to-end PDF direct flow: upload→page count→start→poll to success→COS cache→download translated PDF→quota snapshot refresh (both integral and page count).
