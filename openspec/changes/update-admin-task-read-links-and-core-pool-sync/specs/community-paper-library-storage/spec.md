## ADDED Requirements
### Requirement: Core-pool complete assets can sync into local arXiv-ID reading directories
The system SHALL provide an operator script that syncs completed core-pool assets from COS into a local arXiv-ID-based reading directory layout.

#### Scenario: Sync one completed arXiv paper from COS
- **WHEN** an operator runs the sync script for an `arXiv ID` listed in `backend/arxiv_id/core_pool/complete.md`
- **THEN** the script SHALL download the matched COS reading assets into `data/community_papers/<arxiv_id>/...`
- **AND** it SHALL preserve reader-relevant asset groupings such as `source/`, `preview/`, and `translated/` when those assets exist.

#### Scenario: Sync finds multiple conflicting COS prefixes for one arXiv ID
- **WHEN** the sync script finds more than one candidate COS asset prefix for the same `arXiv ID`
- **THEN** the script SHALL mark that paper as conflicted
- **AND** it SHALL skip downloading that paper until an operator resolves the ambiguity.
