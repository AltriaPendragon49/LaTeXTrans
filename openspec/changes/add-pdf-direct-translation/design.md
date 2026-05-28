## Context
The product already exposes local LaTeX daily quota and NiuTrans PDF direct-translation credits in the authenticated account block. The PDF interface document describes a separate paper-translation API that supports editable PDF upload, English-to-Chinese translation, progress query, cancellation, and translated-PDF download.

The existing `/translate` workspace has three top-level-looking options: `arXiv 编号`, `本地上传`, and `批量翻译`. Those are all LaTeX-source translation modes and should become second-level options under `LaTeX 翻译`. `PDF 直译` becomes a sibling first-level workflow with its own UI and backend service path.

## Goals
- Preserve the current LaTeX translation behavior and quota model.
- Add a clear PDF direct-translation path for authenticated users.
- Proxy the NiuTrans paper-translation API through our backend so secrets and upstream auth material never reach the browser.
- Track upstream `fileNo`, page count, progress, status, failure code, and translated PDF delivery in the current product's task/status model.
- Consume and display PDF direct-translation credits independently from local LaTeX quota.

## Non-Goals
- Do not translate scanned or image-only PDFs in the first release; the upstream document states that only editable PDFs are supported.
- Do not support bilingual output, parsed-file downloads, or source-file downloads for PDF direct translation in the first release.
- Do not reuse the LaTeX parser, LaTeX compiler, RAG terminology pipeline, or origin CLI parity kernel for PDF direct translation.
- Do not make PDF direct translation available to guests unless a later approved spec explicitly changes the authentication policy.

## Decisions
- UI uses two first-level choices: `LaTeX 翻译` and `PDF 直译`. Inside `LaTeX 翻译`, the existing `arXiv 编号`, `本地上传`, and `批量翻译` controls are wrapped in a second-level option container.
- The backend exposes first-party `/api/pdf-direct/*` endpoints and a service adapter that calls the NiuTrans upstream endpoints:
  - upload/page count: `paperUploadAndGetPageNum`
  - start translation: `transPaperFile`
  - status query: `getInfo`
  - cancel: `interrupt`
  - translated PDF download: `download` with `type=1`
- The service signs upstream calls server-side using configured document API credentials. The auth string follows the documented rule: sort non-empty parameters plus `apikey` by ASCII parameter name, omit `authStr` and file fields, then MD5 the joined key-value string.
- The product stores only safe operational metadata: local task id, user id, upstream `fileNo`, page count, file name/size, progress, status, failure cause/code, timestamps, and local/COS artifact references. It does not persist raw upstream tokens, apikeys, passwords, or browser-visible signed auth strings.
- PDF direct task progress maps upstream statuses `101`, `103`, `104`, `105`, and `106` to product states such as uploaded/not-started, processing, canceled, completed, and failed.
- PDF direct translation is billed to the logged-in user's own NiuTrans PDF direct-translation credits. The backend must not deduct local LaTeX daily quota for PDF direct translation. Credit checks use the user's NiuTrans balance snapshot where available and upstream rejection codes as the source of truth. After upload/start/completion/failure responses, the backend refreshes the PDF direct credit snapshot when feasible.
- The existing login integration already verifies credentials through the NiuTrans login endpoint and uses the returned `token` plus `userId` as `Authorization` and `Niutrans-userid` headers for `getUserInfo`. That user-info response includes `unusedNumIntegral`, `unusedNumPage`, and the user's `apikey`. PDF direct implementation should reuse this authenticated user-info chain to obtain the logged-in user's current credit/page snapshot and signing material server-side, without returning raw upstream token, password, or apikey fields to the browser.
- The first release does not expose `dictNo`, `memoryNo`, or `realmCode` controls. It sends the upstream default realm behavior by omitting `realmCode` or using `0`, and omits dictionary/memory parameters unless a later approved spec adds those UI controls.
- The provided PDF API document lists size/page/page-size limit error codes but does not provide numeric limits. The first release therefore should not invent hardcoded frontend numeric limits from guesswork; it should validate PDF file type locally, then surface structured upstream limit errors for file size, page count, and page size.
- When user credits are insufficient, the API returns a stable PDF direct credit error and the UI shows a localized reminder with an action that opens `https://niutrans.com/` for NiuTrans account recharge or management.

## Risks / Trade-offs
- Upstream credit deduction timing is not fully described by the PDF document. The first release should surface accepted/rejected upstream results and refresh balance snapshots instead of attempting local pre-deduction.
- Upstream only supports English-to-Chinese for this endpoint. The UI should make this fixed language pair explicit and avoid offering unsupported language controls for PDF direct translation.
- Long-running upstream tasks require polling. We should reuse the current task status/SSE pattern if practical, but polling every 2 seconds is acceptable if SSE fan-out is not yet available for the new task type.
- The account system is already connected to NiuTrans login/user-info, while the PDF document API excerpt documents `appId` plus `apikey` signing but the login/user-info document only confirms that `getUserInfo` returns the user's `apikey`. Implementation must confirm the exact source of the `appId` used with the logged-in user's signing material.

### Resolved: `appId` and `apikey` for Document API Signing
- **`appId`** is a product-level configuration value. It identifies the "文档翻译 API" application registered on the NiuTrans platform and is the same for all users. Configured server-side as `NIUTRANS_DOC_API_APP_ID`.
- **`apikey`** is per-user, obtained from `getUserInfo` during login. The backend stores the user's `apikey` encrypted in the database. Using the user's `apikey` in the auth string ensures upstream billing is charged to the logged-in user's NiuTrans account.
- Rationale: `getUserInfo` returns `apikey` but not `appId`; both are described as visible in "控制台-个人中心" but `appId` is an application-level identifier (like an OAuth client id), while `apikey` is the user's personal credential. This matches the standard third-party-app-using-user-credentials pattern.

### Resolved: Upstream Token and `apikey` Persistence
- The existing `NiuTransAuthClient.fetch_user_info_balance` method currently extracts only `unusedNumIntegral`. It SHALL be extended to also extract `apikey` and `unusedNumPage` from the `getUserInfo` response.
- The user's `apikey` SHALL be stored encrypted (using the existing `encryption_key` config) in a new column on the `users` table or a dedicated credential table. The upstream NiuTrans login `token` does NOT need to be persisted beyond the login flow — it is only needed once to call `getUserInfo` and fetch the `apikey`.
- For subsequent PDF direct operations, the backend reads the stored encrypted `apikey` directly. If the `apikey` is missing or upstream returns `21000` (鉴权失败), the backend returns a stable error prompting the user to re-login.
- The `niutrans_balance_snapshots` table SHALL be extended with an `unused_num_page` column to track page-based credits alongside the existing `unused_num_integral`.

### Resolved: Download Delivery via COS
- When a PDF direct task reaches `transStatus=105` (completed), the backend SHALL download the translated PDF from the upstream `download` endpoint (`type=1`) and store it in COS under `{cos_base_prefix}/pdf-direct/{user_id}/{fileNo}/translated.pdf`.
- Subsequent download requests from the user SHALL return a COS signed URL instead of re-fetching from upstream.
- This strategy also mitigates upstream file expiry: once the translated PDF is cached in COS, it remains available regardless of upstream `expireTime`.

### Resolved: PDF Direct Task Data Model
- A new `pdf_direct_tasks` table SHALL be created (the existing LaTeX task tables are semantically different and cannot safely represent upstream `fileNo` and document-specific metadata).
- Stored metadata includes: local task id, user id, upstream `fileNo`, file name, file size, page count, progress, transStatus, transFailureCause, transFailureCode, COS artifact key, timestamps.
- No upstream tokens, apikeys, passwords, or auth strings SHALL be stored in this table.

### Resolved: Polling Strategy
- PDF direct task status SHALL be polled every 2 seconds while the task is in `transStatus=103` (processing).
- Maximum polling duration SHALL be bounded by the global `pipeline_timeout_seconds` config (default 1800s). After timeout, the task SHALL be marked as failed with a timeout cause.
- The frontend SHALL use the existing task-status polling or SSE pattern. If SSE fan-out is not yet available for the new task type, 2-second polling is acceptable.

### Resolved: Post-Upload Pre-Start State
- After a successful upload (`paperUploadAndGetPageNum`), the local task SHALL enter `transStatus=101` (未翻译/ready). The user can inspect the page count and decide whether to start translation.
- If the user navigates away without starting, the task remains in the ready state. The frontend SHALL show the uploaded task in the user's task list with a "start translation" action.

## Open Questions
(None remaining — all questions resolved through document analysis and codebase inspection.)

## Migration Plan
1. Add backend configuration for NiuTrans document translation API: `NIUTRANS_DOC_API_BASE_URL`, `NIUTRANS_DOC_API_APP_ID`, timeout, and feature-availability flag.
2. Extend `fetch_user_info_balance` to also extract `apikey` and `unusedNumPage` from the `getUserInfo` response.
3. Add encrypted `apikey` column to `users` table (or a dedicated credential table); add `unused_num_page` column to `niutrans_balance_snapshots`.
4. Create `pdf_direct_tasks` table for PDF direct task metadata.
5. Add backend service adapter for upload/page-count, start, status, interrupt, and translated-PDF download — including COS upload on completion.
6. Add first-party `/api/pdf-direct/*` routes with local-auth protection and stable product error codes.
7. Update frontend workspace routing/state, i18n resources, and authenticated quota refresh behavior.
8. Add unit/integration tests with mocked upstream responses and frontend workflow tests.

## Rollback
Disable or hide the `PDF 直译` first-level option while leaving the LaTeX second-level grouping intact. Backend routes can remain deployed but return a configured-unavailable response if document API credentials are missing.
