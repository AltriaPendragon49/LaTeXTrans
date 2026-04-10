import asyncio
import os
from datetime import datetime

import pytest
from fastapi import HTTPException

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_preview_service, paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Previewable paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "raw abstract",
        "abstract_translated": "涓枃鎽樿",
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


def test_get_paper_preview_reads_relative_library_path(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text("<article><h2>寮曡█</h2></article>", encoding="utf-8")

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["id"] == "asset-preview"
    assert "寮曡█" in result["html_content"]


def test_get_paper_preview_serializes_datetime_generated_at(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text("<article><h2>寮曡█</h2></article>", encoding="utf-8")

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
                "preview_html": {
                    "id": "asset-preview",
                    "task_id": "task-1",
                    "asset_type": "preview_html",
                    "file_path": "data/community_papers/paper-1/preview/preview.html",
                    "file_name": "preview.html",
                    "mime_type": "text/html",
                    "created_at": datetime(2026, 3, 18, 2, 0, 0),
                }
            },
        ),
    )

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["generated_at"] == "2026-03-18 02:00:00"


def test_get_paper_preview_rejects_missing_relative_library_file(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
                "preview_html": {
                    "id": "asset-preview",
                    "task_id": "task-1",
                    "asset_type": "preview_html",
                    "file_path": "data/community_papers/paper-1/preview/missing.html",
                    "file_name": "missing.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert exc_info.value.status_code == 404


def test_get_paper_preview_falls_back_to_existing_english_preview_when_strict_zh_check_rejects(
    monkeypatch, tmp_path
):
    base_dir = tmp_path / "repo"
    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        (
            f'<article class="paper-preview" data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}">'
            "<section><h2>Introduction</h2><p>This is an English fallback preview that should remain readable.</p></section>"
            "</article>"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["id"] == "asset-preview"
    assert "English fallback preview" in result["html_content"]


def test_get_paper_preview_falls_back_to_existing_stale_preview_when_refresh_path_unavailable(
    monkeypatch, tmp_path
):
    base_dir = tmp_path / "repo"
    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        "<article><h2>Legacy Preview</h2><pre class=\"paper-preview__latex\">E=mc^2</pre><p>Readable fallback content.</p></article>",
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["id"] == "asset-preview"
    assert "Legacy Preview" in result["html_content"]
    assert "paper-preview__latex" not in result["html_content"]
    assert "paper-preview__math-block" in result["html_content"]


def test_get_paper_preview_strips_raw_latex_command_blocks_from_legacy_preview(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        (
            "<article>"
            "<h2>Legacy Preview</h2>"
            "<div class=\"paper-preview__command-block\"><code>\\begin{tabular}{cc}A & B \\\\ 1 & 2 \\\\ \\end{tabular}</code></div>"
            "</article>"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert "LaTeX source snippet omitted in HTML preview" in result["html_content"]
    assert "paper-preview__command-block" not in result["html_content"]
    assert "\\begin{tabular}" not in result["html_content"]


def test_get_paper_preview_strips_legacy_table_cell_latex_source_tokens(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        (
            "<article>"
            "<table class=\"paper-preview__table\"><tr>"
            "<th>\\begin{table}\\begin{tabular}{cc}\\hline</th>"
            "<td>\\includegraphics{demo.png}\\multirow{2}{*}{Score}</td>"
            "</tr></table>"
            "</article>"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert "\\begin{table}" not in result["html_content"]
    assert "\\begin{tabular}" not in result["html_content"]
    assert "\\includegraphics" not in result["html_content"]
    assert "\\multirow" not in result["html_content"]


def test_preview_asset_refreshes_when_reader_version_mismatches(tmp_path):
    preview_path = tmp_path / "preview.html"
    preview_path.write_text(
        '<article class="paper-preview" data-reader-version="reader-v5"><h2>寮曡█</h2><p>Readable content</p></article>',
        encoding="utf-8",
    )

    assert paper_service._preview_asset_needs_refresh(preview_path) is True


def test_preview_asset_refreshes_when_same_version_still_contains_stale_reader_artifacts(tmp_path):
    preview_path = tmp_path / "preview.html"
    preview_path.write_text(
        '<article class="paper-preview" data-reader-version="reader-v9"><table><tr><td>[1.1pt] \\multirow{2}{*}{System}</td></tr></table></article>',
        encoding="utf-8",
    )

    assert paper_service._preview_asset_needs_refresh(preview_path) is True


def test_preview_asset_refreshes_when_command_block_contains_raw_latex_source(tmp_path):
    preview_path = tmp_path / "preview.html"
    preview_path.write_text(
        (
            '<article class="paper-preview" data-reader-version="reader-v13">'
            '<div class="paper-preview__command-block"><code>\\includegraphics{demo.png}</code></div>'
            "</article>"
        ),
        encoding="utf-8",
    )

    assert paper_service._preview_asset_needs_refresh(preview_path) is True


def test_get_paper_preview_refreshes_stale_preview_asset(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        '<article class="paper-preview" data-reader-version="day4">\\begin{document}</article>',
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", base_dir / "data" / "community_papers")
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper(trans_latest_task_id="task-translate")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "preview_html": {
                    "id": "asset-preview-old",
                    "task_id": "task-translate",
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
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "id": "asset-preview-new",
                "task_id": "task-translate",
                "asset_type": "preview_html",
                "file_path": "data/community_papers/paper-1/preview/regenerated.html",
                "file_name": "regenerated.html",
                "mime_type": "text/html",
                "created_at": "2026-03-18T03:00:00+00:00",
            },
        ),
    )

    regenerated_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "regenerated.html"
    regenerated_path.write_text(
        f'<article class="paper-preview" data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}"><h2>寮曡█</h2><p>鍙鍐呭</p></article>',
        encoding="utf-8",
    )

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["asset"]["id"] == "asset-preview-new"
    assert "鍙鍐呭" in result["html_content"]


def test_get_paper_preview_recovers_from_task_output_when_preview_asset_missing(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    output_dir = base_dir / "data" / "outputs" / "task-translate"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                community_selected_task_id="task-intake",
                trans_latest_task_id="task-translate",
            ),
        ),
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
                    "file_path": "data/community_papers/paper-1/translated/detail.pdf",
                    "file_name": "detail.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    class _TaskManager:
        def get_task(self, task_id):
            assert task_id == "task-translate"
            return {"task_id": task_id, "output_path": str(output_dir)}

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_resolve_preview_html_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "id": "asset-preview",
                "task_id": "task-translate",
                "asset_type": "preview_html",
                "file_path": "data/community_papers/paper-1/preview/preview.html",
                "file_name": "preview.html",
                "mime_type": "text/html",
                "created_at": "2026-03-18T02:00:00+00:00",
            },
        ),
    )

    preview_path = base_dir / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text("<article><h2>Recovered</h2></article>", encoding="utf-8")

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["id"] == "asset-preview"
    assert "Recovered" in result["html_content"]


def test_get_paper_preview_recovers_from_outputs_dir_when_task_runtime_missing(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    output_dir = base_dir / "data" / "outputs" / "task-translate" / "zh_demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sections_map.json").write_text(
        '[{"section":"1","trans_content":"\\\\section{寮曡█}\\n\\n杩欐槸鍙槄璇绘鏂囥€?}]',
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", base_dir / "data" / "outputs")
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", base_dir / "data" / "community_papers")
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                community_selected_task_id="task-translate",
                trans_latest_task_id="task-translate",
            ),
        ),
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
                    "file_path": "data/community_papers/paper-1/translated/detail.pdf",
                    "file_name": "detail.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    class _TaskManager:
        def get_task(self, task_id):
            assert task_id == "task-translate"
            return None

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_upsert_latest_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "id": "asset-preview",
                "task_id": "task-translate",
                "asset_type": "preview_html",
                "file_path": "data/community_papers/paper-1/preview/preview.html",
                "file_name": "preview.html",
                "mime_type": "text/html",
                "created_at": "2026-03-18T02:00:00+00:00",
            },
        ),
    )
    monkeypatch.setattr(
        paper_service.paper_preview_service,
        "generate_preview_html",
        lambda output_dir, target_dir, source_dirs=None, paper_metadata=None: {
            "file_path": str((target_dir / "preview.html").resolve()),
            "file_name": "preview.html",
            "mime_type": "text/html",
        }
        if (
            target_dir.mkdir(parents=True, exist_ok=True) is None
            and (target_dir / "preview.html").write_text(
                (
                    f'<article data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}">'
                    "<h2>Preview</h2><p>Recovered</p></article>"
                ),
                encoding="utf-8",
            )
            >= 0
        )
        else None,
    )

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["asset_type"] == "preview_html"
    assert "<article" in result["html_content"]


def test_detail_recovers_translated_abstract_when_task_output_path_is_stale(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    output_dir = base_dir / "data" / "outputs" / "task-translate" / "zh_paper"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "main.tex").write_text(
        "\\begin{abstract}杩欐槸鏂扮殑涓枃鎽樿銆俓\end{abstract}\\section{寮曡█}姝ｆ枃",
        encoding="utf-8",
    )

    paper = _paper(
        abstract_raw="English abstract",
        abstract_translated=None,
        trans_latest_task_id="task-translate",
        community_selected_task_id="task-translate",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", base_dir / "data" / "outputs")
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", base_dir / "data" / "community_papers")
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
            return {"task_id": task_id, "output_path": str(base_dir / "missing" / "task-translate")}

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

    assert result["paper"]["abstract_translated"]
    assert result["paper"]["abstract_translated"] != result["paper"]["abstract_raw"]


def test_detail_recovers_translated_abstract_from_envs_map_when_main_tex_missing(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    output_dir = base_dir / "data" / "outputs" / "task-translate" / "zh_paper"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "envs_map.json").write_text(
        '[{"env_name":"abstract","trans_content":"\\\\begin{abstract}杩欐槸 envs_map 涓殑涓枃鎽樿銆俓\\\end{abstract}"}]',
        encoding="utf-8",
    )

    paper = _paper(
        abstract_raw="English abstract",
        abstract_translated=None,
        trans_latest_task_id="task-translate",
        community_selected_task_id="task-translate",
    )

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
            return None

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

    assert result["paper"]["abstract_translated"]
    assert result["paper"]["abstract_translated"] != result["paper"]["abstract_raw"]


def test_detail_recovers_translated_abstract_from_completed_output(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    output_dir = base_dir / "data" / "outputs" / "task-translate" / "zh_paper"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "main.tex").write_text(
        "\\begin{abstract}杩欐槸涓枃鎽樿銆俓\end{abstract}\\section{寮曡█}姝ｆ枃",
        encoding="utf-8",
    )

    paper = _paper(
        abstract_raw="English abstract",
        abstract_translated=None,
        trans_latest_task_id="task-translate",
        community_selected_task_id="task-translate",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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

    assert result["paper"]["abstract_translated"]
    assert result["paper"]["abstract_translated"] != result["paper"]["abstract_raw"]

