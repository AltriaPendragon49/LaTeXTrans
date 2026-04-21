## ADDED Requirements

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
