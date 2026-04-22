## ADDED Requirements
### Requirement: Repeated admin arXiv curation deletes old history before starting over
The admin curation flow SHALL treat repeated `arXiv ID` intake as a full reset instead of an in-place refresh.

#### Scenario: Existing published admin arXiv paper is curated again
- **WHEN** an admin submits an `arXiv ID` that already has a published community paper
- **THEN** the system SHALL hard-delete that published paper and its related curation history before creating the new curation job
- **AND** the new job SHALL receive a fresh `paper_id`.

#### Scenario: Existing failed admin arXiv history is curated again
- **WHEN** an admin submits an `arXiv ID` that only has failed or incomplete retained curation history
- **THEN** the system SHALL hard-delete those retained job records, translation-task rows, retained failed artifacts, and task-scoped local files before creating the new curation job
- **AND** the new job SHALL receive a fresh `paper_id`.

#### Scenario: Duplicate reset encounters an in-flight worker
- **WHEN** an admin submits an `arXiv ID` whose previous curation job is still queued, processing, translating, or publishing
- **THEN** the system SHALL cancel that in-flight curation worker before deletion
- **AND** it SHALL block the replacement submission if the required reset cleanup does not finish successfully.
