## ADDED Requirements
### Requirement: Content pool can consume reviewed ranked hot candidates
The content-pool and admin-curation workflow SHALL treat ranked hot candidates as reviewable inputs rather than automatic publication commands.

#### Scenario: Ranked candidate list is reviewed for intake
- **WHEN** a ranked hot artifact contains candidate arXiv IDs
- **THEN** operators SHALL be able to select a bounded subset for admin curation or content-pool prewarm
- **AND** unselected candidates SHALL remain only as source evidence and SHALL NOT start translation work.

#### Scenario: Candidate reuse avoids duplicate work
- **WHEN** a selected ranked candidate is already queued, translated-ready, or published
- **THEN** the content-pool workflow SHALL reuse the canonical arXiv identity
- **AND** it SHALL record the new ranking evidence without creating duplicate translation or paper records.

### Requirement: Ranked candidate readiness is observable
Ranked hot candidate intake SHALL expose enough readiness information for operators to understand source quality and processing state.

#### Scenario: Operator inspects ranked candidate readiness
- **WHEN** operators review ranked hot candidates
- **THEN** the system SHALL expose candidate counts by window, selected count, already-translated count, queued count, failed count, and missing-evidence count
- **AND** those signals SHALL distinguish discovery, review, curation, translation, and publication stages.
