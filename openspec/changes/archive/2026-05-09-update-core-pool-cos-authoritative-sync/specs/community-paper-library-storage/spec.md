## MODIFIED Requirements
### Requirement: Core-pool complete assets can sync into local arXiv-ID reading directories
The system SHALL provide an operator script that treats backend asset records as the source of truth for completed core-pool assets, syncs recorded assets into a local arXiv-ID-based reading directory layout, and updates `backend/arxiv_id/core_pool/complete.md` as a human-readable completion report.

#### Scenario: Sync completed arXiv papers discovered from backend records
- **WHEN** an operator runs the sync script without explicit arXiv filters
- **THEN** the script SHALL query backend paper and asset records for latest object-storage assets
- **AND** it SHALL download each non-conflicting asset set that contains `source_archive`, `preview_html`, and `translated_pdf` assets into `data/community_papers/<arxiv_id>/...`.

#### Scenario: Sync updates the completion report from backend records
- **WHEN** a non-dry-run sync discovers complete arXiv IDs from backend asset records
- **THEN** the script SHALL write those discovered IDs to `backend/arxiv_id/core_pool/complete.md`
- **AND** the markdown file SHALL represent completed assets observed in backend records rather than a prerequisite input list.

#### Scenario: Sync finds multiple conflicting recorded asset sets for one arXiv ID
- **WHEN** the sync script finds more than one complete recorded asset set for the same `arXiv ID`
- **THEN** the script SHALL mark that paper as conflicted
- **AND** it SHALL skip downloading that paper until an operator resolves the ambiguity.

#### Scenario: Local operator pulls completed server assets and cleans remote copies
- **WHEN** an operator runs the sync script in remote pull-and-clean mode
- **THEN** the script SHALL SSH to the production server and run the same backend-record sync inside the backend runtime
- **AND** it SHALL archive the synced `data/community_papers/<arxiv_id>/...` directories, download and safely extract them into the local destination root, and update local `complete.md`
- **AND** after a successful local extraction it SHALL delete only the remote arXiv-ID output directories included in that archive plus the temporary archive file.
