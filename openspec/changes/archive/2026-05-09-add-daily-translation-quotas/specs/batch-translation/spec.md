## ADDED Requirements
### Requirement: Batch Submissions Respect Daily LaTeX Quota
Batch translation submissions SHALL count each submitted paper or file as one local LaTeX quota item and SHALL reject the entire batch before task creation when the request exceeds the authenticated user's remaining daily quota.

#### Scenario: Batch arXiv submission fits remaining quota
- **WHEN** an authenticated user submits `N` arXiv IDs through batch translation
- **AND** `N` is less than or equal to the user's remaining local LaTeX quota for the current UTC+8 day
- **THEN** the backend SHALL atomically reserve `N` local LaTeX quota items
- **AND** it SHALL create and enqueue one independent translation task for each submitted arXiv ID.

#### Scenario: Batch file submission fits remaining quota
- **WHEN** an authenticated user submits `N` files through batch upload translation
- **AND** `N` is less than or equal to the user's remaining local LaTeX quota for the current UTC+8 day
- **THEN** the backend SHALL atomically reserve `N` local LaTeX quota items
- **AND** it SHALL create and enqueue one independent translation task for each submitted file.

#### Scenario: Batch exceeds remaining quota
- **WHEN** an authenticated user requests a batch with more items than the user's remaining local LaTeX quota
- **THEN** the backend SHALL reject the request before creating any task or enqueueing any translation work
- **AND** it SHALL leave the user's local LaTeX quota usage unchanged
- **AND** it SHALL return a quota-exceeded response that includes requested item count and remaining item count.

#### Scenario: Existing batch limits still apply
- **WHEN** a batch request is evaluated
- **THEN** the backend SHALL enforce both the existing batch-size or active-task limits and the new daily LaTeX quota limit
- **AND** the stricter applicable limit SHALL prevent the request from starting.
