## 1. OpenSpec
- [ ] 1.1 Add proposal, tasks, and design for `refactor-paper-detail-dual-pane-copilot`
- [ ] 1.2 Add delta specs for `community-paper-discovery-ui`, `web-api`, and `web-ui`
- [ ] 1.3 Validate with `openspec validate refactor-paper-detail-dual-pane-copilot --strict --no-interactive`

## 2. Reader workspace
- [ ] 2.1 Define the dual-pane detail layout and reading-first visual contract
- [ ] 2.2 Define paper-scoped copilot persistence and side-panel behavior
- [ ] 2.3 Define soft translated-reader upgrades without full page replacement

## 3. Anchoring model
- [ ] 3.1 Define stable reader anchor metadata in the API contract
- [ ] 3.2 Define citation and action payloads that can target reader anchors
- [ ] 3.3 Define scroll, highlight, and same-paper navigation behavior

## 4. State management and continuity
- [ ] 4.1 Define how the paper detail route keeps the copilot session scoped to the active paper
- [ ] 4.2 Define how reader mode changes synchronize with copilot metadata
- [ ] 4.3 Define loading, partial-ready, and degraded states for the dual-pane shell
