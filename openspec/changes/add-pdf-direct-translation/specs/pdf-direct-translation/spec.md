## ADDED Requirements
### Requirement: PDF Direct Translation Service
The system SHALL provide an authenticated PDF direct-translation workflow that uploads editable PDF files to the NiuTrans paper-translation API and returns translated PDF output without invoking the LaTeX translation pipeline.

#### Scenario: Authenticated user uploads editable PDF for page count
- **WHEN** an authenticated user uploads a PDF through the PDF direct-translation workflow
- **THEN** the backend SHALL call the upstream `paperUploadAndGetPageNum` endpoint with server-side credentials
- **AND** it SHALL return a local PDF-direct task identifier, upstream `fileNo`, and `pageNum`
- **AND** it SHALL persist only safe metadata needed for later status and download operations.

#### Scenario: User starts PDF direct translation
- **WHEN** an authenticated user starts translation for a previously uploaded PDF direct task
- **THEN** the backend SHALL call the upstream `transPaperFile` endpoint using that task's `fileNo`
- **AND** the request SHALL use the supported language pair English to Chinese
- **AND** the first release SHALL omit `dictNo` and `memoryNo`
- **AND** the first release SHALL use upstream default realm behavior by omitting `realmCode` or sending `realmCode=0`
- **AND** the request SHALL NOT start the LaTeX parser, compiler, RAG terminology pipeline, or origin CLI parity kernel.

#### Scenario: PDF direct task completes
- **WHEN** the upstream status query reports `transStatus=105`
- **THEN** the product task SHALL be treated as completed
- **AND** the user SHALL be able to download the translated PDF through the current application's backend.

### Requirement: PDF Direct Translation Status Mapping
The system SHALL map upstream PDF direct-translation statuses and failures into stable product task states and user-visible failure messages.

#### Scenario: Upstream translation is in progress
- **WHEN** the upstream `getInfo` response reports `transStatus=103`
- **THEN** the product task SHALL remain processing
- **AND** the product progress SHALL derive from the upstream `progress` field.

#### Scenario: Upstream translation is terminated
- **WHEN** the upstream `getInfo` response reports `transStatus=104`
- **THEN** the product task SHALL be treated as canceled
- **AND** the UI SHALL stop polling or streaming that task.

#### Scenario: Upstream translation fails
- **WHEN** the upstream `getInfo` response reports `transStatus=106`
- **THEN** the product task SHALL be treated as failed
- **AND** the backend SHALL preserve safe `transFailureCause` and `transFailureCode` fields for diagnostics and localized UI copy.

#### Scenario: Upstream returns known limit or credit errors
- **WHEN** upstream upload, start, status, or download returns documented codes such as `20017` (可用页数不足), `110019` (可用页数或积分不足), or `110020` (可用积分不足)
- **THEN** the backend SHALL return a stable product error indicating insufficient PDF direct-translation pages or credits
- **AND** the backend SHALL NOT report the error as local LaTeX daily quota exhaustion.

#### Scenario: Upstream returns file validation errors
- **WHEN** upstream upload returns `20004` (不支持的文件类型), `210011` (文件类型错误或文件已损坏), `110024` (加密或被保护的文件), `110025` (损坏的文档), or `110029` (未检测到可翻译内容)
- **THEN** the backend SHALL map each to a stable PDF direct validation error with a distinct product error code
- **AND** the UI SHALL show localized guidance based on the structured code.

#### Scenario: Upstream returns file size or page limit errors
- **WHEN** upstream returns `20005` (文件大小超出限制), `210013` (文件超出页数限制), `210014` (文件大小超出限制), or `210015` (文件页面大小超出限制)
- **THEN** the backend SHALL map each to a stable PDF direct limit error
- **AND** the response SHALL include the limit type but NOT fabricate numeric thresholds.

#### Scenario: Upstream returns rate-limit or busy errors
- **WHEN** upstream returns `20022` (请求频繁), `22001` (系统繁忙), or `110000` (系统繁忙)
- **THEN** the backend SHALL return a stable retryable PDF direct error
- **AND** the response SHALL indicate the operation can be retried after a brief delay.

#### Scenario: Upstream returns auth or permission errors
- **WHEN** upstream returns `21000` (鉴权失败) or `20006` (没有该文件操作权限)
- **THEN** the backend SHALL return a stable PDF direct auth error
- **AND** for `21000` the error SHALL indicate the user should re-login to refresh credentials
- **AND** for `20006` the backend SHALL reject the request as a permission error.

#### Scenario: Upstream returns file-not-found or expiry errors
- **WHEN** upstream returns `20003` or `110021` (文件信息不存在、被删除或已过期)
- **THEN** the backend SHALL return a stable PDF direct not-found error
- **AND** the local task SHALL transition to a terminal expired state.

#### Scenario: Upstream reports page count still computing
- **WHEN** upstream returns `20023` (文件页数获取中,请稍后重试)
- **THEN** the backend SHALL return a stable retryable error indicating page count is not yet ready
- **AND** the frontend SHALL poll or offer a retry action.

### Requirement: PDF Direct Translation Cancellation
The system SHALL allow authenticated users to request cancellation of their own running PDF direct-translation tasks.

#### Scenario: User cancels running PDF direct task
- **WHEN** an authenticated user requests cancellation for their own PDF direct task
- **THEN** the backend SHALL call the upstream `interrupt` endpoint with that task's `fileNo`
- **AND** a successful upstream cancellation SHALL transition the local task to canceled.

#### Scenario: User cannot cancel someone else's PDF direct task
- **WHEN** an authenticated user requests cancellation for a PDF direct task owned by another user
- **THEN** the backend SHALL reject the request
- **AND** it SHALL NOT call the upstream interrupt endpoint.

### Requirement: PDF Direct Translation Output Delivery
The system SHALL deliver only translated PDF output for PDF direct-translation tasks in the first release. Translated PDFs SHALL be cached in COS on completion and served from COS thereafter.

#### Scenario: Translated PDF cached to COS on completion
- **WHEN** the backend detects a PDF direct task has reached `transStatus=105` (completed)
- **THEN** it SHALL download the translated PDF from the upstream `download` endpoint with `type=1`
- **AND** it SHALL store the result in COS under `{cos_base_prefix}/pdf-direct/{user_id}/{fileNo}/translated.pdf`
- **AND** it SHALL persist the COS object key on the local task record.

#### Scenario: Download completed translated PDF from COS
- **WHEN** an authenticated owner requests download for a completed PDF direct task
- **THEN** the backend SHALL return a COS signed URL for the cached translated PDF
- **AND** it SHALL NOT re-fetch from upstream on each download request.

#### Scenario: Download before completion
- **WHEN** a user requests download for a PDF direct task that is not completed
- **THEN** the backend SHALL reject the request with a stable not-ready error
- **AND** it SHALL NOT call unsupported bilingual, parsed-file, or source-file download paths.

#### Scenario: Upstream file expired but COS cache available
- **WHEN** a user requests download and the upstream file has expired but the translated PDF is cached in COS
- **THEN** the backend SHALL still return a COS signed URL
- **AND** the download SHALL succeed regardless of upstream file expiry.

### Requirement: PDF Direct Translation User Credit Billing
PDF direct translation SHALL be charged against the logged-in user's own NiuTrans PDF direct-translation credits and SHALL NOT consume the local daily LaTeX translation quota.

#### Scenario: Backend obtains logged-in user's NiuTrans billing context
- **WHEN** the backend prepares a PDF direct-translation upstream request for an authenticated local user
- **THEN** it SHALL resolve that user's stored encrypted `apikey` from the database
- **AND** if the `apikey` is missing or empty, it SHALL return a stable error prompting the user to re-login
- **AND** it SHALL sign upstream document API requests using the product-level `appId` plus the user's `apikey`
- **AND** it SHALL NOT return the apikey, appId, or generated authStr to the browser.

#### Scenario: User apikey is not available
- **WHEN** the backend needs the user's `apikey` for a PDF direct operation but the stored `apikey` is missing
- **THEN** it SHALL return a stable `PDF_DIRECT_CREDENTIAL_UNAVAILABLE` error
- **AND** the UI SHALL prompt the user to re-login to refresh their credentials.

#### Scenario: Non-admin starts PDF direct translation
- **WHEN** an authenticated non-admin user starts PDF direct translation
- **THEN** the backend SHALL NOT reserve or increment the local daily LaTeX translation quota
- **AND** the task SHALL rely on the logged-in user's NiuTrans PDF direct-translation credit availability and upstream acceptance.

#### Scenario: User has insufficient PDF direct credits
- **WHEN** the logged-in user's NiuTrans PDF direct-translation credits are insufficient for a PDF direct operation
- **THEN** the backend SHALL reject or surface the upstream rejection as a stable insufficient-PDF-credit product error
- **AND** the response SHALL include enough structured data for the frontend to show a recharge/account-management action.

#### Scenario: PDF direct operation updates quota snapshot
- **WHEN** a PDF direct upload, start, terminal status, or credit-related failure is processed
- **THEN** the backend SHOULD refresh the user's NiuTrans `unusedNumIntegral` and `unusedNumPage` snapshot when feasible
- **AND** the frontend SHALL keep displaying PDF direct credits (integral and page count) separately from local LaTeX quota.

### Requirement: PDF Direct Translation Security Boundary
The system SHALL keep upstream document API credentials and signing details inside the backend trust boundary.

#### Scenario: Browser submits PDF direct request
- **WHEN** the frontend uploads a PDF or starts a PDF direct task
- **THEN** the browser SHALL send only the current application's local auth token and user-selected file/workflow fields
- **AND** it SHALL NOT receive upstream appId, apikey, authStr, raw upstream login token, or password-like fields.

#### Scenario: Backend signs upstream request
- **WHEN** the backend calls a NiuTrans document API endpoint
- **THEN** it SHALL generate `authStr` server-side from non-empty request parameters plus `apikey`
- **AND** it SHALL exclude `authStr` and file content fields from the signature as documented.

### Requirement: PDF Direct Translation Limit Handling
The system SHALL rely on documented upstream PDF direct-translation limit responses when numeric file-size, page-count, or page-size limits are not available from the provided interface document.

#### Scenario: Frontend validates PDF type only before upload
- **WHEN** a user selects a file for PDF direct translation
- **THEN** the frontend SHALL require a PDF file
- **AND** it SHALL NOT block by hardcoded numeric page count, file size, or page-size thresholds unless those thresholds are later confirmed from upstream documentation or configuration.

#### Scenario: Upstream returns file or page limit error
- **WHEN** upstream returns documented limit codes such as file size exceeded, page limit exceeded, or page-size exceeded
- **THEN** the backend SHALL map the response to a stable PDF direct validation error
- **AND** the UI SHALL show localized guidance based on the structured error code.

### Requirement: PDF Direct Translation Task Lifecycle
The system SHALL manage PDF direct tasks through a well-defined lifecycle: uploaded-ready, processing, completed, canceled, failed, and expired.

#### Scenario: Task enters ready state after upload
- **WHEN** an authenticated user uploads a PDF and the upstream returns `fileNo` and `pageNum`
- **THEN** the local task SHALL be created in a ready state (mapped from upstream `transStatus=101`)
- **AND** the frontend SHALL display the page count and a "start translation" action
- **AND** the user MAY navigate away and return later to start translation.

#### Scenario: Task times out during processing
- **WHEN** a PDF direct task remains in `transStatus=103` (processing) for longer than the configured `pipeline_timeout_seconds` (default 1800s)
- **THEN** the backend SHALL mark the local task as failed with a timeout cause
- **AND** the frontend SHALL stop polling and display a timeout message.

#### Scenario: Upstream task expires
- **WHEN** a PDF direct task's upstream `expireTime` has passed and the task is not yet completed
- **THEN** the backend SHALL transition the local task to an expired state
- **AND** the frontend SHALL remove active actions for that task.

### Requirement: PDF Direct Task Data Model
The system SHALL persist PDF direct task metadata in a dedicated table separate from LaTeX translation tasks.

#### Scenario: PDF direct task record is created
- **WHEN** a PDF direct upload succeeds
- **THEN** the backend SHALL create a row in `pdf_direct_tasks` containing: local task id, user id, upstream `fileNo`, file name, file size in KB, page count, progress, transStatus, transFailureCause, transFailureCode, COS artifact key, timestamps
- **AND** it SHALL NOT store upstream tokens, apikeys, passwords, or auth strings.

#### Scenario: Task status is updated from upstream polling
- **WHEN** the backend polls upstream `getInfo` for a PDF direct task
- **THEN** it SHALL update the local `pdf_direct_tasks` row with the latest progress, transStatus, transFailureCause, transFailureCode, and timestamps
- **AND** upon reaching `transStatus=105` it SHALL trigger COS artifact caching.
