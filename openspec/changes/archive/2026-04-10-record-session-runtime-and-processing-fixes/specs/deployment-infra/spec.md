## MODIFIED Requirements
### Requirement: Runtime-Only Container Contract
The runtime image MUST NOT be used without host code mount and runtime env injection, and the injected backend runtime configuration MUST include the business database connection required by local auth and community persistence.

#### Scenario: Required backend mount and env injection
- **WHEN** backend container starts
- **THEN** `/app/backend` MUST be mounted from host
- **AND** backend `.env` MUST be injected
- **AND** `backend/data/*` MUST be writable

#### Scenario: Business database wiring is present at runtime
- **WHEN** backend container starts with local auth and community persistence enabled
- **THEN** runtime env injection MUST provide a resolvable business database URL such as `DATABASE_URL`
- **AND** startup reconciliation, local auth session persistence, and community-paper persistence MUST be able to open that database without manual in-container edits
- **AND** missing database wiring MUST be treated as a deployment contract violation rather than an acceptable steady-state configuration

#### Scenario: Forbidden naked runtime image run
- **WHEN** runtime image is launched without mounting `/app/backend`
- **THEN** deployment documentation MUST mark this pattern as forbidden
