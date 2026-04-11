# Community Five-Module Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current six-module guide with a fixed five-module paper-guide system whose modules are generated independently as Chinese reader-facing正文 and are required for admin publication.

**Architecture:** Keep the current row-based `community_structured_insights` storage and admin curation pipeline, but replace the fixed key set, module-routing heuristics, prompt boundaries, publish gates, and detail-page rendering with the final five-module contract. Old public papers are out of scope; verification will delete and re-curate `2508.18791` to prove the new pipeline end to end.

**Tech Stack:** FastAPI backend, local/MySQL repository layer, React + Vitest frontend, OpenSpec change records, Playwright/manual browser verification against local services.

---

## Phase 1: Re-baseline the backend contract

- [ ] Update the backend paper-guide schema from the current six-module contract to the final minimal storage contract:
  - `paper_id`
  - `guide_sections.problem.content`
  - `guide_sections.solution.content`
  - `guide_sections.innovation.content`
  - `guide_sections.experiment.content`
  - `guide_sections.future.content`
- [ ] Replace the current module keys with the final fixed set:
  - `problem`
  - `solution`
  - `innovation`
  - `experiment`
  - `future`
- [ ] Keep paper-guide content Chinese-only.
- [ ] Keep five-module completion as a publication gate.
- [ ] Reserve per-module object shape for future metadata expansion, but only implement `content` in this version.

## Phase 2: Keep the generation pipeline content-first and structure-light

- [ ] Ensure the model is never asked to generate overall structure for the five modules.
- [ ] Keep the backend responsible for module ordering, validation, retry, and fallback.
- [ ] Keep the model output as plain Chinese正文 only:
  - no JSON
  - no schema contract
  - no multi-field `summary/body/bullets`
- [ ] Keep markdown/text rendering support on the frontend without introducing richer content types.

## Phase 3: Build module-specific source preparation

- [ ] Rework the backend helper that extracts translated paper text into module-relevant excerpts.
- [ ] Ensure every module input includes:
  - title
  - abstract
  - module-relevant excerpts
- [ ] Route source material approximately as follows:
  - `problem`: title + abstract + introduction + current-method limitation paragraphs
  - `solution`: title + abstract + method / system overview
  - `innovation`: title + abstract + contribution paragraphs + key design paragraphs
  - `experiment`: title + abstract + experiment / evaluation / results
  - `future`: title + abstract + conclusion / discussion / limitation
- [ ] If exact section labels are unavailable, fall back to closest available translated sections in reading order.
- [ ] Keep the prepared excerpt size bounded so prompts remain stable.
- [ ] Avoid using one shared full-paper payload for all modules.

## Phase 4: Implement five independent LLM calls

- [ ] Create one backend prompt template per module question.
- [ ] Use the same prompt frame for all modules:
  - Chinese output
  - reader-oriented explanation
  - no JSON
  - can use paragraphs
  - grounded in provided paper text
- [ ] Add module-boundary constraints:
  - `problem` answers the problem, importance, and prior-method limits
  - `solution` answers how the method works
  - `innovation` answers what is fundamentally new
  - `experiment` answers how effectiveness is validated and what the results show
  - `future` answers realistic extensions, limits, and research implications
- [ ] Call the LLM once per module.
- [ ] Normalize returned text and store it as `guide_sections.<key>.content`.
- [ ] Treat a module as successful only if normalized content is displayable and readable.

## Phase 5: Add retry and fallback logic

- [ ] Keep bounded per-module retries.
- [ ] Do not rerun all five modules when only one fails.
- [ ] If a module still fails after retries, build a simplified fallback from trusted translated inputs such as:
  - title + abstract
  - nearby relevant sections
- [ ] Store fallback content explicitly inside the same module object as ordinary `content` so publication can continue.
- [ ] Make fallback behavior implementation-oriented rather than decorative: even when primary generation fails, fallback must still produce a usable Chinese explanatory paragraph that can be shown to readers.
- [ ] Make sure the fallback path still produces user-readable Chinese text rather than placeholders like `not_ready`.

## Phase 6: Reconnect publication gating

- [ ] Update admin curation publish flow so publication waits for:
  - ingestion complete
  - translation complete
  - compilation complete
  - five module contents ready
- [ ] Change the readiness check to:
  - five required module keys exist under `guide_sections`
  - each `guide_sections.<key>.content` is non-empty after trimming
  - each `guide_sections.<key>.content` passes minimum readability checks such as minimum length and rejection of known failure placeholders
  - no two modules are exact duplicates after normalization
- [ ] Keep failed or partial papers out of the public feed until all five modules are present.

## Phase 7: Update persistence and API output

- [ ] Keep repository serialization/deserialization on the current content-only row model.
- [ ] Remove six-module assumptions from service-level placeholder payloads and readiness ordering.
- [ ] Keep API responses frontend-consumable with stable key semantics for the five-module contract.

## Phase 8: Update the frontend detail pane

- [ ] Change the paper detail right pane to render the new five-module list.
- [ ] Show the fixed Chinese titles:
  - 这篇论文解决什么问题，为什么重要，现有方法的关键不足是什么？
  - 作者的核心思路是什么，方法整体是如何工作的？
  - 论文的关键创新点有哪些，相比已有方法，本质区别在哪里？
  - 论文如何验证方法有效性，主要结论是什么？
  - 这项工作有什么潜在改进或扩展方向，对相关研究有哪些启发？
- [ ] Render each module as an accordion section.
- [ ] Read from `guide_sections.<key>.content` and render `content` as markdown/text only.
- [ ] Remove frontend-side “自动补齐缺失模块” assumptions and only render backend-provided five-module content in fixed order.

## Phase 9: Rewrite tests around the new strategy

- [ ] Replace current tests that assert six-module UI or six-module backend ordering.
- [ ] Add backend tests for:
  - module-specific excerpt selection
  - one-module-at-a-time generation
  - single-module retry
  - fallback content generation
  - module-boundary separation between `solution` and `innovation`
  - publication blocked when any `guide_sections.<key>.content` is empty or fails minimum readability rules
  - publication blocked when modules collapse into exact duplicates
  - publication succeeds when all five `guide_sections.<key>.content` values are readable
- [ ] Add frontend tests for:
  - fixed five titles
  - accordion rendering
  - markdown/text display from `guide_sections.<key>.content`
  - no reader-language dependency for guide language

## Phase 10: Real admin end-to-end verification

- [ ] Delete the existing `2508.18791` paper and its old six-module guide artifacts from DB and local disk before retesting.
- [ ] Restart the backend container.
- [ ] Run a real admin curation publish for `2508.18791`.
- [ ] Verify final success conditions:
  - admin batch status `completed`
  - job status `completed`
  - paper visible publicly
  - five module rows/content present
  - detail API returns the new module shape
  - frontend renders the five-module guide correctly
