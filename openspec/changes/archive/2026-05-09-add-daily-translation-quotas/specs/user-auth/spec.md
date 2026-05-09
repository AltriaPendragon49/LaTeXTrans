## ADDED Requirements
### Requirement: NiuTrans PDF Direct Balance Snapshot
The authentication system SHALL fetch and expose a safe NiuTrans account-balance snapshot for authenticated users so the frontend can display PDF direct-translation credits.

#### Scenario: Login fetches NiuTrans balance
- **WHEN** a user successfully logs in through the local auth flow backed by NiuTrans credentials
- **THEN** the backend SHALL use the upstream `userId` and login `token` to request NiuTrans user information
- **AND** it SHALL extract `unusedNumIntegral` as the PDF direct-translation credits value
- **AND** it SHALL return or persist only safe balance fields needed by the current application.

#### Scenario: Upstream balance fetch fails
- **WHEN** local credential verification succeeds but the NiuTrans user-info request fails or returns an invalid balance payload
- **THEN** the local login SHALL still succeed
- **AND** the user payload or quota snapshot SHALL mark PDF direct-translation credits as unavailable or stale
- **AND** the local LaTeX translation quota SHALL remain usable.

#### Scenario: Upstream secrets are not exposed
- **WHEN** the backend returns login, session bootstrap, or quota snapshot data to the frontend
- **THEN** the response SHALL NOT include raw upstream NiuTrans login tokens, refresh tokens, API keys, nested password fields, or other secret-like upstream fields
- **AND** frontend clients SHALL continue using only the current application's local authenticated session token for project API calls.
