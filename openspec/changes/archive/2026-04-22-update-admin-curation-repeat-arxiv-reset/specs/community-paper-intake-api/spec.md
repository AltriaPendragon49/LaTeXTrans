## MODIFIED Requirements
### Requirement: Community admission is admin-curated and complete-only
The system SHALL admit newly visible community papers only through the admin curation flow, and those papers SHALL become publicly visible only after the full curation pipeline succeeds.

#### Scenario: Admin curation run succeeds fully
- **WHEN** an authenticated admin submits a paper through the admin curation flow
- **AND** intake, metadata preparation, translation, and structured insight generation all succeed
- **THEN** the system SHALL create or reuse one canonical community paper record
- **AND** it SHALL publish that paper as visible community content only after that full success state is reached.

#### Scenario: Repeated admin arXiv curation resets old traces before a new run
- **WHEN** an authenticated admin submits an `arXiv ID` that already has a canonical community paper or prior admin curation history
- **THEN** the system SHALL hard-delete the prior paper record, related assets, structured insights, similar recommendations, curation jobs, translation tasks, retained failed artifacts, and run-scoped local artifacts for that `arXiv ID`
- **AND** it SHALL create the replacement admin curation item only after that reset succeeds
- **AND** the replacement run SHALL start with a fresh `paper_id`.

#### Scenario: Ordinary tool translation succeeds
- **WHEN** a non-admin user completes a translation through the direct tools workflow
- **THEN** the system SHALL keep that result outside the visible community feed by default
- **AND** it SHALL not create a new public community paper solely because the tool translation succeeded.

#### Scenario: Curation pipeline is incomplete or fails
- **WHEN** a curation run has not yet completed all required stages or ends in failure
- **THEN** the corresponding paper SHALL remain absent from the public community feed
- **AND** users SHALL not see a half-finished public community paper card for that run.

### Requirement: Canonical community paper identity is stable across repeated curation
The system SHALL keep a canonical community paper identity stable across later updates, except for the explicit duplicate admin `arXiv ID` reset path that deletes the old paper before recreating it.

#### Scenario: Archive intake later resolves to an existing canonical paper
- **WHEN** archive-based curation is determined to match an already-known canonical community paper
- **THEN** the system SHALL reuse the existing `paper_id`
- **AND** the latest successful curation output SHALL replace the prior published community-facing content for that same paper.

#### Scenario: Canonical paper id stays stable for non-reset updates
- **WHEN** a canonical community paper already exists and the new intake does not enter the duplicate admin arXiv reset path
- **THEN** its `paper_id` SHALL remain unchanged across later curation updates
- **AND** repeated curation SHALL update the paper in place instead of generating a new public identity.
