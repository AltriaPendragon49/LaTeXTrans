# latex-translation-core Specification

## Purpose
Define the current production LaTeX translation kernel. As of the May 2026 cleanup, the backend production path is `origin_cli_parity`: a backend-owned implementation of the legacy CLI translation behavior. Historical modern-kernel enhancement systems that are not used by production have been removed from the codebase and are retained only in archived OpenSpec records.

## Requirements
### Requirement: Backend-Owned Origin CLI Parity Kernel
The backend translation core SHALL execute backend-owned code that reproduces the legacy CLI translation-kernel behavior when `origin_cli_parity` mode is active.

#### Scenario: Production tasks use parity mode
- **WHEN** a backend translation task is created from upload, arXiv download, batch processing, community curation, or community-agent tooling
- **THEN** the effective task configuration MUST use `translation_core_mode = "origin_cli_parity"`
- **AND** the task MUST execute the backend-owned parity kernel.

#### Scenario: Legacy source is not a runtime dependency
- **WHEN** production backend code runs an `origin_cli_parity` task
- **THEN** it MUST NOT dynamically import runtime code from `texts/origin`
- **AND** `texts/origin` MAY be used only by tests, parity comparison scripts, or explicit offline diagnostics.

### Requirement: Production Kernel Scope
The production translation kernel SHALL stay limited to the parity workflow: parse source maps, translate selected content, validate/retry using the parity validator contract, reconstruct LaTeX, compile, and finalize the PDF.

#### Scenario: Modern enhancement systems are absent from production execution
- **WHEN** a production translation task runs
- **THEN** controlled repair, structure repair nodes, hard-freeze orchestration, precompile structure guard, post-compile target-language fallback, residual-English fallback, ultimate downgrade, compilation diagnostic nodes, and intelligent multi-engine selection MUST NOT be called, scheduled, or wrapped as no-op production steps.

#### Scenario: Removed enhancement code is not required
- **WHEN** the backend starts or a translation task executes
- **THEN** runtime MUST NOT require modules under removed enhancement paths such as translation downgrade handlers, repair schedulers, pipeline schemas, controlled repair agents, or structure guard modules.

### Requirement: Parity Parser And Translation Behavior
The parser and translator SHALL use the backend-owned parity prompt and parsing behavior needed to match the legacy CLI baseline.

#### Scenario: Parser environment judgment uses parity prompts
- **WHEN** the parser judges whether environments require translation in parity mode
- **THEN** it MUST use the backend-owned origin CLI parity prompt snapshot
- **AND** it MUST persist map files compatible with downstream parity translation and reconstruction.

#### Scenario: Translator uses parity prompts
- **WHEN** the translator sends first-pass or retry translation requests
- **THEN** it MUST use backend-owned origin CLI parity prompts
- **AND** it MUST preserve the legacy validation-driven retry semantics instead of routing through backend-only repair or downgrade branches.

### Requirement: Parity Reconstruction
The reconstruction stage SHALL rebuild translated LaTeX from parity map files while preserving the legacy CLI output contract.

#### Scenario: Reconstructor uses parity mode
- **WHEN** generation reconstructs the translated project
- **THEN** it MUST instantiate the LaTeX constructor with origin CLI parity behavior
- **AND** it MUST produce a compile-ready translated project directory from the translated maps.

#### Scenario: Translated section bytes are preserved
- **WHEN** translated map content is safe under the parity reconstruction contract
- **THEN** reconstruction MUST preserve that translated content
- **AND** it MUST NOT apply removed backend-only downgrade or source-rollback logic.

### Requirement: Origin CLI Parity Compiler
The compiler SHALL run the legacy parity compile sequence and return a structured result used by generation/finalization.

#### Scenario: Parity compile sequence
- **WHEN** generation compiles a reconstructed parity project
- **THEN** it MUST call `compile_with_origin_cli_parity`
- **AND** the compiler MUST use the parity engine sequence and bibliography handling expected by the legacy CLI baseline.

#### Scenario: Compile result contract
- **WHEN** compilation succeeds
- **THEN** the result MUST include an existing `pdf_path`, status, engine, warnings when present, and error count
- **AND** generation MUST treat a missing returned PDF path as `failed_compilation`.

### Requirement: Parity Health Enhancement Branch
The parity compiler SHALL keep any bounded health enhancement branch isolated to a temporary project copy and MAY skip the branch when baseline output is already acceptable.

#### Scenario: Healthy baseline wins
- **WHEN** baseline origin CLI parity compilation produces an acceptable PDF
- **THEN** the health branch MUST NOT replace that result.

#### Scenario: Temporary health repair is discardable
- **WHEN** the health branch attempts deterministic LaTeX/PDF repairs
- **THEN** it MUST run on a temporary copy
- **AND** failure or non-improvement MUST fall back to the baseline parity result without mutating the primary reconstructed project.

#### Scenario: Health branch stays narrow
- **WHEN** the parity health branch runs
- **THEN** it MAY apply bounded deterministic precompile/PDF health repairs
- **AND** it MUST NOT invoke removed modern-kernel systems such as controlled repair, hard-freeze routing, post-compile target-language fallback, residual-English fallback, ultimate downgrade, or intelligent multi-engine selection.

### Requirement: Compile Queue Observability
The async generation path SHALL expose compile queue waiting only at the shared compilation semaphore boundary.

#### Scenario: Immediate compile path skips waiting status
- **WHEN** the shared compile semaphore has immediate capacity
- **THEN** generation MUST proceed directly to active compilation
- **AND** it MUST NOT emit a waiting-for-compile-slot progress message.

#### Scenario: Contended compile path records timings
- **WHEN** the compile semaphore is locked
- **THEN** generation MUST emit waiting status before awaiting the semaphore
- **AND** the result payload MUST include compile queue wait and compile execution timing.

### Requirement: Runtime-Selectable LaTeX Executor Strategy
The lower-level LaTeX compiler SHALL preserve the parity compile result contract when runtime-selectable host or docker command execution is configured.

#### Scenario: Docker mode avoids nested docker
- **WHEN** docker execution is requested from inside a container runtime
- **THEN** the compiler MUST avoid Docker-in-Docker
- **AND** it MUST use a safe host-compatible executor path.

#### Scenario: Invalid runtime mode falls back safely
- **WHEN** `LATEX_RUNTIME_MODE` is unsupported
- **THEN** the compiler MUST fall back to a safe executor mode
- **AND** emit a warning log.

### Requirement: Current Historical Boundary
Archived specs may describe removed translation-kernel experiments, but current specs SHALL treat `origin_cli_parity` plus the bounded parity health branch as the production source of truth.

#### Scenario: Archived modern-kernel spec conflicts with current parity behavior
- **WHEN** an archived OpenSpec record requires controlled repair, hard-freeze orchestration, structure guard, ultimate downgrade, post-compile fallback, residual-English fallback, or diagnostic nodes for production translation
- **THEN** the current production parity spec MUST take precedence
- **AND** the archived record MUST be interpreted as historical context, not active implementation truth.
