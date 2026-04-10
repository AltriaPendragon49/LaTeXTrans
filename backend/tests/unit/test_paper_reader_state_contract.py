import asyncio
import base64
import json
from typing import Any, Dict

import httpx

from backend.app.core.auth import optional_current_user
from backend.app.main import app
from backend.app.services import paper_service


def _make_client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def test_paper_detail_includes_reader_and_experience_blocks(monkeypatch) -> None:
    async def fake_get_detail(
        *,
        paper_id: str,
        viewer_user_id: str | None = None,
        fast_path: bool = False,
    ) -> Dict[str, Any]:
        assert paper_id == "paper-1"
        assert viewer_user_id is None
        assert fast_path is True
        return {
            "paper": {
                "id": "paper-1",
                "source": "arxiv",
                "arxiv_id": "2503.01010",
                "title": "Test Paper",
                "authors": [],
                "categories": [],
                "abstract_raw": None,
                "abstract_translated": None,
                "community_status": "official",
                "trans_status": "processing",
                "created_at": "2026-03-18T00:00:00Z",
                "official_published_at": None,
                "community_selected_task_id": None,
                "community_selected_asset_id": None,
                "visibility": "public",
                "status": None,
                "like_count": 0,
                "favorite_count": 0,
                "comment_count": 0,
                "view_count": 0,
                "download_count": 0,
                "latest_asset": None,
                "assets": {},
                "viewer_state": {"liked": False, "favorited": False},
            },
            "preview": None,
            "reader_state": "warming",
            "reader": {
                "preferred_mode": "source",
                "available_modes": ["source"],
                "source": {
                    "kind": "external_arxiv_html",
                    "url": "https://arxiv.org/html/2503.01010",
                },
                "translated": None,
                "state": "warming",
            },
            "experience": {
                "stage_label": "正在生成中文版本",
                "can_leave_hint": "你可以先阅读，完成后会自动更�?,
                "failure_type": None,
            },
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.get_community_paper_detail",
        fake_get_detail,
    )

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/paper-1")

    response = asyncio.run(_call())

    assert response.status_code == 200
    data = response.json()
    assert data["paper"]["id"] == "paper-1"
    assert data["reader"]["state"] == "warming"
    assert data["reader"]["preferred_mode"] == "source"
    assert data["experience"]["stage_label"] == "正在生成中文版本"
    assert data["experience"]["can_leave_hint"] == "你可以先阅读，完成后会自动更�?


def test_route_preserves_service_reader_payload(monkeypatch) -> None:
    async def fake_get_detail(
        *,
        paper_id: str,
        viewer_user_id: str | None = None,
        fast_path: bool = False,
    ) -> Dict[str, Any]:
        assert paper_id == "paper-2"
        return {
            "paper": {
                "id": "paper-2",
                "source": "arxiv",
                "arxiv_id": "2503.12345",
                "title": "Recovered Paper",
                "authors": [],
                "categories": [],
                "abstract_raw": "raw",
                "abstract_translated": "zh",
                "community_status": "official",
                "trans_status": "failed",
                "created_at": "2026-03-18T00:00:00Z",
                "official_published_at": None,
                "community_selected_task_id": "task-failed",
                "community_selected_asset_id": None,
                "visibility": "public",
                "status": None,
                "like_count": 0,
                "favorite_count": 0,
                "comment_count": 0,
                "view_count": 0,
                "download_count": 0,
                "latest_asset": None,
                "assets": {},
                "viewer_state": {"liked": False, "favorited": False},
            },
            "preview": None,
            "reader_state": "ready",
            "reader": {
                "preferred_mode": "translated",
                "available_modes": ["source", "translated"],
                "source": {
                    "kind": "external_arxiv_html",
                    "url": "https://arxiv.org/html/2503.12345",
                },
                "translated": {
                    "kind": "translated_pdf",
                    "url": "/api/papers/paper-2/download",
                },
                "state": "translated_ready",
            },
            "experience": {
                "stage_label": "中文版已准备�?,
                "can_leave_hint": None,
                "failure_type": None,
            },
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.get_community_paper_detail",
        fake_get_detail,
    )

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/paper-2")

    response = asyncio.run(_call())

    assert response.status_code == 200
    data = response.json()
    assert data["reader"]["preferred_mode"] == "translated"
    assert data["reader"]["translated"]["kind"] == "translated_pdf"
    assert data["experience"]["stage_label"] == "中文版已准备�?


def test_paper_detail_ignores_forged_viewer_sub_claim(monkeypatch) -> None:
    async def fake_get_detail(
        *,
        paper_id: str,
        viewer_user_id: str | None = None,
        fast_path: bool = False,
    ) -> Dict[str, Any]:
        assert paper_id == "paper-forged"
        assert viewer_user_id is None
        assert fast_path is True
        return {
            "paper": {
                "id": "paper-forged",
                "source": "arxiv",
                "arxiv_id": "2503.77777",
                "title": "Forged viewer state",
                "authors": [],
                "categories": [],
                "abstract_raw": None,
                "abstract_translated": None,
                "community_status": "official",
                "trans_status": "processing",
                "created_at": "2026-03-18T00:00:00Z",
                "official_published_at": None,
                "community_selected_task_id": None,
                "community_selected_asset_id": None,
                "visibility": "public",
                "status": None,
                "like_count": 0,
                "favorite_count": 0,
                "comment_count": 0,
                "view_count": 0,
                "download_count": 0,
                "latest_asset": None,
                "assets": {},
                "viewer_state": {"liked": False, "favorited": False},
            },
            "preview": None,
            "reader_state": "warming",
            "reader": {
                "preferred_mode": "source",
                "available_modes": ["source"],
                "source": None,
                "translated": None,
                "state": "warming",
            },
            "experience": {
                "stage_label": "warming",
                "can_leave_hint": None,
                "failure_type": None,
            },
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.get_community_paper_detail",
        fake_get_detail,
    )

    forged_payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "usr-forged"}).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    forged_token = f"header.{forged_payload}.signature"

    async def _call():
        async with _make_client() as client:
            return await client.get(
                "/api/papers/paper-forged",
                headers={"Authorization": f"Bearer {forged_token}"},
            )

    response = asyncio.run(_call())

    assert response.status_code == 200


def test_paper_detail_uses_verified_current_user_for_viewer_state(monkeypatch) -> None:
    async def fake_optional_current_user():
        return {"id": "usr-verified", "roles": ["user"]}

    async def fake_get_detail(
        *,
        paper_id: str,
        viewer_user_id: str | None = None,
        fast_path: bool = False,
    ) -> Dict[str, Any]:
        assert paper_id == "paper-verified"
        assert viewer_user_id == "usr-verified"
        assert fast_path is True
        return {
            "paper": {
                "id": "paper-verified",
                "source": "arxiv",
                "arxiv_id": "2503.88888",
                "title": "Verified viewer state",
                "authors": [],
                "categories": [],
                "abstract_raw": None,
                "abstract_translated": None,
                "community_status": "official",
                "trans_status": "completed",
                "created_at": "2026-03-18T00:00:00Z",
                "official_published_at": None,
                "community_selected_task_id": None,
                "community_selected_asset_id": None,
                "visibility": "public",
                "status": None,
                "like_count": 0,
                "favorite_count": 0,
                "comment_count": 0,
                "view_count": 0,
                "download_count": 0,
                "latest_asset": None,
                "assets": {},
                "viewer_state": {"liked": True, "favorited": False},
            },
            "preview": None,
            "reader_state": "ready",
            "reader": {
                "preferred_mode": "translated",
                "available_modes": ["translated"],
                "source": None,
                "translated": None,
                "state": "ready",
            },
            "experience": {
                "stage_label": "ready",
                "can_leave_hint": None,
                "failure_type": None,
            },
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.get_community_paper_detail",
        fake_get_detail,
    )
    app.dependency_overrides[optional_current_user] = fake_optional_current_user

    try:
        async def _call():
            async with _make_client() as client:
                return await client.get("/api/papers/paper-verified")

        response = asyncio.run(_call())
    finally:
        app.dependency_overrides.pop(optional_current_user, None)

    assert response.status_code == 200


def test_current_reader_version_marks_raw_latex_blocks_as_stale() -> None:
    html = (
        '<article class="paper-preview" data-reader-version="reader-v13">'
        '<div class="paper-preview__block paper-preview__block--latex">'
        '<pre class="paper-preview__latex">\\\\begin{promptbox}Example</pre>'
        "</div>"
        "</article>"
    )

    assert paper_service._preview_html_needs_refresh(html) is True


def test_looks_untranslated_for_zh_ignores_tiny_cjk_noise_in_english_text() -> None:
    text = "Large Language Models improve retrieval quality �?�?but still require grounded citations."
    assert paper_service._looks_untranslated_for_zh(text) is True


def test_untranslated_english_preview_html_is_not_treated_as_translated(tmp_path) -> None:
    preview_path = tmp_path / "preview.html"
    preview_path.write_text(
        (
            '<article class="paper-preview" data-reader-version="reader-v13">'
            "<section><h2>Introduction</h2>"
            "<p>Large Language Models provide a strong baseline for survey simulation and synthetic respondents.</p>"
            "</section></article>"
        ),
        encoding="utf-8",
    )

    preview_asset = {
        "id": "asset-preview",
        "task_id": "task-preview",
        "asset_type": "preview_html",
        "file_path": str(preview_path),
        "file_name": "preview.html",
        "mime_type": "text/html",
        "created_at": "2026-03-22T00:00:00Z",
    }
    paper = {
        "id": "paper-preview",
        "community_selected_task_id": "task-preview",
        "community_selected_asset_id": "asset-preview",
        "trans_status": "completed",
        "abstract_raw": "English abstract",
        "abstract_translated": "Large Language Models provide a strong baseline for survey simulation.",
    }

    payload = paper_service._build_preview_payload(
        paper_id="paper-preview",
        paper=paper,
        preview_asset=preview_asset,
    )

    normalized = paper_service._normalize_paper_state_from_assets(
        paper,
        asset_map={"preview_html": preview_asset},
    )

    assert payload is None
    assert normalized["trans_status"] == "failed"
    assert normalized["abstract_translated"] is None
