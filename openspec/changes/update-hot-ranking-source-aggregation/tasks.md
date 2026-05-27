## 1. Source Policy
- [ ] 1.1 Confirm first-version source eligibility for arXiv, OpenAlex, Semantic Scholar, GitHub, Hugging Face Papers, and alphaXiv.
- [ ] 1.2 Document which sources are core, optional, or excluded from first-version ranking.

## 2. Ranked Artifact Design
- [ ] 2.1 Define the ranked hot artifact schema, including score breakdown, time decay, source evidence, selected reason, and exclusion reasons.
- [ ] 2.2 Define artifact paths for `3d`, `7d`, `30d`, `90d`, and `all` windows.
- [ ] 2.3 Define dedupe and source-priority behavior for already translated or already queued arXiv IDs.

## 3. Ranking Algorithm
- [ ] 3.1 Implement normalized component scores for attention, authority, implementation, and local engagement.
- [ ] 3.2 Implement window-specific exponential time decay and default `30d` homepage semantics.
- [ ] 3.3 Implement the final `hot_score = evidence_score * time_decay` calculation.
- [ ] 3.4 Add tests for interval filtering, missing-source behavior, time decay, score stability, and explainability payloads.

## 4. Admin And Content Pool Integration
- [ ] 4.1 Expose ranked candidates for operator review without automatically starting translation.
- [ ] 4.2 Support batch submission of approved arXiv IDs through the existing admin curation path.
- [ ] 4.3 Track candidate reuse when a paper is already translated, queued, or published.

## 5. Frontend Filter Experience
- [ ] 5.1 Add the filter icon beside the feed sort tabs and render an active date-window pill.
- [ ] 5.2 Add the desktop anchored popover for publication-date window selection.
- [ ] 5.3 Add the mobile bottom-sheet equivalent.
- [ ] 5.4 Wire selected windows into feed requests, loading states, empty states, and cache keys.

## 6. Verification
- [ ] 6.1 Run unit tests for ranking adapters, component scoring, and time decay.
- [ ] 6.2 Run backend feed API tests for `hotWindow` semantics.
- [ ] 6.3 Run frontend tests for filter popover/sheet behavior and active-pill reset.
- [ ] 6.4 Manually inspect generated `latest.md` artifacts for a representative window.

## 7. Scheduled Daily Cron
- [ ] 7.1 Add `hot_ranking_cron_*` and `hot_ranking_auto_intake_*` configuration parameters to `backend/app/core/config.py`.
- [ ] 7.2 Implement `HotRankingService` in `backend/app/services/hot_ranking_service.py` with methods for: running ranking engine, filtering already-existing papers, auto-creating curation jobs, and generating daily intake summaries.
- [ ] 7.3 Implement the daily cron loop `_hot_ranking_daily_cron()` in `backend/app/main.py` following the existing `asyncio.create_task` + `while True` + `asyncio.sleep` pattern.
- [ ] 7.4 Implement Redis-based cron lock to prevent duplicate runs across Worker restarts.
- [ ] 7.5 Compute the next trigger time in CST timezone (default 03:07) so the cron fires once per day regardless of Worker restart timing.
- [ ] 7.6 Wire auto-intake into the existing `import_or_reuse_paper()` → curation job → `_schedule_curation_job()` flow with admin system user identity.

## 8. Daily Intake Summary
- [ ] 8.1 Define the daily intake summary Markdown template (window, date, intake count, per-paper score breakdown, intake reasons, skipped papers with reasons).
- [ ] 8.2 Write paired JSON artifact with full `source_evidence` arrays for machine consumption.
- [ ] 8.3 Write artifacts to `backend/arxiv_id/hot_ranked/daily_intake/YYYY-MM-DD.{md,json}`.
- [ ] 8.4 Ensure summaries include skip reasons: already translated, already queued, below score threshold, quality gate failed (from prior runs).

## 9. Verification (Extended)
- [ ] 9.1 Run unit tests for `HotRankingService` auto-intake orchestration, dedup logic, and summary generation.
- [ ] 9.2 Run integration test: ranking engine produces candidates → auto-intake creates curation jobs → jobs enter translation → daily summary reflects outcomes.
- [ ] 9.3 Verify cron lock prevents concurrent execution.
- [ ] 9.4 Manually inspect a generated daily intake `YYYY-MM-DD.md` artifact for readability and completeness.
- [ ] 9.5 Verify that auto-intaken papers appear in the admin curation UI with correct source family and score metadata.
