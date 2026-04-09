from __future__ import annotations

import argparse
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.db import db_connection, get_database_dialect

ENTITY_ORDER = (
    "users",
    "user_roles",
    "user_settings",
    "translation_tasks",
    "papers",
    "paper_assets",
    "community_agent_conversations",
    "community_agent_runs",
    "community_agent_events",
)

ENTITY_TABLES: dict[str, dict[str, Any]] = {
    "users": {
        "table": "users",
        "columns": ("id", "external_provider", "external_user_id", "email", "display_name", "token_version", "status", "created_at", "updated_at"),
        "conflict_columns": ("id",),
    },
    "user_roles": {
        "table": "user_roles",
        "columns": ("user_id", "role", "created_at"),
        "conflict_columns": ("user_id", "role"),
    },
    "user_settings": {
        "table": "user_settings",
        "columns": (
            "user_id",
            "default_source_language",
            "default_target_language",
            "translation_mode",
            "compile_strategy",
            "translation_model",
            "generate_glossary",
            "use_author_api",
            "custom_base_url",
            "custom_api_key_encrypted",
            "default_formatting",
            "updated_at",
        ),
        "conflict_columns": ("user_id",),
    },
    "translation_tasks": {
        "table": "translation_tasks",
        "columns": (
            "task_id",
            "user_id",
            "source_type",
            "arxiv_id",
            "status",
            "stage",
            "progress",
            "message",
            "error",
            "detail_code",
            "source_language",
            "target_language",
            "translation_mode",
            "compile_strategy",
            "translation_model",
            "config_hash",
            "source_path",
            "output_path",
            "formatting",
            "generate_glossary",
            "use_author_api",
            "email_notification",
            "created_at",
            "completed_at",
        ),
        "conflict_columns": ("task_id",),
    },
    "papers": {
        "table": "papers",
        "columns": (
            "id",
            "created_by",
            "source",
            "arxiv_id",
            "title",
            "authors",
            "categories",
            "abstract_raw",
            "abstract_translated",
            "visibility",
            "status",
            "community_status",
            "trans_status",
            "trans_latest_task_id",
            "trans_latest_asset_pdf_id",
            "community_selected_task_id",
            "community_selected_asset_id",
            "like_count",
            "favorite_count",
            "comment_count",
            "view_count",
            "download_count",
            "official_published_at",
            "created_at",
            "updated_at",
        ),
        "conflict_columns": ("id",),
    },
    "paper_assets": {
        "table": "paper_assets",
        "columns": ("id", "paper_id", "task_id", "asset_type", "storage_backend", "file_path", "file_name", "mime_type", "is_latest", "created_at"),
        "conflict_columns": ("id",),
    },
    "community_agent_conversations": {
        "table": "community_agent_conversations",
        "columns": ("conversation_id", "user_id", "title", "created_at", "updated_at", "turns"),
        "conflict_columns": ("conversation_id", "user_id"),
    },
    "community_agent_runs": {
        "table": "community_agent_runs",
        "columns": ("run_id", "user_id", "conversation_id", "status", "intent", "mode", "message", "summary", "error", "report", "created_at", "updated_at", "completed_at"),
        "conflict_columns": ("run_id",),
    },
    "community_agent_events": {
        "table": "community_agent_events",
        "columns": ("run_id", "sequence_no", "event_type", "payload", "created_at"),
        "conflict_columns": ("run_id", "sequence_no"),
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _first(row: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def _as_str(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default
    normalized = str(value).strip()
    return normalized if normalized else default


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
    return default


def _as_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return default
    return default


def _as_timestamp(value: Any, default: str | None = None) -> str | None:
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        unix = float(value)
        if unix > 1_000_000_000_000:
            unix = unix / 1000.0
        return datetime.fromtimestamp(unix, tz=timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str):
        candidate = value.strip().replace("Z", "+00:00")
        if not candidate:
            return default
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return value.strip()
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    return _as_str(value, default=default)


def _as_json_value(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _as_json_string(value: Any, fallback: Any = None) -> str | None:
    parsed = _as_json_value(value)
    if parsed is None:
        parsed = fallback
    if parsed is None:
        return None
    return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))


def _as_json_list_string(value: Any) -> str:
    parsed = _as_json_value(value)
    if not isinstance(parsed, list):
        parsed = []
    return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))


def _coerce_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, dict)]
    return []


def _normalize_row(
    entity: str,
    row: dict[str, Any],
    *,
    asset_root: Path | None,
    missing_assets: list[dict[str, Any]],
) -> dict[str, Any]:
    now = _utc_now()

    if entity == "users":
        user_id = _as_str(_first(row, ("id", "user_id", "uid"), None), default=None)
        external_user_id = _as_str(_first(row, ("external_user_id", "externalUserId", "niutrans_user_id"), None), default=None)
        if user_id is None or external_user_id is None:
            raise ValueError("id and external_user_id are required")
        return {
            "id": user_id,
            "external_provider": _as_str(_first(row, ("external_provider", "provider"), "niutrans"), default="niutrans"),
            "external_user_id": external_user_id,
            "email": _as_str(_first(row, ("email",), None), default=None),
            "display_name": _as_str(_first(row, ("display_name", "name"), None), default=None),
            "token_version": _as_int(_first(row, ("token_version",), 1), default=1),
            "status": _as_str(_first(row, ("status",), "active"), default="active"),
            "created_at": _as_timestamp(_first(row, ("created_at",), None), default=now),
            "updated_at": _as_timestamp(_first(row, ("updated_at",), None), default=now),
        }

    if entity == "user_roles":
        user_id = _as_str(_first(row, ("user_id",), None), default=None)
        if user_id is None:
            raise ValueError("user_id is required")
        return {"user_id": user_id, "role": _as_str(_first(row, ("role",), "user"), default="user"), "created_at": _as_timestamp(_first(row, ("created_at",), None), default=now)}

    if entity == "user_settings":
        user_id = _as_str(_first(row, ("user_id",), None), default=None)
        if user_id is None:
            raise ValueError("user_id is required")
        return {
            "user_id": user_id,
            "default_source_language": _as_str(_first(row, ("default_source_language",), "en"), default="en"),
            "default_target_language": _as_str(_first(row, ("default_target_language",), "zh"), default="zh"),
            "translation_mode": _as_str(_first(row, ("translation_mode",), "full"), default="full"),
            "compile_strategy": _as_str(_first(row, ("compile_strategy",), "auto"), default="auto"),
            "translation_model": _as_str(_first(row, ("translation_model",), None), default=None),
            "generate_glossary": int(_as_bool(_first(row, ("generate_glossary",), True), default=True)),
            "use_author_api": int(_as_bool(_first(row, ("use_author_api",), True), default=True)),
            "custom_base_url": _as_str(_first(row, ("custom_base_url",), None), default=None),
            "custom_api_key_encrypted": _as_str(_first(row, ("custom_api_key_encrypted",), None), default=None),
            "default_formatting": _as_json_string(_first(row, ("default_formatting",), None)),
            "updated_at": _as_timestamp(_first(row, ("updated_at",), None), default=now),
        }

    if entity == "translation_tasks":
        task_id = _as_str(_first(row, ("task_id", "id"), None), default=None)
        if task_id is None:
            raise ValueError("task_id is required")
        return {
            "task_id": task_id,
            "user_id": _as_str(_first(row, ("user_id",), None), default=None),
            "source_type": _as_str(_first(row, ("source_type",), "upload"), default="upload"),
            "arxiv_id": _as_str(_first(row, ("arxiv_id",), None), default=None),
            "status": _as_str(_first(row, ("status",), "queued"), default="queued"),
            "stage": _as_str(_first(row, ("stage",), None), default=None),
            "progress": _as_int(_first(row, ("progress",), 0), default=0),
            "message": _as_str(_first(row, ("message",), None), default=None),
            "error": _as_str(_first(row, ("error",), None), default=None),
            "detail_code": _as_str(_first(row, ("detail_code",), None), default=None),
            "source_language": _as_str(_first(row, ("source_language",), "en"), default="en"),
            "target_language": _as_str(_first(row, ("target_language",), "zh"), default="zh"),
            "translation_mode": _as_str(_first(row, ("translation_mode",), "full"), default="full"),
            "compile_strategy": _as_str(_first(row, ("compile_strategy",), "auto"), default="auto"),
            "translation_model": _as_str(_first(row, ("translation_model",), None), default=None),
            "config_hash": _as_str(_first(row, ("config_hash",), None), default=None),
            "source_path": _as_str(_first(row, ("source_path",), None), default=None),
            "output_path": _as_str(_first(row, ("output_path",), None), default=None),
            "formatting": _as_json_string(_first(row, ("formatting",), None)),
            "generate_glossary": int(_as_bool(_first(row, ("generate_glossary",), True), default=True)),
            "use_author_api": int(_as_bool(_first(row, ("use_author_api",), True), default=True)),
            "email_notification": int(_as_bool(_first(row, ("email_notification",), False), default=False)),
            "created_at": _as_timestamp(_first(row, ("created_at",), None), default=now),
            "completed_at": _as_timestamp(_first(row, ("completed_at",), None), default=None),
        }

    if entity == "papers":
        paper_id = _as_str(_first(row, ("id", "paper_id"), None), default=None)
        title = _as_str(_first(row, ("title",), None), default=None)
        if paper_id is None or title is None:
            raise ValueError("id and title are required")
        return {
            "id": paper_id,
            "created_by": _as_str(_first(row, ("created_by", "user_id"), None), default=None),
            "source": _as_str(_first(row, ("source",), "arxiv"), default="arxiv"),
            "arxiv_id": _as_str(_first(row, ("arxiv_id",), None), default=None),
            "title": title,
            "authors": _as_json_list_string(_first(row, ("authors",), None)),
            "categories": _as_json_list_string(_first(row, ("categories",), None)),
            "abstract_raw": _as_str(_first(row, ("abstract_raw",), None), default=None),
            "abstract_translated": _as_str(_first(row, ("abstract_translated",), None), default=None),
            "visibility": _as_str(_first(row, ("visibility",), "public"), default="public"),
            "status": _as_str(_first(row, ("status",), "published"), default="published"),
            "community_status": _as_str(_first(row, ("community_status",), "active"), default="active"),
            "trans_status": _as_str(_first(row, ("trans_status",), "queued"), default="queued"),
            "trans_latest_task_id": _as_str(_first(row, ("trans_latest_task_id",), None), default=None),
            "trans_latest_asset_pdf_id": _as_str(_first(row, ("trans_latest_asset_pdf_id",), None), default=None),
            "community_selected_task_id": _as_str(_first(row, ("community_selected_task_id",), None), default=None),
            "community_selected_asset_id": _as_str(_first(row, ("community_selected_asset_id",), None), default=None),
            "like_count": _as_int(_first(row, ("like_count",), 0), default=0),
            "favorite_count": _as_int(_first(row, ("favorite_count",), 0), default=0),
            "comment_count": _as_int(_first(row, ("comment_count",), 0), default=0),
            "view_count": _as_int(_first(row, ("view_count",), 0), default=0),
            "download_count": _as_int(_first(row, ("download_count",), 0), default=0),
            "official_published_at": _as_timestamp(_first(row, ("official_published_at",), None), default=None),
            "created_at": _as_timestamp(_first(row, ("created_at",), None), default=now),
            "updated_at": _as_timestamp(_first(row, ("updated_at",), None), default=now),
        }

    if entity == "paper_assets":
        asset_id = _as_str(_first(row, ("id", "asset_id"), None), default=None)
        paper_id = _as_str(_first(row, ("paper_id",), None), default=None)
        if asset_id is None or paper_id is None:
            raise ValueError("id and paper_id are required")
        file_path = _as_str(_first(row, ("file_path", "path", "asset_path"), None), default=None)
        if file_path is None:
            raise ValueError("file_path is required")
        resolved = Path(file_path) if Path(file_path).is_absolute() else ((asset_root or Path.cwd()) / Path(file_path))
        if not resolved.exists():
            missing_assets.append({"entity": "paper_assets", "row_id": asset_id, "paper_id": paper_id, "path": file_path, "resolved_path": str(resolved)})
        file_name = _as_str(_first(row, ("file_name",), None), default=None) or Path(file_path).name
        mime_type = _as_str(_first(row, ("mime_type",), None), default=None) or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return {
            "id": asset_id,
            "paper_id": paper_id,
            "task_id": _as_str(_first(row, ("task_id",), None), default=None),
            "asset_type": _as_str(_first(row, ("asset_type",), "translated_pdf"), default="translated_pdf"),
            "storage_backend": _as_str(_first(row, ("storage_backend",), "local_disk"), default="local_disk"),
            "file_path": file_path,
            "file_name": file_name,
            "mime_type": mime_type,
            "is_latest": int(_as_bool(_first(row, ("is_latest",), True), default=True)),
            "created_at": _as_timestamp(_first(row, ("created_at",), None), default=now),
        }

    if entity == "community_agent_conversations":
        conversation_id = _as_str(_first(row, ("conversation_id", "id"), None), default=None)
        user_id = _as_str(_first(row, ("user_id",), None), default=None)
        if conversation_id is None or user_id is None:
            raise ValueError("conversation_id and user_id are required")
        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": _as_str(_first(row, ("title",), "New chat"), default="New chat"),
            "created_at": _as_timestamp(_first(row, ("created_at",), None), default=now),
            "updated_at": _as_timestamp(_first(row, ("updated_at",), None), default=now),
            "turns": _as_json_string(_first(row, ("turns",), []), fallback=[]),
        }

    if entity == "community_agent_runs":
        run_id = _as_str(_first(row, ("run_id", "id"), None), default=None)
        if run_id is None:
            raise ValueError("run_id is required")
        return {
            "run_id": run_id,
            "user_id": _as_str(_first(row, ("user_id",), None), default=None),
            "conversation_id": _as_str(_first(row, ("conversation_id",), None), default=None),
            "status": _as_str(_first(row, ("status",), "queued"), default="queued"),
            "intent": _as_str(_first(row, ("intent",), "answer"), default="answer"),
            "mode": _as_str(_first(row, ("mode",), "chat"), default="chat"),
            "message": _as_str(_first(row, ("message",), None), default=None),
            "summary": _as_str(_first(row, ("summary",), None), default=None),
            "error": _as_str(_first(row, ("error",), None), default=None),
            "report": _as_json_string(_first(row, ("report",), None), fallback=None),
            "created_at": _as_timestamp(_first(row, ("created_at",), None), default=now),
            "updated_at": _as_timestamp(_first(row, ("updated_at",), None), default=now),
            "completed_at": _as_timestamp(_first(row, ("completed_at",), None), default=None),
        }

    if entity == "community_agent_events":
        run_id = _as_str(_first(row, ("run_id",), None), default=None)
        sequence_no = _first(row, ("sequence_no", "sequence"), None)
        if run_id is None or sequence_no is None:
            raise ValueError("run_id and sequence_no are required")
        payload = _as_json_string(_first(row, ("payload",), None), fallback={"type": "status", "data": {}})
        event_type = _as_str(_first(row, ("event_type", "type"), None), default=None)
        if event_type is None:
            parsed = _as_json_value(payload)
            event_type = _as_str(parsed.get("type"), default="status") if isinstance(parsed, dict) else "status"
        return {
            "run_id": run_id,
            "sequence_no": _as_int(sequence_no, default=0),
            "event_type": event_type,
            "payload": payload,
            "created_at": _as_timestamp(_first(row, ("created_at", "timestamp"), None), default=now),
        }

    raise ValueError(f"Unsupported entity: {entity}")


def _load_rows(file_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return _coerce_rows(payload)


def _build_upsert_sql(table: str, columns: tuple[str, ...], conflict_columns: tuple[str, ...], *, dialect: str) -> str:
    column_list = ", ".join(columns)
    placeholders = ", ".join("?" if dialect == "sqlite" else "%s" for _ in columns)
    update_columns = tuple(column for column in columns if column not in conflict_columns)
    if dialect == "sqlite":
        if update_columns:
            updates = ", ".join(f"{column} = excluded.{column}" for column in update_columns)
            return f"insert into {table} ({column_list}) values ({placeholders}) on conflict ({', '.join(conflict_columns)}) do update set {updates}"
        return f"insert into {table} ({column_list}) values ({placeholders}) on conflict ({', '.join(conflict_columns)}) do nothing"
    updates = ", ".join(f"{column} = values({column})" for column in update_columns)
    return f"insert into {table} ({column_list}) values ({placeholders}) on duplicate key update {updates}"


def _row_exists(cursor, *, table: str, conflict_columns: tuple[str, ...], row: dict[str, Any], dialect: str) -> bool:
    placeholder = "?" if dialect == "sqlite" else "%s"
    where = " and ".join(f"{column} = {placeholder}" for column in conflict_columns)
    values = tuple(row[column] for column in conflict_columns)
    cursor.execute(f"select 1 from {table} where {where} limit 1", values)
    return cursor.fetchone() is not None


def run_import(*, input_dir: Path, dry_run: bool = False, asset_root: Path | None = None) -> dict[str, Any]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "dry_run": bool(dry_run),
        "input_dir": str(input_dir),
        "asset_root": str(asset_root) if asset_root is not None else str(Path.cwd()),
        "dialect": None if dry_run else get_database_dialect(),
        "entities": {
            entity: {
                "source_rows": 0,
                "valid_rows": 0,
                "skipped_rows": 0,
                "inserted": 0,
                "updated": 0,
                "missing_assets": 0,
                "errors": 0,
            }
            for entity in ENTITY_ORDER
        },
        "missing_input_files": [],
        "missing_assets": [],
        "errors": [],
    }
    normalized_rows: dict[str, list[dict[str, Any]]] = {entity: [] for entity in ENTITY_ORDER}

    for entity in ENTITY_ORDER:
        entity_report = report["entities"][entity]
        file_path = input_dir / f"{entity}.json"
        if not file_path.exists():
            report["missing_input_files"].append(str(file_path))
            continue

        try:
            rows = _load_rows(file_path)
        except Exception as exc:
            entity_report["errors"] += 1
            report["errors"].append({"entity": entity, "error": f"Failed to parse {file_path.name}: {exc}"})
            continue

        entity_report["source_rows"] = len(rows)
        for row_index, row in enumerate(rows):
            try:
                normalized = _normalize_row(entity, row, asset_root=asset_root, missing_assets=report["missing_assets"])
            except Exception as exc:
                entity_report["errors"] += 1
                entity_report["skipped_rows"] += 1
                report["errors"].append({"entity": entity, "row_index": row_index, "error": str(exc)})
                continue
            normalized_rows[entity].append(normalized)
            entity_report["valid_rows"] += 1

        if entity == "paper_assets":
            entity_report["missing_assets"] = len(report["missing_assets"])

    if dry_run:
        for entity in ENTITY_ORDER:
            report["entities"][entity]["would_upsert"] = report["entities"][entity]["valid_rows"]
        return report

    dialect = get_database_dialect()
    with db_connection(commit=True) as connection:
        cursor = connection.cursor()
        for entity in ENTITY_ORDER:
            entity_report = report["entities"][entity]
            config = ENTITY_TABLES[entity]
            sql = _build_upsert_sql(config["table"], config["columns"], config["conflict_columns"], dialect=dialect)
            for row_index, row in enumerate(normalized_rows[entity]):
                try:
                    existed = _row_exists(cursor, table=config["table"], conflict_columns=config["conflict_columns"], row=row, dialect=dialect)
                    cursor.execute(sql, tuple(row[column] for column in config["columns"]))
                    if existed:
                        entity_report["updated"] += 1
                    else:
                        entity_report["inserted"] += 1
                except Exception as exc:
                    entity_report["errors"] += 1
                    entity_report["skipped_rows"] += 1
                    report["errors"].append({"entity": entity, "row_index": row_index, "error": str(exc)})

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Supabase-exported JSON files into local MySQL/SQLite schema.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing JSON exports (e.g. users.json).")
    parser.add_argument("--asset-root", type=Path, default=None, help="Optional root path for validating relative asset file paths.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report only; do not write to database.")
    parser.add_argument("--report-json", type=Path, default=None, help="Optional path to write structured report JSON.")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit non-zero if report contains errors.")
    args = parser.parse_args()

    report = run_import(input_dir=args.input_dir, dry_run=args.dry_run, asset_root=args.asset_root)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    print(serialized)

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(serialized, encoding="utf-8")

    if args.fail_on_error and report.get("errors"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
