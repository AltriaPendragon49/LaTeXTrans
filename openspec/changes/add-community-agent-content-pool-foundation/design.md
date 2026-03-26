## Context
- The current community flow can silently import and translate papers on demand, but that still makes first-answer quality and latency depend on live network and translation work.
- The product already has community paper records, translation tasks, preview generation, and reader fallback behavior that can be reused by a background prewarm system.
- The requested scope is not a ranking engine or hot-feed product by itself; it is the backend content-pool foundation that makes later agent and reader experiences faster and richer.

## Goals / Non-Goals
- Goals:
  - Add a background pipeline that discovers and prewarms likely-useful papers before users request them.
  - Reuse canonical paper records and existing translation/read pipelines instead of creating a separate storage model.
  - Expose enough readiness and failure signals for operators to verify the pool is healthy.
  - Improve agent and reader hit quality by preferring prewarmed translated evidence when available.
- Non-Goals:
  - Do not solve hot-feed ranking quality in this change.
  - Do not redesign the paper detail UI in this change.
  - Do not add deep research synthesis in this change.
  - Do not replace live import/translation fallback for uncached papers.

## Decisions
- Decision: Model the content pool as a background-job handoff pipeline rather than a request-path feature.
  - Candidate discovery, intake, translation, preview generation, and indexing all happen off the user latency path.
  - User-facing flows still reuse the same paper detail and translation capabilities after content is warmed.

- Decision: Reuse canonical community paper rows keyed by `arxiv_id` and existing paper admission rules.
  - The content pool must never create parallel duplicate paper records for the same paper.
  - If a canonical paper already exists, the pool enriches and prewarms that record instead of creating a new one.

- Decision: Use a staged prewarm lifecycle.
  - Required stages:
    1. discover candidate
    2. admit or reuse canonical paper
    3. fetch or confirm source archive availability
    4. enqueue translation and preview generation
    5. promote translated abstract / translated reader assets / preview outputs
    6. index readiness for internal retrieval
  - Each stage must be idempotent and restart-safe.

- Decision: Make translated evidence promotion explicit.
  - The pool is considered useful only when translated fields such as `abstract_translated`, translated preview HTML, or translated reader-ready assets become queryable and readable by downstream surfaces.
  - English-only papers may still be admitted, but they do not count as translated-ready hits until translated outputs exist.

- Decision: Prefer prewarmed content at read and agent time, but preserve misses.
  - The community agent prefers internal translated evidence from prewarmed papers before starting new on-demand translation work.
  - The public/community reader uses the best available prewarmed readable mode immediately.
  - On-demand import and translation remain the fallback path for papers not yet in the pool.

- Decision: Bound the worker pipeline with concurrency, retries, and source-safe fetch behavior.
  - Candidate fetch and source acquisition must respect configurable rate limits and bounded worker concurrency.
  - Translation and preview generation use the existing task runtime and inherit its retry and failure semantics where possible.
  - Permanent failures stay visible to operators instead of silently looping forever.

- Decision: Log structured readiness and failure signals.
  - Operators need candidate counts, warmed-paper counts, translated-ready counts, source fetch failures, translation failures, and freshness timestamps.
  - Logging and metrics must be sufficient to verify that the pool is improving user-visible hit quality.

## Risks / Trade-offs
- A content pool adds operational complexity because background failures can silently reduce quality if not observed.
- Prewarming too aggressively can create avoidable infrastructure cost and external-source pressure.
- Prewarming too conservatively may not materially improve the first-answer experience.

## Migration Plan
1. Start with a bounded candidate source and a small concurrency cap.
2. Reuse existing paper and translation artifacts instead of introducing a second asset model.
3. Expose readiness signals before expanding source breadth.
4. Keep interactive fallback untouched until the pool proves useful.

## Open Questions
- None for this change. Editorial source selection and feed ranking quality are deferred to later changes.
