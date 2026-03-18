## 1. Start Gate
- [x] 1.1 Mark Day 04B as `In Progress` in `texts/社区打造十天OpenSpec执行索引.md`.
- [x] 1.2 Update the 2-week execution plan so Day 04B is explicit between Day 4 and Day 5.

## 2. Backend TDD
- [x] 2.1 Add failing tests for auto-publishing completed translation tasks into a community paper.
- [x] 2.2 Add failing tests for community library asset copying with relative stored paths.
- [x] 2.3 Add failing tests for preview/download path resolution from relative community asset paths.
- [x] 2.4 Add a failing test that normal `/translate/{task_id}` schedules a community publish watch for authenticated users.
- [x] 2.5 Implement community library storage config and relative path helpers.
- [x] 2.6 Implement community paper publish/reuse logic for completed tasks.
- [x] 2.7 Refactor paper asset sync to copy `source_archive`, `translated_pdf`, and `preview_html` into the community library.
- [x] 2.8 Wire the publish watch into the normal translation start path.

## 3. Validation And Sync
- [x] 3.1 Run `pytest backend/tests/unit/test_papers_translation_bridge.py -q`.
- [x] 3.2 Run `pytest backend/tests/unit/test_papers_download_bridge.py -q`.
- [x] 3.3 Run `pytest backend/tests/unit/test_paper_preview_service.py -q`.
- [x] 3.4 Run the new Day 04B backend tests.
- [x] 3.5 Run `openspec validate add-community-day-04b-paper-library-storage-and-publish-flow --strict --no-interactive`.
- [x] 3.6 Mark this task list complete and update Day 04B to `Applied`.
