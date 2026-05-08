import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.scripts import backfill_community_source_pdfs_to_cos as backfill


def test_build_candidate_report_uses_source_pdf_cos_key():
    candidate = backfill.SourcePdfBackfillCandidate(
        paper_id="paper-1",
        arxiv_id="2501.12345",
        task_id="task-1",
    )

    item = backfill.candidate_to_report_item(candidate, cos_base_prefix="latextrans-prod")

    assert item["paper_id"] == "paper-1"
    assert item["arxiv_id"] == "2501.12345"
    assert item["source_name"] == "2501.12345.pdf"
    assert item["expected_object_key"] == (
        "latextrans-prod/data/community_papers/paper-1/source_pdf/2501.12345.pdf"
    )


def test_dry_run_report_does_not_execute(monkeypatch):
    candidates = [
        backfill.SourcePdfBackfillCandidate(
            paper_id="paper-1",
            arxiv_id="2501.12345",
            task_id="task-1",
        )
    ]
    executed = {"count": 0}

    def _execute_candidate(_candidate):
        executed["count"] += 1
        raise AssertionError("dry-run must not execute uploads")

    monkeypatch.setattr(backfill, "execute_candidate", _execute_candidate)

    report = backfill.run_backfill(candidates=candidates, execute=False, cos_base_prefix="latextrans-prod")

    assert report["dry_run"] is True
    assert report["summary"]["candidate_count"] == 1
    assert report["summary"]["executed_count"] == 0
    assert executed["count"] == 0
