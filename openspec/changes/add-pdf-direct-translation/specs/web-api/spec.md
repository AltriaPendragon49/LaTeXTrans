## ADDED Requirements
### Requirement: PDF Direct Translation API
The web API SHALL expose authenticated first-party endpoints for PDF direct translation while proxying the NiuTrans paper-translation API server-side.

#### Scenario: Upload PDF and get page count
- **WHEN** an authenticated client sends a PDF upload request to the PDF direct API
- **THEN** the backend SHALL validate the request as PDF direct translation work
- **AND** it SHALL call the upstream upload/page-count endpoint server-side
- **AND** it SHALL return local task metadata without exposing upstream secrets.

#### Scenario: Start PDF direct task
- **WHEN** an authenticated owner requests PDF direct translation for an uploaded PDF direct task
- **THEN** the backend SHALL call the upstream start-translation endpoint
- **AND** it SHALL return an accepted local task status without reserving local daily LaTeX quota.
- **AND** it SHALL omit first-release unsupported dictionary and memory parameters unless configured otherwise by a later approved spec.

#### Scenario: Query PDF direct task
- **WHEN** an authenticated owner queries a PDF direct task
- **THEN** the backend SHALL return local metadata plus mapped upstream progress/status fields
- **AND** it SHALL avoid exposing upstream appId, apikey, authStr, raw token, or password-like fields.

#### Scenario: Cancel PDF direct task
- **WHEN** an authenticated owner cancels a running PDF direct task
- **THEN** the backend SHALL proxy the upstream interrupt request
- **AND** it SHALL return the mapped local cancellation result.

#### Scenario: Download PDF direct result
- **WHEN** an authenticated owner downloads a completed PDF direct task
- **THEN** the backend SHALL deliver the translated PDF through the current application's API boundary
- **AND** the route SHALL preserve stable authorization and artifact-delivery behavior.

### Requirement: PDF Direct API Error Semantics
The web API SHALL normalize documented NiuTrans PDF direct errors into stable product error payloads.

#### Scenario: Upstream rejects unsupported file
- **WHEN** upstream returns documented file-type, encrypted-file, damaged-file, scanned/untranslatable, size, page, or page-size errors
- **THEN** the backend SHALL return a stable PDF direct validation error
- **AND** the frontend SHALL be able to show localized guidance without parsing upstream natural-language text.

#### Scenario: Upstream reports insufficient PDF direct credits
- **WHEN** upstream returns documented insufficient-page or insufficient-credit codes
- **THEN** the backend SHALL return a stable PDF direct credit error
- **AND** it SHALL NOT reuse the `DAILY_LATEX_QUOTA_EXCEEDED` error code
- **AND** the error payload SHALL include a NiuTrans account-management URL of `https://niutrans.com/`.

#### Scenario: Upstream is busy or rate-limited
- **WHEN** upstream returns documented busy or frequent-request codes (`20022`, `22001`, `110000`)
- **THEN** the backend SHALL return a stable retryable PDF direct error
- **AND** the response SHALL preserve enough retry context for the UI to advise the user.

#### Scenario: User apikey is not available for signing
- **WHEN** the backend needs the user's `apikey` for document API signing but the stored value is missing
- **THEN** the backend SHALL return error code `PDF_DIRECT_CREDENTIAL_UNAVAILABLE`
- **AND** the HTTP response SHALL indicate the user should re-login.

### Requirement: PDF Direct API Configuration
The web API SHALL gate PDF direct translation behind server-side configuration and feature flags.

#### Scenario: PDF direct translation is disabled
- **WHEN** `PDF_DIRECT_TRANSLATION_ENABLED` is false or document API credentials (`NIUTRANS_DOC_API_APP_ID`, `NIUTRANS_DOC_API_BASE_URL`) are missing
- **THEN** all `/api/pdf-direct/*` endpoints SHALL return a configured-unavailable response
- **AND** the frontend SHALL hide or disable the `PDF 直译` first-level option.

#### Scenario: Document API base URL is configured
- **WHEN** the backend calls upstream document API endpoints
- **THEN** it SHALL use `NIUTRANS_DOC_API_BASE_URL` as the prefix (e.g. `https://api-doc.niutrans.com/documentTransApi`)
- **AND** the individual endpoint paths SHALL be appended: `/paperUploadAndGetPageNum`, `/transPaperFile`, `/getInfo`, `/interrupt`, `/download`.

### Requirement: PDF Direct API Requires Local Authentication
The web API SHALL require the current application's local authenticated session for all PDF direct translation operations.

#### Scenario: Guest calls PDF direct API
- **WHEN** a request without a valid local auth token calls a PDF direct upload, start, status, cancel, or download endpoint
- **THEN** the backend SHALL return HTTP 401 Unauthorized
- **AND** it SHALL NOT call the upstream NiuTrans document API.

#### Scenario: Non-owner calls PDF direct task API
- **WHEN** an authenticated user calls a PDF direct task endpoint for a task owned by another user
- **THEN** the backend SHALL reject the request
- **AND** it SHALL NOT disclose upstream `fileNo`, file metadata, progress, or failure details for that task.
