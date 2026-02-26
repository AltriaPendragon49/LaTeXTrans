# Design: Add LLM Compilation Error Feedback Loop

## Context
The translation pipeline currently has no mechanism to recover from compilation failures caused by LLM over-translation. When a model translates structurally sensitive LaTeX commands (e.g., `\ccsdesc{Computing methodologies~NLG}` → `\ccsdesc{计算方法学~自然语言生成}`), the resulting `.tex` file fails to compile due to macro-level incompatibility (e.g., `\csname...\endcsname` failures with CJK characters).

The companion change `fix-latex-compilation-resilience` (Task 12) introduces a static regex-based masking registry. This change adds a **dynamic, self-learning feedback loop** that discovers new problematic commands at runtime and feeds them back into the translation pipeline.

## Goals
- Automatically diagnose compilation failures caused by translation-induced command corruption.
- Provide targeted retranslation instructions to `TranslatorAgent` without full re-translation.
- Log all discovered problematic commands as structured data for static registry maintenance.
- Limit retry overhead (max 2 compilation retries per task).

## Non-Goals
- Fixing compilation errors unrelated to translation (e.g., missing packages, broken source files).
- Replacing the static `PROTECTED_COMMANDS` registry—the feedback loop supplements it.
- Supporting non-LLM error analysis (e.g., rule-based log parsing)—this is LLM-driven by design.

## Decisions

### 1. LLM as Error Analyzer (not rule-based)
- Use an LLM to interpret compilation log errors and `.tex` context, since the space of possible sensitive commands is unbounded across publisher templates.
- The LLM output is a structured JSON diagnosis, not free-text, to enable programmatic integration with the retry pipeline.

Alternatives considered:
- **Rule-based log parser**: Simple but requires maintaining a growing rule set per template family. Rejected as insufficient for long-tail cases.
- **AST-level diff between source/translated**: More precise but extremely complex for multi-file LaTeX projects. Deferred as future enhancement.

### 2. Injection via TranslatorAgent error report format
- Reuse the existing `errors_report` structure (which already supports `trans_mode=1` retranslation) to inject compilation feedback.
- Add a new field `compilation_feedback` containing the LLM's `fix_instruction` text, which is appended to the retranslation prompt.

Rationale:
- Minimizes code change footprint by reusing the existing validator → translator retry path.
- No new inter-agent protocol is needed.

### 3. MAX_COMPILATION_RETRIES = 2
- Limit compilation retries to 2 to bound latency cost.
- If both retries fail, the task enters `failed_compilation` with accumulated error context.

Rationale:
- Most translation-induced compilation failures have a single root cause that the analyzer can identify on the first try.
- A second retry covers cases where the analyzer's first instruction was partially correct.
- Infinite retries would risk API cost explosion.

### 4. Centralized Fix Log (`compilation_fixes_log.json`)
- All successful and failed fix attempts are logged to a single append-only JSON file.
- This file is designed to be periodically reviewed by maintainers to expand the `PROTECTED_COMMANDS` registry.

Rationale:
- Creates a closed-loop data flywheel: runtime discoveries → human review → static rules → fewer runtime failures.
- JSON format enables easy programmatic analysis.

## Risks and Trade-offs
- **LLM analysis quality**: The analyzer LLM may misidentify the root cause or suggest an incorrect fix. Mitigation: strict JSON schema validation and two-retry limit.
- **Latency**: Each compilation retry adds ~30-60s (compile + LLM analysis). Mitigation: max 2 retries, papers that compile successfully on first attempt have zero overhead.
- **API cost**: Each retry invokes one additional LLM call for analysis plus one for retranslation. Mitigation: bounded by max retries.
- **Fix log growth**: Unbounded append-only log. Mitigation: periodic manual cleanup or rotation (future enhancement).

## Open Questions (Resolved)
1. Should the compilation analyzer use the same LLM model as the translator, or a separate (potentially cheaper) model? → **Decision: Use the same LLM model for consistency.**
2. Should the fix log also record the diff between pre-fix and post-fix translation output for richer context? → **Decision: Yes, the log must include the diff between the failing translation and the successful repaired translation to provide maximum context for rules extraction.**
