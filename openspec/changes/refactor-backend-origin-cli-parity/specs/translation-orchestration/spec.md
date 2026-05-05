## ADDED Requirements
### Requirement: LangGraph Origin Parity Wrapper
The backend SHALL use LangGraph as a thin wrapper around the legacy linear translation workflow when `origin_cli_parity` mode is active.

#### Scenario: Parity graph contains only legacy workflow stages
- **WHEN** the backend builds the translation graph for an `origin_cli_parity` task
- **THEN** the executable graph SHALL route through parse, translate, validate_retry, generate, and finalize in that order
- **AND** repair, ultimate downgrade, post-compile fallback, structure abort, residual-English fallback, and diagnostic nodes SHALL NOT be part of the parity graph.

#### Scenario: Parity graph preserves legacy retry semantics
- **WHEN** validation errors remain after an initial parity translation pass
- **THEN** LangGraph SHALL repeat only the legacy validation-driven retranslation loop for the same maximum retry count as `texts/origin`
- **AND** LangGraph SHALL NOT introduce additional retry, repair, downgrade, or fallback branches.

### Requirement: Origin CLI Parity Precedence
For the current delivery, `origin_cli_parity` SHALL take precedence over any existing modern-kernel requirement that would change legacy CLI translation-kernel behavior.

#### Scenario: Modern requirements are inapplicable to parity tasks
- **WHEN** an existing requirement would require hard-freeze, structure guard, controlled repair, ultimate downgrade, post-compile target-language fallback, residual-English fallback, compilation diagnostics, RAG or terminology mutation, intelligent compiler fallback, no-op retranslation, or other backend-only translation behavior during an `origin_cli_parity` task
- **THEN** that behavior SHALL be treated as not applicable to the parity task
- **AND** the task SHALL preserve the old CLI kernel behavior instead.

#### Scenario: Allowed differences are wrapper-owned only
- **WHEN** backend parity execution is compared with `texts/origin`
- **THEN** differences MAY exist only in framework orchestration, task IDs, timestamps, absolute paths, storage URLs, progress events, and live stochastic LLM response text
- **AND** kernel-controlled prompts, payloads, call ordering, retry decisions, maps, reconstructed `.tex`, compile commands, compile order, and terminal kernel status SHALL match the old CLI under deterministic mocked LLM responses.

### Requirement: Unified Backend Translation Trigger Routing
Every backend path that starts a translation task SHALL route through the same parity task configuration normalizer.

#### Scenario: Trigger config is normalized before task execution
- **WHEN** any backend API, worker, admin flow, batch flow, content-pool flow, paper bridge, or community-agent tool starts a translation
- **THEN** it SHALL produce an effective `origin_cli_parity` task configuration before `CoordinatorAgent.workflow_latextrans_async()` is called
- **AND** the task SHALL use the parity LangGraph wrapper.

### Requirement: Single-Kernel Production Runtime
Production translation task execution SHALL run only the `origin_cli_parity` kernel for the current delivery version.

#### Scenario: Production task does not shadow-run a modern kernel
- **WHEN** a production translation task starts from any backend trigger
- **THEN** the backend SHALL execute exactly one translation kernel lineage for that task
- **AND** it SHALL NOT run a modern backend kernel in parallel with the origin parity kernel.

#### Scenario: Production task emits one translated result lineage
- **WHEN** a production translation task completes or fails
- **THEN** the backend SHALL expose and persist only the result produced by the `origin_cli_parity` kernel
- **AND** it SHALL NOT emit dual old/new translated outputs, compare two kernel outputs, or choose a winner between competing kernel results.

#### Scenario: Offline parity comparison remains outside production execution
- **WHEN** parity comparison tooling runs for tests, scripts, or explicit offline diagnostics
- **THEN** it MAY execute legacy CLI and backend parity paths side by side
- **AND** that comparison SHALL NOT be part of normal production task execution or result selection.
