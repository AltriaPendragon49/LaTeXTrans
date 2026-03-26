## ADDED Requirements
### Requirement: Content pool discovers and prewarms candidate papers off the request path
The system SHALL support a background content-pool pipeline that discovers candidate papers and prewarms them before users request those papers in the interactive community flow.

#### Scenario: Worker discovers a candidate paper
- **WHEN** the background pipeline receives a candidate paper from an approved upstream source
- **THEN** the system SHALL evaluate that candidate off the user request path
- **AND** it SHALL not require a foreground user interaction to start the prewarm process.

#### Scenario: Prewarm lifecycle reaches translated-ready state
- **WHEN** a content-pool candidate successfully completes source acquisition, translation, and preview generation
- **THEN** the system SHALL mark that paper as translated-ready for downstream retrieval and reading
- **AND** translated evidence SHALL become available to internal search and reader surfaces.

### Requirement: Content pool jobs are idempotent and failure-contained
The content-pool pipeline SHALL bound retries, reuse canonical records, and avoid generating duplicate work for the same paper.

#### Scenario: Candidate already exists in the community
- **WHEN** the pipeline encounters a paper whose canonical community record already exists
- **THEN** it SHALL reuse that canonical record
- **AND** it SHALL not create a duplicate paper row for the same `arxiv_id`.

#### Scenario: Prewarm stage fails
- **WHEN** a source acquisition, translation, or preview stage fails
- **THEN** the failure SHALL be recorded as an operator-visible state
- **AND** the pipeline SHALL contain the failure without blocking unrelated candidates.

### Requirement: Content pool exposes operational readiness signals
The system SHALL expose enough structured logging or metrics to verify that the content pool is healthy and improving usable translated coverage.

#### Scenario: Operator inspects pool readiness
- **WHEN** operators inspect the content pool
- **THEN** the system SHALL expose readiness signals such as candidate counts, translated-ready counts, freshness, and failure counts
- **AND** those signals SHALL distinguish between discovery, prewarm, and promotion stages.

#### Scenario: Unauthenticated caller requests operator readiness endpoints
- **WHEN** an unauthenticated caller requests content-pool readiness or job-log signals
- **THEN** the system SHALL reject that request with an authentication-required response
- **AND** operator readiness payloads SHALL only be returned in an authenticated operator context.
