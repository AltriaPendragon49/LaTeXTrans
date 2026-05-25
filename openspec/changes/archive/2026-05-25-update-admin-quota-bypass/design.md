## Context
The existing local daily LaTeX quota protects ordinary authenticated usage by limiting each user to 3 quota-managed LaTeX translation items per UTC+8 natural day. Admin users also pass through this path today, so frontend/admin translation tests can fail with `DAILY_LATEX_QUOTA_EXCEEDED`.

## Goals / Non-Goals
- Goal: Allow every authenticated user with the resolved `admin` role to bypass the local daily LaTeX translation quota.
- Goal: Preserve the existing quota behavior for non-admin users.
- Goal: Keep batch and single-translation behavior consistent.
- Non-goal: Bypass upstream LLM/provider quotas, account member quotas, queue concurrency, active-task limits, batch-size limits, or NiuTrans PDF direct-translation credits.
- Non-goal: Add per-user quota overrides or a new database table.

## Decisions
- Decision: Use the resolved request/session role list as the authority for admin bypass. A user is exempt when their current user payload includes `admin` in roles or equivalent normalized role data.
- Decision: Apply the bypass before local quota reservation so admin requests do not write or increment `user_daily_quotas` for quota-managed LaTeX translation work.
- Decision: Make quota snapshots explicit for admins by indicating an unlimited or bypassed local LaTeX quota state, while leaving PDF direct-translation credit snapshot behavior unchanged.

## Risks / Trade-offs
- Risk: Hiding local quota for admins could be mistaken for unlimited upstream capacity.
  Mitigation: The spec explicitly limits the bypass to local daily LaTeX quota only.
- Risk: Implementing the bypass separately in several route handlers could drift.
  Mitigation: Prefer a small shared service-level predicate or shared helper used by single and batch routes.

## Migration Plan
No schema migration is required. Existing `user_daily_quotas` rows may remain in place; after deployment, admin requests should ignore them for local LaTeX quota enforcement.
