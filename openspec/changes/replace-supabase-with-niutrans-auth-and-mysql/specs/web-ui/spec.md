## RENAMED Requirements

- FROM: `### Requirement: Frontend Public Key Boundary`
- TO: `### Requirement: Frontend Auth Environment Boundary`

## ADDED Requirements

### Requirement: Login UI uses local auth with NiuTrans account links
The web UI SHALL use an in-app login form as the only formal sign-in flow, while exposing registration and account-management links that redirect users to NiuTrans-managed pages.

#### Scenario: User logs in from the current application
- **WHEN** a user submits credentials from the current application's login page
- **THEN** the frontend SHALL call the local backend auth endpoint
- **AND** it SHALL store only the local authenticated session or token returned by the current application
- **AND** later protected API requests SHALL use that local token rather than any Supabase session.

#### Scenario: Frontend restores auth state through session bootstrap
- **WHEN** the frontend starts with a locally stored auth token
- **THEN** it SHALL call the current application's auth bootstrap endpoint to resolve the current user
- **AND** an invalid or expired session response SHALL transition the UI back to the logged-out state.

#### Scenario: User chooses to register a new account
- **WHEN** a user clicks the registration entry from the current application's auth UI
- **THEN** the frontend SHALL redirect the user to the configured NiuTrans registration URL
- **AND** it SHALL not display a local Supabase sign-up or OTP-verification flow.

#### Scenario: Protected feature prompts still keep guest entry clear
- **WHEN** an unauthenticated user attempts to access history, settings, or community-agent persistence features
- **THEN** the frontend SHALL prompt for login using the current application's auth flow
- **AND** guest-available translation entry points SHALL remain usable without sign-in.

## MODIFIED Requirements

### Requirement: Frontend Auth Environment Boundary
Frontend runtime configuration MUST NOT depend on Supabase public keys after local auth migration is complete.

#### Scenario: Frontend env excludes Supabase runtime auth keys
- **WHEN** frontend `.env*` files are prepared for the migrated local stack
- **THEN** the current application SHALL NOT require `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` for runtime auth behavior
- **AND** frontend auth bootstrap SHALL depend only on the current application's own API configuration.
