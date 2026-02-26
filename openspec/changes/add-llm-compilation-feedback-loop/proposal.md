# Change: Add LLM Compilation Error Feedback Loop

## Why
LaTeX compilation failures caused by model-dependent over-translation of structurally sensitive commands (e.g., `\ccsdesc`, `CCSXML`) cannot be fully prevented by a static regex registry alone. Papers from diverse publishers and custom templates introduce an unbounded set of sensitive commands. A closed-loop system is needed where compilation errors are analyzed, root causes are identified, and targeted retranslation is performed automatically—while logging discoveries for long-term regex maintenance.

## What Changes
- Add a **Compilation Error Analyzer** capability:
  - When compilation fails after reconstruction, invoke an LLM with the `main.log` error context and surrounding `.tex` source lines.
  - The LLM identifies the problematic translated command/region and outputs a structured JSON diagnosis: `{command, reason, fix_instruction, part_type, part_id}`.
- Add a **Compilation Retry Loop** in `CoordinatorAgent`:
  - After a `failed_compilation` result from `GeneratorAgent`, invoke the Compilation Error Analyzer.
  - If an actionable fix is returned, inject the fix instruction into the `TranslatorAgent` error report and re-run targeted retranslation (`trans_mode=1`).
  - Reconstruct and compile again (up to `MAX_COMPILATION_RETRIES=2`).
- Add a **Compilation Fix Logging** mechanism:
  - Every successful fix is appended to `data/compilation_fixes_log.json` with fields: `task_id`, `command`, `reason`, `fix_instruction`, `timestamp`.
  - This log serves as a data source for expanding the `PROTECTED_COMMANDS` registry (from `fix-latex-compilation-resilience` Task 12).
- Add an LLM prompt for compilation error analysis in `prompts.py`.

## Impact
- Affected specs:
  - `latex-translation-core` (new Compilation Feedback Loop requirement)
- Affected code:
  - `backend/app/services/agents/coordinator_agent.py` (retry loop)
  - `backend/app/services/agents/translator_agent.py` (accept compilation feedback instructions)
  - `backend/app/services/latex/prompts.py` (new compilation analysis prompt)
  - `backend/app/services/latex/utils.py` (optional: fix log writer)
- Behavioral outcome:
  - Compilation failures caused by over-translation trigger automated diagnosis and targeted fix.
  - Each fix generates maintenance data for the static protection registry.
  - The system self-heals up to `MAX_COMPILATION_RETRIES` times before reporting `failed_compilation`.
- Dependencies:
  - Builds upon `fix-latex-compilation-resilience` Task 12 (regex masking infrastructure) for the logging data sink.
  - Requires structured compilation result propagation from `fix-latex-compilation-resilience` Tasks 2-4 (already deployed).
