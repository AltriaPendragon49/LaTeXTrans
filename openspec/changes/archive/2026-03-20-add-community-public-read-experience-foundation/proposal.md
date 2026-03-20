# Why
- The current community experience behaves like a task-centric SPA shell instead of a content-first public reading surface.
- The diagnosis found four root causes behind the gap versus alphaXiv-like expectations: blank-feeling homepage cold loads, request waterfalls on paper detail, on-demand preview generation during public reading, and no guaranteed baseline content for cold-start environments.
- Day 9 and Day 10 already discuss external hot feeds and demo handoff, but they do not define the runtime guarantees needed so the public community surface feels populated, immediate, and stable for normal readers.

## What Changes
- Define a public-read experience foundation so the homepage and paper detail route can render first-screen discovery content without depending on a fully empty client-only boot path.
- Define a preview-readiness lifecycle so `preview_html` is materialized before normal public reading instead of being synchronously generated on first reader access.
- Define a detail/read contract that eliminates the current metadata-then-preview request waterfall for normal paper reading.
- Define click-through acceleration for existing papers so a feed-to-detail transition can reuse prefetched route code and prefetched detail payloads instead of always waiting for a cold navigation.
- Define a public detail fast path so metadata repair and translated-abstract repair do not block the user-visible detail response for already-published papers.
- Define preview payload reuse so repeated public detail and preview reads do not repeatedly re-read and rebuild the same stored `preview_html` blob.
- Define reader enhancement reuse so the frontend does not repeatedly sanitize and re-enhance the same preview asset when cached detail is refreshed with an equivalent payload.
- Define on-demand reader enhancement asset loading so homepage and feed boot do not eagerly pay for KaTeX reader assets that are only needed on paper-reading routes.
- Define intent-time reader enhancement prewarm so a feed-to-detail transition can start loading reader-only enhancement assets before the click resolves.
- Define a cold-start content floor so operators can provision a baseline official featured set for new environments without relying on organic submissions appearing first.
- Define observability and cacheability guardrails so the team can verify that community public-read latency is improving rather than moving work around invisibly.

## Non-Goals
- This change does not define a recommendation engine, hot-score algorithm, or real-time ranking system.
- This change does not require a full framework rewrite to Next.js or a backend rewrite to Go.
- This change does not replace Day 10 demo-data handoff; it defines the product/runtime capability that Day 10 can later populate and demonstrate.

## Impact
- Modifies capability `community-paper-discovery-ui`.
- Adds capability `community-public-read-experience`.
- Depends on the existing community feed, paper detail, paper library storage, and paper translation bridge behavior already delivered in prior community changes.
