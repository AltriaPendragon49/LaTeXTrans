## 1. Spec And Design
- [x] 1.1 Validate the dual-theme change proposal with OpenSpec.
- [x] 1.2 Confirm the community shell keeps the current palette as the default dark mode.

## 2. TDD Guardrails
- [x] 2.1 Add failing frontend tests for the shared theme toggle behavior.
- [x] 2.2 Add failing coverage for layout-level theme control visibility and localization.

## 3. Frontend Implementation
- [x] 3.1 Add the shared theme provider and persistence configuration.
- [x] 3.2 Implement the day/dark toggle control in the shared shell.
- [x] 3.3 Refactor shared shell and community reading surfaces to use theme-aware tokens.
- [x] 3.4 Add locale entries for the new theme control copy.

## 4. Validation
- [x] 4.1 Run targeted frontend tests for the new theme flow.
- [x] 4.2 Run `npm run i18n:check` in `frontend/`.
- [x] 4.3 Run `openspec validate add-dual-theme-daylight-toggle --strict --no-interactive`.
- [x] 4.4 Update this checklist to final truth.
