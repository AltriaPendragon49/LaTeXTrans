## 1. OpenSpec
- [x] 1.1 Add proposal, tasks, and design for `refactor-paper-detail-dual-pane-copilot`
- [x] 1.2 Add delta specs for `community-paper-discovery-ui`, `web-api`, and `web-ui`
- [x] 1.3 Validate with `openspec validate refactor-paper-detail-dual-pane-copilot --strict --no-interactive`

## 2. Reader workspace
- [x] 2.1 Define the dual-pane detail layout and reading-first visual contract
- [x] 2.2 Define paper-scoped copilot persistence and side-panel behavior
- [x] 2.3 Define soft translated-reader upgrades without full page replacement

## 3. Anchoring model
- [x] 3.1 Define stable reader anchor metadata in the API contract
- [x] 3.2 Define citation and action payloads that can target reader anchors
- [x] 3.3 Define scroll, highlight, and same-paper navigation behavior
- [x] 3.4 Ensure URL-hash anchor activation remains reliable with asynchronously rendered preview content

## 4. State management and continuity
- [x] 4.1 Define how the paper detail route keeps the copilot session scoped to the active paper
- [x] 4.2 Define how reader mode changes synchronize with copilot metadata
- [x] 4.3 Define loading, partial-ready, and degraded states for the dual-pane shell

## 5. Paper-detail copilot parity
- [x] 5.1 Upgrade the paper-detail right pane to a true multi-turn streaming conversation surface
- [x] 5.2 Pass conversation history and paper scope through `streamCommunityAgentRun` from paper detail
- [x] 5.3 Capture reader highlight selection and include structured `reader_selection` context in run payloads
- [x] 5.4 Keep citation-anchor scroll/highlight behavior working alongside multi-turn chat
- [x] 5.5 Add and pass TDD coverage for streaming chat + highlight-context injection in paper detail
- [x] 5.6 Validate updated locale keys with `npm run i18n:check`
- [x] 5.7 Keep selected reader passages visibly highlighted while chatting and clear highlights when selection context is dismissed
- [x] 5.8 Keep the paper-detail composer visibly accessible and remove static filler blocks that obscure the chat entry point
