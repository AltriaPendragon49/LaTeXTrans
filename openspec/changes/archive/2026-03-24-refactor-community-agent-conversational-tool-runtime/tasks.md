## 1. Spec
- [x] 1.1 Add OpenSpec deltas for conversational community agent runtime, API, and UI behavior
- [x] 1.2 Validate the change with `openspec validate refactor-community-agent-conversational-tool-runtime --strict --no-interactive`

## 2. Tests First
- [x] 2.1 Add/update backend unit tests for direct chat replies, tool-calling turns, fallback behavior, and API response fields
- [ ] 2.2 Add/update frontend unit tests for natural chat rendering and removal of structured summary cards
  - Blocked by current project-wide Vitest suite initialization failure (`Cannot read properties of undefined (reading 'config')`) that affects existing frontend tests as well.

## 3. Implementation
- [x] 3.1 Refactor backend community agent orchestration to conversational tool calling
- [x] 3.2 Update API/service/types to expose `message` while keeping compatibility
- [x] 3.3 Update frontend conversation rendering to use the natural assistant message

## 4. Validation
- [x] 4.1 Run targeted backend pytest suites
- [ ] 4.2 Run targeted frontend vitest suites
- [x] 4.3 Run browser acceptance on local backend `9001` and frontend `5173`
