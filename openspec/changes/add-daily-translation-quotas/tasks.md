## 1. Backend Balance Snapshot
- [x] 1.1 Add NiuTrans user-info endpoint configuration and a safe response parser for `unusedNumIntegral`.
- [x] 1.2 Persist/cache only safe NiuTrans balance fields and fetch metadata; never expose upstream token, refresh token, `apikey`, or password-like fields.
- [x] 1.3 Extend login and session bootstrap responses, or add an authenticated quota endpoint, so the frontend can retrieve both quota snapshots.

## 2. Backend Daily LaTeX Quota
- [x] 2.1 Add an idempotent MySQL migration for daily local quota records keyed by user, quota type, and UTC+8 date.
- [x] 2.2 Add a quota repository/service with atomic reserve, release-on-preacceptance-failure, and snapshot methods.
- [x] 2.3 Add configurable defaults for the daily LaTeX quota limit and reset timezone.
- [x] 2.4 Update `backend/file.md` for any new backend production files or materially changed responsibilities.

## 3. Translation Integration
- [x] 3.1 Enforce one-item quota reservation for ordinary arXiv translation starts.
- [x] 3.2 Enforce one-item quota reservation for ordinary uploaded LaTeX/source-package translation starts.
- [x] 3.3 Enforce batch preflight and atomic reservation by item count before creating/enqueuing batch tasks.
- [x] 3.4 Return stable quota-exceeded API errors with requested count, remaining count, limit, used, and reset date.

## 4. Frontend UI And State
- [x] 4.1 Extend local auth/quota TypeScript types and API helpers.
- [x] 4.2 Update the lower-left account/settings/logo component to show the two quota cells side-by-side.
- [x] 4.3 Add loading, stale/unavailable, collapsed, and mobile-safe states without overlap.
- [x] 4.4 Add i18n keys for all new labels, errors, tooltips, and fallback text.

## 5. Verification
- [x] 5.1 Add backend tests for daily reset, single reserve, over-quota rejection, batch atomic rejection, and release on pre-acceptance failure.
- [x] 5.2 Add auth tests proving NiuTrans user-info secret fields are not returned to the frontend.
- [x] 5.3 Add frontend tests or component coverage for the account quota display and over-quota messaging.
- [x] 5.4 Run backend focused tests for auth/quota/translation routes.
- [x] 5.5 Run frontend typecheck/build or relevant tests plus `npm run i18n:check` in `frontend/`.
- [x] 5.6 Run `openspec validate add-daily-translation-quotas --strict --no-interactive`.
