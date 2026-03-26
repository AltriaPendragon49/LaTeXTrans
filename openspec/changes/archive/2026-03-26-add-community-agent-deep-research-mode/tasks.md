## 1. OpenSpec
- [x] 1.1 Add proposal, tasks, and design for `add-community-agent-deep-research-mode`
- [x] 1.2 Add delta specs for `community-agent-assistant`, `web-api`, `web-ui`, and `community-deep-research`
- [x] 1.3 Validate with `openspec validate add-community-agent-deep-research-mode --strict --no-interactive`

## 2. Research-mode behavior
- [x] 2.1 Define the explicit deep research mode entry contract
- [x] 2.2 Define expanded retrieval breadth and evidence collection rules
- [x] 2.3 Define citation-grounded long-form synthesis expectations

## 3. Runtime and API
- [x] 3.1 Define async progress behavior for deep research runs
- [x] 3.2 Define final report payloads and completion states
- [x] 3.3 Define safe limits for retrieval count, context packing, and timeout behavior

## 4. UI and usability
- [x] 4.1 Define how users enter deep research mode
- [x] 4.2 Define how the long-form report is rendered and cited
- [x] 4.3 Define how failures, partial evidence, and degraded runs are surfaced
- [x] 4.4 Ensure progress-only stream states are not accepted as completed deep research output in UI behavior/tests
