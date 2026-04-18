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
- Added a translator-internal Maxtry guard so parts already marked `payload_invariant_passthrough` are not re-enqueued into `_val_fail_parts()`
- This specifically addresses real-paper retry amplification where hard-freeze violations were already safely downgraded to source passthrough, but the translator still spent extra LLM rounds retrying the same protected parts
- Added paragraph-level rescue for sections and captions after hard-freeze invariant failures when the first-pass result merely preserves the English source
- Removed the premature early-return in generic text env translation so invariant-hit envs now try existing plain-text/body rescue before settling on final passthrough
- Preserved bounded fallback behavior: if rescue still cannot produce a safe translated result, the part remains in deterministic passthrough status instead of entering unbounded loops

### Post-record follow-up fixes merged after the initial record

Additional follow-up commits landed on top of this change after the first implementation record was written:

- `ec683cc` `Improve invariant rescue granularity`
- `5764248` `Fix stale invariant retry bookkeeping`
- `6c2d571` `Improve invariant fragment rescue masking`
- `b959c9d` `Retry source-preserved rescue fragments`
- `3bf8307` `Add masked paragraph invariant rescue`
- `c2e54a3` `Refine invariant rescue granularity`
- `7a5444a` `Short-circuit rescue after API fallback`

These commits all stayed inside the same runtime/parity problem family and should be treated as follow-up implementation within this change history rather than unrelated work.

### What the later follow-up commits changed

#### Rescue success bookkeeping

- Cleared stale fail identifiers after successful rescue so translated sections/captions/envs stop re-entering `_val_fail_parts()`
- Normalized nested fail identifiers back to their owning top-level section/caption/env keys before deduplication and cleanup
- Added focused regression coverage for stale fail-queue cleanup and duplicate fail registration

Why this mattered:

- Real-paper server logs showed parts like `4_1` and `3_4` already translated in `sections_map.json` but still reappearing in later retry rounds
- That created a real retry amplification bug independent of hard-freeze correctness

#### Paragraph and fragment rescue refinement

- Added masked paragraph rescue before fragment splitting so raw `\cref{...}` and placeholder tokens are not re-exposed unnecessarily
- Added fragment-level force-retry when the fragment result is still source-preserved
- Added recursive rescue-window splitting for long failed fragments instead of treating a long fragment as all-or-nothing
- Added item-level rescue for list environments so `itemize` / `enumerate` blocks can recover individual items without degrading the whole list
- Added small punctuation/whitespace normalization after fragment/window recomposition

Why this mattered:

- The original paragraph rescue helped quality, but some long English fragments still fell back to source too early
- Later commits intentionally traded a small amount of extra rescue complexity for better Chinese coverage on the difficult `2006.11239` style papers

#### API-failure containment

- Added explicit short-circuit behavior so non-invariant API fallback reasons such as `api_request_failed_after_3_attempts` do not recurse into masked / fragment / window rescue branches
- Kept nested rescue enabled only for invariant-style failures, where finer-grained rescue is still useful
- Prevented list-env item rescue and generic-text env plain-text recovery from re-triggering after ordinary upstream API failure

Why this mattered:

- Once the upstream provider started returning repeated `503` responses, the previous rescue tree could still amplify wall-clock time by exploring finer rescue levels after a provider outage
- `7a5444a` specifically limits that amplification while preserving the hard-freeze guarantee itself

## Live Validation Findings After The Initial Record

### Baseline CLI comparison remained healthy

`NiuTrans/LaTeXTrans/outputs/zh_2006.11239/task_log.json` continued to show a healthy run using:

- `llm_max_concurrent_requests = 10`
- `model = deepseek-chat`
- `base_url = https://one-api.bltcy.top/v1/chat/completions`

That baseline completed in about `203.7s`, with:

- parse about `3.1s`
- translate about `67.5s`
- generate/compile about `124.6s`

### Fresh backend validation runs exposed a new dominant blocker

Real server validation after the later placeholder-rescue commits showed that the dominant live blocker was no longer purely internal retry bookkeeping.

Observed runs included:

- `2006.11239-0418-1024-c9c73148-1f0f-448b-8f57-5e1f644976b5`
- `2006.11239-0418-1125-6c839bfc-60b4-42c1-a308-3f1eeabd8aff`

Key findings:

- Server `.env` was already reduced to `LLM_MAX_CONCURRENT_REQUESTS=3`
- Fresh runs still received repeated `503 Service Unavailable` from `https://one-api.bltcy.top/v1/chat/completions`
- The failures hit ordinary section/caption/env requests, not only hard-freeze rescue branches
- A fresh run remained stuck in `Validating translation results` after more than ten minutes because many fail parts were being retried against an unhealthy upstream route

Conclusion from these later validations:

- The earlier retry-bookkeeping bug was real and was fixed
- However, the remaining inability to hit the `<=10 min` target on live server validation was dominated by upstream provider instability during those windows, not by the placeholder-freeze protocol alone
- The post-`7a5444a` short-circuit still matters because it prevents ordinary upstream outages from exploding into deeper rescue trees

## Verification Run

- `pytest backend/tests/unit/test_llm_runtime.py -q`
- `pytest backend/tests/unit/test_structure_guard_input_order.py -q`
- `pytest backend/tests/unit/test_translator_payload_invariant_passthrough.py -q`
- `pytest backend/tests/unit/test_translator_payload_guard.py -q`
- `openspec validate update-translation-runtime-parity-and-guard-fixes --strict --no-interactive`
- `python -m pytest backend/tests/unit/test_translator_payload_invariant_passthrough.py -q`
- `python -m pytest backend/tests/unit/test_translator_payload_guard.py -q`
- `python -m pytest backend/tests/unit/test_hard_freeze_placeholder_sequence.py -q`

Focused result: all selected tests passed.

Additional rollout evidence captured after the initial record:

- Production server was updated to commit `7a5444a`
- Backend service restarted successfully
- Fresh real-paper validation was attempted for `2006.11239`
- That validation did not meet the final success bar because the upstream provider returned repeated `503` responses during the run

Known unrelated blocker:

- `backend/tests/unit/test_deterministic_repair.py` still has a pre-existing file encoding issue during pytest collection and was not used as a completion gate for this change.
