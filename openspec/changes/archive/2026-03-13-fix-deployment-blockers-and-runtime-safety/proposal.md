# Change: fix-deployment-blockers-and-runtime-safety

## Why
The current deployment path has multiple production blockers: runtime image misuse risk, nested docker execution risk inside runtime containers, multi-worker inconsistency with in-process runtime state, broken task recovery path references, and frontend API/security env issues.

## What Changes
- Enforce runtime-only deployment contract in `texts/DEPLOYMENT.md` with explicit forbidden/allowed patterns.
- Set production default worker count to `1` in runtime container command.
- Harden LaTeX executor selection to avoid nested docker behavior in containers or when docker is unavailable.
- Fix task recovery path fields to use `outputs_dir` and `uploads_dir`.
- Replace frontend API env usage with strict `VITE_API_BASE_URL` and fail-fast behavior when missing.
- Remove frontend service-role env usage and add `.env.example` files.
- Add configurable safe CORS origins via `CORS_ORIGINS`.
- Refactor fallback analysis script to pathlib + CLI args for Linux compatibility.

## Impact
- Affected specs:
  - `deployment-infra`
  - `latex-translation-core`
  - `TaskRuntimeState`
  - `web-ui`
  - `web-api`
- Affected code:
  - `Docker/dockerfile`
  - `backend/app/services/latex/compiler.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/core/config.py`
  - `backend/app/main.py`
  - `frontend/src/**` (API base env enforcement)
  - `texts/DEPLOYMENT.md`
  - `scripts/analyze_fallback_results.py`

## Security Notes
- Frontend service-role exposure was verified in local env setup (`frontend/.env`) before this change.
- Git tracking check result:
  - `backend/.env` is not tracked.
  - `frontend/.env` is not tracked.
  - `backend/.env.example` is tracked.
- This change removes frontend service-role usage and documents mandatory key rotation.
- All previously exposed secrets must be rotated out-of-band immediately.
