# Placeholder Protection Slowdown Investigation

Date: 2026-04-18

## Question

After deploying the latest placeholder-protection changes, a real admin curation run for `2006.11239` felt much slower. The goal of this note is to record:

- where the live task was actually spending time,
- what code paths were changed for placeholder protection,
- what those changes were intended to do,
- what evidence currently suggests is helping,
- what evidence currently suggests is hurting,
- and what should be analyzed next.

## Live Task Snapshot

Investigated live task:

- `2006.11239-0418-0426-c4d6b414-18e0-46a6-8b9d-c26ffe6167d9`

Server-side timing snapshot collected around `2026-04-18 04:40 CST`:

- request accepted at `04:26:59`
- source download and COS upload completed around `04:32:16`
- parser finished at `04:32:25`
- `audit.jsonl` still shows only `node_enter:translate`
- by `04:40:13`, the task had still not emitted `node_exit:translate`

That means the task was not slow because of download, compile queue, or finalization. It was still inside `translate`.

### Current Partial Output State

At the time of inspection, the task had already written partial maps under:

- `backend/data/outputs/2006.11239-0418-0426-c4d6b414-18e0-46a6-8b9d-c26ffe6167d9/zh_2006.11239`

Partial status counts:

- `sections_map.json`
  - `immutable_passthrough`: `2`
  - `translated`: `17`
  - `payload_invariant_passthrough`: `3`
- `envs_map.json`
  - `translated`: `41`
  - `payload_invariant_passthrough`: `2`
- `captions_map.json`
  - `translated`: `29`

Current passthrough survivors:

- sections: `2`, `4_3`, `10`
- envs: `<PLACEHOLDER_ENV_26>`, `<PLACEHOLDER_ENV_31>`

Important observation:

- `4_1` and `3_4` were already translated into Chinese in `sections_map.json`
- but logs still showed them entering later fail-part retry rounds

This is a strong sign that some successful rescues are still leaving stale failure identifiers behind.

## What Changed In Placeholder Protection

There are three relevant layers in the recent rollout.

### 1. Unified hard-freeze boundary

Primary commit:

- `9e430c3 feat: harden unified placeholder freeze protocol`

Main code paths:

- `backend/app/services/latex/utils.py:3567` `freeze_protected_tokens`
- `backend/app/services/latex/utils.py:3638` `verify_hard_freeze_token_stream`
- `backend/app/services/latex/utils.py:3647` `restore_hard_freeze_tokens`
- `backend/app/services/agents/pipeline_invariants.py:38` `HardFreezeProtocolViolation`
- `backend/app/services/agents/translator_agent.py:843` `_prepare_llm_payload_text`
- `backend/app/services/agents/translator_agent.py:864` `_restore_llm_output_text`
- `backend/app/services/agents/translator_agent.py:950` `_call_llm_with_freeze`

What changed:

- Before sending text to the LLM, protected placeholders and structural sentinels are replaced with request-local opaque tokens like `@@HF:...@@`.
- After the model responds, the system verifies that the hard-freeze token stream is exactly preserved in quantity, order, and identity.
- If even one token is dropped, duplicated, reordered, or mutated, the response is rejected with `HardFreezeProtocolViolation`.

Purpose:

- Make placeholder protection a verifiable transport contract instead of relying on prompt obedience.
- Stop fuzzy, speculative “repair” of corrupted placeholder boundaries.
- Prevent the model from silently returning structurally unsafe text that later breaks LaTeX.

What this layer does well:

- It catches real placeholder corruption early and deterministically.

What this layer costs:

- Any model that likes to reorder local markup will now fail hard instead of “mostly working”.
- That is a quality-vs-throughput trade: safer by construction, but more fallbacks and rescue work if the model misbehaves often.

### 2. Invariant-failure rescue and retry containment

Primary commit:

- `2e3b164 Fix invariant fallback retry amplification`

Main code paths:

- `backend/app/services/agents/translator_agent.py:605` `_rescue_plain_text_by_paragraph`
- `backend/app/services/agents/translator_agent.py:915` `_should_skip_fail_part_retry`
- `backend/app/services/agents/translator_agent.py:1896` `_translate_section`
- `backend/app/services/agents/translator_agent.py:2147` `_translate_caption`
- `backend/app/services/agents/translator_agent.py:2536` `_translate_env`
- `backend/app/services/agents/translator_agent.py:1395` `_val_fail_parts`
- `backend/app/services/agents/translator_agent.py:1414` `_retranslate_fail_parts`

What changed:

- If a section or caption hit a hard-freeze invariant and the first-pass result was just the English source, the system no longer gave up immediately.
- It added a paragraph-wise rescue path to try translating smaller chunks before final passthrough.
- Environments were changed so they could still attempt existing plain-text/body rescue before final source preservation.
- `_should_skip_fail_part_retry()` was added so parts already in final safe passthrough states would not keep re-entering Maxtry retry loops.

Purpose:

- Preserve hard-freeze safety.
- Reduce pointless repeated LLM work on already-final passthrough parts.
- Recover more Chinese output before falling back to English.

Expected upside:

- Better quality than pure passthrough when only a few paragraphs are problematic.
- Fewer infinite-feeling retry cascades on parts already known to be source-preserved.

Expected downside:

- More LLM calls during `translate` whenever invariant rescue is triggered.

### 3. Finer-grained fragment rescue

Primary commit:

- `ec683cc Improve invariant rescue granularity`

Main code paths:

- `backend/app/services/agents/translator_agent.py:605` `_rescue_plain_text_by_paragraph`
- `backend/app/services/agents/translator_agent.py:690` `_split_plain_text_rescue_fragments`
- `backend/app/services/agents/translator_agent.py:704` `_translate_plain_text_rescue_piece`
- `backend/app/services/agents/translator_agent.py:765` `_rescue_plain_text_by_fragment`

What changed:

- When paragraph rescue still failed, the system could split the paragraph again into smaller text fragments.
- Placeholder-only fragments are passed through untouched.
- Natural-language fragments are retried independently.
- Leading and trailing whitespace are restored when fragments are stitched back together.

Purpose:

- Reduce English passthrough on sections whose paragraphs are still too large or too token-dense for paragraph rescue.
- Recover Chinese around protected placeholders instead of discarding the whole paragraph.

Expected upside:

- Better translation quality on papers where paragraph rescue is still too coarse.

Expected downside:

- More LLM requests per failing section.
- More nested failure events.
- If retry bookkeeping is imperfect, fragment rescue can amplify retry traffic much more than paragraph rescue did.

## What The Live Evidence Says

### What appears positive

The current in-progress output is not a total regression in quality.

Examples from the live partial maps:

- section `4_1` is already Chinese
- section `3_4` is already Chinese
- section `4_4` is already Chinese

This matters because the earlier degraded server run on the same paper had many English-heavy passthrough sections. So the “rescue more before giving up” direction is not obviously wrong.

Current partial snapshot is still worse than the local CLI-style baseline, but it is not simply “all new protection, no gain”.

### What appears negative

The live task is clearly spending too long inside `translate`, and the logs show multiple nested retry rounds:

- `04:35:39` `Retranslating fail parts ... attempt 1/3`
- `04:37:41` `Retranslating fail parts ... attempt 2/3`
- `04:39:28` `Retranslating fail parts ... attempt 3/3`

During those rounds, the logs show many hard-freeze violations for:

- whole sections like `4_1`, `3_4`
- paragraph subparts like `4_1:paragraph:6`
- fragment subparts like `10:paragraph:0:fragment:1`

The key suspicious pattern is this:

1. A section hits invariant failure.
2. Rescue logic later succeeds and writes Chinese into `sections_map.json`.
3. But the original failure identifier was already registered into the fail-part lists.
4. `_val_fail_parts()` still sees those identifiers and schedules more retry rounds.

This is visible in the live task because:

- `sections_map.json` already shows `4_1` and `3_4` as `translated`
- yet logs later still show:
  - `Retranslating fail parts: ['4_1', '4_1:paragraph:6', '3_4'], attempt 2/3`
  - `Retranslating fail parts: ['4_1', '4_1:paragraph:6', '3_4'], attempt 3/3`

That suggests the current bookkeeping is not purely “retry only unresolved failures”. It is at least partly “retry anything that ever failed during an intermediate subcall”.

## Why It Feels Slower

At this point, the strongest working hypothesis is:

### Hypothesis A: rescue success does not fully unregister earlier failure ids

Relevant code:

- `backend/app/services/agents/translator_agent.py:891` `_register_llm_part_failure`
- `backend/app/services/agents/translator_agent.py:350` `_clear_api_fallback`
- `backend/app/services/agents/translator_agent.py:1395` `_val_fail_parts`
- `backend/app/services/agents/translator_agent.py:1414` `_retranslate_fail_parts`

Behavior:

- `_request_llm_for_trans()` registers a fail-part immediately when a hard-freeze invariant is raised.
- If later rescue succeeds, `api_fallback_reason` may be cleared, but the earlier fail-part identifier is not removed from `fail_section_nums`, `fail_caption_phs`, or `fail_env_phs`.
- Once `self.have_fail_parts` is true, `_val_fail_parts()` runs retry rounds over the accumulated lists.

Why this matters:

- A section can end up translated successfully and still get revisited later.
- The cost is no longer just “one rescue path”; it becomes “rescue path plus one or more Maxtry rounds”.

### Hypothesis B: fragment rescue made the bookkeeping bug much more visible

Relevant code:

- `backend/app/services/agents/translator_agent.py:690`
- `backend/app/services/agents/translator_agent.py:704`
- `backend/app/services/agents/translator_agent.py:765`

Behavior:

- `ec683cc` adds more nested LLM calls per difficult paragraph.
- Each nested fragment call can independently register a fail-part on invariant violation.
- Even if some of those fragment identifiers are later ignored because they are not top-level sections, they still indicate more nested failing work happened.

Why this matters:

- More nested rescue calls means more opportunities to mark a part as failed.
- If success does not clean up failure bookkeeping, the slowdown becomes much easier to trigger on real papers.

## Current Judgment: Positive Or Negative?

As of this investigation, the answer is mixed.

### Hard-freeze itself

Judgment: positive

Reason:

- It gives a real safety guarantee.
- The violations seen in logs are real model boundary mutations, not imaginary parser paranoia.

Without this layer, the system would likely accept more corrupted placeholder sequences and push broken TeX deeper into the pipeline.

### Paragraph rescue and bounded passthrough

Judgment: mostly positive

Reason:

- It improves quality over blind English passthrough.
- It preserves bounded behavior.
- It does not create infinite loops by itself.

Important bound:

- `_val_fail_parts()` is capped by `Maxtry` (currently `3`)
- `_call_llm_with_freeze()` also has bounded network and `429` retries

So the current behavior is expensive, but not unbounded.

### Fragment rescue in its current form

Judgment: likely mixed leaning negative for runtime, but potentially positive for quality

Reason:

- It probably helps recover more Chinese in some difficult sections.
- But the live task shows a real performance penalty.
- The slowdown likely comes from interaction with stale fail-part bookkeeping, not from the idea of fragment rescue alone.

So the likely conclusion is:

- the design goal is reasonable,
- the current implementation path is too expensive,
- and the main bug is probably retry bookkeeping rather than placeholder protection correctness.

## What To Inspect Next

The next focused investigation should test one narrow question:

Can a section that eventually succeeds via paragraph or fragment rescue still remain in `fail_section_nums` and re-enter `_val_fail_parts()`?

That should be validated with a regression test around:

- `_register_llm_part_failure`
- `_clear_api_fallback`
- `_translate_section`
- `_val_fail_parts`

The most likely fix direction is not “remove hard-freeze” and not “remove rescue”.

The likely fix direction is:

- if a section/caption/env finishes in a safe translated state,
- remove its top-level identifier from the fail-part retry lists before Maxtry retranslation starts,
- and possibly avoid registering nested paragraph/fragment identifiers into top-level fail queues at all.

## Bottom Line

The current slowdown does not look like compile slowness or queue slowness.

It looks like:

1. hard-freeze is catching real token-order corruption,
2. rescue logic is trying to recover quality,
3. some parts do recover successfully,
4. but failure bookkeeping is still causing extra retry rounds after success,
5. and fragment rescue made that amplification much more visible on `2006.11239`.

So the placeholder protection direction is not obviously a mistake, but the current orchestration around it likely has a real negative runtime side effect that should be fixed before judging the overall approach.
