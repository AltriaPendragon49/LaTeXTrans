from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import uuid4

from backend.app.api.routes import download as download_route
from backend.app.repositories.community_paper_repository import CommunityPaperRepository
from backend.app.services import paper_service
from backend.app.services.task_manager import task_manager
from backend.scripts.mysql_script_connection import describe_mysql_script_target, mysql_script_connection


TERMINAL_SUCCESS_STATUSES = {"completed", "completed_with_warnings"}
ACTIVE_CURATION_STATUSES = {"queued", "admitted", "translating", "publishing", "completed"}


@dataclass(frozen=True)
class TaskCandidate:
    arxiv_id: str
    task_id: str
    status: str
    source_path: Optional[str]
    output_path: Optional[str]
    completed_at: Any
    duration_seconds: Optional[int]
    output_exists: bool
    source_exists: bool
    task_log_exists: bool
    translated_pdf_path: Optional[str]
    existing_paper_id: Optional[str]
    existing_curation_statuses: tuple[str, ...]

    @property
    def publishable(self) -> bool:
        return bool(
            self.arxiv_id
            and self.task_id
            and self.source_exists
            and self.output_exists
            and self.task_log_exists
            and self.translated_pdf_path
            and not self.existing_paper_id
            and not any(status in ACTIVE_CURATION_STATUSES for status in self.existing_curation_statuses)
        )

    @property
    def skip_reasons(self) -> list[str]:
        reasons: list[str] = []
        if not self.source_exists:
            reasons.append("source_missing")
        if not self.output_exists:
            reasons.append("output_missing")
        if not self.task_log_exists:
            reasons.append("task_log_missing")
        if not self.translated_pdf_path:
            reasons.append("translated_pdf_missing")
        if self.existing_paper_id:
            reasons.append("paper_already_exists")
        if any(status in ACTIVE_CURATION_STATUSES for status in self.existing_curation_statuses):
            reasons.append("active_or_completed_curation_exists")
        return reasons

    def score(self) -> tuple[int, int, int, float]:
        completed_at = _timestamp_score(self.completed_at)
        duration_ok = 1 if self.duration_seconds is not None and self.duration_seconds > 30 else 0
        status_ok = 1 if self.status == "completed" else 0
        ready = 1 if self.publishable else 0
        return ready, duration_ok, status_ok, completed_at


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _timestamp_score(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, datetime):
        return value.timestamp()
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _fetchall(cursor: Any) -> list[dict[str, Any]]:
    rows = cursor.fetchall() or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(dict(row))
        else:
            normalized.append({key: row[key] for key in row.keys()})
    return normalized


def _placeholders(count: int) -> str:
    return ", ".join(["%s"] * count)


def _resolve_existing_path(value: Any) -> Optional[Path]:
    text = str(value or "").strip()
    if not text:
        return None
    return paper_service._resolve_storage_path(text)


def _find_task_log(output_path: Optional[Path]) -> Optional[Path]:
    if output_path is None or not output_path.exists():
        return None
    direct = list(output_path.glob("zh_*/task_log.json"))
    if direct:
        return direct[0]
    nested = list(output_path.glob("**/task_log.json"))
    return nested[0] if nested else None


def _find_translated_pdf(output_path: Optional[Path]) -> Optional[Path]:
    if output_path is None or not output_path.exists():
        return None
    pdf_path = download_route._find_translated_pdf(output_path)
    if pdf_path and pdf_path.exists():
        return pdf_path
    return None


def _load_orphan_rows(
    *,
    arxiv_ids: Optional[set[str]] = None,
    task_ids: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    conditions = [
        "t.status in ('completed','completed_with_warnings')",
        (
            "not exists ("
            "select 1 from community_curation_jobs c "
            "where c.task_id = t.task_id "
            "and c.status in ('queued','processing','translating','publishing','completed')"
            ")"
        ),
    ]
    params: list[Any] = []
    if arxiv_ids:
        conditions.append(f"t.arxiv_id in ({_placeholders(len(arxiv_ids))})")
        params.extend(sorted(arxiv_ids))
    if task_ids:
        conditions.append(f"t.task_id in ({_placeholders(len(task_ids))})")
        params.extend(sorted(task_ids))

    where_clause = " and ".join(conditions)
    query = f"""
        select
            t.arxiv_id,
            t.task_id,
            t.status,
            t.source_path,
            t.output_path,
            t.source_language,
            t.target_language,
            t.completed_at,
            timestampdiff(second, t.created_at, t.completed_at) as duration_seconds,
            p.id as existing_paper_id,
            group_concat(distinct c_any.status order by c_any.created_at separator ',') as existing_curation_statuses
        from translation_tasks t
        left join papers p on p.arxiv_id = t.arxiv_id
        left join community_curation_jobs c_any on c_any.arxiv_id = t.arxiv_id
        where {where_clause}
        group by
            t.arxiv_id,
            t.task_id,
            t.status,
            t.source_path,
            t.output_path,
            t.source_language,
            t.target_language,
            t.completed_at,
            duration_seconds,
            p.id
        order by t.created_at asc, t.task_id asc
    """
    with mysql_script_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, tuple(params))
        return _fetchall(cursor)


def _candidate_from_row(row: dict[str, Any]) -> TaskCandidate:
    source_path = _resolve_existing_path(row.get("source_path"))
    output_path = _resolve_existing_path(row.get("output_path"))
    task_log = _find_task_log(output_path)
    translated_pdf = _find_translated_pdf(output_path)
    statuses = tuple(
        status
        for status in str(row.get("existing_curation_statuses") or "").split(",")
        if status
    )
    return TaskCandidate(
        arxiv_id=str(row.get("arxiv_id") or "").strip(),
        task_id=str(row.get("task_id") or "").strip(),
        status=str(row.get("status") or "").strip(),
        source_path=str(source_path) if source_path else None,
        output_path=str(output_path) if output_path else None,
        completed_at=row.get("completed_at"),
        duration_seconds=(
            int(row["duration_seconds"]) if row.get("duration_seconds") is not None else None
        ),
        output_exists=bool(output_path and output_path.exists()),
        source_exists=bool(source_path and source_path.exists()),
        task_log_exists=bool(task_log and task_log.exists()),
        translated_pdf_path=str(translated_pdf) if translated_pdf else None,
        existing_paper_id=str(row.get("existing_paper_id") or "").strip() or None,
        existing_curation_statuses=statuses,
    )


def _select_candidates(rows: Iterable[dict[str, Any]]) -> tuple[list[TaskCandidate], list[TaskCandidate]]:
    by_arxiv: dict[str, list[TaskCandidate]] = {}
    for row in rows:
        candidate = _candidate_from_row(row)
        if not candidate.arxiv_id:
            continue
        by_arxiv.setdefault(candidate.arxiv_id, []).append(candidate)

    selected: list[TaskCandidate] = []
    skipped: list[TaskCandidate] = []
    for candidates in by_arxiv.values():
        ordered = sorted(candidates, key=lambda item: item.score(), reverse=True)
        winner = ordered[0]
        if winner.publishable:
            selected.append(winner)
            skipped.extend(ordered[1:])
        else:
            skipped.extend(ordered)
    return selected, skipped


def _candidate_report(candidate: TaskCandidate) -> dict[str, Any]:
    return {
        "arxiv_id": candidate.arxiv_id,
        "task_id": candidate.task_id,
        "status": candidate.status,
        "duration_seconds": candidate.duration_seconds,
        "source_exists": candidate.source_exists,
        "output_exists": candidate.output_exists,
        "task_log_exists": candidate.task_log_exists,
        "translated_pdf_path": candidate.translated_pdf_path,
        "publishable": candidate.publishable,
        "skip_reasons": candidate.skip_reasons,
    }


def _default_created_by() -> str:
    with mysql_script_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            select created_by
            from community_curation_jobs
            where created_by is not null and created_by <> ''
            order by created_at desc
            limit 1
            """
        )
        row = cursor.fetchone()
    if isinstance(row, dict):
        value = row.get("created_by")
    elif row is not None:
        value = row[0]
    else:
        value = None
    return str(value or "admin-orphan-backfill").strip()


def _find_reusable_failed_job(
    *,
    repository: CommunityPaperRepository,
    candidate: TaskCandidate,
) -> Optional[dict[str, Any]]:
    jobs = repository.list_curation_jobs(search=candidate.arxiv_id)
    for job in jobs:
        if (
            str(job.get("arxiv_id") or "").strip() == candidate.arxiv_id
            and str(job.get("task_id") or "").strip() == candidate.task_id
            and str(job.get("status") or "").strip() == "failed"
            and str(job.get("terminal_reason") or "").strip() == "orphan_backfill_publish_failed"
        ):
            return job
    return None


async def _publish_candidate(
    *,
    candidate: TaskCandidate,
    repository: CommunityPaperRepository,
    batch_id: str,
    created_by: str,
) -> dict[str, Any]:
    created_at = _utc_now_naive()
    reusable_job = _find_reusable_failed_job(repository=repository, candidate=candidate)
    job_payload = {
        "job_id": (
            str(reusable_job.get("job_id"))
            if reusable_job
            else f"curation-job-{uuid4().hex}"
        ),
        "batch_id": (
            str(reusable_job.get("batch_id"))
            if reusable_job and reusable_job.get("batch_id")
            else batch_id
        ),
        "paper_id": (
            str(reusable_job.get("paper_id"))
            if reusable_job and reusable_job.get("paper_id")
            else uuid4().hex
        ),
        "source_type": "arxiv",
        "arxiv_id": candidate.arxiv_id,
        "original_filename": None,
        "source_path": candidate.source_path,
        "task_id": candidate.task_id,
        "source_language": "en",
        "target_language": "zh",
        "status": "failed" if reusable_job else "backfill_pending",
        "error": None,
        "created_by": created_by,
        "created_at": reusable_job.get("created_at") if reusable_job else created_at,
        "updated_at": created_at,
    }
    try:
        task = task_manager.get_task(candidate.task_id)
        if not task or task.get("status") not in TERMINAL_SUCCESS_STATUSES:
            raise RuntimeError(f"Task {candidate.task_id} is not recoverable as a completed task")

        published = await paper_service._publish_admin_curation_job(
            job=job_payload,
            metadata={"arxiv_id": candidate.arxiv_id},
            translated_task_id=candidate.task_id,
        )
        completion_updates = {
            "paper_id": published.get("id"),
            "published_paper_id": published.get("id"),
            "status": "completed",
            "terminal_task_status": "completed",
            "terminal_reason": None,
            "timeout_reason": None,
            "error": None,
            "failed_artifact_path": None,
            "artifact_storage_backend": None,
            "updated_at": _utc_now_naive(),
        }
        if reusable_job:
            updated_job = repository.update_curation_job(str(job_payload["job_id"]), completion_updates)
        else:
            updated_job = repository.insert_curation_job({**job_payload, **completion_updates})
        return {
            "arxiv_id": candidate.arxiv_id,
            "task_id": candidate.task_id,
            "job_id": job_payload["job_id"],
            "paper_id": published.get("id"),
            "status": "completed",
            "job": updated_job,
        }
    except Exception as exc:
        try:
            await paper_service._delete_placeholder_curation_paper_if_present(
                repository=repository,
                paper_id=str(job_payload["paper_id"]),
            )
        except Exception:
            pass
        failure_updates = {
            "status": "failed",
            "terminal_task_status": candidate.status,
            "terminal_reason": "orphan_backfill_publish_failed",
            "error": str(exc)[:2000],
            "updated_at": _utc_now_naive(),
        }
        if reusable_job:
            repository.update_curation_job(str(job_payload["job_id"]), failure_updates)
        else:
            repository.insert_curation_job({**job_payload, **failure_updates})
        return {
            "arxiv_id": candidate.arxiv_id,
            "task_id": candidate.task_id,
            "job_id": job_payload["job_id"],
            "status": "failed",
            "error": str(exc),
        }


async def run_backfill(
    *,
    dry_run: bool,
    limit: Optional[int],
    arxiv_ids: Optional[set[str]],
    task_ids: Optional[set[str]],
    created_by: Optional[str],
) -> dict[str, Any]:
    rows = _load_orphan_rows(arxiv_ids=arxiv_ids, task_ids=task_ids)
    selected, skipped = _select_candidates(rows)
    selected = sorted(selected, key=lambda item: item.completed_at or "")
    if limit is not None:
        skipped.extend(selected[limit:])
        selected = selected[:limit]

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "database": describe_mysql_script_target(),
        "loaded_task_rows": len(rows),
        "selected_count": len(selected),
        "skipped_count": len(skipped),
        "selected": [_candidate_report(candidate) for candidate in selected],
        "skipped": [_candidate_report(candidate) for candidate in skipped],
        "results": [],
    }
    if dry_run:
        return report

    repository = CommunityPaperRepository()
    batch_id = f"curation-backfill-{uuid4().hex}"
    actor = str(created_by or _default_created_by()).strip()
    report["batch_id"] = batch_id
    report["created_by"] = actor
    for candidate in selected:
        result = await _publish_candidate(
            candidate=candidate,
            repository=repository,
            batch_id=batch_id,
            created_by=actor,
        )
        report["results"].append(result)
    return report


def _parse_values(values: Optional[list[str]]) -> Optional[set[str]]:
    if not values:
        return None
    parsed = {
        item.strip()
        for value in values
        for item in str(value or "").split(",")
        if item.strip()
    }
    return parsed or None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill admin curation records for completed translation tasks that were never published through admin curation."
    )
    parser.add_argument("--dry-run", action="store_true", help="Inspect candidates without writing database rows or assets.")
    parser.add_argument("--execute", action="store_true", help="Write curation jobs and publish selected candidates.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of publishable arXiv candidates to process.")
    parser.add_argument("--arxiv-id", action="append", default=None, help="Restrict to one or more arXiv IDs. Comma-separated values are accepted.")
    parser.add_argument("--task-id", action="append", default=None, help="Restrict to one or more task IDs. Comma-separated values are accepted.")
    parser.add_argument("--created-by", default=None, help="created_by value for inserted curation jobs. Defaults to the latest existing curation actor.")
    parser.add_argument("--report-json", type=Path, default=None, help="Optional path to write the JSON report.")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")
    if not args.dry_run and not args.execute:
        parser.error("Use --dry-run to inspect or --execute to write changes.")
    if args.dry_run and args.execute:
        parser.error("--dry-run and --execute are mutually exclusive.")

    report = asyncio.run(
        run_backfill(
            dry_run=bool(args.dry_run),
            limit=args.limit,
            arxiv_ids=_parse_values(args.arxiv_id),
            task_ids=_parse_values(args.task_id),
            created_by=args.created_by,
        )
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    print(rendered)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
