## MODIFIED Requirements
### Requirement: Admin curation publishes only complete papers
The admin curation workflow SHALL only publish a paper into the community feed after all required curation stages have succeeded.

#### Scenario: Paper reaches complete curated state
- **WHEN** curation finishes metadata preparation, translation, structured insight generation, and persisted similar-recommendation generation successfully
- **THEN** the paper SHALL become visible in the community feed
- **AND** it SHALL appear as a complete curated paper rather than a processing placeholder.

#### Scenario: Paper has not completed required curation stages
- **WHEN** any required curation stage is still running or has failed
- **THEN** the paper SHALL remain outside the public community feed
- **AND** the UI SHALL not expose it as an incomplete community result.
