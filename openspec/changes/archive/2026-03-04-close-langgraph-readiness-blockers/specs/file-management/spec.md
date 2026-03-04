## MODIFIED Requirements
### Requirement: Failed Output Quarantine
The system SHALL quarantine failed task outputs into `data/failed_tasks`, and SHALL move only `outputs/{task_id}` artifacts.  
The system SHALL NOT move `terms/{task_id}` and SHALL NOT move or delete upload cache artifacts as part of this quarantine behavior.  
After quarantine, the system SHALL perform scoped replay-evidence reference rewrite so replay references remain reachable from the new quarantine root.

#### Scenario: Quarantine Failed Task Output
- **WHEN** task status is updated to `failed` or `failed_compilation`
- **THEN** the system moves `data/outputs/{task_id}` to `data/failed_tasks/{task_id}`
- **AND** the quarantined files remain available for debugging.

#### Scenario: Scoped replay reference rewrite after quarantine
- **WHEN** output quarantine succeeds
- **THEN** replay references under old task root (`.../outputs/{task_id}/...`) are rewritten to the new failed root
- **AND** rewrite applies only to scoped evidence fields (`replay_bundle_ref`, `main_tex_path`, and bundle keys ending `_path`/`_ref` when in-scope)
- **AND** unrelated absolute paths MUST remain unchanged.

#### Scenario: Evidence chain warning without status mutation
- **WHEN** rewritten `replay_bundle_ref` or `main_tex_path` is unreachable
- **THEN** the system writes `evidence_chain_broken=true` and a warning event in task log
- **AND** task terminal status semantics remain unchanged.
