# latex-translation-core Delta

## ADDED Requirements

### Requirement: Compilation Error Feedback Loop
The system SHALL analyze LaTeX compilation failures caused by translation-induced command corruption, provide targeted retranslation instructions, and retry compilation automatically.

#### Scenario: LLM-driven compilation error diagnosis
- **WHEN** compilation fails with `status=failed_compilation`
- **THEN** the system MUST invoke an LLM with the compilation log error context and surrounding `.tex` source lines
- **AND** MUST parse a structured JSON diagnosis identifying the problematic translated command, the reason for failure, and a fix instruction.

#### Scenario: Targeted retranslation from compilation feedback
- **WHEN** the compilation error analyzer returns an actionable fix with `affected_part_type` and `affected_part_id`
- **THEN** the system MUST inject the fix instruction into the `TranslatorAgent` error report
- **AND** MUST re-run targeted retranslation for only the affected part (`trans_mode=1`).

#### Scenario: Compilation retry with limit
- **WHEN** retranslation produces an updated translation output
- **THEN** the system MUST reconstruct and recompile the document
- **AND** MUST limit compilation retries to `MAX_COMPILATION_RETRIES` (default: 2)
- **AND** if all retries are exhausted, MUST report `failed_compilation` with accumulated error context.

#### Scenario: Unactionable compilation error graceful degradation
- **WHEN** the LLM analyzer cannot identify an actionable fix (returns unparseable response or non-translation error)
- **THEN** the system MUST skip the retry loop and report `failed_compilation` immediately.

#### Scenario: Compilation fix logging for maintenance
- **WHEN** a compilation retry succeeds or fails
- **THEN** the system MUST append a structured JSON record to `data/compilation_fixes_log.json`
- **AND** the record MUST include `task_id`, `command`, `reason`, `fix_instruction`, `timestamp`, and `success` status.

#### Scenario: No retry overhead for successful compilations
- **WHEN** compilation succeeds on the first attempt
- **THEN** the system MUST NOT invoke the compilation error analyzer
- **AND** MUST NOT add any latency to the task.
