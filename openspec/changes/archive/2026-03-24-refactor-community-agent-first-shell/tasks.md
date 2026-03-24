## 1. Spec Sync
- [x] 1.1 Record the provider-backed agent baseline in the active change.
- [x] 1.2 Add conversation workspace, history, reader recovery, and tools restoration scope to the active change.

## 2. Conversation Workspace
- [x] 2.0 Add baseline full-flow tests for homepage → conversation → detail routing.
- [x] 2.1 Route homepage submits into a dedicated conversation page.
- [x] 2.2 Persist saved conversations for the current authenticated user and render them in a left-side history list.
- [x] 2.3 Reshape the answer surface to emphasize overview, core points, citations, and next actions.
- [x] 2.4 Remove homepage summary clutter so tracked / official bookkeeping no longer competes with the agent launch surface.

## 3. Agent Tooling
- [x] 3.1 Keep provider-backed reasoning, search, import, and translation bridge as the implementation baseline.
- [x] 3.2 Expose the translation workflow as an agent tool without removing the standalone tool workflow.
- [x] 3.3 Tighten the visible agent timeline / tool feedback.
- [x] 3.4 Rewrite the provider prompt so the real LLM produces paper-native structured answers.
- [x] 3.5 Make the conversation flow behave like a true paper-domain multi-turn chat agent rather than a single-turn launcher.

## 4. Reader Recovery
- [x] 4.1 Prefer sanitized local English HTML, then source PDF, in the reader shell.
- [x] 4.2 Recover translated HTML preview from failed tasks when translated section outputs exist.
- [x] 4.3 Recover translated PDF fallback from failed tasks when PDF artifacts exist.
- [x] 4.4 Fix detail-page reader / experience mapping so compile failure does not imply total translated unavailability.
- [x] 4.5 Refine the homepage, conversation page, and reader shell with an alphaXiv-inspired composition and improved HTML presentation.
- [x] 4.6 Strip additional upstream arXiv chrome from sanitized local English HTML before rendering it in the source reader.
- [x] 4.7 Add an explicit English / Chinese reader-mode switch and ensure English falls back to PDF when HTML is unavailable.
- [x] 4.8 Fix shared-shell sidebar/topbar spacing so the visible sidebar and sticky header never overlap homepage content.

## 5. Legacy Tools Restoration
- [x] 5.1 Restore the old direct translation workflow as the primary tools-hub content.
- [x] 5.2 Remove or demote community-first framing from the standalone translation tool.
- [x] 5.3 Keep the translation workflow callable by the community agent while leaving the standalone dashboard intact.

## 6. Validation
- [x] 6.1 Add or update TDD coverage for conversation routing, saved history, reader recovery, and tools restoration.
- [x] 6.2 Run `openspec validate refactor-community-agent-first-shell --strict --no-interactive`.
- [x] 6.3 Run targeted backend tests, frontend tests, i18n validation, and browser QA.
- [x] 6.4 Start frontend and backend with the project server scripts and complete real browser acceptance.
- [x] 6.5 Verify browser QA against the actively patched backend instance rather than a stale local port.
- [x] 6.6 Re-run final browser acceptance on backend `9001` with frontend `5173` so the verified stack matches `backend/start.bat`.
