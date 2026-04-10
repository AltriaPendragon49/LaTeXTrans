## MODIFIED Requirements

### Requirement: User Registration
The system SHALL delegate account creation and account-recovery flows to NiuTrans-managed pages instead of implementing local registration or OTP verification flows inside the current application.

#### Scenario: User chooses to register from the login page
- **WHEN** an unauthenticated user clicks the registration entry in the current application's login UI
- **THEN** the system SHALL open the configured NiuTrans registration page
- **AND** the current application SHALL NOT attempt to create a local account directly.

#### Scenario: User needs account recovery
- **WHEN** an unauthenticated user requests password recovery or similar account maintenance from the current application's auth UI
- **THEN** the system SHALL redirect or link the user to the NiuTrans-managed account page
- **AND** account recovery SHALL remain outside the local auth implementation scope.

### Requirement: Email Password Authentication
The system SHALL provide an in-app login form that sends credentials to the local backend, delegates credential verification to the NiuTrans login API, and establishes a local project session after successful upstream verification.

#### Scenario: User logs in through the in-app form
- **WHEN** the user submits valid credentials from the current application's login page
- **THEN** the backend SHALL call the NiuTrans login API to verify the credentials
- **AND** it SHALL map the returned NiuTrans `userId` into a local user record
- **AND** it SHALL issue the project's own JWT or session token
- **AND** the frontend SHALL use only that local token for subsequent authenticated API calls.

#### Scenario: Upstream authentication fails
- **WHEN** the user submits invalid credentials or the upstream login API rejects the login
- **THEN** the current application SHALL surface a login failure message
- **AND** it SHALL NOT create a local authenticated session.

### Requirement: User Logout
The system SHALL support local logout by clearing the current application's own session state without depending on Supabase session revocation.

#### Scenario: User logs out
- **WHEN** an authenticated user clicks logout in the current application
- **THEN** the frontend SHALL clear the local auth token or session state
- **AND** protected API calls using that cleared session SHALL no longer succeed.

### Requirement: Guest Mode (Temporary Tasks)
The system SHALL continue to allow unauthenticated users to use the temporary translation workflow while limiting persistence and protected user features to authenticated users.

#### Scenario: Guest user creates a temporary translation task
- **WHEN** an unauthenticated user submits a basic translation request
- **THEN** the system SHALL create a guest-capable task without requiring a local authenticated user
- **AND** the task SHALL remain outside authenticated user history persistence semantics.

#### Scenario: Authenticated user persists a new task
- **WHEN** an authenticated user starts a translation task through the current application
- **THEN** the system SHALL bind the persisted task to the local authenticated user id
- **AND** the task SHALL become visible through authenticated history flows backed by the local database.

### Requirement: Backend JWT Verification
The backend API SHALL verify only the project's own local auth token for authenticated routes, while guest-allowed routes continue to accept anonymous requests.

#### Scenario: Valid local auth token
- **WHEN** an API request carries a valid local Authorization Bearer token issued by the current application
- **THEN** the backend SHALL resolve the local current-user context from that token
- **AND** authenticated routes SHALL use that local user identity for authorization and persistence.

#### Scenario: Missing auth token on guest-allowed route
- **WHEN** a guest-capable API request omits the Authorization header
- **THEN** the backend SHALL allow the request to proceed without an authenticated user context
- **AND** it SHALL apply guest-mode behavior for persistence and feature limits.

#### Scenario: Missing auth token on protected route
- **WHEN** a protected API request omits the Authorization header
- **THEN** the backend SHALL return HTTP 401 Unauthorized
- **AND** it SHALL not attempt to infer identity from an upstream token or database RLS helper.

## REMOVED Requirements

### Requirement: OTP Input UX
**Reason**: Email OTP verification is no longer implemented inside the current application after moving account creation and recovery to NiuTrans-managed pages.
**Migration**: Keep registration or account-management entry points in the UI, but redirect those actions to NiuTrans-managed pages instead of showing local OTP input flows.
