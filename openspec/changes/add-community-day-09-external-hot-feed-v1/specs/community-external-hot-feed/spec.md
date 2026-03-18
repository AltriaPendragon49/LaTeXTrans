## ADDED Requirements
### Requirement: External hot feed v1
The system SHALL expose a hot-feed entry by mirroring an external paper ranking source instead of computing a full internal hot-score model during the MVP phase.

#### Scenario: Import a batch of external hot papers
- **WHEN** the MVP hot-feed job runs manually or on a simple schedule
- **THEN** the system SHALL be able to import a batch of externally ranked papers into local storage
- **AND** the import SHALL not require an internal behavior-based score calculation.

#### Scenario: Label the source of hot-feed items
- **WHEN** a user browses the hot-feed view
- **THEN** the system SHALL show that the ranking comes from an external source or mirror
- **AND** it SHALL avoid implying that the ordering is an internal community popularity score.

#### Scenario: Contain hot-feed failures
- **WHEN** the external source is unavailable or limited
- **THEN** the system SHALL log the failure and preserve core paper browsing paths
- **AND** hot-feed issues SHALL not block submit, detail, translation, preview, download, or moderation flows.
