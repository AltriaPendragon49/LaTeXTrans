import asyncio
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


def _paper(**overrides):
    paper = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2501.12345",
        "title": "Paper title",
        "authors": [],
        "categories": [],
        "abstract_raw": "English abstract",
        "abstract_translated": None,
        "community_status": "user_fallback",
        "trans_status": "completed",
        "created_at": "2026-03-18T02:00:00+00:00",
        "official_published_at": None,
        "community_selected_task_id": "task-translate",
        "community_selected_asset_id": "asset-preview",
        "visibility": "public",
        "status": "published",
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
        "trans_latest_task_id": "task-translate",
        "trans_latest_asset_pdf_id": None,
    }
    paper.update(overrides)
    return paper


def test_detail_repairs_stale_english_translated_abstract_from_completed_output(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    output_dir = base_dir / "data" / "outputs" / "task-translate" / "zh_paper"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "envs_map.json").write_text(
        '[{"env_name":"abstract","trans_content":"\\\\begin{abstract}这是修复后的中文摘要。\\\\end{abstract}"}]',
        encoding="utf-8",
    )

    paper = _paper(abstract_translated="This is the wrong stale English abstract.")

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", base_dir / "data" / "outputs")
    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=paper))
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
                    "file_path": "data/community_papers/paper-1/translated/detail.pdf",
                    "file_name": "detail.pdf",
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
            0,
            result={"paper-1": {"liked": False, "favorited": False}},
        ),
    )

    class _TaskManager:
        def get_task(self, task_id):
            assert task_id == "task-translate"
            return {"task_id": task_id, "output_path": str(output_dir)}

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result={**paper, "id": paper_id, **payload}),
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-1",
            viewer_user_id="user-1",
        )
    )

    assert result["paper"]["abstract_translated"] == "这是修复后的中文摘要�?
