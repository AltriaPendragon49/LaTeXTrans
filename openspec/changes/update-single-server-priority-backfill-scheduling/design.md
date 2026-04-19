## Context

The production backend currently runs on one Tencent Cloud server with one backend process and no spare machine for queue offloading. The frontend is not colocated on that machine, so backend CPU, memory, and compile capacity can be focused on translation work. The near-term requirement is not public high-concurrency translation demand; it is sustained ingestion of thousands of papers so the reading platform has enough inventory.

This leads to a different optimization target from a typical public queueing service:

- interactive user requests must stay responsive when they appear
- backfill should consume all otherwise-idle translation capacity
- translation quality guardrails must remain intact
- the system should remain simple enough to operate on one server

## Goals / Non-Goals

- Goals:
  - Prioritize interactive translation requests over internal backfill on a single server.
  - Let backfill occupy all available translation slots when no interactive work is waiting.
  - Pause backfill only at safe, resumable checkpoints.
  - Reduce 429 waiting time by using multiple tokens from the same relay provider more intelligently.
  - Keep the current single-paper LangGraph orchestration as the inner translation kernel.
  - Make the rollout incremental, feature-flagged, and easy to disable.

- Non-Goals:
  - No distributed queue, multi-host scheduler, or mandatory Redis dependency in this phase.
  - No splitting of a single paper's LangGraph nodes across multiple workers.
  - No weakening of `validate`, `repair_translation`, compile-aware fallback, or target-language persistence semantics.
  - No change that forces public-facing high-concurrency product behavior before it is needed.

## Decisions

### 1. Use a single-machine dual-lane scheduler

The scheduler will expose two logical lanes:

- `interactive`: user-facing work, always higher priority
- `backfill`: internal ingestion work, opportunistic and preemptible only at safe boundaries

Scheduling policy:

- backfill may borrow every idle translation slot by default
- when an interactive task arrives, the scheduler marks one running backfill task for cooperative yield
- the yielded backfill task gives up its slot only after reaching a safe checkpoint
- once interactive pressure disappears, the yielded backfill task is resumed from its checkpoint before newer backfill tasks are preferred

This preserves high utilization without introducing abrupt cancellation.

### 2. Keep LangGraph as the indivisible per-paper kernel

The current per-paper LangGraph orchestration remains the authoritative execution kernel. The new scheduler is an outer control plane only. It may decide:

- which paper gets a slot
- when a running backfill paper should yield at the next checkpoint
- which token lease a request should use

It may not:

- move individual LangGraph nodes of one paper into separate workers
- interrupt a node while an LLM request is in flight
- interrupt compile execution mid-subprocess

This is the main stability guardrail for avoiding regressions in translation behavior.

### 3. Introduce cooperative checkpoints instead of abrupt pause

Backfill pause/resume must be cooperative. Safe checkpoints are explicit orchestration boundaries such as:

- parse completed
- a section or environment batch has been fully flushed to durable intermediate artifacts
- a validation/retry round has completed
- immediately before entering compile queue wait
- immediately after compile finishes and results are persisted

At each checkpoint the runtime records enough resume metadata to continue from the last completed boundary rather than restarting the whole paper.

This is intentionally narrower than general-purpose process suspension. We only support pause at places where the pipeline already has durable, replayable state.

### 4. Start with conservative single-server capacity

Because the observed server is a 4 vCPU / ~8 GB RAM machine and LaTeX compilation is the sharpest shared bottleneck, the initial recommended policy is:

- backend API process count stays at `1`
- translation task slots start at `2`
- compile concurrency remains `1`

Backfill may occupy both translation slots when the interactive lane is empty. When interactive work appears, one slot is recovered at the next checkpoint. This gives meaningful throughput gain without turning compile or memory pressure into a stability risk.

### 4a. Split admin backfill ownership from the web-serving runtime

The current codebase still keeps translation runtime state partially in memory, so a full cross-process shared queue is not safe yet. To protect the user-facing site without re-architecting the entire translation kernel in one step, this change introduces a narrower split:

- `web` runtime: serves HTTP traffic and keeps ordinary interactive translation behavior
- `worker` runtime: polls queued admin curation/delete jobs from durable storage and owns background backfill execution
- `all` runtime: legacy compatibility mode for local development or single-process fallback

This avoids running heavy admin backfill orchestration inside the same Python process that answers homepage and health requests.

### 4b. Let worker backfill yield to real browser pressure

Because both runtimes still share one physical server, splitting processes is necessary but not sufficient. The worker therefore watches a lightweight file-backed "frontend pressure" heartbeat written by the web runtime. When the heartbeat is recent:

- the worker should avoid starting a new backfill task
- already-running work is allowed to finish its current safe step
- the worker process is additionally de-prioritized with OS niceness where supported

This keeps the user's desired behavior: background work can still occupy most spare capacity, but it must make room once real access traffic appears.

### 5. Add a health-aware token pool instead of naive round-robin

The user has multiple API keys from different accounts on the same relay provider. In phase 1, the system-managed pool is explicitly:

- `base_url_A` with `2` independent keys
- `base_url_B` with `3` independent keys

These five endpoint-credential pairs are the pool members. A simple round-robin strategy is not enough. The pool needs per-member state:

- cooldown-until timestamp
- recent `429` streak
- recent `503` streak
- transient network failure state
- last successful use
- optional lease ownership while a request is active

Request policy:

- if the current pool member hits consecutive `429` or consecutive `503` and another healthy member exists, retry locally only for a short window measured in seconds, then fail over quickly
- if every token in the pool is rate-limited, keep retrying on the current token instead of thrashing across equally exhausted tokens
- interactive tasks may keep waiting/retrying during pool exhaustion
- backfill admission becomes more conservative when the entire pool is exhausted, so interactive tasks are not forced to queue behind useless retry churn

This matches the user's requirement that the token pool exists to shorten waits, not to create longer sleeps per request.

Important scope boundary for phase 1:

- only system-managed credentials participate in this pool
- all translation-runtime system-managed chat-completion calls in the paper pipeline, including post-translation structured insight generation, must reuse the same pool helper and health state
- user-supplied `custom_api_key/custom_base_url` requests keep the current single-credential behavior
- persisted user custom credentials from settings also keep the current single-credential behavior in phase 1

This isolates the rollout and avoids silently changing user-owned API routing behavior.

### 6. Defer only non-critical post-success artifacts

Two parts of the current path are good candidates for sidecarization:

- terminology-table generation
- successful-compilation diagnostic enrichment

They will move out of the main slot only behind feature flags and only when the preceding translation result is already durable. Failure-path diagnostics stay synchronous because they are part of correctness and operator actionability.

For rollout safety:

- interactive traffic can keep legacy inline behavior by default
- backfill can enable deferred artifacts first
- sidecar jobs must be idempotent and resumable

### 6a. Move community feed reads to paginated first-page caching

The public homepage should no longer fetch the full community paper list on first render. The feed now returns:

- `items`
- `total`
- `offset`
- `limit`
- `has_more`
- `next_offset`

The web runtime caches the first `latest` page with an empty query for a short TTL and invalidates that cache whenever public paper state changes. The frontend increments via `load more` instead of re-fetching the whole corpus.

### 6b. Prewarm thumbnail cache on publish

Thumbnail endpoints already cache after first access, but the first homepage visit still pays the rasterization/download cost. This change adds a shared thumbnail-cache helper and schedules warmup when a paper becomes publicly ready, covering:

- source PDF thumbnails when a local or arXiv source preview exists
- translated PDF thumbnails when translated output becomes public

### 7. No external Redis requirement in phase 1

A Redis queue is not required for this phase because:

- there is only one backend server
- the backend already must remain a single worker while runtime state is partially in-process
- online translation demand is modest
- the main requirement is smarter local scheduling, not cross-host coordination

Redis remains a future option if the system later needs:

- multi-process or multi-host schedulers
- durable shared queue state across several backend instances
- stronger cross-restart scheduling guarantees for large backfill fleets

## Risks / Trade-offs

- Cooperative yield is more complex than plain FIFO. Mitigation: keep checkpoint boundaries narrow and explicit.
- Token-pool behavior can accidentally change quality if it alters model/runtime parity. Mitigation: the pool chooses credentials only; it does not change prompt, model, or repair semantics.
- Deferred artifacts can create output-timing differences. Mitigation: gate the behavior behind flags and roll it out to backfill first.
- Single-server throughput can still be compile-bound. Mitigation: keep compile concurrency fixed at `1` and optimize scheduler utilization around it instead of pretending compilation is parallel-safe.

## Migration Plan

1. Implement phase-1 token-pool support for system-managed credentials only.
2. Preserve current behavior for request-supplied and user-stored custom credentials.
3. Add tests that prove `429/503` failover and all-members-exhausted behavior.
4. Deploy split `web` and `worker` runtimes on the same host so admin backfill is removed from the web-serving process.
5. Enable frontend-pressure-aware backfill admission in the worker runtime.
6. Roll community feed pagination/load-more and first-page cache together so the web runtime stops whole-list fetches.
7. Enable thumbnail prewarm after public-paper publish transitions.
8. Enable deferred post-success artifacts for backfill only after parity testing passes.

## Validation Plan

Use a small regression corpus with about two papers per issue type:

- baseline/simple papers
- math-dense papers
- complex environment-heavy papers
- fallback-sensitive papers
- pause/resume-sensitive papers

Add targeted automated checks for:

- interactive priority over backfill
- checkpointed cooperative yield/resume
- token failover to another healthy system-managed member
- consecutive `503` failover behavior
- custom user key bypassing the system-managed pool
- all-token-exhausted retry behavior
- compile-slot protection
- feature-flag rollback to legacy behavior

## Open Questions

- None for proposal scope. The user has already approved the single-server, priority-first, stability-first direction for formalization.
