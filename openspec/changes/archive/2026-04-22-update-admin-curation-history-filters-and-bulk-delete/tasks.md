## 1. Backend filter semantics and delete API
- [x] 1.1 Normalize the history filter contract so `all` behaves as unfiltered and `processing` includes `processing`, `translating`, and `publishing`.
- [x] 1.2 Add a batch delete API that accepts selected admin curation job ids and reuses the existing hard-delete behavior per job.
- [x] 1.3 Add backend tests for filter normalization, grouped processing semantics, and partial-success batch delete responses.

## 2. Frontend history management
- [x] 2.1 Update the admin history page so every visible filter option maps to the intended backend semantics and reloads correctly.
- [x] 2.2 Add row selection, current-result select-all, selected-count feedback, and batch delete affordances on the history page.
- [x] 2.3 Route all new UI copy through locale keys and add frontend tests for filters and batch delete interactions.

## 3. Verification and deployment
- [x] 3.1 Run focused backend and frontend test suites covering the history page and admin curation APIs.
- [x] 3.2 Run `openspec validate update-admin-curation-history-filters-and-bulk-delete --strict --no-interactive`.
- [x] 3.3 Deploy the fix, verify history filters on the server, and exercise batch delete against real selected records.
