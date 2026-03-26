# Change: Add community agent content pool foundation

## Why
- The current community flow still relies too heavily on on-demand import and translation when the agent encounters a new paper, which adds latency exactly when the user expects an immediate high-quality answer.
- We need to decouple “finding and warming high-value papers” from “serving the current conversation” so the system can turn more requests into direct hits on precomputed translated evidence.
- A dedicated content-pool foundation gives later agent and reader experiences a reusable source of prewarmed abstracts, previews, and translated reading assets.

## What Changes
- Add a background content-pool pipeline that continuously discovers, admits, and prewarms selected arXiv/community papers before users ask for them.
- Define how the content pool reuses canonical community paper records, generates translated-ready artifacts, and promotes searchable translated evidence.
- Define rate control, idempotency, observability, and failure-containment rules for the prewarm pipeline.
- Teach the community agent and read experience to prefer prewarmed translated evidence when it already exists, while preserving on-demand import as the fallback path.

## Impact
- Affected specs:
  - `community-paper-intake-api`
  - `community-public-read-experience`
  - `community-agent-assistant`
  - new capability `community-content-pool-foundation`
- Affected backend:
  - community paper intake/import pipeline
  - translation task orchestration and preview generation handoff
  - internal search/read models used by the community agent
- Follow-up changes required later:
  - hot-feed ranking and editorial source tuning
  - dual-pane reading workspace
  - deep research mode
