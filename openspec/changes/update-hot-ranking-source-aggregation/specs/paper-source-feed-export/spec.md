## ADDED Requirements
### Requirement: Time-windowed multi-source hot ranking
The source export workflow SHALL support a ranked hot-candidate mode that aggregates multiple public evidence sources into publication-date windows.

#### Scenario: Export ranked hot papers for a finite window
- **WHEN** an operator exports ranked hot candidates for `3d`, `7d`, `30d`, or `90d`
- **THEN** the workflow SHALL include only candidates whose canonical arXiv publication date falls inside that window
- **AND** it SHALL rank valid candidates with a multi-source score rather than a single platform feed order.

#### Scenario: Export ranked hot papers for all time
- **WHEN** an operator exports ranked hot candidates for `all`
- **THEN** the workflow SHALL remove the publication-date eligibility limit
- **AND** it SHALL use age-normalized scholarly impact so older papers do not dominate solely because they have had more time to accumulate citations.

#### Scenario: Source evidence is retained
- **WHEN** a ranked hot artifact is written
- **THEN** every candidate SHALL include score breakdown, confidence, source evidence, publication date, source freshness, and an operator-readable selection reason
- **AND** missing optional sources SHALL be represented as missing evidence rather than causing the whole export to fail.

### Requirement: Hot ranking source eligibility policy
The source export workflow SHALL distinguish canonical metadata, platform momentum, scholarly impact, reproducibility, and low-confidence buzz sources.

#### Scenario: Primary source families are used
- **WHEN** ranked hot candidates are generated
- **THEN** arXiv SHALL be used for canonical identity and freshness metadata
- **AND** alphaXiv SHALL be eligible as a platform-momentum source
- **AND** OpenAlex and Semantic Scholar SHALL be eligible as scholarly-impact sources
- **AND** code or repository sources SHALL be capped so they do not overwhelm non-CS disciplines.

#### Scenario: Fragile or unsuitable sources are encountered
- **WHEN** a possible upstream source lacks an approved public API, has unstable access terms, has been sunset, or does not provide reliable arXiv identity mapping
- **THEN** the workflow SHALL exclude that source from required ranking dependencies
- **AND** it MAY record the source as an optional manual or future enrichment candidate.

### Requirement: Ranked hot artifacts are reviewable before translation
Ranked hot exports SHALL produce operator-reviewable candidate lists and SHALL NOT automatically translate every discovered paper.

#### Scenario: Operator reviews ranked candidates
- **WHEN** a ranked hot export completes
- **THEN** the workflow SHALL write both JSON and Markdown artifacts for the selected window
- **AND** the Markdown artifact SHALL show enough score and evidence summary for an operator to decide which arXiv IDs to curate.

#### Scenario: Candidate is already translated or queued
- **WHEN** a ranked hot candidate already exists as translated, queued, or published community content
- **THEN** downstream workflows SHALL reuse the canonical paper identity
- **AND** they SHALL NOT require duplicate translation solely because the ranking source changed.
