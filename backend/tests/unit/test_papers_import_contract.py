from typing import Any, Dict

import asyncio
import httpx
import pytest

from backend.app.main import app
from backend.app.services import paper_service


def _make_client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def test_import_reuses_existing_paper(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_import_paper(*, source: str, arxiv_id: str) -> Dict[str, Any]:
        assert source == "arxiv"
        assert arxiv_id == "2503.01010"
        return {
            "paper_id": "paper-existing",
            "reused": True,
            "imported": False,
            "reader_state": "source_ready",
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.import_or_reuse_paper",
        fake_import_paper,
    )

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/papers/import",
                json={"source": "arxiv", "arxiv_id": "2503.01010"},
            )

    response = asyncio.run(_call())
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "paper_id": "paper-existing",
        "reused": True,
        "imported": False,
        "reader_state": "source_ready",
    }


def test_import_creates_new_paper_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_import_paper(*, source: str, arxiv_id: str) -> Dict[str, Any]:
        return {
            "paper_id": "paper-new",
            "reused": False,
            "imported": True,
            "reader_state": "source_ready",
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.import_or_reuse_paper",
        fake_import_paper,
    )

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/papers/import",
                json={"source": "arxiv", "arxiv_id": "9999.00001"},
            )

    response = asyncio.run(_call())
    assert response.status_code == 200
    data = response.json()
    assert data["paper_id"] == "paper-new"
    assert data["reused"] is False
    assert data["imported"] is True
    assert data["reader_state"] == "source_ready"


def test_import_requires_arxiv_id() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.post("/api/papers/import", json={"source": "arxiv"})

    response = asyncio.run(_call())

    assert response.status_code == 400
    assert response.json()["detail"] == "arxiv_id is required"


def test_import_service_reuses_existing_arxiv_paper(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(arxiv_id: str):
        assert arxiv_id == "2503.01010"
        return {"id": "paper-existing"}

    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", fake_fetch)

    result = asyncio.run(
        paper_service.import_or_reuse_paper(source="arxiv", arxiv_id="2503.01010")
    )

    assert result == {
        "paper_id": "paper-existing",
        "reused": True,
        "imported": False,
        "reader_state": "source_ready",
    }


def test_import_service_creates_new_paper_when_database_lookup_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch(arxiv_id: str):
        assert arxiv_id == "2503.01010"
        return None

    async def fake_submit(**kwargs: Any) -> Dict[str, Any]:
        assert kwargs["arxiv_id"] == "2503.01010"
        return {"paper": {"id": "paper-imported"}}

    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", fake_fetch)
    monkeypatch.setattr(
        paper_service,
        "_load_baseline_seed_rows",
        lambda: [{"id": "paper-seed", "arxiv_id": "2503.01010"}],
    )
    monkeypatch.setattr(paper_service, "submit_arxiv_paper", fake_submit)

    result = asyncio.run(
        paper_service.import_or_reuse_paper(source="arxiv", arxiv_id="2503.01010")
    )

    assert result == {
        "paper_id": "paper-imported",
        "reused": False,
        "imported": True,
        "reader_state": "source_ready",
    }


def test_submit_arxiv_paper_allows_public_import_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_resolve_admission(**kwargs: Any) -> Dict[str, Any]:
        assert kwargs["submitter_context"] == {
            "user_id": None,
            "roles": [],
            "is_admin": False,
        }
        return {
            "community_status": "fallback",
            "admission_result": "created",
            "existing_paper": None,
        }

    async def fake_download_arxiv(*, request: Any, credentials: Any, current_user: Any = None) -> Any:
        assert credentials is None
        assert current_user is None
        assert request.arxiv_id == "2509.09871"
        return type("ArxivResponse", (), {"task_id": "task-2509"})()

    async def fake_fetch_metadata(arxiv_id: str) -> Dict[str, Any]:
        assert arxiv_id == "2509.09871"
        return {
            "title": "Fresh arXiv import",
            "authors": ["Ada Lovelace"],
            "categories": ["cs.AI"],
            "abstract_raw": "Raw abstract",
        }

    async def fake_insert_paper(payload: Dict[str, Any]) -> Dict[str, Any]:
        assert payload["created_by"] is None
        assert payload["arxiv_id"] == "2509.09871"
        return {"id": "paper-public", **payload}

    scheduled: list[Any] = []

    monkeypatch.setattr(paper_service, "resolve_community_admission", fake_resolve_admission)
    monkeypatch.setattr(paper_service.arxiv_route, "download_arxiv", fake_download_arxiv)
    monkeypatch.setattr(paper_service, "_fetch_arxiv_metadata", fake_fetch_metadata)
    monkeypatch.setattr(paper_service, "_insert_paper", fake_insert_paper)
    monkeypatch.setattr(paper_service.asyncio, "create_task", lambda coro: scheduled.append(coro))

    result = asyncio.run(
        paper_service.submit_arxiv_paper(
            arxiv_id="2509.09871",
            credentials=None,
        )
    )

    for coro in scheduled:
        coro.close()

    assert result["paper"]["id"] == "paper-public"
    assert result["paper"]["trans_status"] == "not_started"
    assert result["task"] == {"task_id": "task-2509", "status": "processing"}
    assert result["admission_result"] == "created"
