## ADDED Requirements
> Current status: superseded in part by the May 9, 2026 cleanup. `origin_cli_parity` remains current production truth, but unused modern backend enhancement systems are removed from production code instead of being retained as dormant systems.

### Requirement: Origin CLI Parity Translation Kernel
The backend translation core SHALL execute backend-owned code that reproduces the legacy CLI translation-kernel behavior from `texts/origin` when `origin_cli_parity` mode is active.

#### Scenario: Parser artifacts match the legacy CLI
- **WHEN** the backend parity kernel parses the same LaTeX source tree as `texts/origin`
- **THEN** it SHALL produce byte-for-byte identical `inputs_map.json`, `envs_map.json`, `captions_map.json`, `newcommands_map.json`, and `sections_map.json` kernel artifacts for deterministic inputs
- **AND** no backend-only parser enhancement SHALL alter those artifacts in parity mode.

#### Scenario: Translator LLM calls match the legacy CLI contract
- **WHEN** the backend parity kernel translates parsed artifacts
- **THEN** it SHALL use backend-owned migrated prompt code with the same legacy prompt initialization, prompt text, message payload shape, `temperature`, `max_new_tokens`, timeout behavior, retry behavior, source fallback behavior, and per-section translation semantics as `texts/origin`
- **AND** backend-only hard-freeze, rescue, repair, no-op retry, target-language fallback, and payload-skip guard logic SHALL NOT change the accepted translation content in parity mode.

#### Scenario: Production runtime is backend-owned
- **WHEN** production backend code runs an `origin_cli_parity` task
- **THEN** every required legacy behavior SHALL be provided from files under `backend/`
- **AND** production code SHALL NOT dynamically import, extend `sys.path` to, or read runtime code from repo-root `texts/origin`, `src.formats`, or `src.agents`
- **AND** `texts/origin` SHALL be used only by tests, parity comparison scripts, or explicit offline diagnostics as the canonical behavior baseline.

#### Scenario: Validator retry loop matches the legacy CLI
- **WHEN** validation reports errors after the first translation pass
- **THEN** the backend parity kernel SHALL switch to the legacy retranslation mode and retry validation-driven translation at most three rounds, matching `texts/origin/src/agents/coordinator_agent.py`
- **AND** it SHALL NOT replace that loop with backend validation subclassification, repair routing, or downgrade routing.

#### Scenario: Generator and compiler match the legacy CLI
- **WHEN** translation and validation finish
- **THEN** the backend parity kernel SHALL reconstruct the translated project and attempt compilation using the legacy generator and compile semantics
- **AND** the default legacy compile path SHALL try pdflatex before xelatex, without backend intelligent compilation fallback changing the selected output.

#### Scenario: Adapter changes are wrapper-only
- **WHEN** backend code integrates the old CLI kernel into FastAPI, task management, storage, or LangGraph
- **THEN** compatibility code SHALL adapt only framework-owned concerns such as paths, config plumbing, progress callbacks, task IDs, timestamps, and storage locations
- **AND** it SHALL NOT rewrite, improve, normalize, repair, or reinterpret parser, translator, validator, generator, compiler, prompt, payload, retry, or artifact behavior.

### Requirement: Modern Translation Systems Remain Unused In Parity Mode
Modern backend translation-protection and repair systems SHALL NOT be invoked by `origin_cli_parity` tasks. Systems removed by the May 9, 2026 cleanup are historical only and SHALL NOT be treated as production dependencies.

#### Scenario: Parity task bypasses modern safeguards
- **WHEN** a backend translation task runs in `origin_cli_parity` mode
- **THEN** hard-freeze transport, precompile structure guard, controlled repair, ultimate downgrade, post-compile target-language fallback, residual-English fallback, compilation diagnostics, parser environment LLM judgment, intelligent compiler fallback, RAG or terminology mutation, and backend-only quality-improvement paths SHALL NOT be called, scheduled, or wrapped as no-op steps
- **AND** task logs or config snapshots SHALL identify them as not invoked for that task.
