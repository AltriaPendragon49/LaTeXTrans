# translation-orchestration Specification

## Purpose
TBD - created by archiving change reuse-placehodler-finish. Update Purpose after archive.
## Requirements
### Requirement: High-Risk Text Pre-LLM Isolation
The system SHALL strictly isolate structural LaTeX components and high-risk text tokens before they reach the language model to prevent structural corruption.

#### Scenario: Inline Math Hard Isolation
- **WHEN** the LaTeX text fragment contains inline math (`$...$` or `\(...\)`) that is not escaped and not inside a verbatim/code block
- **THEN** the system MUST extract the math block
- **AND** replace it with an immutable placeholder (e.g., `<INLMATH_01>`)
- **AND** the LLM MUST NOT receive any raw math syntax (`$`, `_`, `^`, `\`) within this isolated block.

#### Scenario: Code-like Text Token Escaping
- **WHEN** the text fragment contains non-math, code-like identifiers containing underscores (e.g. `user_id_field`)
- **THEN** the system MUST pre-process these tokens by escaping the underscores (`\_`) or replacing them via lightweight placeholders
- **AND** NO bare `_` may enter the semantic translation payload destined for the LLM in text mode.

### Requirement: Validation Subclassification and Controlled LLM Retry
The validation agent SHALL subclassify structural (Type C) errors to differentiate between isolated slip-ups and total structural collapse, deploying controlled LLM retries only for safe scenarios.

#### Scenario: Type C1 (Local/Contained) Classification
- **WHEN** the Validator Agent detects a missing placeholder, an isolated `math_delimiter_mismatch`, or a specific contained drop
- **THEN** it MUST classify the error as C1.

#### Scenario: Controlled 1-Max Retry for C1
- **WHEN** a C1 error is identified
- **THEN** the system MUST execute exactly 1 targeted retry using the LLM
- **AND** inject 100-200 characters of surrounding context alongside the error type
- **AND** strictly instruct the LLM: *Only restore missing symbols; do not modify placeholders; do not retranslate content.*

#### Scenario: Type C2 (Global/Structural) Classification
- **WHEN** the Validator Agent detects severe structural breakdown, such as missing `\begin{env}` or `\end{env}` or widespread command loss
- **THEN** it MUST classify the error as C2
- **AND** the system MUST bypass the LLM retry loop entirely, proceeding directly to deterministic repair or fallback.

### Requirement: Deterministic LaTeX Structural Repair
The repair strategy MUST rely on deterministic rules rather than context-dependent guessing across translated text, and structural fallback candidates MUST preserve target-language content until compilation proves they are unsafe.

#### Scenario: Limited fallback granularity after compile failure
- **WHEN** an uncorrectable structural failure mandates fallback handling
- **THEN** the system MUST limit this handling to the specific isolated chunk or environment containing the error
- **AND** MUST NOT blanketly revert an entire section or document unless the structure guard already rejected the bundle globally.

### Requirement: State-Machine Orchestration and Agent Scope
The system SHALL orchestrate parsing, translation, validation, and compilation exclusively through a LangGraph StateMachine.

#### Scenario: LangGraph Agent Guardrails
- **WHEN** the agent handles orchestration across paragraphs, package conflicts, or layout logic
- **THEN** it operates within scope
- **AND** the system MUST PREVENT the agent from executing character-level syntax fixes or entering infinite retry cycles.

#### Scenario: Phase 4b Intelligent Diagnostic Activation
- **WHEN** compilation fails and the pipeline enters the finalization stage
- **THEN** the system MUST activate the `CompilationDiagnosticNode` by default (unless `use_compilation_diagnostics` is explicitly disabled)
- **AND** the node MUST remain isolated from the source LaTeX files.

### Requirement: Structured Diagnostic Output
The diagnostic node SHALL emit formalized failure reports post-compilation to aid system maintainers and downstream consumers.

#### Scenario: Emitting the Diagnostic Payload
- **WHEN** a compilation failure limits out or reaches an unrecoverable state
- **THEN** the Agent MUST generate a `DiagnosticReport` Pydantic object
- **AND** the report MUST include: `task_id`, `error_count`, `root_cause_category`, `suggestions` (predefined action whitelist), `confidence`, and `is_actionable` flag.

### Requirement: Translation Outcome Observability
The system SHALL persist per-section translation outcome metadata and validation-level fallback diagnostics for every task run without changing external API request/response contracts.

#### Scenario: Section metadata persistence
- **WHEN** a section translation result is written to `sections_map.json`
- **THEN** the section entry MUST include `translation_status`, `translation_retry_count`, and `no_op_detected`
- **AND** `fallback_reason` MUST be present for fallback statuses
- **AND** existing readers that do not consume these fields MUST remain compatible.

#### Scenario: Validation completion diagnostics persistence
- **WHEN** the coordinator writes the `validation_completed` event into `task_log.json`
- **THEN** the event payload MUST include `fallback_parts`, `noop_sections`, and `c1_retry_enforced_once` when available
- **AND** existing task log consumers MUST remain backward compatible with the enriched payload.

### Requirement: Safe Reference Argument Underscore Handling
The validator SHALL treat underscore characters inside safe reference command arguments as non-math text keys and MUST NOT classify them as math delimiter mismatch errors.

#### Scenario: Safe command argument underscores are ignored for math mismatch
- **WHEN** translated text contains underscores inside first-level arguments of safe commands such as `\ref{...}`, `\eqref{...}`, `\label{...}`, `\pageref{...}`, `\autoref{...}`, and `\cite*{...}` variants
- **THEN** underscore tokens inside those argument spans MUST be excluded from bare-math-token mismatch checks.

#### Scenario: Real text-mode bare underscore still triggers structural path
- **WHEN** translated text contains a bare `_` outside placeholders, safe command argument spans, and math regions
- **THEN** the validator and deterministic repair path MUST still classify/repair it through the structural safety workflow.

### Requirement: C1 Retry Budget Enforcement
The translation flow SHALL enforce a global maximum of one LLM retry per part for C1 errors across the full validation-retry lifecycle.

#### Scenario: First C1 occurrence consumes retry budget
- **WHEN** a part first enters C1 handling
- **THEN** the system MUST allow one targeted LLM retry before deterministic repair and revalidation.

#### Scenario: Subsequent C1 occurrences bypass additional LLM retries
- **WHEN** the same part re-enters C1 handling in later rounds
- **THEN** the system MUST skip further LLM retries for that part
- **AND** continue with deterministic fix, revalidation, and fallback logic.

### Requirement: No-op Re-translation Guardrail
The section translation flow SHALL detect high-similarity no-op outputs and perform exactly one forced retranslation attempt before finalizing section status.

#### Scenario: No-op threshold triggers single forced retry
- **WHEN** section output meets no-op thresholds (`SequenceMatcher >= 0.97`, `CJK chars < 16`, `English words >= 80`)
- **THEN** the system MUST execute one strengthened retranslation attempt
- **AND** mark `no_op_detected` as true for the section.

#### Scenario: Persistent no-op is retained with explicit metadata
- **WHEN** the forced retry still results in a no-op-like output
- **THEN** the system MAY retain the resulting text under existing safety policy
- **AND** section metadata MUST preserve no-op and fallback status context for traceability.

### Requirement: Eqnarray Environment Row-Safe Translation
The system SHALL process `eqnarray` environments with strict row-level controls to prevent structural corruption from whole-block translation.

#### Scenario: Eqnarray rows are split and rebuilt deterministically
- **WHEN** an environment is `eqnarray` (or `eqnarray*`)
- **THEN** the system MUST preserve begin/end boundaries, split rows by explicit row delimiters, and rebuild using the original separator sequence
- **AND** `%` comments MUST be masked/restored through immutable placeholders during processing.

#### Scenario: Math rows are preserved and text rows are selectively translated
- **WHEN** the system classifies eqnarray rows into `math` and `text`
- **THEN** rows classified as `math` MUST be preserved without semantic translation
- **AND** rows classified as `text` MAY be translated via the env translation path.

#### Scenario: Eqnarray row mismatch triggers row-level fallback
- **WHEN** translated row output violates immutable `EQROW` placeholder sequence integrity
- **THEN** the affected row MUST fall back to source-row content
- **AND** the environment entry MUST increment `row_fallback_count`
- **AND** fallback MUST remain row-scoped instead of escalating immediately to section-level rollback.

### Requirement: List Environment Item-Anchor Integrity
The system SHALL enforce item command structure integrity for `enumerate` and `itemize` environments via immutable item anchors.

#### Scenario: Item anchors are enforced for list env translation
- **WHEN** a target environment is `enumerate`/`itemize` (including starred forms)
- **THEN** each `\item` command MUST be anchored as an immutable `<ITEM_n>` token during translation
- **AND** token count and order MUST match exactly before restoration.

#### Scenario: Persistent item-anchor mismatch triggers list env fallback
- **WHEN** `<ITEM_n>` integrity still fails after the allowed retry budget
- **THEN** the system MUST apply compile-first fallback for that environment
- **AND** set env fallback subtype to `list_env_fallback`.

### Requirement: Immutable Placeholder Validation for ITEM and EQROW
The validator SHALL explicitly validate immutable placeholder sequence integrity for `ITEM` and `EQROW` tokens.

#### Scenario: ITEM placeholder mismatch is classified as C1
- **WHEN** validator detects `item_anchor_sequence_mismatch` or list item order mismatch
- **THEN** the error MUST be classified as C1 for controlled retry handling.

#### Scenario: EQROW placeholder mismatch is classified as C2
- **WHEN** validator detects `eqrow_placeholder_sequence_mismatch`
- **THEN** the error MUST be classified as C2 for structural handling without extra LLM retry.

### Requirement: Environment Translation Metadata Persistence
The system SHALL persist env-level outcome metadata in `envs_map.json` for each environment translation record.

#### Scenario: Env metadata fields are always written
- **WHEN** an environment translation result is persisted
- **THEN** the entry MUST include `translation_status`, `fallback_subtype`, and `row_fallback_count`
- **AND** `fallback_subtype` MUST default to `none` when no env fallback occurred.

#### Scenario: Math-only eqnarray is explicitly marked
- **WHEN** an eqnarray environment has no text rows requiring translation
- **THEN** the system MUST mark env `translation_status` as `math_preserved`
- **AND** preserve environment structure and content.

### Requirement: Validation Summary Includes Env Fallback Subtype Counters
The coordinator SHALL persist env fallback subtype counters in the `validation_completed` task log payload.

#### Scenario: Env fallback subtype counters are emitted
- **WHEN** `validation_completed` is written
- **THEN** payload MUST include `fallback_count_env_math`, `fallback_count_env_list`, and `fallback_count_env_other` when available.

### Requirement: Deterministic Oversize Safe Input Gate
The system SHALL make oversize downgrade decisions with a versioned, replayable safe-input-limit function and persist all related gate inputs.

#### Scenario: Versioned safe input limit is replayable
- **WHEN** oversize downgrade gating is evaluated
- **THEN** the system MUST compute safe input budget through `safe_limit_v1(model_context_tokens, prompt_reserve_tokens)`
- **AND** replay metadata MUST include `safe_limit_id`, `model_context_tokens`, `prompt_reserve_tokens`, and `safe_input_limit`.

#### Scenario: Safe input limit is deterministic under fixed configuration
- **WHEN** the same configuration is evaluated repeatedly
- **THEN** `safe_input_limit` MUST remain identical across runs.

#### Scenario: Conservative estimator trade-off is explicit
- **WHEN** oversize downgrade policy documentation is evaluated
- **THEN** the estimator policy MUST explicitly state that `estimate_tokens_v1 = ceil(utf8_bytes/3)` is a conservative anti-truncation gate
- **AND** it MUST explicitly state this estimator is not tokenizer-equivalent precision.

### Requirement: Oversize Source Pass-Through Path Isolation
The system SHALL isolate oversize-downgraded chunks from all secondary mutation pipelines and forward them directly to final reconstruction merge.

#### Scenario: Oversize downgraded chunk bypasses translator and mutation chains
- **WHEN** a chunk is marked with `translated=false` and `downgrade_reason=oversize_no_safe_boundary`
- **THEN** the chunk MUST bypass translator invocation
- **AND** the chunk MUST bypass structural extraction, placeholder refill, terminology replacement, and macro rewrite chains
- **AND** the chunk MAY only enter final reconstruction merge as source pass-through content.

### Requirement: Unified Structural-Risk LLM Entry
All structural-risk translation requests MUST use one freeze/restore LLM entrypoint so payload guarding and restoration are applied consistently.

#### Scenario: Structural-risk call bypass attempt
1. Given a structural-risk callsite for section/env/caption translation or retranslation
2. When the call is executed
3. Then it MUST pass through the unified freeze entrypoint
4. And direct raw client invocation outside that entrypoint MUST NOT occur.

### Requirement: C1/C2 Routing Without Speculative Injection
C1/C2 orchestration MUST retain existing retry and deterministic repair semantics while prohibiting speculative structure-token injection and validate-stage source rollback.

#### Scenario: C2 structural error is recorded but translation is preserved
- **WHEN** the validator classifies a section or environment as `C2`
- **THEN** the system MUST record that unit as a post-compile fallback candidate
- **AND** MUST NOT overwrite `trans_content` with source text during validation
- **AND** the first compilation attempt MUST use the preserved target-language text.

#### Scenario: Compile succeeds despite recorded structural risk
- **WHEN** a section or environment is recorded as a structural fallback candidate
- **AND** the first compilation attempt succeeds
- **THEN** the system MUST retain the target-language translation
- **AND** MUST NOT execute deterministic target-language downgrade for that unit.

### Requirement: Precompile Structure Validation Is Externally Visible
The system SHALL expose compile-time structure validation as a distinct precompile phase so operators and downstream UIs can distinguish structural checking from compile queue wait time.

#### Scenario: Structure validation status precedes compile queue waiting
- **WHEN** the generator locates the compile-ready `main.tex`
- **THEN** it MUST emit a dedicated status such as `Checking project structure...`
- **AND** this status MUST occur before any compile queue waiting message can be shown.

#### Scenario: Structure validation duration is recorded separately
- **WHEN** `validate_project_structure` executes during the compile pipeline
- **THEN** the system MUST record its execution duration in runtime logs or audit metrics
- **AND** the recorded duration MUST measure the validation call itself rather than surrounding compile execution time.

### Requirement: Standalone Orchestration Runtime Independence
The translation orchestrator SHALL be runnable in a standalone CLI environment without FastAPI lifecycle hooks, task queues, or task-manager persistence.

#### Scenario: Running the orchestrator in standalone CLI mode
- **WHEN** the standalone CLI invokes `CoordinatorAgent.workflow_latextrans`
- **THEN** the orchestrator MUST run without importing FastAPI, Supabase, or `task_manager`
- **AND** progress reporting MUST flow through CLI logging or progress callbacks
- **AND** compile-runtime observability MUST be written to local task logs rather than backend runtime state stores.

### Requirement: Validation Retry Stagnation Short-Circuit
The orchestration layer SHALL terminate validation retry loops early when repeated retries no longer reduce the remaining structural error set.

#### Scenario: Retry loop makes no progress
- **WHEN** validation is rerun after a retry/repair step
- **AND** the remaining error set is unchanged from the previous validation round
- **THEN** the system MUST short-circuit further retry rounds for that run
- **AND** MUST record a `validation_retry_short_circuited_no_progress` event in `task_log.json`
- **AND** MUST continue with the existing fallback / compile path instead of looping again.

### Requirement: Task-Start Runtime Observability
The orchestration layer SHALL persist the effective runtime configuration used for a task start, including masked LLM settings required for parity debugging.

#### Scenario: Task-start log records effective LLM runtime config
- **WHEN** the coordinator writes the `task_started` event into `task_log.json`
- **THEN** the payload MUST include the effective runtime configuration used by the task
- **AND** MUST include masked `llm_config` fields such as `base_url`, `model`, timeout-related values, and masked API-key presence
- **AND** MUST NOT persist the raw API key.

