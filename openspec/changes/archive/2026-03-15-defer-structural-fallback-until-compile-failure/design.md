## Context
The pipeline currently treats structural fallback as an immediate source rollback. `TranslatorAgent._apply_compile_first_fallback()` overwrites target-language content and the orchestrator can escalate to `ultimate_downgrade` before any compile attempt. That makes structural telemetry and final content diverge from the intended target-language persistence behavior.

## Goals
- Preserve target-language text through validation and repair whenever possible.
- Limit deterministic downgrade to compile-failure handling.
- Keep the existing validator, C1 retry, and deterministic repair model intact.
- Bound fallback-induced recompilation to exactly one extra compile attempt.

## Non-Goals
- Do not redesign `fallback_source_api_failure`.
- Do not introduce a new LLM-based fallback engine.
- Do not change oversize downgrade or math-preserved flows.

## Decisions
- Decision: keep `_apply_compile_first_fallback()` as the entrypoint, but change it from "apply source rollback" to "mark pending post-compile fallback".
  - Rationale: minimizes churn in validator and retry routing.
- Decision: preserve `FallbackReport` emission, but treat these reports as compile-stage downgrade candidates instead of proof that source rollback already happened.
  - Rationale: keeps repair telemetry and observability intact.
- Decision: add one orchestrator node for post-compile target-language fallback instead of routing from validate directly to `ultimate_downgrade`.
  - Rationale: the orchestration change is local and keeps compile retry policy explicit.
- Decision: reuse `ultimate_downgrade_segment()` as the deterministic renderer, but only feed it target-language `trans_content`.
  - Rationale: preserves existing deterministic safety guarantees without creating a second renderer.
- Decision: add a new config flag `enable_post_compile_target_language_fallback` defaulting to `True`, while keeping `enable_compile_first_structural_fallback` as a deprecated compatibility field.
  - Rationale: old task configs still deserialize cleanly, but behavior becomes explicit.

## Risks / Trade-offs
- Risk: preserving structurally risky target-language text may increase first-pass compile failures.
  - Mitigation: allow exactly one deterministic post-compile downgrade and one compile retry.
- Risk: existing tests rely on `fallback_source_compile_first`.
  - Mitigation: replace them with status assertions for the pending and final target-language fallback states.
- Risk: stale empty change directory confuses `openspec list`.
  - Mitigation: remove the empty placeholder directory during this implementation.

## Migration Plan
1. Add the new OpenSpec change and deltas.
2. Update config capture to include the new flag and keep the deprecated flag readable.
3. Change translator fallback metadata to pending states only.
4. Add post-compile fallback routing and compile retry limits in the orchestrator.
5. Update and rename tests to assert actual post-compile behavior.
6. Validate the OpenSpec change and targeted unit tests.

## Open Questions
- None. This change intentionally excludes API-failure target-language compensation.
