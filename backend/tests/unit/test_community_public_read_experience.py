import asyncio
import json
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Previewable paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "raw abstract",
        "abstract_translated": "中文摘要",
        "community_status": "official",
        "trans_status": "completed",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T02:00:00+00:00",
        "community_selected_task_id": "task-1",
        "community_selected_asset_id": "asset-preview",
        "visibility": "public",
        "status": "published",
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
    }
    base.update(overrides)
    return base


def test_list_papers_does_not_fall_back_to_operator_baseline_seed(monkeypatch, tmp_path):
    baseline_path = tmp_path / "community-baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "items": [
                    _paper(
                        id="paper-baseline",
                        title="Operator baseline paper",
                        community_selected_task_id=None,
                        community_selected_asset_id=None,
                    )
                ]
            }
        ),
        encoding="utf-8",
    )

    class _Query:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def neq(self, *_args, **_kwargs):
            return self

        def execute(self):
            return type("_Result", (), {"data": []})()

    class _Client:
        def table(self, _name):
            return _Query()

    monkeypatch.setattr(paper_service.settings, "community_baseline_seed_path", baseline_path)
    monkeypatch.setattr(paper_service, "run_db_blocking", lambda fn, **_kwargs: asyncio.sleep(0, result=fn()))
    monkeypatch.setattr(paper_service, "_fetch_asset_maps_for_papers", lambda _paper_ids: asyncio.sleep(0, result={}))

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result == {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": None,
        "has_more": False,
        "next_offset": None,
        "source_mode": "database",
    }


def test_detail_does_not_resolve_from_operator_baseline_seed(monkeypatch, tmp_path):
    baseline_path = tmp_path / "community-baseline.json"
    baseline_path.write_text(
        json.dumps({"items": [_paper(id="paper-baseline", title="Operator baseline paper")]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "community_baseline_seed_path", baseline_path)
    monkeypatch.setattr(
        paper_service,
        "get_community_paper_repository",
        lambda: type(
            "_UnavailableRepository",
            (),
            {"get_paper_by_id": staticmethod(lambda _paper_id: (_ for _ in ()).throw(RuntimeError("db offline")))},
        )(),
    )

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-baseline"))

    assert excinfo.value.status_code == 404


def test_list_papers_returns_empty_state_when_admin_and_seed_are_unavailable(monkeypatch):
    monkeypatch.setattr(paper_service.settings, "community_baseline_seed_path", None)

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result == {
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": None,
        "has_more": False,
        "next_offset": None,
        "source_mode": "database",
    }


def test_detail_includes_preview_bootstrap_when_reader_is_ready(monkeypatch, tmp_path):
    preview_path = tmp_path / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text("<article><h2>Readable</h2></article>", encoding="utf-8")

    monkeypatch.setattr(paper_service.settings, "base_dir", tmp_path)
    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=_paper()))
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "preview_html": {
                    "id": "asset-preview",
                    "task_id": "task-1",
                    "asset_type": "preview_html",
                    "file_path": "data/community_papers/paper-1/preview/preview.html",
                    "file_name": "preview.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["reader_state"] == "ready"
    assert result["preview"]["asset"]["id"] == "asset-preview"
    assert "Readable" in result["preview"]["html_content"]


def test_detail_marks_preview_as_warming_and_schedules_recovery(monkeypatch):
    scheduled = {"count": 0}

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                trans_status="completed",
                community_selected_task_id="task-translate",
                community_selected_asset_id=None,
            ),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-translate",
                    "asset_type": "translated_pdf",
                    "file_path": "data/community_papers/paper-1/translated/paper.pdf",
                    "file_name": "paper.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )
    monkeypatch.setattr(
        paper_service.asyncio,
        "create_task",
        lambda coro: (scheduled.__setitem__("count", scheduled["count"] + 1), coro.close())[0],
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["reader_state"] == "ready"
    assert result["preview"] is None
    assert result["reader"]["translated"]["kind"] == "translated_pdf"
    assert scheduled["count"] == 1


def test_detail_falls_back_to_source_pdf_when_sanitized_html_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper(trans_status="not_started")),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_sanitized_arxiv_html",
        lambda _arxiv_id: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["reader_state"] == "ready"
    assert result["reader"]["source"]["kind"] == "source_pdf"
    assert result["reader"]["source"]["url"].endswith("/2503.01010.pdf")


def test_preview_route_keeps_unavailable_preview_as_not_found(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_ensure_public_paper",
        lambda _paper_id: asyncio.sleep(0, result=_paper(trans_status="processing")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert excinfo.value.status_code == 404


def test_detail_recovers_translated_preview_even_when_task_failed(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                trans_status="failed",
                community_selected_task_id="task-failed",
                community_selected_asset_id=None,
            ),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "id": "asset-preview-recovered",
                "task_id": "task-failed",
                "asset_type": "preview_html",
                "file_path": "data/community_papers/paper-1/preview/preview.html",
                "file_name": "preview.html",
                "mime_type": "text/html",
                "created_at": "2026-03-20T00:00:00+00:00",
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_build_preview_payload",
        lambda **_kwargs: {
            "paper_id": "paper-1",
            "task_id": "task-failed",
            "asset": {
                "id": "asset-preview-recovered",
                "task_id": "task-failed",
                "asset_type": "preview_html",
                "file_name": "preview.html",
                "mime_type": "text/html",
                "created_at": "2026-03-20T00:00:00+00:00",
            },
            "html_content": "<article><h2>Recovered preview</h2></article>",
            "generated_at": "2026-03-20T00:00:00+00:00",
        },
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["preview"] is not None
    assert "Recovered preview" in result["preview"]["html_content"]
    assert result["reader_state"] == "ready"
    assert result["reader"]["preferred_mode"] == "translated"
    assert result["reader"]["state"] == "translated_ready"
    assert result["reader"]["translated"]["kind"] == "preview_html"
    assert result["experience"]["stage_label"] == "中文版已准备好"


def test_detail_uses_translated_pdf_fallback_when_preview_is_missing(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                trans_status="failed",
                community_selected_task_id="task-failed",
                community_selected_asset_id=None,
            ),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        paper_service,
        "_ensure_translated_pdf_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "id": "asset-pdf-recovered",
                "task_id": "task-failed",
                "asset_type": "translated_pdf",
                "file_path": "data/community_papers/paper-1/translated/paper.pdf",
                "file_name": "paper.pdf",
                "mime_type": "application/pdf",
                "created_at": "2026-03-20T00:00:00+00:00",
            },
        ),
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["preview"] is None
    assert result["reader_state"] == "ready"
    assert result["reader"]["preferred_mode"] == "translated"
    assert result["reader"]["translated"]["kind"] == "translated_pdf"
    assert result["reader"]["translated"]["url"] is not None
    assert result["experience"]["stage_label"] == "中文版已准备好"


def test_detail_prefers_sanitized_source_html_when_available(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper(trans_status="not_started")),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_sanitized_arxiv_html",
        lambda _arxiv_id: asyncio.sleep(
            0,
            result='<article class="paper-body"><h1>Clean HTML</h1><p>Readable section.</p></article>',
        ),
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["reader"]["source"]["kind"] == "source_html"
    assert "Clean HTML" in result["reader"]["source"]["html_content"]


def test_fetch_sanitized_arxiv_html_strips_outer_arxiv_chrome(monkeypatch):
    paper_service._source_html_cache.clear()

    class _Response:
        text = """
        <html>
          <body>
            <nav>site nav</nav>
            <aside>side tools</aside>
            <article class="ltx_document">
              <div>\\WarningFilter latexText page 8 contains only floats</div>
              <h1>Top matter title</h1>
              <div class="ltx_page_navbar">jump links</div>
              <div class="ltx_authors">authors block</div>
              <div class="ltx_abstract"><p>Abstract block.</p></div>
              <figure><img src="figures/demo.png" alt="Figure demo" /></figure>
              <section><h2>Readable section</h2><p>Main body.</p></section>
            </article>
            <footer>site footer</footer>
          </body>
        </html>
        """

        def raise_for_status(self):
            return None

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None):
            return _Response()

    monkeypatch.setattr(paper_service.httpx, "AsyncClient", _AsyncClient)

    result = asyncio.run(paper_service._fetch_sanitized_arxiv_html("2603.14482"))

    assert result is not None
    assert "site nav" not in result
    assert "side tools" not in result
    assert "jump links" not in result
    assert "authors block" in result
    assert "Top matter title" in result
    assert "\\WarningFilter" not in result
    assert "Abstract block." in result
    assert "Readable section" in result
    assert 'src="https://arxiv.org/html/2603.14482/figures/demo.png"' in result
    assert "latextrans-source-article" in result

