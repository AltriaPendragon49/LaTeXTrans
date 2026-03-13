## ADDED Requirements
### Requirement: Configurable CORS Origin Allowlist
Backend SHALL support comma-separated CORS origin configuration via `CORS_ORIGINS`.

#### Scenario: Parse multiple origins from env
- **WHEN** `CORS_ORIGINS` contains a comma-separated list
- **THEN** backend MUST parse and trim each origin
- **AND** backend MUST ignore empty entries

#### Scenario: Wildcard is rejected
- **WHEN** `CORS_ORIGINS` includes `*`
- **THEN** backend configuration MUST reject this value
- **AND** startup MUST not silently downgrade to wildcard behavior

#### Scenario: Middleware uses parsed allowlist
- **WHEN** backend app initializes CORS middleware
- **THEN** middleware MUST use parsed configured allowlist directly
