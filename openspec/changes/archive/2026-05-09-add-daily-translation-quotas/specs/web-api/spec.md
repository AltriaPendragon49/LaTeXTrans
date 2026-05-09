## ADDED Requirements
### Requirement: Daily LaTeX Translation Quota
The web API SHALL enforce an independent local daily LaTeX translation quota for authenticated users. The default quota SHALL be 3 items per authenticated user per UTC+8 natural day.

#### Scenario: Authenticated user starts an ordinary arXiv translation
- **WHEN** an authenticated user starts translation work for one arXiv ID
- **AND** the user has at least one remaining local LaTeX quota item for the current UTC+8 day
- **THEN** the API SHALL reserve one local LaTeX quota item before accepting translation work
- **AND** the accepted task SHALL proceed without deducting NiuTrans PDF direct-translation credits.

#### Scenario: Authenticated user starts an ordinary uploaded-source translation
- **WHEN** an authenticated user starts translation work for one uploaded LaTeX file, source folder, or source archive
- **AND** the user has at least one remaining local LaTeX quota item for the current UTC+8 day
- **THEN** the API SHALL reserve one local LaTeX quota item before accepting translation work
- **AND** the accepted task SHALL proceed without deducting NiuTrans PDF direct-translation credits.

#### Scenario: Local daily quota is exhausted
- **WHEN** an authenticated user has no remaining local LaTeX quota items for the current UTC+8 day
- **AND** the user attempts to start quota-managed LaTeX translation work
- **THEN** the API SHALL return a quota-exceeded error before creating or enqueuing new translation work
- **AND** the error payload SHALL include the quota limit, used count, remaining count, requested count, and reset date.

#### Scenario: Daily quota refreshes
- **WHEN** the UTC+8 natural day changes
- **THEN** the user's local LaTeX quota usage SHALL reset for the new quota date
- **AND** prior-day usage SHALL NOT reduce the new day's remaining count.

#### Scenario: Failed accepted task does not refund quota
- **WHEN** translation work has already been accepted and later fails, is cancelled, or fails compilation
- **THEN** the local LaTeX quota item reserved for that accepted work SHALL remain consumed
- **AND** NiuTrans PDF direct-translation credits SHALL remain unaffected.

### Requirement: Translation Quota Snapshot API
The web API SHALL provide an authenticated quota snapshot that separates local LaTeX quota from NiuTrans PDF direct-translation credits.

#### Scenario: Authenticated user requests quota snapshot
- **WHEN** an authenticated user requests the current quota snapshot through login, session bootstrap, or a dedicated quota endpoint
- **THEN** the API SHALL return local LaTeX quota fields including limit, used, remaining, quota date, and reset timezone
- **AND** it SHALL return PDF direct-translation credit fields based on NiuTrans `unusedNumIntegral` when available
- **AND** the response SHALL make clear that PDF direct-translation credits are积分 rather than a `remaining/limit` daily quota.

#### Scenario: NiuTrans balance is unavailable
- **WHEN** no valid NiuTrans `unusedNumIntegral` snapshot is available
- **THEN** the API SHALL still return the local LaTeX quota snapshot
- **AND** it SHALL mark the PDF direct-translation credit status as unavailable or stale instead of failing the entire quota response.
