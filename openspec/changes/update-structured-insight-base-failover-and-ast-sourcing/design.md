## Context

Structured insight generation currently happens after main translation succeeds. In production, the main translation path can finish successfully while the five structured-insight modules later hit repeated `503` responses on the relay layer and fall back to weaker content. At the same time, the current source assembly mostly consumes translated runtime sections or preview HTML, which means the guide quality degrades when translated excerpts are thin or preview recovery is stale.

This change needs to improve both robustness and quality without breaking three approved boundaries:

- structured insight remains part of the synchronous admin publication gate
- output remains Chinese-only
- global token-pool health remains member-level rather than provider-wide or base-wide

## Goals / Non-Goals

- Goals:
  - Prefer richer structured-insight inputs derived from runtime section artifacts that still retain raw TeX/AST content alongside translated excerpts.
  - Shorten end-to-end structured insight latency by generating the five modules concurrently when possible.
  - Reduce repeated `503` failures on one relay base during one structured-insight task without globally banning that base.
  - Keep unreadable, duplicated, or missing modules repairable without rerunning already-good modules.

- Non-Goals:
  - No change to the main translation LangGraph node structure.
  - No global base-level health state or global base bans.
  - No relaxation of publication gating or Chinese-only persistence.
  - No dependence on preview HTML as the primary structured-insight source.

## Decisions

### 1. Build hybrid structured-insight source packets from runtime artifacts first

The structured-insight source builder will read `sections_map.json` and produce normalized per-section packets that preserve:

- the original section title
- raw section text extracted from the original TeX/AST-backed `content`
- translated section text extracted from `trans_content`

For each guide module, the builder will compose a hybrid excerpt that includes:

- paper title and abstract anchor
- module-relevant original-source cues
- module-relevant translated excerpts for Chinese grounding

If runtime section artifacts are missing, the system may still fall back to preview HTML, but that remains a degraded path rather than the normal source of truth.

### 2. Use parallel first-pass generation plus targeted repair

The five guide modules will be generated concurrently in the first pass. That removes the unnecessary serial wall-clock cost that currently exists when the modules are independent.

To preserve quality, the pipeline keeps a second stage:

- validate all first-pass outputs for readability, emptiness, and duplication
- only re-run the invalid modules
- provide already-successful module briefs to the repair prompts so the repaired module can avoid overlap
- use fallback content only for modules that still fail after bounded repair

This preserves the existing "retry only the failed module" principle while still allowing the fast path to run in parallel.

### 3. Keep global health member-level, but add structured-insight task-local base preference

The shared pool continues to track health per endpoint-credential member. A member hitting repeated `503` failures enters cooldown independently; other keys on the same base remain usable for other tasks if they are healthy.

Structured insight adds only a task-local preference layer:

- count retryable `503` responses by `base_url` during the current structured-insight task
- once one base accumulates 3 `503` responses during that task, later member selection for that task should prefer the other base when a healthy member exists there
- do not mark the whole base globally unhealthy

This matches the observed failure mode without overreacting at the global scheduler level.

### 4. Increase member-level 503 cooldown, but keep short current-member retries under full exhaustion

The current one-second `503` cooldown is too short to reduce churn. The pool will move to:

- consecutive-member `503` threshold: 3
- member cooldown after threshold: a longer bounded interval measured in several seconds

This cooldown affects member selection for other requests. It does not stop the current request from retrying its current member when every member is unavailable. In the all-members-exhausted case, the request keeps retrying the current member on a short interval so we do not replace one long wait with blind rotation.

### 5. Keep structured insight synchronous and Chinese-only

The publication gate semantics do not change:

- structured insight still blocks admin publication until all five modules are available
- stored content remains Chinese-only
- fallback content still has to pass readability validation before publication continues

## Risks / Trade-offs

- Parallel first-pass generation removes the current `previous_module_briefs` serial dependency. Mitigation: retain strong per-module boundaries and add a targeted repair phase that can use successful module briefs when overlap appears.
- Hybrid sourcing may surface noisy original LaTeX fragments. Mitigation: continue normalizing source text through existing TeX-to-text helpers and keep module excerpt size bounded.
- A longer `503` cooldown could reduce immediate reuse of one member. Mitigation: apply the cooldown per member only and keep all-members-exhausted retry on the current member.

## Validation Plan

- Unit-test hybrid source assembly from runtime sections and preview fallback.
- Unit-test parallel generation behavior plus targeted repair of unreadable or duplicated modules.
- Unit-test task-local base preference after cumulative `503` responses without globally blacklisting the base.
- Unit-test longer member `503` cooldown and current-member retry when all members are exhausted.
- Validate the full change on the server through the admin ingestion path for `arXiv:2508.18791`.
