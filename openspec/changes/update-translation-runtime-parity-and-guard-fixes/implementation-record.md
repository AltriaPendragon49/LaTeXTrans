# Implementation Record

## Timing Evidence

### Single-task CLI baseline

`NiuTrans/LaTeXTrans/outputs/zh_2006.11239/task_log.json`

- Total: about `196.8s`
- Parse: about `3.1s`
- Translate: about `67.5s`
- Validation: about `0.4s`
- Compile and finalization tail: about `123.5s`
- Effective task config recorded `llm_max_concurrent_requests = 10`

`NiuTrans/LaTeXTrans/outputs/zh_2010.11929/task_log.json`

- Total: about `103.0s`
- Parse: about `0.5s`
- Translate: about `83.6s`
- Validation: about `13.6s`
- No meaningful compile tail because the old false-positive structure guard aborted precompile
- Effective task config recorded `llm_max_concurrent_requests = 10`

### Current backend path before this change

Key mismatches found in code:

- `backend/app/core/config.py` defaulted `llm_max_concurrent_requests` to `3`
- `backend/app/api/routes/translate.py` capped per-task parity at `3`
- `backend/app/core/config.py` still keeps `max_concurrent_compilations = 1`

Conclusion:

- The backend path had a confirmed single-task LLM concurrency regression versus CLI.
- Multi-task slowness is not only an LLM issue because compile work is still serialized by the compile semaphore.
- This change restores LLM parity to `10` and deliberately leaves compile serialization unchanged as a separate bottleneck.

## Code Changes In This Worktree

### Runtime parity

- Raised backend default `llm_max_concurrent_requests` from `3` to `10`
- Raised route-level `CLI_PARITY_TASK_LLM_MAX_CONCURRENT_REQUESTS` from `3` to `10`
- Updated `backend/.env.example` to match

### Structure guard stability

- Fixed project-text assembly to inline `\input` / `\include` content at the original callsite
- Fixed nested include resolution to be relative to the current file directory
- This removes the false-positive `Unexpected closing environment: 'tabularx'` class seen on `2010.11929`

### Hard-freeze retry control

- Deduplicated failed-part tracking so the same section/caption/env identifier is not appended repeatedly
- Propagated `payload_invariant_passthrough` handling to captions and environments
- Short-circuited invariant-failed environment paths so they preserve source content and metadata instead of re-entering expensive recovery loops

## Verification Run

- `pytest backend/tests/unit/test_llm_runtime.py -q`
- `pytest backend/tests/unit/test_structure_guard_input_order.py -q`
- `pytest backend/tests/unit/test_translator_payload_invariant_passthrough.py -q`
- `pytest backend/tests/unit/test_translator_payload_guard.py -q`
- `openspec validate update-translation-runtime-parity-and-guard-fixes --strict --no-interactive`

Focused result: all selected tests passed.

Known unrelated blocker:

- `backend/tests/unit/test_deterministic_repair.py` still has a pre-existing file encoding issue during pytest collection and was not used as a completion gate for this change.
