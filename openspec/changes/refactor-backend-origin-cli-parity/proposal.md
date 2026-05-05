# Change: Make Backend Translation Tasks Origin CLI Parity

## Why
The backend translation result must be produced by the same translation kernel behavior as the legacy CLI under `texts/origin`. The current backend can still route through modern LangGraph behavior, repair branches, hard-freeze safeguards, structure guards, compilation diagnostics, and fallback systems, so its output cannot be treated as exactly identical to the old CLI.

## What Changes
- For the current delivery, roll the backend translation kernel back as a whole to the old CLI behavior under `texts/origin`, with only framework orchestration, task-state, storage, and progress-reporting wrappers allowed to differ.
- Make an `origin_cli_parity` translation kernel the default and required backend core for every production translation trigger.
- Use LangGraph only as a wrapper around the legacy linear workflow: parse, translate, validate with up to three retry rounds, generate, finalize.
- Preserve the legacy CLI parser, translator prompts, LLM payload shape, call ordering, retry behavior, validator behavior, reconstruction, and compilation semantics as the canonical behavior.
- Route all backend trigger paths through one parity config normalizer, including normal upload, arXiv translation, batch translation, admin/community curation, community paper translation, content-pool prewarm, and community-agent triggered translation.
- Production runtime executes only the parity kernel for a task; it must not run old and new kernels in parallel, emit dual results, or select between competing kernel outputs.
- Retain newer backend systems such as hard-freeze, structure guard, repair, ultimate downgrade, post-compile target-language fallback, residual-English checks, and diagnostics, but do not invoke them for parity translation tasks.
- Add deterministic parity tests that compare backend LangGraph-wrapped execution against `texts/origin` with mocked LLM responses and byte-for-byte kernel artifact diffs.

## Impact
- Affected specs: `latex-translation-core`, `translation-orchestration`, `web-api`, `batch-translation`, `community-paper-translation-bridge`, `community-content-pool-foundation`, `community-admin-curation`, `community-agent-assistant`, `standalone-cli-interface`
- Affected code:
  - `backend/app/api/routes/translate.py`
  - `backend/app/models/config_models.py`
  - `backend/app/services/agents/coordinator_agent.py`
  - `backend/app/services/agents/langgraph_orchestrator.py`
  - `backend/app/services/agents/parser_agent.py`
  - `backend/app/services/agents/translator_agent.py`
  - `backend/app/services/agents/validator_agent.py`
  - `backend/app/services/agents/generator_agent.py`
  - `backend/app/services/latex/*`
  - `backend/app/services/paper_service.py`
  - `backend/app/services/community_agent/skills/start_translation_kernel.py`
  - parity comparison scripts and tests under `scripts/` and backend tests
