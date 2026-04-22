## ADDED Requirements

### Requirement: Layered Remedial Translation Budgets
The translation orchestration layer SHALL bound failure-driven remedial work with explicit ceilings across local callsites, per-part rescue, per-task rescue, no-progress streaks, and outer validation rounds.

#### Scenario: Local remedial retry budget is exhausted
- **WHEN** a single remedial callsite has already retried the same repair action `2` times
- **THEN** the system MUST stop issuing further retries from that local callsite
- **AND** it MUST continue through the next deterministic fallback or terminal path instead of looping again.

#### Scenario: Part-level nested rescue budget is exhausted
- **WHEN** one translated part reaches `4` nested rescue attempts in the same task run
- **THEN** the system MUST stop nested rescue for that part
- **AND** it MUST preserve the best allowed fallback outcome for that part without consuming further nested rescue budget.

#### Scenario: Task-level nested rescue budget is exhausted
- **WHEN** the task reaches `24` total nested rescue attempts across all parts
- **THEN** the orchestration layer MUST reject further nested rescue attempts for the task
- **AND** remaining parts MUST continue only through non-nested fallback or terminal failure handling.

#### Scenario: Consecutive no-progress remedial streak is exhausted
- **WHEN** `3` consecutive remedial attempts complete without reducing the remaining failure set or materially improving the candidate output
- **THEN** the system MUST stop further remedial LLM work for that run
- **AND** it MUST continue through the existing fallback or terminal failure path.

#### Scenario: Outer validation rounds are exhausted
- **WHEN** the run has already completed `2` validate-and-retranslate rounds
- **THEN** the system MUST NOT start a third outer remedial round
- **AND** it MUST resolve the task through compile, downgrade, or terminal failure handling using the current best state.

### Requirement: Task-Level Remedial Call Accounting
The translation orchestration layer SHALL maintain one explicit per-task counter for failure-driven remedial LLM calls and SHALL use semantic counting rules that do not depend on helper-function naming.

#### Scenario: Repair-oriented LLM invocation counts against the task budget
- **WHEN** the system issues an LLM call for nested rescue, paragraph rescue, masked rescue, fragment rescue, force retry, validate-triggered retranslation, or another repair-like corrective invocation
- **THEN** that invocation MUST increment the task remedial-call counter.

#### Scenario: First-pass translation does not count against the task remedial budget
- **WHEN** the system performs a normal first-pass translation or another non-failure-driven baseline step
- **THEN** that invocation MUST NOT increment the remedial-call counter.

#### Scenario: Task remedial-call budget is exhausted
- **WHEN** the task remedial-call counter reaches `40`
- **THEN** the orchestration layer MUST reject additional remedial LLM invocations for that task
- **AND** it MUST record a stable terminal or fallback reason identifying remedial-budget exhaustion.

### Requirement: Hard-Freeze Violation Budgeting
The translation orchestration layer SHALL treat repeated `HARD_FREEZE_PROTOCOL_VIOLATION` events as a bounded task-level failure signal rather than an unbounded retry trigger.

#### Scenario: Hard-freeze violations remain recoverable below the cap
- **WHEN** a task has accumulated fewer than `8` `HARD_FREEZE_PROTOCOL_VIOLATION` events
- **THEN** the orchestration layer MAY continue through the normal bounded retry or fallback path for the affected units.

#### Scenario: Hard-freeze violation cap is exhausted
- **WHEN** a task reaches `8` `HARD_FREEZE_PROTOCOL_VIOLATION` events
- **THEN** the system MUST stop issuing further remedial work that depends on accepting new violating responses
- **AND** it MUST resolve the task through terminal failure or bounded non-LLM fallback with an explicit recorded reason.

### Requirement: Fatal Upstream Provider Errors Are Bounded
The translation orchestration layer SHALL treat deterministic upstream-provider fatal errors as bounded termination or bounded failover signals rather than as ordinary rescue candidates.

#### Scenario: Fatal provider error short-circuits repeated remedial work
- **WHEN** an LLM call fails with a deterministic fatal provider error such as authentication failure, quota exhaustion, unsupported model, or equivalent non-retryable upstream denial
- **THEN** the orchestration layer MUST NOT route that failure into unbounded nested rescue, validate-triggered retranslation, or repeated force-retry loops
- **AND** it MUST continue only through a bounded failover or terminal path.

#### Scenario: Fatal provider handling records stable failure reason
- **WHEN** bounded failover is unavailable or exhausted after a fatal provider error
- **THEN** the task MUST resolve with a stable machine-readable terminal reason identifying the upstream fatal-error class
- **AND** operators MUST be able to distinguish quota, authentication, and model-availability style failures from structural translation failures.

### Requirement: Execution-Stage Timeout Uses an Explicit Start Boundary
The translation orchestration and admin-curation timeout logic SHALL begin execution-stage timing from one explicit persisted runtime boundary that denotes active translation work.

#### Scenario: Execution timing does not start at enqueue time
- **WHEN** a translation task has been created, queued, downloaded, or source-validated but has not yet emitted the persisted active-translation-start boundary
- **THEN** execution-stage timeout measurement MUST NOT begin
- **AND** any elapsed time before that boundary MUST remain outside the execution-stage timeout budget.

#### Scenario: Execution timing begins at persisted active-work boundary
- **WHEN** the task emits the persisted active-translation-start boundary for the current run
- **THEN** execution-stage timeout measurement MUST begin from that timestamp
- **AND** later timeout handling MUST use that persisted boundary instead of curation-side enqueue timestamps or inferred heuristics.
