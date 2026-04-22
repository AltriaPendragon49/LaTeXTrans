## Context
The current hard-freeze protocol treats every protected-token occurrence as a transport handshake that must be preserved in exact sequence. This is robust for high-risk structural anchors, but it is too strict for section-level prose where harmless local reorderings often still produce a compilable and readable translated result. Once those attempts are rejected, the current pipeline frequently falls into source passthrough or repeated placeholder-style Chinese fallback text, which violates the intended target-language-first policy.

## Goals / Non-Goals
- Goals:
  - Preserve real translated text whenever a structurally simplified output can still compile safely.
  - Reduce false-positive hard-freeze protocol violations for section-like prose payloads.
  - Keep strict protection for anchors whose misplacement would silently corrupt object ownership.
- Non-Goals:
  - Rework the entire placeholder system back to the prototype implementation.
  - Remove hard-freeze from all translation paths.
  - Guarantee acceptance of every reordered placeholder sequence.

## Decisions
- Decision: Introduce risk-tiered hard-freeze verification.
  - Exact token-stream equality remains mandatory for high-risk anchors:
    - begin/end structural pairs
    - math anchors
    - `ITEM` anchors
    - caption ownership anchors
    - reference/label-style tokens whose loss or cross-object drift would silently corrupt semantics
  - Section-like prose payloads may pass with a relaxed protected-token check so long as required high-risk anchors remain stable and no protected token is lost, duplicated, substituted, or moved across object boundaries.
- Decision: Structured downgrade is target-language-only.
  - Deterministic downgrade renderers may simplify structure, escape TeX, or unwrap formatting, but they may only operate on materially translated target-language text.
  - If only source-English or fixed fallback boilerplate remains, the unit must be marked as failed/last-resort fallback rather than a successful downgrade.
- Decision: Brutal fixed-sentence fallback is not a valid downgrade.
  - The repeated fallback sentence may remain as a bounded terminal rescue artifact if needed for compatibility, but it must not qualify as structured downgrade success and must not suppress clearer failure metadata.

## Risks / Trade-offs
- Relaxing hard-freeze for prose can admit more structurally noisy candidates, so object-local ownership checks must remain strict for high-risk anchors.
- Tightening downgrade success criteria will surface more explicit failure states where the current system previously pretended to succeed with placeholder-like Chinese text.
- Some existing audit expectations may need status/fallback-reason updates because target-language-only downgrade is narrower than the current implementation.

## Migration Plan
1. Update spec requirements to define risk-tiered hard-freeze semantics and target-language-only downgrade success.
2. Add regression tests that fail under the current strict token-stream equality and current downgrade acceptance.
3. Implement relaxed verification for section-like payloads while preserving strict verification for high-risk anchors.
4. Reject downgrade success when the candidate lacks materially translated target-language content.
5. Verify focused backend tests and update OpenSpec task tracking before deploy.

## Open Questions
- None for this change. The accepted direction is to prioritize real translated text over exact section-level token-stream equality, while keeping strict anchor protection for the listed high-risk structures.
