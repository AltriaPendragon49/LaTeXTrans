# Tasks: Fix 404 Polling and Task Recovery

1. **Fix Backend Task Recovery Typo**
   - [x] Update `d:\future\antigravity\LaTexTrans\backend\app\services\task_manager.py` to use `settings.outputs_dir` and `settings.uploads_dir`.
   - [x] Ensure `_recover_from_filesystem` and `_infer_paths_from_filesystem` work without throwing `Settings` attribute errors.

2. **Fix Frontend 404 Infinite Polling Loop**
   - [x] In `d:\future\antigravity\LaTexTrans\frontend\src\hooks\use-task-status-sse.ts`, catch 404 responses inside the `startPolling` logic.
   - [x] If a 404 response is caught, call `cleanup()` and invoke a graceful completion or deletion handler instead of trying to poll again.

3. **Enhance Global Concurrency for LLM Requests**
   - [x] Modify `d:\future\antigravity\LaTexTrans\backend\app\services\agents\translator_agent.py` to properly import and utilize `global_llm_semaphore` where necessary.
   - [x] Re-evaluate internal `asyncio.Semaphore(10)` limits if they exceed safe thresholds.

4. **Verify Updates**
   - [x] Start backend server and test task recovery logic.
   - [x] Start frontend dev server, run a mock task, delete it mid-way, and verify the frontend stops polling immediately upon receiving a 404.
