# Change: True Structured Downgrade With Risk-Tiered Hard-Freeze

## Current Status
Superseded and not current. This change described a modern-kernel fallback experiment that depended on hard-freeze and ultimate-downgrade code paths. The May 9, 2026 production cleanup removed those unused enhancement paths from the translation kernel. Current production behavior is defined by `origin_cli_parity` plus the bounded parity health branch.

## Why
Current translation fallback behavior rejects too many section-level candidates at the hard-freeze boundary and then converges toward source-English passthrough or fixed placeholder-style Chinese text. That behavior improves transport safety, but it misses the product goal: if a structurally simplified output can still compile and preserve real translated prose, the system should keep that translated prose instead of discarding it.

## What Changes
- Relax hard-freeze acceptance for section-like prose payloads from exact token-stream equality to risk-tiered structural invariants.
- Keep strict exact preservation for high-risk structural anchors such as begin/end pairs, math anchors, list item anchors, caption ownership, and reference/label object-local tokens.
- Redefine structured downgrade so it succeeds only when the input contains materially translated target-language text.
- Forbid fixed placeholder-style Chinese fallback text from being treated as valid structured downgrade output.
- Forbid source-English passthrough from being recorded as a successful structured downgrade outcome.

## Impact
- Affected specs: `latex-translation-core`, `hard-freeze`, `translation-orchestration`
- Historical affected code: `backend/app/services/latex/utils.py`, `backend/app/services/agents/translator_agent.py`, removed ultimate-downgrade module, `backend/app/services/agents/langgraph_orchestrator.py`, targeted backend tests
