## MODIFIED Requirements
### Requirement: Global API Rate Limiting
The system SHALL implement a globally shared concurrency limit for all outbound LLM API requests.

#### Scenario: Enforcing global LLM concurrency
- **WHEN** multiple tasks or sub-tasks trigger LLM requests
- **THEN** they MUST acquire a global `asyncio.Semaphore` with a default ceiling of `10`
- **AND** excess requests SHALL queue without blocking or timing out.

## ADDED Requirements
### Requirement: Project-Text Assembly Preserves Include Structure
The system SHALL assemble compile-ready project text in source order so precompile structure validation sees the same logical nesting that LaTeX would see.

#### Scenario: Included table body stays at the callsite
- **WHEN** a parent file opens a structural wrapper such as `table` and inserts a child file through `\input` or `\include`
- **AND** the child file contains nested environments such as `tabularx`
- **THEN** project-text assembly MUST inline the child content at the original callsite
- **AND** the assembled text MUST preserve begin/end ordering across parent and child content.

#### Scenario: Nested relative includes resolve from the current file directory
- **WHEN** an included file contains a nested relative `\input` or `\include`
- **THEN** the resolver MUST interpret that path relative to the current file's directory
- **AND** valid nested child files MUST be assembled without requiring project-root-relative paths.
