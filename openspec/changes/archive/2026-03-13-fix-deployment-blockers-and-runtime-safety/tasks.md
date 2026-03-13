## 1. Implementation
- [x] 1.1 Create OpenSpec change files and deltas for deployment/runtime safety behavior.
- [x] 1.2 Update `texts/DEPLOYMENT.md` with runtime-only contract, forbidden pattern, systemd example, Nginx loopback proxy, and key-rotation requirement.
- [x] 1.3 Update `Docker/dockerfile` workers default from 4 to 1 and document runtime-state reason.
- [x] 1.4 Patch `backend/app/services/latex/compiler.py` executor selection for container/no-docker safe fallback to HostLatexExecutor.
- [x] 1.5 Fix `backend/app/services/task_manager.py` path field usage to `outputs_dir` / `uploads_dir`.
- [x] 1.6 Enforce frontend API env `VITE_API_BASE_URL` via shared resolver and remove `VITE_API_URL` usage.
- [x] 1.7 Remove frontend `VITE_SUPABASE_SERVICE_ROLE_KEY`; add backend/frontend `.env.example`.
- [x] 1.8 Add `CORS_ORIGINS` env parsing with wildcard rejection in backend config.
- [x] 1.9 Refactor `scripts/analyze_fallback_results.py` to pathlib + CLI args for cross-platform use.

## 2. Validation
- [x] 2.1 Run `openspec validate fix-deployment-blockers-and-runtime-safety --strict --no-interactive`.
- [x] 2.2 Run backend syntax check: `python -m compileall backend/app`.
- [x] 2.3 Run frontend build/type check: `npm --prefix frontend run build`.
- [x] 2.4 Verify frontend build artifacts do not include `localhost:8000` or service-role key strings.
