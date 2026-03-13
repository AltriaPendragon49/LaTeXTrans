## ADDED Requirements
### Requirement: External API Namespace Prefix
All externally exposed backend API endpoints SHALL be namespaced under `/api`.

#### Scenario: Public API request uses /api prefix
- **WHEN** a client requests history data
- **THEN** the request path is `GET /api/history`
- **AND** the endpoint is handled by backend API routing.

#### Scenario: Legacy non-prefixed path is not handled
- **WHEN** a client requests `GET /health`
- **THEN** FastAPI does not expose this endpoint as a public API route.

#### Scenario: Health endpoint under API namespace
- **WHEN** a monitoring system requests `GET /api/health`
- **THEN** the backend returns HTTP 200 JSON health payload.
