## ADDED Requirements
### Requirement: Safe Executor Selection Without Nested Docker
LaTeX executor selection MUST avoid Docker-in-Docker and remain safe in runtime containers.

#### Scenario: Container runtime forces host executor
- **WHEN** `LATEX_RUNTIME_MODE=docker`
- **AND** backend is running inside a container runtime
- **THEN** system MUST use `HostLatexExecutor`
- **AND** system MUST log a warning about nested docker prevention

#### Scenario: Docker unavailable forces host executor
- **WHEN** `LATEX_RUNTIME_MODE=docker`
- **AND** docker binary or daemon is unavailable
- **THEN** system MUST use `HostLatexExecutor`
- **AND** system MUST log a warning

#### Scenario: Host with docker available uses docker executor
- **WHEN** `LATEX_RUNTIME_MODE=docker`
- **AND** backend is on host runtime with docker available
- **THEN** system MUST use `DockerLatexExecutor`

#### Scenario: Explicit host mode remains supported
- **WHEN** `LATEX_RUNTIME_MODE=host`
- **THEN** system MUST use `HostLatexExecutor`

#### Scenario: Invalid runtime mode downgrades safely
- **WHEN** `LATEX_RUNTIME_MODE` is an unknown value
- **THEN** system MUST log a warning
- **AND** system MUST fallback to `HostLatexExecutor`
