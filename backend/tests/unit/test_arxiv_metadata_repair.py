import asyncio

import pytest
import requests

from backend.app.services import paper_service


class _FakeArxivResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_fetch_arxiv_metadata_retries_transient_request_failures(monkeypatch):
    calls: list[str] = []

    def fake_get(*_args, **_kwargs):
        calls.append("attempt")
        if len(calls) < 3:
            raise requests.Timeout("temporary arxiv timeout")
        return _FakeArxivResponse(
            """<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
              <entry>
                <title>Recovered arXiv Metadata</title>
                <summary>Recovered abstract body.</summary>
                <published>2025-01-02T03:04:05Z</published>
                <author><name>Alice Example</name></author>
                <author><name>Bob Example</name></author>
                <category term="cs.LG" />
              </entry>
            </feed>"""
        )

    monkeypatch.setattr(paper_service.requests, "get", fake_get)
    monkeypatch.setattr(paper_service.time, "sleep", lambda _seconds: None)

    metadata = paper_service._fetch_arxiv_metadata_sync("2501.00001")

    assert len(calls) == 3
    assert metadata["title"] == "Recovered arXiv Metadata"
    assert metadata["authors"] == ["Alice Example", "Bob Example"]
    assert metadata["categories"] == ["cs.LG"]
    assert metadata["abstract_raw"] == "Recovered abstract body."
    assert metadata["arxiv_published_at"] == "2025-01-02T03:04:05+00:00"


def test_repair_published_arxiv_metadata_scans_and_hydrates_placeholder_papers(monkeypatch):
    placeholder = {
        "id": "paper-fallback",
        "source": "arxiv",
        "arxiv_id": "2501.00001",
        "title": "arXiv:2501.00001",
        "authors": [],
        "categories": [],
        "abstract_raw": None,
        "arxiv_published_at": None,
        "visibility": "public",
        "status": "published",
        "community_status": "official",
    }
    healthy = {
        **placeholder,
        "id": "paper-healthy",
        "arxiv_id": "2501.00002",
        "title": "Healthy title",
        "authors": ["Alice"],
        "categories": ["cs.AI"],
        "abstract_raw": "Healthy abstract",
        "arxiv_published_at": "2025-01-02T03:04:05+00:00",
    }

    class _FakeRepository:
        def list_published_arxiv_papers_needing_metadata_repair(self, *, limit: int):
            assert limit == 10
            return [dict(placeholder)]

    async def fake_hydrate(paper):
        assert paper["id"] == "paper-fallback"
        return dict(healthy, id=paper["id"], arxiv_id=paper["arxiv_id"])

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeRepository())
    monkeypatch.setattr(paper_service, "_hydrate_arxiv_metadata_if_needed", fake_hydrate)

    result = asyncio.run(paper_service.repair_published_arxiv_metadata(limit=10))

    assert result == {
        "scanned": 1,
        "repaired": 1,
        "unrepaired": 0,
        "failed": 0,
    }
