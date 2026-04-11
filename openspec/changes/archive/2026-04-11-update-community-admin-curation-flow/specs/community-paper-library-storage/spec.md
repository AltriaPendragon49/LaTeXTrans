## ADDED Requirements
### Requirement: Completed admin curation runs publish into the community library
The system SHALL let successful admin curation runs become community-library papers only after the full curation pipeline succeeds.

#### Scenario: Publish a fully successful admin curation run
- **WHEN** an admin curation run completes intake, metadata preparation, translation, and structured insight generation successfully
- **THEN** the system SHALL create or reuse the canonical community paper record
- **AND** it SHALL copy the selected community assets into that paper's community library directory.

### Requirement: Community hard delete removes library assets completely
The system SHALL remove a hard-deleted community paper from both local database records and local community-library storage.

#### Scenario: Admin hard deletes a community paper
- **WHEN** an authorized admin performs a hard delete for a community paper
- **THEN** the system SHALL delete the paper's local `community_papers/<paper_id>` directory and related stored asset rows
- **AND** the corresponding paper SHALL no longer resolve through normal community preview, detail, or download flows.

## REMOVED Requirements
### Requirement: Completed authenticated translation tasks auto-publish to the community library
**Reason**: Ordinary authenticated translation tools must remain separate from the curated public community library.
**Migration**: Only successful admin curation runs publish new community papers into the community library.

### Requirement: Normal translation start schedules community publish watching
**Reason**: Direct translation tools no longer schedule community publication as part of ordinary translation behavior.
**Migration**: Publication watches move to the admin curation flow instead of the normal tools translation path.
