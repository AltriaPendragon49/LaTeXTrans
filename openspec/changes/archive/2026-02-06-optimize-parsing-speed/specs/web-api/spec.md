## ADDED Requirements

### Requirement: Environment Translation Judgment
The ParserAgent SHALL determine which LaTeX environments need translation with optimized filtering:
1. **Extended skip list**: Skip LLM calls for environments that are clearly translatable or non-translatable based on environment type
2. **Content length filter**: Skip LLM calls for environments with content shorter than 20 characters

The system SHALL maintain the existing concurrency limit (`Semaphore(5)`) to avoid API rate limiting.

#### Scenario: Environment in skip list
- **WHEN** a LaTeX environment is of type `abstract`, `itemize`, `enumerate`, `description`, `proof`, `definition`, `theorem`, or `lemma`
- **THEN** the system SHALL skip LLM judgment for that environment

#### Scenario: Short content filtering
- **WHEN** an environment has content shorter than 20 characters
- **THEN** the system SHALL skip LLM judgment for that environment

#### Scenario: Preserve existing behavior for complex environments
- **WHEN** an environment does not match any skip criteria
- **THEN** the system SHALL call LLM individually (not batched) to determine translation need
- **AND** the concurrency limit of 5 simultaneous calls SHALL be maintained
