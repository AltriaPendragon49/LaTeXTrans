"""Hot Ranking Service - orchestrates the daily hot ranking pipeline.

Steps:
  1. rank_ranking_cycle  - rank candidates via the ranking engine and write artifacts
  2. filter_existing_papers - query DB to find already-existing papers
  3. auto_intake         - auto-intake top candidates via admin curation
  4. generate_daily_summary - write daily intake artifacts
  5. run_full_cycle      - run all of the above in sequence
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.services.ranking.engine import rank_candidates
from backend.app.services.ranking.schemas import (
    DailyIntakeSummary,
    RankedCandidate,
    RankResult,
    ScoreBreakdown,
    SourceEvidence,
)
from backend.app.services.ranking.artifact_writer import (
    utc_now_iso,
    write_daily_intake_artifacts,
    write_window_artifacts,
)
from backend.app.core.timezone_utils import get_cst_now

logger = logging.getLogger(__name__)

# ── Demo / Synthetic data generators ────────────────────────────────────

_DEMO_ARXIV_IDS = [
    "2501.12345",
    "2502.23456",
    "2503.34567",
    "2504.45678",
    "2505.56789",
    "2501.09876",
    "2502.98765",
    "2503.87654",
    "2504.76543",
    "2505.65432",
    "2401.11111",
    "2402.22222",
    "2403.33333",
    "2404.44444",
    "2405.55555",
    "2406.66666",
    "2407.77777",
    "2408.88888",
    "2409.99999",
    "2410.00000",
    "2311.13579",
    "2312.24680",
    "2301.11223",
    "2302.33445",
    "2303.55667",
]


def _pub_date_from_arxiv_id(arxiv_id: str) -> str:
    """Infer an ISO publication date from an arXiv ID like 2501.12345 → 2025-01-15T00:00:00Z."""
    parts = arxiv_id.split(".")
    if len(parts) >= 2 and len(parts[0]) == 4:
        yy = int(parts[0][:2])
        mm = int(parts[0][2:])
        year = 2000 + yy
        if 1 <= mm <= 12:
            return f"{year:04d}-{mm:02d}-15T00:00:00Z"
    return "2025-01-15T00:00:00Z"


def _generate_demo_candidates(window: str = "30d") -> list[dict]:
    """Generate synthetic candidate data for the ranking engine.

    Used as a fallback when source adapters are unavailable.
    Publication dates are spread across recent days so they survive window filtering.
    """
    from random import Random

    rng = Random(42)
    now = datetime.now(timezone.utc)
    candidates: list[dict] = []
    for idx, arxiv_id in enumerate(_DEMO_ARXIV_IDS):
        # Spread candidates across the last 60 days so every window has some data
        days_ago = rng.uniform(0, 60)
        pub_dt = now - timedelta(days=days_ago)
        pub_date = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_attention = rng.uniform(0, 500)
        raw_authority = rng.uniform(0, 300)
        raw_implementation = rng.uniform(0, 200)
        raw_local = rng.uniform(0, 100)

        candidates.append({
            "arxiv_id": arxiv_id,
            "title": f"Demo Paper {idx + 1}: Advances in Machine Learning",
            "authors": ["Author A", "Author B"],
            "categories": ["cs.LG", "cs.AI"],
            "publication_date": pub_date,
            "raw_attention": raw_attention,
            "raw_authority": raw_authority,
            "raw_implementation": raw_implementation,
            "raw_local": raw_local,
        })
    return candidates


# ── Service class ───────────────────────────────────────────────────────


class HotRankingService:
    """Orchestrates the hot ranking pipeline: rank → filter → intake → summarize."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._intaken_in_run: set[str] = set()  # in-memory dedup

    # ── Helpers ──────────────────────────────────────────────────────

    def _get_arxiv_id_dir(self) -> Path:
        """Resolve the base output directory for hot ranking artifacts."""
        raw = getattr(self.settings, "hot_ranking_arxiv_id_dir", "") or ""
        if raw:
            return Path(raw)
        # Default: backend/arxiv_id/hot_ranked
        return Path(__file__).resolve().parent.parent.parent / "arxiv_id" / "hot_ranked"

    def _exported_at(self) -> str:
        """Return the current UTC timestamp as an ISO string."""
        return utc_now_iso()

    # ── Step 1: Ranking ──────────────────────────────────────────────

    async def run_ranking_cycle(self, window: str | None = None) -> RankResult:
        """Run the ranking engine and write window artifacts.

        1. Try to enrich candidates via source adapters (fail-soft).
        2. If source adapters fail, use demo/synthetic data.
        3. Call engine.rank_candidates().
        4. Write window artifacts.
        5. Return RankResult.
        """
        active_window = window or getattr(self.settings, "hot_ranking_auto_intake_default_window", "3d") or "3d"
        exported_at = self._exported_at()
        raw_candidates: list[dict] = []

        # --- Try live source adapters ---
        try:
            from backend.app.services.ranking.source_adapters import collect_candidates_from_sources

            # Collect real candidates from alphaXiv hot feed + all source adapters
            source_candidates = await collect_candidates_from_sources(limit=200)
            if source_candidates:
                raw_candidates = source_candidates
                logger.info(
                    "Hot ranking: collected %d candidates from live source adapters",
                    len(raw_candidates),
                )
        except Exception as exc:
            logger.warning(
                "Hot ranking: source adapters failed, falling back to demo data: %s", exc
            )

        # --- Fall back to demo data ---
        if not raw_candidates:
            logger.info("Hot ranking: using demo/synthetic candidate data")
            raw_candidates = _generate_demo_candidates(window=active_window)

        # --- Rank ---
        ranked = rank_candidates(raw_candidates, window=active_window)

        # --- Write artifacts ---
        base_dir = self._get_arxiv_id_dir()
        try:
            paths = write_window_artifacts(ranked, window=active_window, base_dir=base_dir, exported_at=exported_at)
            logger.info(
                "Hot ranking: wrote %d candidates to %s and %s",
                len(ranked),
                paths["json"],
                paths["md"],
            )
        except Exception as exc:
            logger.error("Hot ranking: failed to write window artifacts: %s", exc)

        return RankResult(
            window=active_window,
            candidates=ranked,
            exported_at=exported_at,
            total_count=len(ranked),
        )

    # ── Step 2: Filter existing papers ───────────────────────────────

    async def filter_existing_papers(
        self, candidates: list[RankedCandidate]
    ) -> tuple[list[RankedCandidate], list[dict]]:
        """Query DB to find already-existing papers.

        For each candidate, check:
        - get_paper_by_arxiv_id() → if found, paper exists
        - list_curation_jobs_for_arxiv_id() → if active job exists, skip

        Returns: (new_candidates, skipped_info_list)

        NOTE: Uses try/except for DB access. If DB is unavailable, logs a warning
        and returns all candidates as new with an empty skipped list.
        """
        new_candidates: list[RankedCandidate] = []
        skipped_info: list[dict] = []

        try:
            from backend.app.services.paper_service import get_community_paper_repository

            repository = get_community_paper_repository()
        except Exception as exc:
            logger.warning(
                "Hot ranking: cannot access paper repository, skipping DB filter: %s", exc
            )
            return list(candidates), []

        for candidate in candidates:
            try:
                # Check if paper already exists in DB
                paper_row = await asyncio.to_thread(
                    repository.get_paper_by_arxiv_id, candidate.arxiv_id
                )
                if paper_row is not None:
                    skipped_info.append({
                        "arxiv_id": candidate.arxiv_id,
                        "reason": "already_in_library",
                        "paper_id": paper_row.get("id", ""),
                    })
                    continue

                # Check if there is an active curation job
                curation_jobs = await asyncio.to_thread(
                    repository.list_curation_jobs_for_arxiv_id, candidate.arxiv_id
                )
                active_statuses = {"queued", "processing", "translating", "publishing", "pending"}
                has_active_job = any(
                    job.get("status", "").lower() in active_statuses
                    for job in (curation_jobs or [])
                )
                if has_active_job:
                    skipped_info.append({
                        "arxiv_id": candidate.arxiv_id,
                        "reason": "active_curation_job_exists",
                    })
                    continue

                new_candidates.append(candidate)

            except Exception as exc:
                logger.warning(
                    "Hot ranking: DB check failed for %s, treating as new: %s",
                    candidate.arxiv_id,
                    exc,
                )
                new_candidates.append(candidate)

        logger.info(
            "Hot ranking: %d new, %d skipped (already existing)",
            len(new_candidates),
            len(skipped_info),
        )
        return new_candidates, skipped_info

    # ── Steps 3-4: Auto-intake ───────────────────────────────────────

    async def auto_intake(
        self, candidates: list[RankedCandidate]
    ) -> dict[str, Any]:
        """Auto-intake top candidates via admin curation.

        1. Filter by min_score from settings.
        2. Take top_n from settings.
        3. For each candidate:
           a. Check self._intaken_in_run (in-memory dedup).
           b. Call import_or_reuse_paper(source="arxiv", arxiv_id=...).
           c. Log the intent to create a curation job.
        4. Return intake result dict.

        Uses late imports to avoid circular dependencies.
        """
        min_score = float(getattr(self.settings, "hot_ranking_auto_intake_min_score", 50.0) or 50.0)
        top_n = int(getattr(self.settings, "hot_ranking_auto_intake_top_n", 20) or 20)

        intaken: list[dict] = []
        skipped: list[dict] = []
        errors: list[dict] = []

        # Filter and sort
        eligible = [c for c in candidates if c.hot_score >= min_score]
        eligible.sort(key=lambda c: -c.hot_score)
        eligible = eligible[:top_n]

        if not eligible:
            logger.info("Hot ranking auto_intake: no candidates above threshold %.1f", min_score)
            return {"intaken": [], "skipped": [], "errors": []}

        # Late imports (avoid circular deps)
        try:
            from backend.app.services.paper_service import (
                _schedule_curation_job,
                import_or_reuse_paper,
            )
            from backend.app.repositories.community_paper_repository import (
                CommunityPaperRepository,
            )
        except ImportError as exc:
            logger.error(
                "Hot ranking: cannot import paper_service functions for auto_intake: %s", exc
            )
            return {
                "intaken": [],
                "skipped": [],
                "errors": [{"arxiv_id": "N/A", "error": f"ImportError: {exc}"}],
            }

        system_user_id = getattr(self.settings, "hot_ranking_system_user_id", "") or ""
        repository = CommunityPaperRepository()

        for candidate in eligible:
            try:
                # In-memory dedup within this run
                if candidate.arxiv_id in self._intaken_in_run:
                    skipped.append({
                        "arxiv_id": candidate.arxiv_id,
                        "reason": "already_intaken_in_this_run",
                    })
                    continue

                self._intaken_in_run.add(candidate.arxiv_id)

                # Import or reuse the paper
                result = await import_or_reuse_paper(
                    source="arxiv",
                    arxiv_id=candidate.arxiv_id,
                )

                paper_id = result.get("paper_id", "")
                reused = result.get("reused", False)
                imported = result.get("imported", False)

                logger.info(
                    "Hot ranking auto_intake: %s paper_id=%s (reused=%s, imported=%s)",
                    candidate.arxiv_id,
                    paper_id,
                    reused,
                    imported,
                )

                # Update hot_score on the paper record
                try:
                    await asyncio.to_thread(
                        repository.update_paper, paper_id, {"hot_score": candidate.hot_score}
                    )
                except Exception as exc:
                    logger.warning(
                        "Hot ranking auto_intake: failed to update hot_score for %s: %s",
                        paper_id, exc,
                    )

                # Create and schedule a curation job for the paper
                created_at = datetime.now(timezone.utc).isoformat()
                batch_id = f"hot-ranking-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
                job_payload = {
                    "job_id": f"curation-job-{uuid4().hex}",
                    "batch_id": batch_id,
                    "paper_id": paper_id,
                    "source_type": "arxiv",
                    "arxiv_id": candidate.arxiv_id,
                    "original_filename": None,
                    "source_path": None,
                    "task_id": None,
                    "source_language": "en",
                    "target_language": "zh",
                    "source_family": "hot_ranking",
                    "hot_score": candidate.hot_score,
                    "score_breakdown": {
                        "attention": candidate.score_breakdown.attention,
                        "authority": candidate.score_breakdown.authority,
                        "implementation": candidate.score_breakdown.implementation,
                        "local": candidate.score_breakdown.local,
                    },
                    "status": "queued",
                    "error": None,
                    "created_by": system_user_id,
                    "created_at": created_at,
                    "updated_at": created_at,
                }
                stored = await asyncio.to_thread(repository.insert_curation_job, job_payload)
                job_id = str(stored.get("job_id") or "")
                if job_id:
                    _schedule_curation_job(job_id)
                    logger.info(
                        "Hot ranking auto_intake: curation job %s scheduled for %s",
                        job_id,
                        candidate.arxiv_id,
                    )
                else:
                    logger.warning(
                        "Hot ranking auto_intake: curation job creation returned empty job_id for %s",
                        candidate.arxiv_id,
                    )

                intaken.append({
                    "arxiv_id": candidate.arxiv_id,
                    "paper_id": paper_id,
                    "title": candidate.title or "",
                    "hot_score": candidate.hot_score,
                    "score_breakdown": {
                        "attention": candidate.score_breakdown.attention,
                        "authority": candidate.score_breakdown.authority,
                        "implementation": candidate.score_breakdown.implementation,
                        "local": candidate.score_breakdown.local,
                    },
                    "selected_reason": candidate.selected_reason,
                    "reused": reused,
                    "imported": imported,
                })

            except Exception as exc:
                logger.error(
                    "Hot ranking auto_intake: failed for %s: %s",
                    candidate.arxiv_id,
                    exc,
                    exc_info=True,
                )
                errors.append({
                    "arxiv_id": candidate.arxiv_id,
                    "error": str(exc),
                })

        logger.info(
            "Hot ranking auto_intake: intaken=%d, skipped=%d, errors=%d",
            len(intaken),
            len(skipped),
            len(errors),
        )
        return {"intaken": intaken, "skipped": skipped, "errors": errors}

    # ── Step 5: Generate daily summary ──────────────────────────────

    async def generate_daily_summary(
        self,
        rank_result: RankResult,
        intake_result: dict,
    ) -> DailyIntakeSummary:
        """Generate daily intake summary.

        Build DailyIntakeSummary dataclass, write artifacts via
        write_daily_intake_artifacts.  Returns the summary.
        """
        now_cst = get_cst_now()
        date_str = now_cst.strftime("%Y-%m-%d")
        exported_at = self._exported_at()

        intaken_papers = intake_result.get("intaken", []) if intake_result else []
        skipped_papers = intake_result.get("skipped", []) if intake_result else []

        total_candidates = len(rank_result.candidates)
        intaken_count = len(intaken_papers)
        below_threshold = sum(
            1 for c in rank_result.candidates
            if c.hot_score < float(getattr(self.settings, "hot_ranking_auto_intake_min_score", 50.0) or 50.0)
        )

        # Count existing papers
        existing_count = total_candidates - intaken_count - below_threshold
        # But also account for those in skipped due to already-existing
        already_existing = len([s for s in skipped_papers if s.get("reason") == "already_in_library"])
        existing_count = max(existing_count, already_existing)

        summary = DailyIntakeSummary(
            date=date_str,
            window=rank_result.window,
            triggered_at=exported_at,
            total_candidates=total_candidates,
            existing_count=existing_count,
            below_threshold_count=below_threshold,
            intaken_count=intaken_count,
            intaken_papers=intaken_papers,
            skipped_papers=skipped_papers,
            quality_gate_failures_from_prior_runs=[],
        )

        # Write artifacts
        base_dir = self._get_arxiv_id_dir()
        try:
            paths = write_daily_intake_artifacts(summary, base_dir)
            logger.info(
                "Hot ranking: wrote daily intake summary to %s and %s",
                paths["json"],
                paths["md"],
            )
        except Exception as exc:
            logger.error("Hot ranking: failed to write daily intake artifacts: %s", exc)

        return summary

    # ── Full cycle ──────────────────────────────────────────────────

    async def run_full_cycle(self) -> dict[str, Any]:
        """Run the complete daily cycle: rank → filter → intake → summarize.

        Returns a dict with summary information for logging/reporting.
        Always writes artifacts even if some steps fail.
        """
        window = (
            getattr(self.settings, "hot_ranking_auto_intake_default_window", "3d")
            or "3d"
        )
        logger.info("Hot ranking daily cycle started for window=%s", window)

        # Step 1: Rank
        try:
            rank_result = await self.run_ranking_cycle(window=window)
        except Exception as exc:
            logger.error("Hot ranking: rank cycle failed: %s", exc, exc_info=True)
            return {"status": "error", "step": "rank", "window": window, "error": str(exc)}

        # Step 2: Filter
        try:
            new_candidates, skipped = await self.filter_existing_papers(rank_result.candidates)
        except Exception as exc:
            logger.error("Hot ranking: filter step failed: %s", exc, exc_info=True)
            new_candidates = rank_result.candidates
            skipped = []

        # Step 3-4: Intake
        auto_intake_enabled = bool(
            getattr(self.settings, "hot_ranking_auto_intake_enabled", True)
        )
        intake_result: dict = {}
        if auto_intake_enabled and new_candidates:
            try:
                intake_result = await self.auto_intake(new_candidates)
            except Exception as exc:
                logger.error("Hot ranking: auto_intake failed: %s", exc, exc_info=True)
                intake_result = {"intaken": [], "skipped": [], "errors": [{"error": str(exc)}]}

        # Step 5: Summarize
        try:
            summary = await self.generate_daily_summary(rank_result, intake_result)
        except Exception as exc:
            logger.error("Hot ranking: summary generation failed: %s", exc, exc_info=True)
            return {
                "status": "partial",
                "window": window,
                "ranked": len(rank_result.candidates),
                "intaken": 0,
                "error": str(exc),
            }

        return {
            "status": "completed",
            "window": window,
            "ranked": len(rank_result.candidates),
            "new_candidates": len(new_candidates),
            "skipped_existing": len(skipped),
            "intaken": summary.intaken_count,
            "date": summary.date,
        }
