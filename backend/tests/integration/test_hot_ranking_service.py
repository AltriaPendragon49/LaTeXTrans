"""Integration tests for HotRankingService."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the repo root is on sys.path so that backend.* imports work.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
def temp_base_dir():
    """Provide a temporary directory for artifact output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ── Artifact Writer tests ──────────────────────────────────────────────


class TestArtifactWriter:
    """Tests for artifact_writer.py."""

    def test_write_window_artifacts_without_candidates(self, temp_base_dir):
        from backend.app.services.ranking.artifact_writer import write_window_artifacts

        result = write_window_artifacts([], window="30d", base_dir=temp_base_dir)
        assert (temp_base_dir / "30d").exists()
        assert result["json"].exists()
        assert result["md"].exists()

        payload = json.loads(result["json"].read_text(encoding="utf-8"))
        assert payload["source_mode"] == "hot-ranked"
        assert payload["source_family"] == "hot_ranking"
        assert payload["window"] == "30d"
        assert payload["count"] == 0

    def test_write_window_artifacts_with_candidates(self, temp_base_dir):
        from backend.app.services.ranking.artifact_writer import (
            write_window_artifacts,
        )
        from backend.app.services.ranking.schemas import RankedCandidate, ScoreBreakdown

        candidates = []
        for i in range(5):
            candidates.append(
                RankedCandidate(
                    arxiv_id=f"2501.{10000 + i:05d}",
                    window="30d",
                    hot_score=95.0 - i * 5,
                    evidence_score=75.0,
                    age_days=float(i),
                    half_life_days=10.0,
                    time_decay=0.9,
                    score_breakdown=ScoreBreakdown(
                        attention=80.0, authority=60.0, implementation=40.0, local=20.0
                    ),
                    title=f"Test Paper {i}",
                    publication_date="2025-01-15T00:00:00Z",
                    selected_reason="Strong attention signals.",
                    rank=i + 1,
                )
            )

        result = write_window_artifacts(
            candidates, window="7d", base_dir=temp_base_dir
        )
        assert result["json"].exists()
        assert result["md"].exists()

        payload = json.loads(result["json"].read_text(encoding="utf-8"))
        assert payload["count"] == 5
        assert payload["window"] == "7d"
        assert len(payload["records"]) == 5
        assert payload["records"][0]["arxiv_id"] == "2501.10000"
        assert payload["records"][0]["rank"] == 1

    def test_write_daily_intake_artifacts(self, temp_base_dir):
        from backend.app.services.ranking.artifact_writer import write_daily_intake_artifacts
        from backend.app.services.ranking.schemas import DailyIntakeSummary

        summary = DailyIntakeSummary(
            date="2025-06-01",
            window="30d",
            triggered_at="2025-06-01T12:00:00Z",
            total_candidates=50,
            existing_count=10,
            below_threshold_count=15,
            intaken_count=25,
            intaken_papers=[
                {
                    "arxiv_id": "2501.12345",
                    "title": "Cool Paper",
                    "hot_score": 92.0,
                    "score_breakdown": {
                        "attention": 80.0,
                        "authority": 60.0,
                        "implementation": 40.0,
                        "local": 20.0,
                    },
                    "selected_reason": "Strong attention.",
                }
            ],
            skipped_papers=[
                {"arxiv_id": "2401.99999", "reason": "already_in_library"}
            ],
        )

        result = write_daily_intake_artifacts(summary, temp_base_dir)
        assert result["json"].exists()
        assert result["md"].exists()

        payload = json.loads(result["json"].read_text(encoding="utf-8"))
        assert payload["date"] == "2025-06-01"
        assert payload["intaken_count"] == 25
        assert len(payload["intaken_papers"]) == 1
        assert len(payload["skipped_papers"]) == 1


# ── HotRankingService tests ────────────────────────────────────────────


class TestHotRankingService:
    """Tests for hot_ranking_service.py."""

    def test_instantiation(self):
        """Service should instantiate without error."""
        from backend.app.services.hot_ranking_service import HotRankingService

        service = HotRankingService()
        assert service is not None
        assert isinstance(service._intaken_in_run, set)

    @pytest.mark.asyncio
    async def test_run_ranking_cycle_with_demo_data(self, temp_base_dir):
        """run_ranking_cycle should produce results with demo data."""
        from backend.app.services.hot_ranking_service import HotRankingService
        from unittest.mock import patch, PropertyMock

        service = HotRankingService()
        # Override base dir to use temp
        with patch(
            "backend.app.services.ranking.source_adapters.collect_candidates_from_sources",
            side_effect=Exception("network unavailable"),
        ):
            with patch.object(
                service,
                "_get_arxiv_id_dir",
                return_value=temp_base_dir,
            ):
                result = await service.run_ranking_cycle(window="30d")
                assert result.window == "30d"

    @pytest.mark.asyncio
    async def test_run_ranking_cycle_async(self, temp_base_dir):
        """run_ranking_cycle should produce a valid RankResult."""
        from backend.app.services.hot_ranking_service import HotRankingService
        from backend.app.services.ranking.schemas import RankResult
        from unittest.mock import patch, AsyncMock

        service = HotRankingService()

        # Make source collection raise so we exercise the demo fallback.
        # collect_candidates_from_sources is late-imported inside run_ranking_cycle
        # from ranking.source_adapters, so patch there.
        with patch(
            "backend.app.services.ranking.source_adapters.collect_candidates_from_sources",
            side_effect=Exception("network unavailable"),
        ):
            with patch.object(service, "_get_arxiv_id_dir", return_value=temp_base_dir):
                result = await service.run_ranking_cycle(window="30d")
                assert isinstance(result, RankResult)
                assert result.window == "30d"
                assert result.total_count > 0
                assert len(result.candidates) > 0
                # Candidates should be sorted by rank
                for i in range(1, len(result.candidates)):
                    assert result.candidates[i - 1].hot_score >= result.candidates[i].hot_score

    @pytest.mark.asyncio
    async def test_filter_existing_papers_all_new_when_db_unavailable(self, temp_base_dir):
        """When DB is unavailable, filter_existing_papers should return all as new."""
        from backend.app.services.hot_ranking_service import HotRankingService
        from backend.app.services.ranking.schemas import RankedCandidate, ScoreBreakdown

        service = HotRankingService()
        candidates = [
            RankedCandidate(
                arxiv_id=f"2501.{10000 + i:05d}",
                window="30d",
                hot_score=90.0,
                evidence_score=75.0,
                age_days=5.0,
                half_life_days=10.0,
                time_decay=0.9,
                score_breakdown=ScoreBreakdown(
                    attention=80.0, authority=60.0, implementation=40.0, local=20.0
                ),
                title=f"Test Paper {i}",
                rank=i + 1,
            )
            for i in range(5)
        ]

        # Mock the import to fail (simulate DB unavailable at import level).
        # filter_existing_papers does a late import from paper_service, so patch there.
        with patch(
            "backend.app.services.paper_service.get_community_paper_repository",
            side_effect=ImportError("No DB"),
        ):
            new_candidates, skipped = await service.filter_existing_papers(candidates)
            assert len(new_candidates) == 5
            assert len(skipped) == 0

    @pytest.mark.asyncio
    async def test_filter_existing_papers_with_mocked_repo(self, temp_base_dir):
        """filter_existing_papers should correctly filter existing papers."""
        from backend.app.services.hot_ranking_service import HotRankingService
        from backend.app.services.ranking.schemas import RankedCandidate, ScoreBreakdown

        service = HotRankingService()
        candidates = [
            RankedCandidate(
                arxiv_id=f"2501.{10000 + i:05d}",
                window="30d",
                hot_score=90.0,
                evidence_score=75.0,
                age_days=5.0,
                half_life_days=10.0,
                time_decay=0.9,
                score_breakdown=ScoreBreakdown(
                    attention=80.0, authority=60.0, implementation=40.0, local=20.0
                ),
                title=f"Test Paper {i}",
                rank=i + 1,
            )
            for i in range(3)
        ]

        mock_repo = MagicMock()
        # First candidate exists in DB
        mock_repo.get_paper_by_arxiv_id.side_effect = [
            {"id": "paper-1", "arxiv_id": "2501.10000"},  # exists
            None,  # new
            None,  # new
        ]
        mock_repo.list_curation_jobs_for_arxiv_id.return_value = []

        with patch(
            "backend.app.services.paper_service.get_community_paper_repository",
            return_value=mock_repo,
        ):
            new_candidates, skipped = await service.filter_existing_papers(candidates)
            assert len(new_candidates) == 2
            assert len(skipped) == 1
            assert skipped[0]["arxiv_id"] == "2501.10000"
            assert skipped[0]["reason"] == "already_in_library"

    @pytest.mark.asyncio
    async def test_auto_intake_empty_candidates(self):
        """auto_intake with empty list should return empty results."""
        from backend.app.services.hot_ranking_service import HotRankingService

        service = HotRankingService()
        result = await service.auto_intake([])
        assert result["intaken"] == []
        assert result["skipped"] == []
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_auto_intake_below_threshold(self):
        """Candidates below min_score should be skipped."""
        from backend.app.services.hot_ranking_service import HotRankingService
        from backend.app.services.ranking.schemas import RankedCandidate, ScoreBreakdown
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.hot_ranking_auto_intake_min_score = 100.0
        mock_settings.hot_ranking_auto_intake_top_n = 20
        mock_settings.hot_ranking_system_user_id = ""

        service = HotRankingService(settings=mock_settings)
        candidates = [
            RankedCandidate(
                arxiv_id=f"2501.{10000 + i:05d}",
                window="30d",
                hot_score=30.0 + i,
                evidence_score=25.0,
                age_days=5.0,
                half_life_days=10.0,
                time_decay=0.9,
                score_breakdown=ScoreBreakdown(
                    attention=40.0, authority=30.0, implementation=20.0, local=10.0
                ),
                title=f"Low Score Paper {i}",
                rank=i + 1,
            )
            for i in range(3)
        ]
        result = await service.auto_intake(candidates)
        assert result["intaken"] == []
        assert len(result.get("skipped", [])) == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_auto_intake_uses_admin_curation_batch(self):
        """Eligible candidates should go through the existing admin curation path."""
        from backend.app.services.hot_ranking_service import HotRankingService
        from backend.app.services.ranking.schemas import RankedCandidate, ScoreBreakdown
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.hot_ranking_auto_intake_min_score = 50.0
        mock_settings.hot_ranking_auto_intake_top_n = 20
        mock_settings.hot_ranking_system_user_id = "admin-user"

        candidate = RankedCandidate(
            arxiv_id="2501.12345",
            window="30d",
            hot_score=90.0,
            evidence_score=75.0,
            age_days=5.0,
            half_life_days=10.0,
            time_decay=0.9,
            score_breakdown=ScoreBreakdown(
                attention=80.0, authority=60.0, implementation=40.0, local=20.0
            ),
            title="Eligible Paper",
            rank=1,
        )

        async def _submit_batch(**kwargs):
            assert kwargs["arxiv_ids"] == ["2501.12345"]
            assert kwargs["current_user"] == {"id": "admin-user"}
            assert kwargs["schedule_jobs"] is False
            return {
                "items": [
                    {
                        "job_id": "job-1",
                        "paper_id": "paper-1",
                        "arxiv_id": "2501.12345",
                    }
                ]
            }

        mock_repo = MagicMock()
        service = HotRankingService(settings=mock_settings)
        with patch(
            "backend.app.services.paper_service.submit_admin_arxiv_curation_batch",
            side_effect=_submit_batch,
        ), patch(
            "backend.app.services.paper_service.get_community_paper_repository",
            return_value=mock_repo,
        ), patch(
            "backend.app.services.paper_service._schedule_curation_job",
        ) as schedule_job:
            result = await service.auto_intake([candidate])

        mock_repo.update_curation_job.assert_called_once()
        schedule_job.assert_called_once_with("job-1")

        assert result["errors"] == []
        assert result["skipped"] == []
        assert result["intaken"][0]["job_id"] == "job-1"
        assert result["intaken"][0]["paper_id"] == "paper-1"
        assert result["intaken"][0]["hot_score"] == 90.0

    def test_generate_daily_summary(self):
        """generate_daily_summary should produce a valid DailyIntakeSummary."""
        import asyncio
        from backend.app.services.hot_ranking_service import HotRankingService
        from backend.app.services.ranking.schemas import RankedCandidate, RankResult, ScoreBreakdown

        service = HotRankingService()
        candidates = [
            RankedCandidate(
                arxiv_id=f"2501.{10000 + i:05d}",
                window="30d",
                hot_score=90.0 - i * 5,
                evidence_score=75.0,
                age_days=5.0,
                half_life_days=10.0,
                time_decay=0.9,
                score_breakdown=ScoreBreakdown(
                    attention=80.0, authority=60.0, implementation=40.0, local=20.0
                ),
                title=f"Test Paper {i}",
                rank=i + 1,
            )
            for i in range(5)
        ]
        rank_result = RankResult(
            window="30d",
            candidates=candidates,
            exported_at="2025-06-01T12:00:00Z",
            total_count=5,
        )
        intake_result = {
            "intaken": [
                {
                    "arxiv_id": "2501.10000",
                    "title": "Test Paper 0",
                    "hot_score": 90.0,
                    "score_breakdown": {
                        "attention": 80.0,
                        "authority": 60.0,
                        "implementation": 40.0,
                        "local": 20.0,
                    },
                    "selected_reason": "Strong attention.",
                    "paper_id": "paper-1",
                    "reused": False,
                    "imported": True,
                }
            ],
            "skipped": [
                {"arxiv_id": "2501.10001", "reason": "already_in_library"}
            ],
            "errors": [],
        }

        # Use a temp dir for artifact writing
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(
                service, "_get_arxiv_id_dir", return_value=Path(tmpdir)
            ):
                summary = asyncio.run(
                    service.generate_daily_summary(rank_result, intake_result)
                )
                assert summary.date
                assert summary.total_candidates == 5
                assert summary.intaken_count == 1
                assert len(summary.intaken_papers) == 1
                assert len(summary.skipped_papers) == 1
                assert summary.intaken_papers[0]["arxiv_id"] == "2501.10000"

                # Verify artifacts written
                daily_dir = Path(tmpdir) / "daily_intake"
                assert daily_dir.exists()
                md_files = list(daily_dir.glob("*.md"))
                json_files = list(daily_dir.glob("*.json"))
                assert len(md_files) >= 1
                assert len(json_files) >= 1

    @pytest.mark.asyncio
    async def test_run_full_cycle(self, temp_base_dir):
        """run_full_cycle should complete all steps and return summary."""
        from backend.app.services.hot_ranking_service import HotRankingService
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.hot_ranking_auto_intake_enabled = False
        mock_settings.hot_ranking_auto_intake_default_window = "30d"
        mock_settings.hot_ranking_arxiv_id_dir = ""
        mock_settings.hot_ranking_auto_intake_min_score = 50.0
        mock_settings.hot_ranking_auto_intake_top_n = 20

        service = HotRankingService(settings=mock_settings)

        # Make source collection fail so we exercise the demo fallback.
        with patch(
            "backend.app.services.ranking.source_adapters.collect_candidates_from_sources",
            side_effect=Exception("network unavailable"),
        ):
            with patch.object(service, "_get_arxiv_id_dir", return_value=temp_base_dir):
                result = await service.run_full_cycle()
                assert result["status"] == "completed"
                assert result["window"] == "30d"
                assert result["ranked"] > 0
                assert "intaken" in result
                assert "date" in result

                # Verify window artifacts were written
                window_dir = temp_base_dir / "30d"
                assert window_dir.exists()
                assert (window_dir / "latest.json").exists()
                assert (window_dir / "latest.md").exists()
