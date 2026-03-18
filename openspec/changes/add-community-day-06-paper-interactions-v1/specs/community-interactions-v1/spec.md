## ADDED Requirements
### Requirement: Paper interactions v1
The system SHALL provide minimum social interactions on papers through likes, favorites, and comments without requiring a nested discussion model.

#### Scenario: Toggle likes and favorites
- **WHEN** a user likes or favorites a paper from the Feed or detail surface
- **THEN** the system SHALL support idempotent toggle behavior for the current user
- **AND** the visible counters SHALL converge with the stored interaction state.

#### Scenario: Create and read v1 comments
- **WHEN** a user opens the comments section for a paper
- **THEN** the system SHALL return the current v1 comment list
- **AND** the user SHALL be able to create a new top-level comment through the same paper-owned contract.

#### Scenario: Keep interaction counters consistent
- **WHEN** interaction writes complete successfully
- **THEN** Feed cards and paper detail reads SHALL expose the same effective counts
- **AND** any deferred reconciliation strategy SHALL preserve one user-visible truth for MVP usage.
