## 1. Schema And Backend Contracts
- [ ] 1.1 Add persistent schema support for favorite folders, folder-paper favorite relations, and daily de-duplicated paper views while preserving derived counters on `papers`.
- [ ] 1.2 Extend community-paper API and service contracts for favorites workspace reads, folder CRUD, per-paper folder assignment, like toggle, and idempotent view recording.
- [ ] 1.3 Update community-paper list/detail payloads and sort handling so the frontend receives persisted viewer state plus `latest` / `views` / `likes` ordering.

## 2. Frontend Experience
- [ ] 2.1 Add the authenticated favorites sidebar entry plus favorites routes for folder listing and folder-content views.
- [ ] 2.2 Implement a shared favorite picker for homepage cards and paper detail with multi-folder selection, inline folder creation, deferred submit semantics, and explicit success/error feedback.
- [ ] 2.3 Implement feed-card like toggles, favorited/highlighted states, and the updated sort controls using persisted backend data only.

## 3. Verification
- [ ] 3.1 Add or update backend tests for folder constraints, like idempotency, daily view de-duplication, and sort fallback rules.
- [ ] 3.2 Add or update frontend tests for sidebar gating, favorites flows, active-state rendering, and optimistic interaction feedback.
- [ ] 3.3 Update `backend/file.md` for any backend production-file additions or responsibility changes and run OpenSpec plus implementation verification before completion.
