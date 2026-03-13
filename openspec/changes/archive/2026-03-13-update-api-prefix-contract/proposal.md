# Change: Unify External API Prefix Contract to /api

## Why
Production frontend requests were sent to non-prefixed paths such as `/history`, while backend public endpoints are expected under `/api/*`. This caused 404 errors in deployed environments.

## What Changes
- Define a strict external API namespace contract: all public backend API endpoints are exposed under `/api/*`.
- Align health endpoint contract to `/api/health` for monitoring and frontend/backend integration.
- Clarify frontend URL composition: `VITE_API_BASE_URL` provides only origin/base host, and request paths append `/api/...` at call sites.

## Impact
- Affected specs: `web-api`, `deployment-infra`
- Affected code:
  - `backend/app/main.py`
  - `frontend/src/lib/api.ts`
  - `frontend/src/pages/History.tsx`
  - `frontend/src/pages/Settings.tsx`
  - `frontend/src/hooks/use-task-status-sse.ts`
  - `frontend/src/store/useStore.ts`
  - `frontend/src/pages/Comparisons.tsx`
  - `frontend/src/pages/Processing.tsx`
  - `frontend/src/components/TerminologyTable.tsx`
  - `frontend/.env.development`, `frontend/.env.example`
