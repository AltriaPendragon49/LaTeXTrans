import asyncio
import base64
import json
from io import BytesIO
from types import SimpleNamespace

from fastapi import UploadFile

from backend.app.api.routes.translate import TranslateRequest
from backend.app.services import paper_service


def _jwt_for(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id}).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"header.{payload}.sig"


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "upload",
        "arxiv_id": None,
        "title": "Week 1 Paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "raw abstract",
        "abstract_translated": None,
        "community_status": "user_fallback",
        "trans_status": "not_started",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": None,
        "community_selected_task_id": "task-upload",
        "community_selected_asset_id": "asset-source",
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


def test_week1_main_path_flows_from_submit_to_preview_and_download(monkeypatch, tmp_path):
    def _close_task(coro):
        coro.close()
        return None

    source_dir = tmp_path / "paper-source"
    source_dir.mkdir()

    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service.upload_route,
        "upload_file",
        lambda **_kwargs: asyncio.sleep(
            0,
            result=SimpleNamespace(task_id="task-upload", status="pending", source_path="D:/tmp/paper.zip"),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_insert_paper",
        lambda payload: asyncio.sleep(
            0,
            result={
                "id": "paper-1",
                "created_at": "2026-03-18T00:00:00+00:00",
                **payload,
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_create_source_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "id": "asset-source",
                "task_id": "task-upload",
                "asset_type": "source_archive",
                "file_path": "data/community_papers/paper-1/source.zip",
                "file_name": "source.zip",
                "mime_type": "application/zip",
                "created_at": "2026-03-18T00:00:00+00:00",
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result=_paper(id=paper_id, **payload)),
    )

    submit_result = asyncio.run(
        paper_service.submit_uploaded_paper(
            file=UploadFile(filename="paper.zip", file=BytesIO(b"zip-bytes")),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
        )
    )

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper()),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "source_archive": {
                    "id": "asset-source",
                    "paper_id": "paper-1",
                    "task_id": "task-upload",
                    "asset_type": "source_archive",
                    "file_path": str(source_dir),
                    "file_name": "source.zip",
                    "mime_type": "application/zip",
                    "created_at": "2026-03-18T00:00:00+00:00",
                }
            },
        ),
    )

    class _TaskManager:
        def create_task(self, **kwargs):
            return "task-translate"

        def update_task(self, task_id, **kwargs):
            return None

        def persist_task_if_needed(self, task_id):
            return True

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_enqueue_existing_task_translation",
        lambda **kwargs: asyncio.sleep(0, result={"task_id": kwargs["task_id"], "status": "queued"}),
    )
    monkeypatch.setattr(
        paper_service.asyncio,
        "create_task",
        _close_task,
    )

    translate_result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
        )
    )

    monkeypatch.setattr(
        paper_service,
        "_ensure_public_paper",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                trans_status="completed",
                community_selected_task_id="task-translate",
                community_selected_asset_id="asset-preview",
            ),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "preview_html": {
                    "id": "asset-preview",
                    "task_id": "task-translate",
                    "asset_type": "preview_html",
                    "file_path": "data/community_papers/paper-1/preview.html",
                    "file_name": "preview.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T01:00:00+00:00",
                },
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-translate",
                    "asset_type": "translated_pdf",
                    "file_path": "data/community_papers/paper-1/paper.pdf",
                    "file_name": "paper.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T01:00:00+00:00",
                },
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_resolve_storage_path",
        lambda path: SimpleNamespace(
            exists=lambda: True,
            read_text=lambda encoding="utf-8": "<article>Preview</article>",
            stat=lambda: SimpleNamespace(st_mtime=1_710_000_000),
            __str__=lambda self: path,
        ),
    )
    monkeypatch.setattr(paper_service.time, "time", lambda: 1_710_000_600)

    preview_result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    download_session = asyncio.run(
        paper_service.create_paper_download_session(paper_id="paper-1")
    )

    assert submit_result["paper"]["id"] == "paper-1"
    assert submit_result["paper"]["trans_status"] == "not_started"
    assert translate_result["task_id"] == "task-translate"
    assert translate_result["reused_existing_task"] is False
    assert preview_result["asset"]["asset_type"] == "preview_html"
    assert preview_result["html_content"] == "<article>Preview</article>"
    assert download_session["download_url"].startswith("/api/papers/paper-1/download?token=")
