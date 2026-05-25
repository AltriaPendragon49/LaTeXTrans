## MODIFIED Requirements
### Requirement: Batch Submissions Respect Daily LaTeX Quota
Batch translation submissions by authenticated non-admin users SHALL count each submitted paper or file as one local LaTeX quota item and SHALL reject the entire batch before task creation when the request exceeds the authenticated non-admin user's remaining daily quota. Authenticated users whose resolved roles include `admin` SHALL bypass only this local daily LaTeX quota for batch submissions.

#### Scenario: Non-admin batch arXiv submission fits remaining quota
- **WHEN** an authenticated non-admin user submits `N` arXiv IDs through batch translation
- **AND** `N` is less than or equal to the user's remaining local LaTeX quota for the current UTC+8 day
- **THEN** the backend SHALL atomically reserve `N` local LaTeX quota items
- **AND** it SHALL create and enqueue one independent translation task for each submitted arXiv ID.

#### Scenario: Non-admin batch file submission fits remaining quota
- **WHEN** an authenticated non-admin user submits `N` files through batch upload translation
- **AND** `N` is less than or equal to the user's remaining local LaTeX quota for the current UTC+8 day
- **THEN** the backend SHALL atomically reserve `N` local LaTeX quota items
- **AND** it SHALL create and enqueue one independent translation task for each submitted file.

#### Scenario: Non-admin batch exceeds remaining quota
- **WHEN** an authenticated non-admin user requests a batch with more items than the user's remaining local LaTeX quota
- **THEN** the backend SHALL reject the request before creating any task or enqueueing any translation work
- **AND** it SHALL leave the user's local LaTeX quota usage unchanged
- **AND** it SHALL return a quota-exceeded response that includes requested item count and remaining item count.

#### Scenario: Admin batch bypasses local daily quota
- **WHEN** an authenticated user whose resolved roles include `admin` submits a batch arXiv or batch upload translation request
- **THEN** the backend SHALL evaluate the request without reserving or incrementing local daily LaTeX quota usage
- **AND** it SHALL create and enqueue eligible translation tasks for the submitted items
- **AND** the request SHALL remain subject to existing batch-size limits, active-task limits, queue limits, upstream/provider quotas, and task execution safeguards.

#### Scenario: Existing batch limits still apply
- **WHEN** a batch request is evaluated
- **THEN** the backend SHALL enforce the existing batch-size or active-task limits
- **AND** for non-admin users it SHALL also enforce the daily LaTeX quota limit
- **AND** the stricter applicable limit SHALL prevent the request from starting.
