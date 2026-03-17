## 1. Spec + tests
- [x] 1.1 Add OpenSpec deltas for history resilience and batch `config_hash` persistence.
- [x] 1.2 Add a backend regression test covering persisted `config_hash` for authenticated task creation.
- [x] 1.3 Add a backend regression test covering batch translation `config_hash` persistence calls.
- [x] 1.4 Add a frontend regression test covering automatic history recovery after a transient fetch failure.

## 2. Implementation
- [x] 2.1 Make authenticated history queries use safe per-call authenticated clients in threaded DB execution.
- [x] 2.2 Make the history page retry recoverable load failures without requiring manual refresh.
- [x] 2.3 Persist `config_hash` for authenticated batch-created tasks, including persistence-retry paths.

## 3. Validation
- [x] 3.1 Run `openspec validate update-history-resilience-and-batch-config-hash --strict --no-interactive`.
- [x] 3.2 Run targeted backend pytest coverage for the new regression tests.
- [x] 3.3 Run targeted frontend vitest coverage for the new regression tests.
