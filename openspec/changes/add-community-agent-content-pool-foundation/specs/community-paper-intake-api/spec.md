## ADDED Requirements
### Requirement: Background content pool admission reuses the same canonical paper rules
The community paper intake layer SHALL allow the background content pool to admit or reuse papers using the same canonical paper model that interactive imports already use.

#### Scenario: Background pool admits a new paper
- **WHEN** the content pool decides to warm a paper that does not yet exist in the community database
- **THEN** the intake layer SHALL create one canonical paper record for that `arxiv_id`
- **AND** later interactive imports SHALL reuse that same paper instead of creating a second record.

#### Scenario: Background pool encounters an existing paper
- **WHEN** the content pool decides to warm a paper that already exists in the community database
- **THEN** the intake layer SHALL reuse the existing canonical paper
- **AND** the content pool SHALL enrich that paper’s assets and readiness state rather than creating a duplicate admission path.
