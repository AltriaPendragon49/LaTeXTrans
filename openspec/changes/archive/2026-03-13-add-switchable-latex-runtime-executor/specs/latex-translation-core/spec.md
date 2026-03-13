## ADDED Requirements

### Requirement: Runtime-Selectable LaTeX Executor Strategy
The system MUST support a runtime-selectable LaTeX command executor strategy for compilation subprocesses while preserving existing compilation behavior and fallback logic.

#### Scenario: Default docker execution
- **WHEN** `LATEX_RUNTIME_MODE` is unset
- **THEN** the compiler MUST execute LaTeX commands through docker runtime.

#### Scenario: Explicit host compatibility
- **WHEN** `LATEX_RUNTIME_MODE` equals `host`
- **THEN** the compiler MUST execute the original LaTeX command directly on host
- **AND** host runtime behavior MUST remain consistent with the pre-change host execution path.

#### Scenario: Docker-based execution wrapping
- **WHEN** `LATEX_RUNTIME_MODE` equals `docker`
- **THEN** the compiler MUST execute LaTeX commands through `docker run --rm`
- **AND** MUST map the working directory into the container and set container working directory explicitly
- **AND** MUST NOT use `shell=True`.

#### Scenario: Compilation behavior invariance across runtime modes
- **WHEN** runtime mode switches between `host` and `docker`
- **THEN** compile parameter semantics, engine fallback ordering, and error-handling flow MUST remain unchanged
- **AND** process-tree cleanup behavior (`_kill_process_tree`) MUST remain unchanged.

#### Scenario: Output and diagnostics consistency in docker mode
- **WHEN** docker runtime mode is enabled
- **THEN** compilation outputs MUST be written to the same host output locations expected by existing logic
- **AND** stdout/stderr capture and log parsing flow MUST remain available to existing diagnostics.

#### Scenario: Invalid runtime mode fallback
- **WHEN** `LATEX_RUNTIME_MODE` is set to an unsupported value
- **THEN** the compiler MUST fall back to docker execution mode
- **AND** MUST emit a warning log for the invalid configuration.
