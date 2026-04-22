# community-admin-curation Specification

## Purpose
TBD - created by archiving change update-community-admin-curation-flow. Update Purpose after archive.
## Requirements
### Requirement: Admin curation page is visible only to local admins
The product SHALL expose the community curation page only to authenticated users with the local `admin` role.

#### Scenario: Admin user opens the shared shell
- **WHEN** an authenticated user with the local `admin` role renders the shared shell
- **THEN** the shell SHALL show the `社区论文新增入库` navigation entry
- **AND** visiting that page SHALL be allowed for that user.

#### Scenario: Non-admin user opens the shared shell
- **WHEN** an authenticated user without the local `admin` role renders the shared shell
- **THEN** the `社区论文新增入库` navigation entry SHALL be hidden
- **AND** the corresponding page route SHALL not be available as a normal product action.

### Requirement: Admin curation page supports both arXiv and archive intake
The admin curation page SHALL support official community-paper intake through newline-delimited `arXiv ID` entry and TeX-containing archive upload.

#### Scenario: Admin curates by newline-delimited arXiv ids
- **WHEN** an admin pastes one `arXiv ID` per line on the curation page
- **THEN** the page SHALL parse each non-empty line as one intake item
- **AND** it SHALL submit the parsed items into the community curation pipeline
- **AND** the UI SHALL show the parsed item count before submission.

#### Scenario: Admin curates by archive upload
- **WHEN** an admin uploads a TeX-containing archive on the curation page
- **THEN** the page SHALL submit that archive into the same community curation pipeline
- **AND** the UI SHALL show tracked progress for that item.

### Requirement: Admin curation page supports bounded-concurrency batch handling
The admin curation page SHALL support multi-item submission while using bounded parallelism behind the scenes, and the admin history surface SHALL allow durable management of retained task records through accurate status filters and selected-item hard deletion.

#### Scenario: Admin submits a mixed or multi-item batch
- **WHEN** an admin submits multiple items in one curation batch
- **THEN** the system SHALL track each paper separately inside the batch
- **AND** the backend SHALL schedule execution with bounded concurrency to improve throughput without dropping the final publication quality bar.

#### Scenario: Admin filters history records by processing state
- **WHEN** an admin views the curation task history and selects the `processing` filter
- **THEN** the history result SHALL include jobs whose persisted statuses are `processing`, `translating`, or `publishing`
- **AND** the result SHALL exclude `queued`, `completed`, and `failed` jobs unless they also match a different active filter.

#### Scenario: Admin views all history records
- **WHEN** an admin selects the `all` filter on the curation task history page
- **THEN** the history query SHALL not apply a status restriction
- **AND** queued, in-flight, completed, and failed jobs SHALL all remain eligible for display.

#### Scenario: Admin deletes selected history records
- **WHEN** an admin selects one or more currently listed curation history records and confirms batch delete
- **THEN** the system SHALL hard-delete each selected record using the existing per-job deletion rules
- **AND** the response SHALL report which job ids were deleted and which job ids failed deletion so the admin can retry only the remaining items.

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

### Requirement: Admin role assignment uses local role state after normal account creation
The product SHALL treat admin access as a local-role assignment layered on top of a normally created user account.

#### Scenario: Existing local user is granted admin
- **WHEN** an operator marks an existing local user record as `admin` through the supported local role mechanism
- **THEN** the next resolved session for that user SHALL include the `admin` role
- **AND** the community curation page and admin-only controls SHALL become available to that user.

### Requirement: Admin curation uses stage-aware timeout budgets
The admin-curation workflow SHALL track admission waiting and active translation execution as separate timeout domains instead of enforcing one shared wall-clock timeout across the entire intake flow.

#### Scenario: Queue or download time does not consume execution timeout
- **WHEN** a curation job is downloading source files, validating intake artifacts, or waiting in the translation queue before active processing begins
- **THEN** that elapsed time MUST count only toward admission-stage waiting
- **AND** it MUST NOT consume the active translation execution timeout budget.

#### Scenario: Admission-stage timeout fires before translation starts
- **WHEN** the curation job exceeds the configured admission-stage waiting budget before the translation task enters active processing
- **THEN** the curation job MUST transition to a terminal failed state with an admission-timeout reason
- **AND** it MUST NOT report that failure as an execution-timeout of translation work.

#### Scenario: Execution-stage timeout fires after translation starts
- **WHEN** the translation task has entered active processing and later exceeds the configured execution-stage timeout budget
- **THEN** the curation job MUST transition to a terminal failed state with an execution-timeout reason
- **AND** the recorded timeout duration MUST exclude the earlier queue or download waiting time.

#### Scenario: Execution timeout uses translation active-work boundary
- **WHEN** admin curation monitors a translation task that has been accepted but has not yet emitted the persisted active-translation-start boundary
- **THEN** the curation workflow MUST continue treating the job as admission-stage waiting
- **AND** it MUST NOT promote that job into execution-stage timeout accounting yet.

### Requirement: Admin curation translation defaults are cost-bounded
The admin-curation workflow SHALL apply curation-specific translation defaults that remove lower-value spend while preserving required publication outputs.

#### Scenario: Curation-triggered translation disables terminology table generation
- **WHEN** admin curation starts a translation task for intake
- **THEN** the effective translation config MUST default `generate_terminology_table` to `false`
- **AND** the task MUST remain eligible for successful curation completion without a terminology-table artifact.

#### Scenario: Structured insight generation remains enabled
- **WHEN** admin curation translation uses the curation-specific defaults from this change
- **THEN** structured insight generation MUST remain enabled unless another approved change explicitly disables it
- **AND** successful curation MUST still require the structured insight stage.

### Requirement: Admin curation status exposes stable failure reasons
The admin-curation workflow SHALL expose machine-readable timeout and terminal reasons so operators can distinguish admission backlog, execution overrun, retry-budget exhaustion, and upstream-provider failure.

#### Scenario: Curation status includes timeout reason
- **WHEN** a curation job fails due to admission-stage timeout or execution-stage timeout
- **THEN** the tracked curation status MUST include a stable machine-readable timeout reason
- **AND** operators MUST be able to distinguish which timeout domain fired.

#### Scenario: Curation status includes upstream or budget terminal reason
- **WHEN** the underlying translation task ends because of remedial-budget exhaustion or a fatal upstream-provider error
- **THEN** the tracked curation status MUST expose the corresponding stable terminal reason
- **AND** the curation UI or API consumer MUST NOT need to infer that reason from free-form log text.

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

### Requirement: Admin curation task records page is visible only to local admins
The product SHALL expose an admin-only curation task records page for managing retained curation history.

#### Scenario: Admin opens the task records page
- **WHEN** an authenticated user with the local `admin` role renders the shared shell
- **THEN** the shell SHALL show a navigation entry for the admin curation task records page
- **AND** visiting that page SHALL be allowed for that user.

#### Scenario: Non-admin user opens the shared shell
- **WHEN** an authenticated user without the local `admin` role renders the shared shell
- **THEN** the task records navigation entry SHALL be hidden
- **AND** the corresponding page route SHALL not be available as a normal product action.

### Requirement: Admin curation task records page shows retained task history
The admin curation task records page SHALL show retained curation jobs across queued, processing, completed, and failed states.

#### Scenario: Admin reviews retained curation history
- **WHEN** an admin opens the task records page
- **THEN** the page SHALL show curation jobs with status, task identifiers, batch identifiers, timestamps, and error context
- **AND** it SHALL support simple filtering by status plus search by `arXiv ID` or `batch_id`.

### Requirement: Admin curation task records page supports permanent delete management
The admin curation task records page SHALL allow admins to permanently delete failed or completed curation records.

#### Scenario: Admin permanently deletes a failed curation record
- **WHEN** an admin confirms deletion for a failed curation job
- **THEN** the system SHALL permanently remove the retained curation-job row, retained translation-task row, and retained failed artifacts for that job.

#### Scenario: Admin permanently deletes a completed curation record
- **WHEN** an admin confirms deletion for a completed curation job that published a paper
- **THEN** the system SHALL reuse the existing admin hard-delete flow for the published paper and its assets
- **AND** it SHALL also remove the linked curation-job history row.

