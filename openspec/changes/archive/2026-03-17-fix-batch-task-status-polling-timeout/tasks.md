## 1. Implementation
- [x] 1.1 Remove the fixed batch polling cutoff that can leave active tasks stale.
- [x] 1.2 Stop batch polling only on terminal task state or component unmount.
- [x] 1.3 Guard against duplicate pollers for the same batch task.

## 2. Validation
- [x] 2.1 Verify the frontend still builds successfully after the polling change.
- [x] 2.2 Add a focused `BatchTranslation` regression test covering StrictMode lifecycle replay and terminal status polling.
