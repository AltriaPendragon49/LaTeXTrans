## ADDED Requirements
### Requirement: Community engagement persistence supports foldered favorites and daily de-duplicated views
The community schema SHALL persist engagement for community papers through normalized relationship tables and deterministic uniqueness constraints.

#### Scenario: Favorite folders and folder membership are normalized
- **WHEN** the schema persists community-paper favorites
- **THEN** it SHALL store user-owned favorite folders separately from folder-paper membership rows
- **AND** it SHALL enforce unique folder names per user
- **AND** it SHALL enforce unique folder-paper membership per folder

#### Scenario: Like and view de-duplication constraints are explicit
- **WHEN** the schema persists likes or daily paper views
- **THEN** it SHALL enforce at most one like row per user and paper
- **AND** it SHALL enforce at most one daily view row per `(paper_id, business_date, principal_type, principal_key)` tuple

#### Scenario: Fast feed counters remain queryable on papers
- **WHEN** community feeds need to sort or display engagement totals
- **THEN** the schema SHALL keep non-negative aggregate counters for likes, favorites, and views on the `papers` table
- **AND** backend write paths SHALL be able to update those counters consistently with the underlying relationship rows
