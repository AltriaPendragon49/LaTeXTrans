## ADDED Requirements
### Requirement: Shared Redis service backs public community-paper discovery state
Production deployment SHALL provide a shared Redis service for public community-paper feed cache and ranking state.

#### Scenario: Multiple backend instances serve one public feed state
- **WHEN** multiple backend processes or hosts serve public `GET /api/papers` requests
- **THEN** they SHALL read and write the same Redis-backed public feed cache and ranking indexes
- **AND** steady-state correctness SHALL NOT depend on process-local public feed memory.

#### Scenario: Redis outage falls back to canonical reads
- **WHEN** the shared Redis service is unavailable or unhealthy
- **THEN** the backend SHALL fall back to the canonical database-backed public read path
- **AND** it SHALL NOT reintroduce divergent process-local feed caches as the production durability mechanism.

### Requirement: Public feed index maintenance is singleton-safe
Any scheduled rebuild, repair, or backfill path for Redis-backed public community-paper indexes SHALL run under singleton-safe execution.

#### Scenario: Scheduled index maintenance runs in production
- **WHEN** the system rebuilds or repairs the Redis-backed `latest`, `views`, or `likes` indexes
- **THEN** that work SHALL run in a dedicated worker role or under a distributed singleton lock
- **AND** multiple web instances SHALL NOT race to rebuild the same public index set concurrently.
