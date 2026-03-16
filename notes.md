# Notes

## Scope
- Exclude the already archived `support-global-ui-language` change and the direct spec updates produced by its archive.
- Focus on staged/unstaged workspace changes that still carry product or engineering behavior needing specification.

## Findings
- Most staged backend/frontend changes map back to the archived global UI language + i18n hardening work and should not be re-specified.
- The only clearly spec-worthy behavioral drift outside that archived scope is compile-phase observability in `backend/app/services/agents/generator_agent.py` and `backend/app/services/latex/structure_guard.py`.
- Current runtime reports `Waiting for compile slot` before `find_main_tex_file()` / `validate_project_structure()`, which makes precompile validation latency look like queue contention.
- `validate_project_structure()` currently runs without a dedicated user/operator-visible phase message or timing telemetry.
- `frontend/coverage/` is generated output noise, not product behavior; it should be cleaned separately rather than modeled in OpenSpec.
- Existing draft `update-compile-queue-reporting` captures part of this idea, but the audit suggests the spec should be anchored around compile-phase observability and explicit precompile validation visibility.

## Deliverables
- New change: `openspec/changes/update-compile-phase-observability/`
- Audit summary: `workspace_unrelated_changes_audit.md`
