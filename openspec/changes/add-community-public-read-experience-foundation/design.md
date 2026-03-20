# Design: Community Public-Read Experience Foundation

## Context

The current community surface already supports:

- a public homepage feed,
- public paper detail,
- paper-owned preview and download routes,
- library-copied paper assets.

However, the public reader path still feels operational rather than content-first because:

1. the homepage starts from a client-rendered shell,
2. the first feed load is not guaranteed to arrive with the initial public document,
3. paper detail and preview are fetched as separate reader-visible steps,
4. preview generation can still happen on the first public read,
5. a new environment can legitimately have no public papers to show.

This change defines user-visible runtime guarantees without forcing one exact implementation stack.

## Decision 1: First-screen homepage content must not depend on an empty boot path

The product needs a stronger contract than "render loading and eventually fill in results."

Accepted implementation patterns:

- SSR or streamed server rendering for the homepage route,
- static pre-render plus incremental refresh,
- HTML plus serialized bootstrap data for the first feed page,
- another equivalent mechanism that gives the first public route enough content to render discovery immediately.

Rejected pattern:

- shipping a public homepage that always waits for client mount and a fresh post-mount fetch before first-screen discovery content can appear.

The spec intentionally does not force a framework rewrite. A Vite/FastAPI stack may still satisfy the contract by serializing an initial payload or serving a pre-rendered discovery shell with embedded feed data.

## Decision 2: Initial homepage fetch cannot pay search debounce tax

Search debounce is useful for user typing, but it should not delay the initial homepage data path.

Therefore the change distinguishes:

- initial route hydration / first public load,
- user-initiated query refinement.

Only the second path may use debounce.

## Decision 3: Public paper reading must be preview-ready before the reader asks for it

The current fallback of generating `preview_html` from the `GET /api/papers/{paper_id}/preview` path is acceptable for repair or exceptional recovery, but not for the normal public reading path.

Normal read path:

- publish or sync task completes,
- preview materialization runs in background,
- paper becomes reader-ready,
- public preview reads return stored assets.

Exceptional recovery path:

- stale or missing preview is detected,
- the system may run a repair job,
- the user-facing route must expose a clear unavailable or warming state rather than doing an opaque long synchronous generation step.

## Decision 4: Paper detail and preview need a unified first-read contract

The public reader should not need to visibly wait for:

1. detail metadata,
2. then a second preview fetch,
3. then preview generation.

Accepted approaches:

- detail response includes the first-read payload directly,
- detail response includes bootstrap preview payload,
- detail navigation triggers deterministic prefetch before the reader becomes interactive,
- another equivalent contract that makes the normal read path effectively single-phase from the user perspective.

The design does not require every preview byte to live in the detail payload, but it does require the reading experience to avoid a user-visible waterfall under normal conditions.

## Decision 5: Cold-start environments need an operator-managed content floor

The team needs a way to avoid launching a public community homepage that is technically healthy but socially empty.

This change therefore requires a baseline official content floor that operators can provision by configuration, seed job, import task, or curated publish flow.

This is intentionally different from Day 10 demo data:

- Day 10 can define the specific demo set and handoff package.
- This change defines the underlying runtime capability that production or staging can use to stay non-empty.

## Decision 6: Observability must measure public-read readiness

The change should be verified with explicit signals, not subjective impressions alone.

Recommended metrics include:

- homepage initial payload availability,
- homepage public-read time-to-first-paper,
- paper detail read-ready latency,
- preview materialization backlog / failure rate,
- cold-start baseline provisioning status.

The spec should require measurable readiness signals while leaving exact metric names to implementation.

## Decision 7: Existing-paper click-through must prefetch both route code and detail payload

Improving the homepage alone is not enough if users still click an existing paper and then wait through:

1. route chunk download,
2. detail fetch,
3. preview bootstrap hydration.

The feed therefore needs a click-through acceleration layer for dominant navigation paths:

- prefetch the paper detail route chunk on intent signals such as hover, focus, or pointer-down,
- prefetch the public paper detail payload for visible or intentful cards,
- reuse the prefetched payload on the destination route.

The design does not require speculative prefetch for every paper in the feed immediately; it requires at least intent-based prefetch for the common click-through path.

## Decision 8: Public detail repair work must not block the fast path

The current detail path can still perform heavyweight repair work such as:

- arXiv metadata hydration,
- translated abstract recovery from task outputs,
- stale preview recovery checks.

Those repairs are useful, but they should not hold the normal public detail response hostage.

Accepted public-detail behavior:

- return the best already-stored detail payload immediately,
- return preview bootstrap if already ready,
- schedule metadata / abstract / preview repair in background when needed,
- expose warming or unavailable reader state explicitly.

Rejected behavior:

- blocking the user-visible detail response on repair attempts that can touch remote metadata or task-output filesystem scans.

## Decision 9: Stored preview payload assembly must reuse previously loaded HTML when the asset is unchanged

The public reader still pays avoidable cost if each request:

- reads the same `preview_html` file from disk multiple times,
- re-evaluates refresh markers against the same unchanged content,
- rebuilds the same API payload for the same asset on every detail and preview request.

For a stored preview asset, the backend should treat the generated HTML as a cacheable read model keyed by immutable asset identity plus file freshness signals.

Accepted implementation patterns:

- process-local in-memory caching keyed by asset id / path / generated timestamp,
- equivalent reuse keyed by file stat plus asset identity,
- another mechanism that avoids repeated full-file reads for unchanged public preview assets.

Rejected pattern:

- reading the full preview file once to decide freshness and then reading the full file again to build the response payload for the same request.

## Decision 10: Reader enhancement work must reuse prepared output for unchanged preview assets

The public reader performs expensive client-side work after preview data arrives:

- HTML sanitization,
- KaTeX auto-render enhancement.

If a prefetched detail payload is refreshed with an equivalent preview asset, the reader should not redo the same enhancement work just because object identity changed.

Therefore the frontend should reuse prepared reader HTML for stable preview signatures such as:

- asset id,
- generated timestamp,
- equivalent content hash or equivalent stable marker.

The goal is to keep the first visible reader stable and avoid repeating the most expensive client-side preparation when the preview content has not materially changed.

## Decision 11: Reader-only enhancement assets must load on demand and support intent-time prewarm

The public homepage and feed should not eagerly pay the transfer and parse cost of reader-only enhancement assets such as:

- KaTeX auto-render logic,
- KaTeX stylesheet and font payloads,
- other preview-only enhancement helpers that are irrelevant to non-reader routes.

Accepted implementation patterns:

- route-scoped chunks for reader-only dependencies,
- dynamic import for enhancement helpers used only after preview HTML is present,
- intent-time prewarm on hover, focus, or pointer-down for the dominant feed-to-detail transition.

Rejected pattern:

- loading reader-only enhancement dependencies as part of the common homepage bootstrap when the user has not yet shown reading intent.
