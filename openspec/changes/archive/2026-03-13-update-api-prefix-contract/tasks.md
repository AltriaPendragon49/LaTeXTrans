## 1. Implementation
- [x] 1.1 Refactor backend FastAPI route registration to expose public endpoints under `/api/*`.
- [x] 1.2 Migrate health endpoint contract from `/health` to `/api/health`.
- [x] 1.3 Update frontend API calls to compose URLs as `${VITE_API_BASE_URL}/api/...`.
- [x] 1.4 Keep authentication headers and CORS behavior unchanged while fixing only path composition.
- [x] 1.5 Normalize env examples to avoid double `/api` prefix in development examples.

## 2. Validation
- [x] 2.1 Verify route registration includes `/api/health` and excludes `/health` from FastAPI handling.
- [x] 2.2 Verify history request path becomes `/api/history?page=1&page_size=10`.
- [x] 2.3 Run OpenSpec strict validation for this change.
