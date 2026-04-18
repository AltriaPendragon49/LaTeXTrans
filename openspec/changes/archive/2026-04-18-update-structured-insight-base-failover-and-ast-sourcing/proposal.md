# Change: Update Structured Insight Base Failover And AST Sourcing

## Why
- Structured insight generation is currently more fragile than the main translation path because it still depends too heavily on translated preview/runtime excerpts and runs the five modules serially.
- The observed `503` failures are concentrated in structured insight generation, especially when multiple keys share the same relay `base_url`. We need a faster, more stable path that improves sourcing quality without weakening publication gating or global token-pool health semantics.

## What Changes
- Add a hybrid structured-insight source builder that prefers runtime section artifacts carrying both raw TeX/AST-derived content and translated excerpts, with preview HTML kept only as a bounded fallback.
- Change five-module structured insight generation to a parallel first pass with targeted repair/fallback for only the modules that remain invalid, unreadable, or duplicated.
- Extend the shared system-managed token pool so structured insight tasks can prefer another `base_url` after cumulative task-local `503` pressure, while keeping global health strictly member-level.
- Increase member-level `503` handling from the current short one-second cooldown to a longer bounded cooldown and keep all-members-exhausted behavior on the current member.
- Keep structured insight output Chinese-only and keep structured insight generation as a synchronous admin publication gate.

## Impact
- Affected specs: `community-structured-insights`, `queue-token-isolation`
- Affected code: `backend/app/services/paper_service.py`, `backend/app/services/agents/llm_token_pool.py`, `backend/tests/unit/test_structured_insight_generation.py`, `backend/tests/unit/test_system_llm_token_pool.py`
