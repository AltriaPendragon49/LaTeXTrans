## ADDED Requirements
### Requirement: Translation Workspace First-Level Mode Split
The translation workspace SHALL present `LaTeX 翻译` and `PDF 直译` as first-level workflow choices.

#### Scenario: User opens translation workspace
- **WHEN** an authenticated user opens `/translate`
- **THEN** the UI SHALL show first-level choices for `LaTeX 翻译` and `PDF 直译`
- **AND** `LaTeX 翻译` SHALL remain the default first-level choice unless a deep link or saved workspace state selects otherwise.

#### Scenario: User selects LaTeX translation
- **WHEN** the user selects `LaTeX 翻译`
- **THEN** the existing `arXiv 编号`, `本地上传`, and `批量翻译` controls SHALL appear as second-level options inside a shared container
- **AND** their existing behavior, validation, and quota handling SHALL remain unchanged.

#### Scenario: User selects PDF direct translation
- **WHEN** the user selects `PDF 直译`
- **THEN** the UI SHALL replace the LaTeX second-level controls with the PDF direct-translation workspace
- **AND** it SHALL avoid showing LaTeX-only advanced configuration, parser, compiler, or RAG controls as active PDF direct settings.

### Requirement: PDF Direct Translation UI
The frontend SHALL provide a dedicated authenticated UI for PDF direct translation.

#### Scenario: Authenticated user prepares PDF direct translation
- **WHEN** an authenticated user enters the `PDF 直译` workspace
- **THEN** the UI SHALL provide a PDF upload control
- **AND** it SHALL indicate that the first release supports editable PDF files and English-to-Chinese translation.
- **AND** it SHALL NOT expose `dictNo`, `memoryNo`, or `realmCode` controls in the first release.

#### Scenario: Uploaded PDF page count is available
- **WHEN** the backend returns page count information for an uploaded PDF
- **THEN** the UI SHALL display the page count and a start-translation action
- **AND** it SHALL keep the local LaTeX daily quota display separate from the PDF direct credits display.

#### Scenario: PDF direct task is running
- **WHEN** a PDF direct task has started
- **THEN** the UI SHALL show progress derived from backend status updates
- **AND** it SHALL provide a cancel action while cancellation is still valid.

#### Scenario: PDF direct task completes
- **WHEN** a PDF direct task reaches completed state
- **THEN** the UI SHALL provide a translated-PDF download action
- **AND** it SHALL refresh or request the latest quota snapshot when feasible.

#### Scenario: PDF direct credits are insufficient
- **WHEN** the backend reports insufficient PDF direct-translation credits for the logged-in user
- **THEN** the UI SHALL show a localized insufficient-credit reminder
- **AND** it SHALL provide an action that opens `https://niutrans.com/` for NiuTrans recharge or account management.

#### Scenario: Upstream reports PDF file or page limits
- **WHEN** the backend reports a structured PDF direct file-size, page-count, or page-size limit error
- **THEN** the UI SHALL show localized guidance based on that structured code
- **AND** it SHALL NOT claim an unsupported numeric limit unless that limit is provided by backend configuration or upstream response data.

#### Scenario: Guest attempts PDF direct translation
- **WHEN** an unauthenticated user tries to use `PDF 直译`
- **THEN** the frontend SHALL route the user into the current local login flow
- **AND** it SHALL NOT upload the PDF before authentication succeeds.

### Requirement: PDF Direct Translation Copy Uses I18n
All user-visible PDF direct-translation UI copy SHALL come from centralized i18n resources.

#### Scenario: New PDF direct labels render
- **WHEN** the frontend renders first-level choices, upload prompts, status text, errors, cancellation text, or download actions for PDF direct translation
- **THEN** those strings SHALL resolve from maintained locale resources
- **AND** no new hardcoded user-visible PDF direct copy SHALL be introduced in frontend source files.
