## 1. Spec and Cleanup
- [x] 1.1 Add proposal, design, and delta specs for deferred structural fallback.
- [ ] 1.2 Remove the empty `eliminate-silent-enhanced-fallback` placeholder change directory.

## 2. Pipeline Changes
- [x] 2.1 Add the new post-compile fallback config and capture it in task metadata.
- [x] 2.2 Change `TranslatorAgent` structural fallback handling to record pending candidates without source rollback.
- [x] 2.3 Change `langgraph_orchestrator` to attempt compile before deterministic downgrade and allow one compile retry.
- [x] 2.4 Keep deterministic downgrade input bound to target-language `trans_content`.

## 3. Tests
- [x] 3.1 Update unit tests that currently assert `fallback_source_compile_first`.
- [x] 3.2 Replace skipped final-language fallback tests with real post-compile fallback coverage.
- [x] 3.3 Add compile-success, compile-failure, and single-retry regression tests.

## 4. Validation
- [x] 4.1 Run `openspec validate defer-structural-fallback-until-compile-failure --strict --no-interactive`.
- [x] 4.2 Run the targeted fallback-related unit tests.
