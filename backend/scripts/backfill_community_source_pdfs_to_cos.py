from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
import json
from pathlib import PurePosixPath
from typing import Any, Iterable, Sequence

from backend.app.core.config import get_settings
from backend.app.db import get_database_dialect
from backend.app.services import paper_service
from backend.scripts.mysql_script_connection import describe_mysql_script_target, mysql_script_connection


@dataclass(frozen=True)
class SourcePdfBackfillCandidate:
    paper_id: str
    arxiv_id: str
    task_id: str | None = None


def _placeholder(index: int) -> str:
    _ = index
    return "%s" if get_database_dialect() == "mysql" else "?"


def _normalize_key(value: str) -> str:
    normalized = PurePosixPath(str(value or "").replace("\\", "/").strip("/"))
    parts = [part for part in normalized.parts if part and part != "."]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"Unsafe object key: {value}")
    return "/".join(parts)


def expected_source_pdf_object_key(*, paper_id: str, arxiv_id: str, cos_base_prefix: str) -> str:
    filename = paper_service._source_pdf_filename(arxiv_id)
    relative = f"data/community_papers/{paper_id}/source_pdf/{filename}"
    prefix = str(cos_base_prefix or "").strip().strip("/")
    if not prefix:
        return _normalize_key(relative)
    return _normalize_key(f"{prefix}/{relative}")


def candidate_to_report_item(candidate: SourcePdfBackfillCandidate, *, cos_base_prefix: str) -> dict[str, Any]:
    return {
        "paper_id": candidate.paper_id,
        "arxiv_id": candidate.arxiv_id,
        "task_id": candidate.task_id,
        "source_name": paper_service._source_pdf_filename(candidate.arxiv_id),
        "expected_object_key": expected_source_pdf_object_key(
            paper_id=candidate.paper_id,
            arxiv_id=candidate.arxiv_id,
            cos_base_prefix=cos_base_prefix,
        ),
    }


def load_candidates(*, limit: int, arxiv_ids: Sequence[str] | None = None) -> list[SourcePdfBackfillCandidate]:
    normalized_ids = [str(item or "").strip() for item in (arxiv_ids or []) if str(item or "").strip()]
    params: list[Any] = ["arxiv", "public", "removed", "source_pdf", True]
    where = (
        "p.source = "
        + _placeholder(0)
        + " and p.visibility = "
        + _placeholder(1)
        + " and p.status <> "
        + _placeholder(2)
        + " and trim(coalesce(p.arxiv_id, '')) <> ''"
        + " and not exists ("
        + "select 1 from paper_assets a where a.paper_id = p.id"
        + " and a.asset_type = "
        + _placeholder(3)
        + " and a.is_latest = "
        + _placeholder(4)
        + ")"
    )
    if normalized_ids:
        placeholders = []
        for arxiv_id in normalized_ids:
            placeholders.append(_placeholder(len(params)))
            params.append(arxiv_id)
        where += " and p.arxiv_id in (" + ", ".join(placeholders) + ")"
    params.append(max(1, int(limit or 100)))
    sql = (
        "select p.id, p.arxiv_id, p.community_selected_task_id, p.trans_latest_task_id "
        "from papers p where "
        + where
        + " order by coalesce(p.official_published_at, p.created_at, '') asc limit "
        + _placeholder(len(params) - 1)
    )
    with mysql_script_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall() or []

    candidates: list[SourcePdfBackfillCandidate] = []
    for row in rows:
        getter = row.get if isinstance(row, dict) else lambda key, default=None: row[key] if key in row.keys() else default
        paper_id = str(getter("id") or "").strip()
        arxiv_id = str(getter("arxiv_id") or "").strip()
        if not paper_id or not arxiv_id:
            continue
        task_id = str(getter("community_selected_task_id") or getter("trans_latest_task_id") or "").strip() or None
        candidates.append(SourcePdfBackfillCandidate(paper_id=paper_id, arxiv_id=arxiv_id, task_id=task_id))
    return candidates


def execute_candidate(candidate: SourcePdfBackfillCandidate) -> dict[str, Any]:
    asset = asyncio.run(
        paper_service.persist_arxiv_source_pdf_asset(
            paper_id=candidate.paper_id,
            task_id=candidate.task_id,
            arxiv_id=candidate.arxiv_id,
        )
    )
    return {
        "paper_id": candidate.paper_id,
        "arxiv_id": candidate.arxiv_id,
        "asset_id": asset.get("id"),
        "storage_backend": asset.get("storage_backend"),
        "file_path": asset.get("file_path"),
    }


def run_backfill(
    *,
    candidates: Iterable[SourcePdfBackfillCandidate],
    execute: bool,
    cos_base_prefix: str,
) -> dict[str, Any]:
    candidate_list = list(candidates)
    report: dict[str, Any] = {
        "dry_run": not execute,
        "candidates": [
            candidate_to_report_item(candidate, cos_base_prefix=cos_base_prefix)
            for candidate in candidate_list
        ],
        "executed": [],
        "errors": [],
    }
    if execute:
        for candidate in candidate_list:
            try:
                report["executed"].append(execute_candidate(candidate))
            except Exception as exc:
                report["errors"].append(
                    {
                        "paper_id": candidate.paper_id,
                        "arxiv_id": candidate.arxiv_id,
                        "error": str(exc),
                    }
                )
    report["summary"] = {
        "candidate_count": len(candidate_list),
        "executed_count": len(report["executed"]),
        "error_count": len(report["errors"]),
    }
    return report


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill missing community source_pdf assets to COS.")
    parser.add_argument("--execute", action="store_true", help="Upload PDFs and write paper_assets rows.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum candidates to inspect.")
    parser.add_argument("--arxiv-id", action="append", default=[], help="Limit to one arXiv ID; may be repeated.")
    parser.add_argument("--output-report", help="Optional JSON report path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    settings = get_settings()
    if args.execute and str(settings.storage_backend_mode or "").strip().lower() != "cos":
        raise RuntimeError("Execute mode requires STORAGE_BACKEND_MODE=cos.")
    candidates = load_candidates(limit=args.limit, arxiv_ids=args.arxiv_id)
    report = run_backfill(
        candidates=candidates,
        execute=bool(args.execute),
        cos_base_prefix=settings.cos_base_prefix,
    )
    report["database"] = describe_mysql_script_target()
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_report:
        with open(args.output_report, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
