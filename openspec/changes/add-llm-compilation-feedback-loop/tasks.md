# Tasks: add-llm-compilation-feedback-loop

## 1. Compilation Error Analysis LLM Prompt
- [ ] 1.1 Design the system prompt for compilation error analysis in `backend/app/services/latex/prompts.py`.
  - Input: LaTeX log error lines, surrounding `.tex` source context (±10 lines around error).
  - Output: Structured JSON `{command, reason, fix_instruction, affected_part_type, affected_part_id}`.
- [ ] 1.2 Add unit tests for prompt formatting and expected JSON output schema validation.

## 2. Compilation Error Analyzer Agent
- [ ] 2.1 Implement `CompilationAnalyzerAgent` (or method within `ValidatorAgent`) that:
  - Receives `error_summary`, `log_path`, and `transed_latex_dir` from failed `GeneratorAgent` result.
  - Reads the `.log` file and extracts error context lines.
  - Reads the reconstructed `.tex` file around the error line number.
  - Calls the LLM with the analysis prompt.
  - Parses and validates the structured JSON response.
- [ ] 2.2 Add fallback behavior: if LLM returns unparseable response, return `None` (no actionable fix).
- [ ] 2.3 Add unit tests with mocked LLM responses for known error patterns (`\ccsdesc`, `CCSXML`).

## 3. Coordinator Compilation Retry Loop
- [ ] 3.1 In `CoordinatorAgent.workflow_latextrans_async()`, wrap the generation step in a retry loop (`MAX_COMPILATION_RETRIES=2`).
- [ ] 3.2 On `failed_compilation`, invoke `CompilationAnalyzerAgent`.
- [ ] 3.3 If analyzer returns an actionable fix, inject it into the `TranslatorAgent` error report format and re-run targeted retranslation.
- [ ] 3.4 Re-run `GeneratorAgent.execute()` with updated translation maps.
- [ ] 3.5 Log each retry attempt to `task_log.json` with `compilation_retry` event.
- [ ] 3.6 Add progress updates for compilation retry phase (e.g., "Analyzing compilation error, retry 1/2").

## 4. Compilation Fix Logging
- [ ] 4.1 Implement `log_compilation_fix(task_id, fix_data)` in `utils.py` that appends to `data/compilation_fixes_log.json`.
- [ ] 4.2 Include fields: `task_id`, `command`, `reason`, `fix_instruction`, `timestamp`, `success`, and `translation_diff` (showing the before/after text of the repaired part).
- [ ] 4.3 Add unit tests for log file creation and append behavior.

## 5. Integration Testing and Validation
- [ ] 5.1 End-to-end test with `5194e3ef-ff77-4080-8461-fb2abcc71338` (zh_2404.10981):
  - First compilation fails due to `\ccsdesc` translation.
  - Analyzer identifies `\ccsdesc` as the problematic command.
  - Retranslation produces a corrected section without translated `\ccsdesc`.
  - Second compilation succeeds.
- [ ] 5.2 Verify that `compilation_fixes_log.json` contains the correct fix record.
- [ ] 5.3 Verify no performance regression for papers that compile successfully on first attempt (no unnecessary retry).
