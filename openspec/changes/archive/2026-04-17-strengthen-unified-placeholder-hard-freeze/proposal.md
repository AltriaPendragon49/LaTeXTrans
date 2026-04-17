# Change: Strengthen unified placeholder hard-freeze

## Why
The current translation pipeline protects some structural artifacts through freeze-and-restore helpers, prompt instructions, and post-hoc validation, but ordinary `PLACEHOLDER_*` tokens still rely too heavily on model compliance and fuzzy recovery. This leaves a stability gap: the model may mutate a protected token, and the system then has to guess whether it can safely recover the result.

We want a stronger contract. All protected placeholders and synthetic structural sentinels should be treated as immutable protocol objects during every structural-risk LLM call. Mutated outputs must be rejected as invalid attempts, while the existing validator, retry, repair, and compile-aware fallback layers remain intact as downstream defense in depth.

## What Changes
- Introduce a unified hard-freeze transport protocol for every protected placeholder/sentinel that can appear in structural-risk LLM payloads.
- Replace human-readable placeholder strings with opaque per-request transport tokens before calling the LLM, then decode them only after exact protocol verification succeeds.
- Reject any LLM response that drops, duplicates, reorders, substitutes, or invents hard-freeze tokens instead of attempting speculative placeholder repair at the LLM-boundary layer.
- Route these invalid attempts through the existing retry/fallback pipeline without removing current validator, repair, reconstruction, or compile fallback behavior.
- Preserve current downstream safety nets such as validator checks and reconstruction-time placeholder recovery for compatibility and defense in depth.

## Impact
- Affected specs:
  - `hard-freeze`
  - `latex-translation-core`
  - `translation-orchestration`
- Affected code:
  - `backend/app/services/agents/translator_agent.py`
  - `backend/app/services/agents/validator_agent.py`
  - `backend/app/services/latex/utils.py`
  - payload-freeze / restore helpers and related tests
