from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.repositories import CommunityPaperRepository
from backend.app.services import paper_service

ARXIV_ID_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5}(?:v\d+)?)(?!\d)")


@dataclass
class LocalPaperCandidate:
    paper_id: str
    paper_dir: Path
    arxiv_id: str
    source_path: Path
    preview_path: Path | None
    translated_pdf_path: Path | None
    created_at: str
    updated_at: str


def _iso_utc_from_path(path: Path) -> str:
    timestamp = path.stat().st_mtime
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()


def _iter_candidate_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in sorted(root.iterdir()) if path.is_dir()]


def _match_arxiv_id(value: str) -> str | None:
    match = ARXIV_ID_RE.search(value)
    if not match:
        return None
    return match.group(1)


def _infer_arxiv_id(source_root: Path, translated_root: Path) -> tuple[str | None, Path | None]:
    if source_root.exists():
        for child in sorted(source_root.iterdir()):
            candidate = _match_arxiv_id(child.name)
            if candidate:
                return candidate, child
        for child in sorted(source_root.rglob("*")):
            candidate = _match_arxiv_id(child.name)
            if candidate:
                return candidate, child

    if translated_root.exists():
        for child in sorted(translated_root.rglob("*.pdf")):
            candidate = _match_arxiv_id(child.name)
            if candidate:
                return candidate, child

    return None, None


def _find_preview_html(preview_root: Path) -> Path | None:
    if not preview_root.exists():
        return None
    preview_html = preview_root / "preview.html"
    if preview_html.exists():
        return preview_html
    candidates = sorted(preview_root.rglob("*.html"))
    return candidates[0] if candidates else None


def _find_translated_pdf(translated_root: Path) -> Path | None:
    if not translated_root.exists():
        return None
    candidates = sorted(translated_root.rglob("*.pdf"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _storage_path_for_db(path: Path, *, settings) -> str:
    resolved = path.resolve()
    candidate_roots = [settings.base_dir, settings.community_papers_dir.parent]
    for root in candidate_roots:
        try:
            relative = resolved.relative_to(root.resolve())
            return str(relative).replace("\\", "/")
        except Exception:
            continue
    return str(path).replace("\\", "/")


def discover_local_papers(root: Path) -> list[LocalPaperCandidate]:
    candidates: list[LocalPaperCandidate] = []
    for paper_dir in _iter_candidate_dirs(root):
        source_root = paper_dir / "source"
        preview_root = paper_dir / "preview"
        translated_root = paper_dir / "translated"

        arxiv_id, inferred_source = _infer_arxiv_id(source_root, translated_root)
        if not arxiv_id or inferred_source is None:
            continue

        preview_path = _find_preview_html(preview_root)
        translated_pdf_path = _find_translated_pdf(translated_root)
        timestamp_sources = [path for path in [translated_pdf_path, preview_path, inferred_source, paper_dir] if path is not None]
        created_at = _iso_utc_from_path(timestamp_sources[-1])
        updated_at = _iso_utc_from_path(timestamp_sources[0])

        candidates.append(
            LocalPaperCandidate(
                paper_id=paper_dir.name,
                paper_dir=paper_dir,
                arxiv_id=arxiv_id,
                source_path=inferred_source,
                preview_path=preview_path,
                translated_pdf_path=translated_pdf_path,
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    return candidates


def _metadata_for(arxiv_id: str) -> dict[str, Any]:
    try:
        return paper_service._fetch_arxiv_metadata_sync(arxiv_id)
    except Exception:
        return {}


def _preview_has_translated_content(preview_path: Path | None) -> bool:
    if preview_path is None:
        return False
    return paper_service._preview_asset_has_translated_content({"file_path": str(preview_path)})


def bootstrap_local_community_papers(*, dry_run: bool = False) -> dict[str, Any]:
    settings = get_settings()
    repository = CommunityPaperRepository()
    root = settings.community_papers_dir
    discovered = discover_local_papers(root)

    report: dict[str, Any] = {
        "root": str(root),
        "dry_run": dry_run,
        "discovered": len(discovered),
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "papers": [],
    }

    for candidate in discovered:
        metadata = _metadata_for(candidate.arxiv_id)
        existing = repository.get_paper_by_arxiv_id(candidate.arxiv_id)
        paper_id = str(existing.get("id")) if existing else candidate.paper_id
        translated_ready = candidate.translated_pdf_path is not None or _preview_has_translated_content(candidate.preview_path)

        latest_asset_id = f"{paper_id}:preview_html"
        if candidate.preview_path is None and candidate.translated_pdf_path is not None:
            latest_asset_id = f"{paper_id}:translated_pdf"
        if candidate.preview_path is None and candidate.translated_pdf_path is None:
            latest_asset_id = f"{paper_id}:source_archive"

        payload = {
            "id": paper_id,
            "created_by": None,
            "source": "arxiv",
            "arxiv_id": candidate.arxiv_id,
            "title": metadata.get("title") or f"arXiv:{candidate.arxiv_id}",
            "authors": metadata.get("authors") or [],
            "categories": metadata.get("categories") or [],
            "abstract_raw": metadata.get("abstract_raw"),
            "abstract_translated": existing.get("abstract_translated") if existing else None,
            "visibility": "public",
            "status": "published",
            "community_status": "official",
            "trans_status": "completed" if translated_ready else "not_started",
            "trans_latest_task_id": existing.get("trans_latest_task_id") if existing else None,
            "trans_latest_asset_pdf_id": f"{paper_id}:translated_pdf" if candidate.translated_pdf_path else None,
            "community_selected_task_id": existing.get("community_selected_task_id") if existing else None,
            "community_selected_asset_id": latest_asset_id,
            "like_count": int(existing.get("like_count") or 0) if existing else 0,
            "favorite_count": int(existing.get("favorite_count") or 0) if existing else 0,
            "comment_count": int(existing.get("comment_count") or 0) if existing else 0,
            "view_count": int(existing.get("view_count") or 0) if existing else 0,
            "download_count": int(existing.get("download_count") or 0) if existing else 0,
            "official_published_at": existing.get("official_published_at") if existing and existing.get("official_published_at") else candidate.updated_at,
            "created_at": existing.get("created_at") if existing and existing.get("created_at") else candidate.created_at,
            "updated_at": candidate.updated_at,
        }

        report["papers"].append(
            {
                "paper_id": paper_id,
                "arxiv_id": candidate.arxiv_id,
                "title": payload["title"],
                "existing": bool(existing),
                "preview": str(candidate.preview_path) if candidate.preview_path else None,
                "translated_pdf": str(candidate.translated_pdf_path) if candidate.translated_pdf_path else None,
                "source_path": str(candidate.source_path),
            }
        )

        if dry_run:
            if existing:
                report["updated"] += 1
            else:
                report["inserted"] += 1
            continue

        if existing:
            repository.update_paper(paper_id, payload)
            report["updated"] += 1
        else:
            repository.insert_paper(payload)
            report["inserted"] += 1

        repository.upsert_latest_asset(
            paper_id=paper_id,
            task_id=None,
            asset_type="source_archive",
            file_path=_storage_path_for_db(candidate.source_path, settings=settings),
            file_name=candidate.source_path.name,
            mime_type="application/x-directory" if candidate.source_path.is_dir() else "application/octet-stream",
            asset_id=f"{paper_id}:source_archive",
            created_at=candidate.created_at,
        )
        if candidate.preview_path:
            repository.upsert_latest_asset(
                paper_id=paper_id,
                task_id=None,
                asset_type="preview_html",
                file_path=_storage_path_for_db(candidate.preview_path, settings=settings),
                file_name=candidate.preview_path.name,
                mime_type="text/html",
                asset_id=f"{paper_id}:preview_html",
                created_at=_iso_utc_from_path(candidate.preview_path),
            )
        if candidate.translated_pdf_path:
            repository.upsert_latest_asset(
                paper_id=paper_id,
                task_id=None,
                asset_type="translated_pdf",
                file_path=_storage_path_for_db(candidate.translated_pdf_path, settings=settings),
                file_name=candidate.translated_pdf_path.name,
                mime_type="application/pdf",
                asset_id=f"{paper_id}:translated_pdf",
                created_at=_iso_utc_from_path(candidate.translated_pdf_path),
            )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Register on-disk community papers into the local MySQL/SQLite database.")
    parser.add_argument("--dry-run", action="store_true", help="Discover papers and print what would be registered without modifying the database.")
    parser.add_argument("--report-json", type=Path, default=None, help="Optional path to write the structured report JSON.")
    args = parser.parse_args()

    report = bootstrap_local_community_papers(dry_run=args.dry_run)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
