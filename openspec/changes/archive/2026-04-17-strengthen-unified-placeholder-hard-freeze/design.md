## Context
The repository already has a `hard-freeze` contract, but the current implementation is mixed:
- some structural artifacts are frozen with internal placeholders such as `ENV_*`, `INLMATH_*`, and `PROTECTED_CMD_*`
- some user-facing placeholders such as `PLACEHOLDER_ENV_*`, `PLACEHOLDER_CAP_*`, `PLACEHOLDER_*_begin`, `PLACEHOLDER_*_end`, and `PLACEHOLDER_NEWCOMMAND_*` still rely on prompt instructions, term-dict hints, or fuzzy post-processing
- the validator catches many failures after the fact, but boundary integrity is not yet expressed as a strict transport protocol

That means the model can still emit an output that "looks close enough" to a placeholder-bearing response while actually violating the system's structural contract. The requested change is to make placeholder protection strict without deleting the current downstream safety layers.

## Goals / Non-Goals
- Goals:
  - Treat every protected placeholder/sentinel as an immutable transport object for every structural-risk LLM call.
  - Make protocol acceptance binary: either the response preserves the exact hard-freeze token stream, or the attempt is invalid.
  - Keep existing validation, retry, repair, reconstruction, and compile fallback layers.
  - Improve observability so operators can distinguish protocol violations from later-stage structural errors.
- Non-Goals:
  - Guarantee that the LLM itself never emits a bad response.
  - Remove legacy fuzzy recovery in reconstruction while old artifacts or edge paths still exist.
  - Replace downstream validator and compile safety checks with hard-freeze alone.

## Decisions
- Decision: Use one unified hard-freeze registry for all protected artifacts.
  - Covered artifacts:
    - parser placeholders: `PLACEHOLDER_ENV_*`, `PLACEHOLDER_CAP_*`, `PLACEHOLDER_NEWCOMMAND_*`, `PLACEHOLDER_*_begin`, `PLACEHOLDER_*_end`
    - payload-isolation sentinels: `ENV_*`, `ENV_BEGIN_*`, `ENV_END_*`, `INLMATH_*`, `ITEM_*`, `EQROW_*`, `EQCOMMENT_*`, `PROTECTED_CMD_*`
    - any future structural sentinel added to the registry
  - Why:
    - The current split between "hard frozen" and "softly protected" tokens is the main stability gap.

- Decision: Replace protected artifacts with opaque transport tokens before the LLM sees them.
  - Token properties:
    - unique per occurrence, not just per logical placeholder family
    - scoped to one request
    - carries kind + ordinal + request nonce + verifier digest
    - intentionally meaningless to the model
  - Example shape:
    - source payload fragment: `We prove <PLACEHOLDER_ENV_12> using $x+y$.`
    - transport payload fragment: `We prove @@HF:ENVPH:0007:7D83F1C2@@ using @@HF:INLMATH:0008:4A9B2201@@.`
  - Why:
    - If each occurrence has its own exact token, the system can detect missing, duplicated, reordered, substituted, or hallucinated tokens without ambiguity.

- Decision: Protocol acceptance happens before any decode or persistence.
  - Verification steps:
    - extract the hard-freeze token stream from the prepared request payload
    - extract the hard-freeze token stream from the raw model output
    - require exact sequence equality, not only set equality
    - reject if any expected token is missing
    - reject if any token is duplicated
    - reject if any unknown token appears
    - reject if token order changes
  - Why:
    - A strong boundary guarantee comes from refusing to decode any response that fails the transport contract.

- Decision: Decoding is table-driven, never fuzzy, at the hard-freeze boundary.
  - Decode rule:
    - only exact tokens present in the request-local registry may decode back to original placeholders/sentinels
    - mutated transport tokens are not "repaired" at this boundary
  - Why:
    - Fuzzy recovery at the boundary weakens the guarantee and reintroduces guesswork.

- Decision: Existing downstream safety layers remain in place.
  - Retained layers:
    - validator placeholder / structural checks
    - controlled retry
    - repair loop
    - reconstruction-time recovery helpers
    - compile-aware fallback and structure guard
  - Why:
    - Hard-freeze prevents a class of boundary corruption, but later-stage structural issues can still happen through other paths.

- Decision: "Absolute protection" is defined as "no corrupted protected token can be accepted or persisted," not "the model can never output corruption."
  - Guarantee:
    - the model may still return invalid text
    - but the system will not trust, decode, or persist a protected-token-bearing response unless the transport handshake matches exactly
  - Why:
    - This is the only honest way to give a strong guarantee in an LLM system.

## Request / Response Model
### What the LLM receives
For every structural-risk request, the user payload sent to the LLM contains natural-language text plus opaque hard-freeze transport tokens only. The original placeholders/sentinels are not exposed.

Example:

```text
[Current LaTeX Paragraph]:
The result in @@HF:ENVPH:0007:7D83F1C2@@ follows from @@HF:INLMATH:0008:4A9B2201@@ and @@HF:CMD:0009:91DE02AB@@.
```

### What the LLM is expected to return
The model must return translated natural language while leaving every `@@HF:...@@` token unchanged and in the same order.

Accepted example:

```text
结果 @@HF:ENVPH:0007:7D83F1C2@@ 来自 @@HF:INLMATH:0008:4A9B2201@@ 和 @@HF:CMD:0009:91DE02AB@@。
```

Rejected examples:

```text
结果 @@HF:ENVPH:0007:7D83F1C2@@ 来自 @@HF:CMD:0009:91DE02AB@@ 和 @@HF:INLMATH:0008:4A9B2201@@。
```

```text
结果 @@HF:ENVPH:0007:7D83F1C2@@ 来自 HF:INLMATH:0008:4A9B2201 和 @@HF:CMD:0009:91DE02AB@@。
```

```text
结果 @@HF:ENVPH:0007:7D83F1C2@@ 来自 @@HF:INLMATH:0008:4A9B2201@@ 和 @@HF:INLMATH:0008:4A9B2201@@。
```

### Why this is strongly safe
The guarantee does not depend on the model obeying the prompt. It depends on the system refusing to accept any response whose transport-token sequence is not exactly the same as the one it sent. A broken token can still be generated by the model, but it cannot cross the boundary into decoded or persisted translation state.

## Risks / Trade-offs
- More LLM responses will be rejected early.
  - Mitigation:
    - route invalid attempts through existing retry and fallback semantics
    - improve observability so these failures are explainable
- Hard-freeze protocol bugs could cause false rejections.
  - Mitigation:
    - add protocol-focused tests for every placeholder family and retry path
    - keep downstream validators during rollout
- Request-local opaque tokens reduce debuggability when reading raw payloads.
  - Mitigation:
    - persist a redacted per-request freeze manifest for audit/replay

## Migration Plan
1. Define a unified registry of protected placeholder families and transport-token encoding rules.
2. Add a request-local freeze manifest that maps original protected artifacts to opaque tokens.
3. Route all structural-risk LLM entrypoints through the same freeze -> call -> verify -> decode boundary.
4. Emit typed protocol-violation reasons when the returned token stream is not an exact match.
5. Preserve existing validator/retry/repair/compile fallback behavior after protocol rejection.
6. Add tests that cover first-translation, retranslation, env translation, list/eqnarray translation, and failure routing.

## Open Questions
- Whether to reuse the existing protection-log file or introduce a dedicated hard-freeze audit manifest.
  - Initial recommendation:
    - keep the existing log for backwards compatibility
    - add a dedicated request-local freeze manifest for protocol debugging
