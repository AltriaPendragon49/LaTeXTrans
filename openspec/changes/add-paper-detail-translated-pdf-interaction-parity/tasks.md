## 1. OpenSpec
- [x] 1.1 Confirm decisions for renderer strategy, locator strategy, persistence scope, and rollout scope
- [x] 1.2 Confirm unresolved-locator fallback policy as auto-switch to translated HTML
- [x] 1.3 Confirm first release platform scope as desktop-first
- [ ] 1.4 Add and validate spec deltas for `web-ui` and `web-api`
- [ ] 1.5 Validate with `openspec validate add-paper-detail-translated-pdf-interaction-parity --strict --no-interactive`

## 2. API Contract
- [ ] 2.1 Extend paper-detail response metadata to include embeddable translated-PDF reader URL and locator-ready metadata
- [ ] 2.2 Extend agent run context contract to support optional PDF locator fields in `reader_selection`
- [ ] 2.3 Add fallback contract when locator mapping is missing or unresolved

## 3. Frontend Reader Foundation
- [ ] 3.1 Introduce translated-PDF interactive reader surface (non-iframe path)
- [ ] 3.2 Implement translated-PDF text selection capture and toolbar actions
- [ ] 3.3 Keep selection context visible in copilot pane and preserve Ask AI flow

## 4. Highlight, Notes, and Navigation Parity
- [ ] 4.1 Support translated-PDF highlight creation/removal with stable annotation ids
- [ ] 4.2 Support My Notes list focusing and in-document jump for translated-PDF annotations
- [ ] 4.3 Support citation/hash navigation to translated-PDF locations with graceful fallback
- [ ] 4.4 Deliver items in sections 2-4 within one release gate (no staged external rollout)
- [ ] 4.5 On unresolved translated-PDF locator, auto-switch to translated HTML while preserving conversation state

## 5. Verification
- [ ] 5.1 Add unit/component tests for translated-PDF selection + Ask AI context payload
- [ ] 5.2 Add tests for translated-PDF note/highlight focus and fallback behavior
- [ ] 5.3 Run regression coverage for existing HTML-reader interaction paths
- [ ] 5.4 Verify desktop-first acceptance criteria and mobile fallback behavior
