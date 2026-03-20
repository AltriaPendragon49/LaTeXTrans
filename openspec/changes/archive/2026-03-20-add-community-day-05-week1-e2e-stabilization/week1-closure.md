# Week 1 Closure Record

## Demo Route
1. Open `/translate`.
2. Use the `CommunitySubmitPanel` paper-first intake flow.
3. Submit by either:
   - arXiv import via `POST /api/papers/submit`
   - source upload via `POST /api/papers/submit` multipart
4. Land on `/paper/:paperId`.
5. From the paper detail page:
   - start translation,
   - open processing when the selected task is still active,
   - preview translated HTML when available,
   - request a signed download session for the translated PDF.

## Automated Coverage
- Backend submit semantics:
  - `backend/tests/unit/test_papers_submit_contract.py`
- Backend translation bridge and stale-task protection:
  - `backend/tests/unit/test_papers_translation_bridge.py`
- Backend community list/detail resilience and transient DB retry coverage:
  - `backend/tests/unit/test_papers_list_detail_contract.py`
- Backend task persistence idempotency coverage:
  - `backend/tests/unit/test_batch_config_hash_persistence.py`
- Backend Week 1 happy-path contract:
  - `backend/tests/unit/test_community_week1_main_path.py`
- Backend preview / download / publish bridging:
  - `backend/tests/unit/test_papers_preview_bridge.py`
  - `backend/tests/unit/test_papers_download_bridge.py`
  - `backend/tests/unit/test_papers_library_publish_flow.py`
- Frontend feed state coverage:
  - `frontend/src/pages/CommunityFeed.test.tsx`
- Frontend detail state and action coverage:
  - `frontend/src/pages/PaperDetail.test.tsx`
- Frontend submit-surface coverage:
  - `frontend/src/components/community/CommunitySubmitPanel.test.tsx`
- Frontend preview and processing stability:
  - `frontend/src/components/community/PaperPreviewReader.test.tsx`
  - `frontend/src/pages/Processing.test.tsx`

## Accepted Week 1 Known Issues
- The legacy direct-task workflow remains available under a collapsible compatibility section on `/translate`; it is not removed in Day 5.
- Batch translation remains task-centric and is intentionally out of the paper-first Week 1 demo path.
- The generic detail error state routes the user back to the feed instead of offering an inline retry action.

## Post-Apply Stabilization Notes
- Runtime logs exposed a source-asset reuse regression where syncing a community `source_archive` onto the same destination path deleted the source directory before translation started.
- `backend/app/services/paper_service.py` now treats same-path source copies as a no-op and retries transient `httpx.RemoteProtocolError` failures once for community paper DB reads/writes.
- `backend/app/services/task_manager.py` now treats duplicate `translation_tasks.task_id` inserts as idempotent and refreshes the existing row instead of logging a false hard failure.
- Regression coverage was added for:
  - same-path source asset reuse,
  - transient Supabase disconnect retry on paper listing,
  - duplicate task persistence refresh behavior.

## Manual Caveats
- Backend community tests should be run from the repo root, not `backend/`, to avoid local `.env` loading drift.
- The stable demo path assumes authentication is available before using the new paper-first submit surface.
- arXiv intake may temporarily surface progress on the selected task before the paper settles into `not_started`.
- If Supabase is fully unavailable instead of briefly disconnecting, community list/detail and paper-sync operations still fail fast after the single retry; that remains infrastructure-sensitive rather than a paper-flow logic issue.
