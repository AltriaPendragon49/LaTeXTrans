## ADDED Requirements
### Requirement: Single-server web and worker runtimes can be split safely
The deployment MUST support running the user-facing backend and the admin backfill executor as separate runtime roles on the same host.

#### Scenario: Web runtime serves traffic without owning admin backfill loops
- **WHEN** the backend process is started with runtime role `web`
- **THEN** it MUST initialize user-facing HTTP handling
- **AND** it MUST NOT start admin curation polling, admin delete polling, or orphan cleanup loops that belong to the background executor.

#### Scenario: Worker runtime owns background admin polling
- **WHEN** the backend process is started with runtime role `worker`
- **THEN** it MUST poll queued admin curation and delete jobs from durable storage
- **AND** it MAY skip legacy global restart reconciliation that is unsafe while translation ownership is split across runtimes.
