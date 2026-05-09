## Context
The current application authenticates users by verifying credentials against the NiuTrans login API, then issues its own local session token. The NiuTrans user-info document under `texts/用户额度积分` defines a separate `GET /NiuTransConsole/user/getUserInfo` endpoint that requires the upstream login `token` and `userId`, and returns account fields including `unusedNumIntegral`.

The product now needs two different quota concepts in the same lower-left account area:

- `LaTeX 翻译`: the application's own daily quota, currently 3 items per authenticated user per UTC+8 natural day.
- `PDF 直译`: NiuTrans account credits, displayed as returned积分 from `unusedNumIntegral`.

These concepts are intentionally independent. Starting LaTeX translation consumes only the local daily LaTeX quota. The NiuTrans PDF direct-translation credits are returned and displayed only in this change.

## Goals
- Show the current local daily LaTeX quota as `remaining/limit`.
- Show PDF direct-translation credits as `<unusedNumIntegral>积分`, not as a `3/3` quota.
- Enforce the local quota across ordinary arXiv ID translation, uploaded LaTeX/source-package translation, and batch translation.
- Reject over-quota batch submissions before any task is created or enqueued.
- Keep raw upstream NiuTrans tokens, refresh tokens, API keys, and password-like fields out of frontend responses.

## Non-Goals
- Do not spend, deduct, or enforce NiuTrans `unusedNumIntegral` for LaTeX translation.
- Do not build the PDF direct-translation workflow itself.
- Do not change LLM provider pool quotas, active task quotas, or admin/community curation quotas.
- Do not count source download or file upload alone as translation consumption when no translation work is started.

## Decisions

### Local LaTeX quota model
Add a MySQL-backed daily quota record keyed by local `user_id`, quota date, and quota type. The first quota type for this feature is `latex_translation`.

The service computes quota date with UTC+8 natural-day semantics. The default limit is 3 and should be configurable from backend settings so production can adjust without code changes.

Quota reservation must be atomic. For a single translation start, reserve 1 item before creating/enqueuing translation work. For a batch request, reserve the full requested item count in one transaction. If reservation fails, return an explicit quota-exceeded response and do not create or enqueue new work. If task creation fails before work is accepted, roll back or release the reservation. Once the API accepts translation work, later translation failure, compilation failure, or user cancellation does not refund the daily quota.

Existing active-task limits remain separate. A request must pass both the active-task guard and the daily LaTeX quota guard when both apply.

### Translation trigger scope
Count the user-facing LaTeX translation starts from:

- ordinary arXiv ID translation,
- ordinary uploaded LaTeX/source-package translation,
- batch arXiv submissions, one item per arXiv ID,
- batch upload submissions, one item per file.

Admin/community curation, background prewarm, community-agent internal publication flows, and provider-level LLM quota handling are outside this quota unless a future approved change expands the scope.

### NiuTrans balance snapshot
After successful upstream login, call:

- `GET https://niutrans.com/NiuTransConsole/user/getUserInfo`
- headers: `Authorization: <login token>` and `Niutrans-userid: <userId>`

Persist or cache only a safe account-balance snapshot, especially `unusedNumIntegral`, plus fetch status and timestamp. Do not return raw upstream login token, refresh token, `apikey`, nested user `password`, or other secret-like upstream fields to the frontend.

If NiuTrans user-info fetching fails, local login still succeeds. The quota response marks PDF direct credits as unavailable or stale while keeping the local LaTeX quota usable.

### API shape
Expose a quota snapshot through the authenticated auth/session API surface, either embedded in `/api/auth/me` and login responses or through a small authenticated quota endpoint reused by both login bootstrap and frontend refresh.

The response shape should separate local quota from NiuTrans display credits, for example:

```json
{
  "latex_translation": {
    "limit": 3,
    "used": 0,
    "remaining": 3,
    "quota_date": "2026-05-07",
    "reset_timezone": "Asia/Shanghai"
  },
  "pdf_direct": {
    "unused_integral": 60,
    "source": "niutrans",
    "status": "available",
    "fetched_at": "2026-05-07T00:00:00Z"
  }
}
```

Client-visible error responses for quota exhaustion should be machine-readable and include current limit, used, remaining, requested item count, and reset date.

### UI placement
Use the existing lower-left account/settings/logo component rather than adding a separate floating widget. The component can become taller to fit two quota cells under or near the account/settings controls.

The visual layout is:

- left: `LaTeX 翻译：remaining/limit`,
- right: `PDF 直译：unusedNumIntegral积分`.

All new visible copy must use the frontend i18n resources. Collapsed and mobile shell states must remain non-overlapping; compact states may use abbreviated display, tooltip, or a sheet if the desktop account block is not visible.

## Risks / Trade-offs
- NiuTrans balance can be stale if only fetched at login. The UI must tolerate stale/unavailable status and the implementation can add a manual or session-refresh endpoint if secure token handling is available.
- Quota reservation must happen before task creation but be released on pre-acceptance failure; this needs focused tests to avoid charging users for rejected requests.
- Existing guest-capable backend paths and newer frontend login-gating specs are not fully aligned. This change scopes local daily quota to authenticated users and should not silently introduce anonymous per-IP accounting.

## Migration Plan
1. Add MySQL tables/columns for daily LaTeX quota records and safe NiuTrans balance snapshots.
2. Backfill is not required; users start with `0/3` used for the current UTC+8 day.
3. Keep migration idempotent and update `backend/file.md` if new backend production files are added.
4. Roll back by disabling quota enforcement through config only if needed, while preserving read-only snapshot fields.
