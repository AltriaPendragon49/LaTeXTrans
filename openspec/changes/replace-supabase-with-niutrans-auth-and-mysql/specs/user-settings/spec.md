## MODIFIED Requirements

### Requirement: User Settings Storage
The system SHALL store user settings in MySQL and bind each settings record to the current application's local authenticated user identity instead of relying on Supabase Postgres and RLS.

#### Scenario: First authenticated access to settings
- **WHEN** an authenticated user first visits the settings page or requests the settings API
- **AND** no settings row exists yet for that local user id
- **THEN** the system SHALL create or return the default settings state for that local user
- **AND** the default language direction SHALL remain `en -> zh`
- **AND** the default `default_formatting` value SHALL remain `null`.

#### Scenario: Read user settings
- **WHEN** an authenticated user requests `GET /api/settings`
- **THEN** the system SHALL return the current local user's settings from MySQL
- **AND** it SHALL include `default_formatting` when present.

#### Scenario: Update user settings
- **WHEN** an authenticated user requests `PUT /api/settings`
- **THEN** the system SHALL update the current local user's settings in MySQL
- **AND** it SHALL return the updated settings snapshot
- **AND** `default_formatting` SHALL remain serializable as structured JSON data.
