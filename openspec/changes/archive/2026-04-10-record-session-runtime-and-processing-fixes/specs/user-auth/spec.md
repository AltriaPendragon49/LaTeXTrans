## MODIFIED Requirements
### Requirement: Email Password Authentication
The system SHALL provide an in-app login form that sends an email address or phone number identifier plus password to the local backend, delegates credential verification to the NiuTrans login API, and establishes a local project session after successful upstream verification.

#### Scenario: User logs in through the in-app form with email
- **WHEN** the user submits a valid email address and password from the current application's login page
- **THEN** the backend SHALL call the NiuTrans login API to verify the credentials
- **AND** it SHALL map the returned NiuTrans `userId` into a local user record
- **AND** it SHALL issue the project's own JWT or session token
- **AND** the frontend SHALL use only that local token for subsequent authenticated API calls

#### Scenario: User logs in through the in-app form with phone number
- **WHEN** the user submits a valid phone number and password from the current application's login page
- **THEN** the frontend SHALL allow that identifier without email-only validation failure
- **AND** the backend SHALL send the phone number identifier through the same local auth contract used for email sign-in
- **AND** the resulting authenticated session contract SHALL remain identical to email-based login

#### Scenario: Upstream authentication fails
- **WHEN** the user submits invalid credentials or the upstream login API rejects the login
- **THEN** the current application SHALL surface a login failure message
- **AND** it SHALL NOT create a local authenticated session
