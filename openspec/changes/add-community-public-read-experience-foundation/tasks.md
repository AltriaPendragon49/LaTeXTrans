## 1. Experience Contract
- [x] 1.1 Define the homepage first-screen delivery contract for public discovery.
- [x] 1.2 Define the paper detail read contract so normal reading does not require a client-visible metadata-then-preview waterfall.
- [x] 1.3 Define the preview-readiness lifecycle for publish, refresh, and stale-asset recovery.
- [x] 1.4 Add existing-paper click-through acceleration for detail-route code and payload prefetch.
- [x] 1.5 Add a public detail fast path so metadata and abstract repair no longer block the visible reader entry.
- [x] 1.6 Reuse stored preview payload assembly so unchanged preview assets do not re-read and rebuild the same HTML on every public detail or preview request.
- [x] 1.7 Reuse prepared reader HTML so equivalent preview refreshes do not re-run expensive client-side sanitization and enhancement work.
- [x] 1.8 Load reader-only enhancement assets on demand so homepage/feed boot no longer eagerly includes KaTeX reader dependencies.
- [x] 1.9 Prewarm reader-only enhancement assets on detail click intent alongside route and data prefetch.

## 2. Cold-Start And Operations
- [x] 2.1 Define the operator-managed baseline content floor for empty or newly deployed environments.
- [x] 2.2 Define cache and observability requirements for public feed, detail, and preview reads.

## 3. Delivery Planning
- [x] 3.1 Identify the frontend, backend, and data-layer implementation touchpoints needed after approval.
- [x] 3.2 Identify the validation coverage required for homepage readiness, preview readiness, and cold-start provisioning.
- [x] 3.3 Identify the public-reader fidelity touchpoints for dominant reading layout, math-only display, malformed inline-math cleanup, and scholarly multi-column HTML fallback.

## 4. Validation
- [x] 4.1 Run `openspec validate add-community-public-read-experience-foundation --strict --no-interactive`.
- [x] 4.2 Run targeted frontend and backend tests for detail prefetch, cached detail reuse, and non-blocking public detail repair.
- [x] 4.3 Run targeted tests for preview payload reuse and equivalent-preview reader enhancement reuse.
- [x] 4.4 Run targeted tests for reader enhancement lazy loading and intent-time prewarm.
