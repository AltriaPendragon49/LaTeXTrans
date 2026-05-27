## ADDED Requirements
### Requirement: Time-windowed evidence-based hot ranking
The source export workflow SHALL support a ranked hot-candidate mode that combines public evidence with publication-date windows and time decay.

#### Scenario: Export ranked hot papers for a finite window
- **WHEN** an operator exports ranked hot candidates for `3d`, `7d`, `30d`, or `90d`
- **THEN** the workflow SHALL include only candidates whose canonical arXiv publication date falls inside that window
- **AND** it SHALL rank valid candidates with an evidence score multiplied by a window-specific time-decay factor rather than a single platform feed order.

#### Scenario: Export ranked hot papers for all time
- **WHEN** an operator exports ranked hot candidates for `all`
- **THEN** the workflow SHALL remove the publication-date eligibility limit
- **AND** it SHALL use age normalization and time decay so older papers do not dominate solely because they have had more time to accumulate citations.

#### Scenario: Source evidence is retained
- **WHEN** a ranked hot artifact is written
- **THEN** every candidate SHALL include score breakdown, time decay, source evidence, publication date, source freshness, and an operator-readable selection reason
- **AND** missing optional sources SHALL be represented as missing evidence rather than causing the whole export to fail.

### Requirement: Hot ranking evidence policy
The source export workflow SHALL distinguish canonical metadata, attention, authority, implementation, local engagement, and excluded low-confidence sources.

#### Scenario: Primary source families are used
- **WHEN** ranked hot candidates are generated
- **THEN** arXiv SHALL be used for canonical identity and freshness metadata
- **AND** Hugging Face Papers and alphaXiv SHALL be eligible as attention sources when accessible
- **AND** OpenAlex and Semantic Scholar SHALL be eligible as authority sources
- **AND** GitHub repository evidence SHALL be eligible as an implementation source
- **AND** implementation evidence SHALL be capped so it does not overwhelm non-CS disciplines.

#### Scenario: Fragile or unsuitable sources are encountered
- **WHEN** a possible upstream source lacks an approved public API, has unstable access terms, has been sunset, or does not provide reliable arXiv identity mapping
- **THEN** the workflow SHALL exclude that source from required ranking dependencies
- **AND** it MAY record the source as an optional manual or future enrichment candidate.

### Requirement: Hot ranking score remains simple and explainable
Ranked hot exports SHALL compute hotness with a small number of named score components and a visible time-decay factor.

#### Scenario: Hot score is calculated
- **WHEN** a ranked hot candidate has normalized evidence signals
- **THEN** the workflow SHALL calculate an evidence score from attention, authority, implementation, and local engagement components
- **AND** it SHALL calculate `hot_score` by multiplying the evidence score by the selected window's time-decay factor.

#### Scenario: Time decay is applied by window
- **WHEN** a candidate is ranked for `3d`, `7d`, `30d`, `90d`, or `all`
- **THEN** the workflow SHALL use a configured half-life for that window
- **AND** the selected half-life SHALL be visible in the generated artifact metadata.

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

### Requirement: Scheduled daily hot-ranking auto-intake
The system SHALL provide a periodic Worker-side cron task that refreshes hot rankings daily and automatically starts admin-curation translation for qualified new candidates.

#### Scenario: Daily cron triggers hot ranking refresh
- **WHEN** the Worker process reaches the configured daily trigger time in CST timezone
- **THEN** the cron task SHALL run the hot ranking engine for the configured default window
- **AND** it SHALL write updated `latest.json` and `latest.md` artifacts under `backend/arxiv_id/hot_ranked/{window}/`
- **AND** it SHALL acquire a Redis lock before execution to prevent concurrent duplicate runs.

#### Scenario: New top-ranked papers are auto-intaked
- **WHEN** the daily cron has produced a fresh ranked candidate list
- **THEN** the task SHALL query the database for already-translated, already-queued, and already-published arXiv IDs
- **AND** it SHALL exclude those arXiv IDs from auto-intake
- **AND** it SHALL select the top-N remaining candidates (configurable, default 20) above the minimum score threshold (configurable, default 50)
- **AND** it SHALL create a curation job for each selected candidate with admin system user identity, `source_family="hot_ranking"`, and the hot score breakdown stored in job metadata
- **AND** it SHALL schedule each curation job through the existing `_schedule_curation_job` flow.

#### Scenario: Auto-intake skips already-in-progress papers
- **WHEN** a candidate arXiv ID has an existing curation job in `processing`, `translating`, `queued`, or `publishing` status
- **THEN** the auto-intake task SHALL skip that candidate
- **AND** it SHALL record the skip reason in the daily intake summary.

#### Scenario: Daily intake summary is generated
- **WHEN** the daily cron run completes (whether successful, partial, or with zero intakes)
- **THEN** the task SHALL write a Markdown summary to `backend/arxiv_id/hot_ranked/daily_intake/YYYY-MM-DD.md`
- **AND** the summary SHALL include: trigger window, timestamp, total candidate count, skip count with reasons, intake count, and a per-paper table with hot score, component breakdown, and intake reason
- **AND** a paired JSON artifact SHALL be written to `backend/arxiv_id/hot_ranked/daily_intake/YYYY-MM-DD.json` with full `source_evidence` arrays.

#### Scenario: Auto-intake respects quality gates
- **WHEN** an auto-intaken curation job completes translation but fails the community quality gate
- **THEN** the paper SHALL NOT be published
- **AND** the quality gate failure SHALL be visible in the admin curation UI for that job
- **AND** the next daily summary SHALL list previously-auto-intaken papers that failed quality gating.
