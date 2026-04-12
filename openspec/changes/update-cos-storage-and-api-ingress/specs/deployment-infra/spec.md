## ADDED Requirements
### Requirement: Cloudflare-managed API ingress shields the production origin
Production browser traffic SHALL reach `api.latextrans.online` through a Cloudflare-managed edge path rather than depending on direct public browser access to the CVM origin TLS endpoint.

#### Scenario: External browser reaches the API through the Cloudflare edge
- **WHEN** an external browser requests `https://api.latextrans.online/api/health`
- **THEN** the request SHALL be served through the Cloudflare-managed ingress path
- **AND** the response SHALL remain stable for normal browser TLS and HTTP behavior without direct public origin dependence.

#### Scenario: Production origin is not the browser-facing durability boundary
- **WHEN** production API ingress is configured
- **THEN** the CVM origin SHALL act as an internal or Cloudflare-facing origin rather than the primary direct browser TLS endpoint
- **AND** deployment validation SHALL confirm the public route does not rely on direct origin exposure for steady-state browser access.

### Requirement: Production runtime artifact persistence is object-storage-backed with ephemeral origin cache
Production runtime artifacts SHALL use object storage as the canonical durable store, while local origin disk acts only as a temporary cache.

#### Scenario: Production task artifact is persisted successfully
- **WHEN** production generates a retained upload, output, preview, PDF, or task-log artifact
- **THEN** the system SHALL upload the canonical copy to object storage
- **AND** it SHALL remove the local cached copy after that artifact is no longer needed by the active task stage.

#### Scenario: Local development runs without object storage
- **WHEN** object storage is not configured in a local development environment
- **THEN** the backend SHALL continue using the existing local-disk storage layout
- **AND** developers SHALL not be required to provision COS for normal local iteration.
