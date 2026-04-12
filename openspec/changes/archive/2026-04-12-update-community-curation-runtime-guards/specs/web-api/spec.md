## MODIFIED Requirements
### Requirement: Backend Runtime Parity Config Propagation
The web API SHALL pass the effective backend runtime parity configuration into the coordinator/task snapshot instead of relying on implicit defaults.

#### Scenario: Translate request builds parity-complete agent config
- **WHEN** the backend starts a translation task from the web API
- **THEN** it MUST propagate the effective translation/orchestration config into `agent_config`
- **AND** that config MUST include `translation_mode`, `generate_terminology_table`, `use_compilation_diagnostics`, `category`, `model_context_tokens`, `prompt_reserve_tokens`, `task_id`, `output_dir`, and `tex_sources_dir`
- **AND** the captured task configuration snapshot MUST reflect those effective values.

#### Scenario: Task-level LLM concurrency is bounded for parity
- **WHEN** the backend computes the per-task LLM concurrency passed into orchestration
- **THEN** it MUST cap the task-level value to the parity-safe ceiling of `3`
- **AND** MUST record the effective bounded value in the task-start/runtime snapshot.
