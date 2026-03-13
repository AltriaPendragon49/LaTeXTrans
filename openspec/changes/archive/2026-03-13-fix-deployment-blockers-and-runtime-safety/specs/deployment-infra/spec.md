## MODIFIED Requirements
### Requirement: Dynamic API URL Resolution
Frontend API calls SHALL use environment variable `VITE_API_BASE_URL` and MUST NOT hardcode localhost fallback.

#### Scenario: Production build has no hardcoded localhost fallback
- **WHEN** frontend is built in production mode
- **THEN** build artifacts MUST NOT contain `localhost:8000`

#### Scenario: Missing API base env fails fast
- **WHEN** `VITE_API_BASE_URL` is not set
- **THEN** frontend MUST throw an explicit configuration error
- **AND** frontend MUST block API request creation

## ADDED Requirements
### Requirement: Runtime-Only Container Contract
The runtime image MUST NOT be used without host code mount and runtime env injection.

#### Scenario: Required backend mount and env injection
- **WHEN** backend container starts
- **THEN** `/app/backend` MUST be mounted from host
- **AND** backend `.env` MUST be injected
- **AND** `backend/data/*` MUST be writable

#### Scenario: Forbidden naked runtime image run
- **WHEN** runtime image is launched without mounting `/app/backend`
- **THEN** deployment documentation MUST mark this pattern as forbidden

### Requirement: Loopback-Only Host Publishing
Backend service exposure on shared host MUST be loopback-only.

#### Scenario: Host loopback port publish
- **WHEN** backend container is launched in production
- **THEN** host publish MUST be `127.0.0.1:9001:9001`
- **AND** Nginx MUST proxy to `http://127.0.0.1:9001`

### Requirement: Production Worker Guardrail
Production runtime SHALL default to a single worker until runtime-state is fully externalized.

#### Scenario: Runtime command uses one worker
- **WHEN** runtime starts with default command
- **THEN** `uvicorn` worker count MUST be `1`

### Requirement: Service Role Secret Boundary and Rotation
Service-role credentials MUST remain backend-only, and exposed keys MUST be rotated.

#### Scenario: Frontend env excludes service-role key
- **WHEN** frontend env files are prepared
- **THEN** `VITE_SUPABASE_SERVICE_ROLE_KEY` MUST NOT be present

#### Scenario: Exposure remediation documented
- **WHEN** deployment documentation is reviewed
- **THEN** it MUST include a mandatory key-rotation notice for exposed service-role credentials
