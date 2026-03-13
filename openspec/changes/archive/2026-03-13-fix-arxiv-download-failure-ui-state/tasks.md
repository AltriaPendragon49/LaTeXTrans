## 1. Implementation
- [x] 1.1 Update `pollDownloadProgress` SSE handlers to branch on terminal `status` instead of treating `complete` as unconditional success.
- [x] 1.2 Add a shared failure transition path for download flow to set `status=failed`, preserve backend message, and show error toast.
- [x] 1.3 Keep existing successful path unchanged for `pending + progress=100`.

## 2. Validation
- [x] 2.1 Verify failed arXiv download no longer shows `Source Ready`.
- [x] 2.2 Verify success toast is only shown when terminal status is successful.
- [x] 2.3 Run `openspec validate fix-arxiv-download-failure-ui-state --strict --no-interactive`.
