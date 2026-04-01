# Change: Add paper-detail translated-PDF interaction parity

## Why
- The paper detail page already supports rich HTML-reader interactions (selection highlight, notes, Ask AI, citation/location jumps), but translated PDF mode currently cannot provide equivalent interaction quality.
- Product direction requires that all key reader operations available in paper-detail HTML mode become available (or explicitly degraded with user-visible fallback) in translated PDF mode.
- Current translated-PDF delivery and anchor metadata are sufficient for viewing/downloading, but not sufficient for reliable in-PDF selection grounding and navigation.

## What Changes
- Define translated-PDF interactive parity requirements for paper detail, including selection, highlight, notes, Ask AI context, and location navigation behavior.
- Define graceful degradation rules for capabilities that cannot be resolved in-PDF at runtime.
- Extend paper-detail API contracts to provide embeddable translated-PDF metadata and locator/navigation metadata required by the UI.
- Extend community-agent run context contract to support optional PDF locator metadata alongside existing `reader_selection` fields.
- Define a single-release implementation plan that ships translated-PDF interaction parity together.

## Impact
- Affected specs:
  - `web-ui`
  - `web-api`
- Affected frontend:
  - `frontend/src/components/community/PaperDetailWorkspace.tsx`
  - `frontend/src/pages/PaperDetail.tsx`
  - translated PDF reader rendering path and selection/annotation state model
- Affected backend:
  - paper detail payload assembly in `backend/app/services/paper_service.py`
  - paper APIs in `backend/app/api/routes/papers.py`
  - community-agent run context normalization in `backend/app/services/community_agent/orchestrator.py`

## Confirmed Decisions
1. Translated PDF rendering engine: **Option B**
   - Move translated-PDF mode to an interactive PDF renderer (e.g., PDF.js) for full parity capability.
2. Locator mapping strategy: **Option B**
   - Generate/store stable PDF locator mapping with translation assets.
3. Annotation persistence scope: **Option A**
   - Local/session-scoped notes and highlights in the first iteration.
4. Delivery scope: **Option B**
   - Full translated-PDF interaction parity in one release.
5. Unresolved locator fallback UX: **Switch**
   - Automatically switch to translated HTML mode when a translated-PDF locator cannot be resolved.
6. First-release platform scope: **Desktop-first**
   - Desktop reaches full translated-PDF parity in the first release; mobile keeps a safe fallback experience.

## Remaining Product Choices
- None
