from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import time
from typing import Any, Iterable, Optional, Sequence
import zipfile

from backend.app.core.config import get_settings
from backend.app.db import get_database_dialect
from backend.app.services.storage_backend import CosStorageBackend, StoredObjectRef, _ensure_cos_config
from backend.scripts.mysql_script_connection import mysql_script_connection, resolve_mysql_script_config


OUTPUT_MANIFEST_FILENAME = "storage_manifest.json"
TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH = "_downloads/translated_source.zip"
TRANSLATED_SOURCE_SUFFIXES = {".tex", ".bib", ".cls", ".sty", ".bst"}
COMMUNITY_ASSET_TYPES = {"source_archive", "preview_html", "translated_pdf"}
COMPLETED_STATUSES = {"completed", "completed_with_warnings"}


@dataclass(frozen=True)
class PathAlias:
    source: str
    target: str


@dataclass
class PathResolver:
    base_dir: Path
    aliases: list[PathAlias] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.base_dir = self.base_dir.resolve(strict=False)

    @staticmethod
    def _norm(value: str | Path) -> str:
        return str(value).replace("\\", "/").rstrip("/")

    def resolve(self, value: str | Path, *, failed_artifact: bool = False) -> Path:
        raw = str(value or "").strip()
        if not raw:
            return self.base_dir
        normalized = self._norm(raw)
        for alias in self.aliases:
            source = self._norm(alias.source)
            target = self._norm(alias.target)
            if normalized == source:
                return Path(target)
            if normalized.startswith(f"{source}/"):
                return Path(target) / normalized[len(source) + 1 :]

        candidate = Path(raw)
        if candidate.is_absolute():
            return candidate
        if normalized.startswith("data/"):
            return self.base_dir / normalized
        if failed_artifact and normalized.startswith("failed_tasks/"):
            return self.base_dir / "data" / normalized
        return self.base_dir / normalized

    def logical_data_path(self, value: str | Path) -> str:
        path = self.resolve(value)
        try:
            return path.resolve(strict=False).relative_to(self.base_dir).as_posix()
        except Exception:
            normalized = self._norm(value).strip("/")
            marker = "/data/"
            if marker in normalized:
                return normalized[normalized.index(marker) + 1 :]
            if normalized.startswith("data/"):
                return normalized
            return normalized

    def logical_failed_artifact_path(self, value: str | Path) -> str:
        path = self.resolve(value, failed_artifact=True)
        try:
            relative = path.resolve(strict=False).relative_to(self.base_dir / "data").as_posix()
        except Exception:
            normalized = self._norm(value).strip("/")
            marker = "/failed_tasks/"
            if marker in normalized:
                return normalized[normalized.index(marker) + 1 :]
            if normalized.startswith("data/failed_tasks/"):
                return normalized[len("data/") :]
            return normalized
        if relative.startswith("failed_tasks/"):
            return relative
        return f"failed_tasks/{relative.strip('/')}"


@dataclass(frozen=True)
class LocalFileTarget:
    local_path: str
    object_key: str
    full_key: str
    size_bytes: int
    content_type: str
    kind: str


@dataclass(frozen=True)
class GeneratedTarget:
    output_dir: str
    object_key: str
    full_key: str
    content_type: str
    kind: str
    size_bytes: Optional[int] = None


@dataclass(frozen=True)
class DbUpdate:
    table: str
    row_id: str
    fields: dict[str, str]


@dataclass
class MigrationPlan:
    upload_files: list[LocalFileTarget] = field(default_factory=list)
    generated_uploads: list[GeneratedTarget] = field(default_factory=list)
    db_updates: list[DbUpdate] = field(default_factory=list)
    orphan_cos_keys: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    missing_local_assets: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    cleanup_roots: list[str] = field(default_factory=list)

    def target_full_keys(self) -> set[str]:
        return {item.full_key for item in self.upload_files} | {item.full_key for item in self.generated_uploads}

    def summary(self) -> dict[str, Any]:
        by_kind: dict[str, int] = {}
        bytes_by_kind: dict[str, int] = {}
        for item in self.upload_files:
            by_kind[item.kind] = by_kind.get(item.kind, 0) + 1
            bytes_by_kind[item.kind] = bytes_by_kind.get(item.kind, 0) + int(item.size_bytes)
        for item in self.generated_uploads:
            by_kind[item.kind] = by_kind.get(item.kind, 0) + 1
            if item.size_bytes is not None:
                bytes_by_kind[item.kind] = bytes_by_kind.get(item.kind, 0) + int(item.size_bytes)
        return {
            "upload_file_count": len(self.upload_files),
            "generated_upload_count": len(self.generated_uploads),
            "upload_bytes_known": sum(item.size_bytes for item in self.upload_files)
            + sum(item.size_bytes or 0 for item in self.generated_uploads),
            "upload_counts_by_kind": by_kind,
            "upload_known_bytes_by_kind": bytes_by_kind,
            "db_update_count": len(self.db_updates),
            "orphan_cos_key_count": len(self.orphan_cos_keys),
            "conflict_count": len(self.conflicts),
            "missing_local_asset_count": len(self.missing_local_assets),
            "warning_count": len(self.warnings),
            "cleanup_roots": self.cleanup_roots,
        }

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "upload_files": [asdict(item) for item in self.upload_files],
            "generated_uploads": [asdict(item) for item in self.generated_uploads],
            "db_updates": [asdict(item) for item in self.db_updates],
            "orphan_cos_keys": self.orphan_cos_keys,
            "conflicts": self.conflicts,
            "missing_local_assets": self.missing_local_assets,
            "warnings": self.warnings,
            "cleanup_roots": self.cleanup_roots,
        }


@dataclass
class MigrationContext:
    base_dir: Path
    cos_base_prefix: str
    resolver: PathResolver


def _normalize_key(value: str | Path) -> str:
    normalized = PurePosixPath(str(value).replace("\\", "/").strip("/"))
    parts = [part for part in normalized.parts if part and part != "."]
    if not parts:
        raise ValueError("Object key cannot be empty.")
    if any(part == ".." for part in parts):
        raise ValueError(f"Object key cannot contain path traversal: {value}")
    return "/".join(parts)


def full_cos_key(object_key: str, base_prefix: str) -> str:
    key = _normalize_key(object_key)
    prefix = str(base_prefix or "").strip().strip("/")
    if prefix and key != prefix and not key.startswith(f"{prefix}/"):
        return f"{prefix}/{key}"
    return key


def _content_type_for(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for file_path in sorted(path for path in root.rglob("*") if path.is_file()):
        yield file_path


def _relative_key_for_file(root: Path, file_path: Path, object_root: str) -> str:
    if root.is_file():
        return object_root
    relative = file_path.relative_to(root).as_posix()
    return f"{object_root.rstrip('/')}/{relative}"


def _add_file_targets(
    plan: MigrationPlan,
    *,
    root: Path,
    object_root: str,
    base_prefix: str,
    kind: str,
    skip_relative_paths: set[str] | None = None,
) -> None:
    skip_relative_paths = skip_relative_paths or set()
    for file_path in _iter_files(root):
        if root.is_dir():
            relative = file_path.relative_to(root).as_posix()
            if relative in skip_relative_paths:
                continue
        object_key = _relative_key_for_file(root, file_path, object_root)
        plan.upload_files.append(
            LocalFileTarget(
                local_path=str(file_path),
                object_key=object_key,
                full_key=full_cos_key(object_key, base_prefix),
                size_bytes=file_path.stat().st_size,
                content_type=_content_type_for(file_path),
                kind=kind,
            )
        )


def _iter_task_log_candidates(output_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    root_log = output_dir / "task_log.json"
    if root_log.is_file():
        candidates.append(root_log)
    if output_dir.is_dir():
        for child in sorted(output_dir.iterdir()):
            if child.is_dir() and (child / "task_log.json").is_file():
                candidates.append(child / "task_log.json")
    return candidates


def _find_translated_pdf_relative_path(output_dir: Path) -> Optional[str]:
    for log_path in _iter_task_log_candidates(output_dir):
        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in reversed(entries):
            if not isinstance(entry, dict):
                continue
            if entry.get("event") not in {"compilation_completed", "compilation_completed_with_warnings"}:
                continue
            raw_pdf_path = str(entry.get("pdf_path") or "").strip()
            if not raw_pdf_path:
                continue
            candidate = Path(raw_pdf_path)
            if not candidate.is_absolute():
                candidate = log_path.parent / candidate
            if candidate.is_file():
                try:
                    return candidate.relative_to(output_dir).as_posix()
                except Exception:
                    continue

    for candidate in sorted(output_dir.glob("*_translated.pdf")):
        if candidate.is_file():
            return candidate.relative_to(output_dir).as_posix()

    for child in sorted(output_dir.iterdir()):
        if not child.is_dir():
            continue
        expected = child / f"{child.name}.pdf"
        if expected.is_file():
            return expected.relative_to(output_dir).as_posix()

    return None


def _has_translated_source_members(output_dir: Path) -> bool:
    for file_path in output_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.as_posix().endswith(TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH):
            continue
        if file_path.name == OUTPUT_MANIFEST_FILENAME:
            continue
        if file_path.suffix.lower() in TRANSLATED_SOURCE_SUFFIXES:
            return True
    return False


def build_output_manifest(output_dir: Path) -> dict[str, Any]:
    terminology_file = output_dir / "terminology_table.csv"
    if terminology_file.exists():
        terminology_relative = terminology_file.relative_to(output_dir).as_posix()
    else:
        matches = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("terminology_table.csv"))
        terminology_relative = matches[0] if matches else None

    logs = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*.log") if path.is_file())
    return {
        "translated_pdf": _find_translated_pdf_relative_path(output_dir),
        "translated_source_archive": (
            TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH if _has_translated_source_members(output_dir) else None
        ),
        "terminology_csv": terminology_relative,
        "logs": logs,
    }


def _manifest_bytes_for_output(output_dir: Path) -> bytes:
    return json.dumps(build_output_manifest(output_dir), ensure_ascii=False, indent=2).encode("utf-8")


def create_translated_source_archive(output_dir: Path, archive_path: Path) -> bool:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    added = False
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in output_dir.rglob("*") if path.is_file()):
            if file_path == archive_path:
                continue
            try:
                relative = file_path.relative_to(output_dir).as_posix()
            except Exception:
                continue
            if relative in {OUTPUT_MANIFEST_FILENAME, TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH}:
                continue
            if file_path.suffix.lower() not in TRANSLATED_SOURCE_SUFFIXES:
                continue
            info = zipfile.ZipInfo(relative)
            try:
                date_time = time.localtime(file_path.stat().st_mtime)[:6]
            except OSError:
                date_time = (1980, 1, 1, 0, 0, 0)
            info.date_time = max(date_time, (1980, 1, 1, 0, 0, 0))
            with file_path.open("rb") as handle:
                archive.writestr(info, handle.read(), compress_type=zipfile.ZIP_DEFLATED)
            added = True
    if not added:
        archive_path.unlink(missing_ok=True)
    return added


def _row_to_dict(row: Any, columns: Sequence[str] | None = None) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    if columns:
        return {column: value for column, value in zip(columns, row)}
    try:
        return dict(row)
    except Exception:
        return {}


def _placeholder(_: int) -> str:
    if resolve_mysql_script_config() is not None or get_database_dialect() == "mysql":
        return "%s"
    return "?"


def _fetch_dicts(cursor: Any) -> list[dict[str, Any]]:
    rows = cursor.fetchall()
    columns = [item[0] for item in (cursor.description or [])]
    return [_row_to_dict(row, columns) for row in rows]


def load_inventory_from_mysql() -> dict[str, list[dict[str, Any]]]:
    with mysql_script_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "select id, paper_id, task_id, asset_type, storage_backend, file_path, "
            "file_name, mime_type, is_latest, created_at "
            "from paper_assets where file_path is not null and file_path <> ''"
        )
        paper_assets = _fetch_dicts(cursor)
        cursor.execute(
            "select task_id, status, source_path, output_path "
            "from translation_tasks where task_id is not null and task_id <> ''"
        )
        translation_tasks = _fetch_dicts(cursor)
        cursor.execute(
            "select job_id, task_id, status, failed_artifact_path, artifact_storage_backend "
            "from community_curation_jobs "
            "where failed_artifact_path is not null and failed_artifact_path <> ''"
        )
        curation_jobs = _fetch_dicts(cursor)
    return {
        "paper_assets": paper_assets,
        "translation_tasks": translation_tasks,
        "community_curation_jobs": curation_jobs,
    }


def build_migration_plan(
    *,
    context: MigrationContext,
    paper_assets: Sequence[dict[str, Any]],
    translation_tasks: Sequence[dict[str, Any]],
    curation_jobs: Sequence[dict[str, Any]],
    cos_objects: dict[str, int],
) -> MigrationPlan:
    plan = MigrationPlan()

    for row in paper_assets:
        asset_id = str(row.get("id") or "").strip()
        asset_type = str(row.get("asset_type") or "").strip()
        file_path_value = str(row.get("file_path") or "").strip()
        if not asset_id or not file_path_value or asset_type not in COMMUNITY_ASSET_TYPES:
            continue
        local_path = context.resolver.resolve(file_path_value)
        if not local_path.exists():
            plan.missing_local_assets.append(
                {"table": "paper_assets", "row_id": asset_id, "asset_type": asset_type, "path": file_path_value}
            )
            continue
        logical = context.resolver.logical_data_path(file_path_value)
        object_key = full_cos_key(logical, context.cos_base_prefix)
        _add_file_targets(
            plan,
            root=local_path,
            object_root=object_key,
            base_prefix=context.cos_base_prefix,
            kind=f"paper_asset:{asset_type}",
        )
        plan.db_updates.append(
            DbUpdate(
                table="paper_assets",
                row_id=asset_id,
                fields={"storage_backend": "object_storage", "file_path": object_key},
            )
        )

    for row in translation_tasks:
        task_id = str(row.get("task_id") or "").strip()
        if not task_id:
            continue
        fields: dict[str, str] = {}

        source_path_value = str(row.get("source_path") or "").strip()
        if source_path_value:
            source_path = context.resolver.resolve(source_path_value)
            logical_source = context.resolver.logical_data_path(source_path_value)
            fields["source_path"] = logical_source
            if source_path.exists():
                _add_file_targets(
                    plan,
                    root=source_path,
                    object_root=logical_source,
                    base_prefix=context.cos_base_prefix,
                    kind="task_source",
                )
            else:
                plan.missing_local_assets.append(
                    {"table": "translation_tasks", "row_id": task_id, "asset_type": "source_path", "path": source_path_value}
                )

        output_path_value = str(row.get("output_path") or "").strip()
        if output_path_value:
            output_path = context.resolver.resolve(output_path_value)
            logical_output = f"data/outputs/{task_id}"
            fields["output_path"] = logical_output
            if output_path.exists() and output_path.is_dir():
                _add_file_targets(
                    plan,
                    root=output_path,
                    object_root=logical_output,
                    base_prefix=context.cos_base_prefix,
                    kind="task_output",
                    skip_relative_paths={OUTPUT_MANIFEST_FILENAME, TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH},
                )
                manifest_key = f"{logical_output}/{OUTPUT_MANIFEST_FILENAME}"
                manifest_size = len(_manifest_bytes_for_output(output_path))
                plan.generated_uploads.append(
                    GeneratedTarget(
                        output_dir=str(output_path),
                        object_key=manifest_key,
                        full_key=full_cos_key(manifest_key, context.cos_base_prefix),
                        content_type="application/json",
                        kind="task_output_manifest",
                        size_bytes=manifest_size,
                    )
                )
                if _has_translated_source_members(output_path):
                    archive_key = f"{logical_output}/{TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH}"
                    plan.generated_uploads.append(
                        GeneratedTarget(
                            output_dir=str(output_path),
                            object_key=archive_key,
                            full_key=full_cos_key(archive_key, context.cos_base_prefix),
                            content_type="application/zip",
                            kind="task_output_source_archive",
                        )
                    )
            else:
                status = str(row.get("status") or "").strip().lower()
                payload = {
                    "table": "translation_tasks",
                    "row_id": task_id,
                    "asset_type": "output_path",
                    "status": status,
                    "path": output_path_value,
                }
                if status in COMPLETED_STATUSES:
                    plan.missing_local_assets.append(payload)
                else:
                    plan.warnings.append(payload)

        if fields:
            plan.db_updates.append(DbUpdate(table="translation_tasks", row_id=task_id, fields=fields))

    for row in curation_jobs:
        job_id = str(row.get("job_id") or "").strip()
        artifact_path_value = str(row.get("failed_artifact_path") or "").strip()
        if not job_id or not artifact_path_value:
            continue
        local_path = context.resolver.resolve(artifact_path_value, failed_artifact=True)
        logical = context.resolver.logical_failed_artifact_path(artifact_path_value)
        if local_path.exists():
            _add_file_targets(
                plan,
                root=local_path,
                object_root=logical,
                base_prefix=context.cos_base_prefix,
                kind="failed_curation_artifact",
            )
            plan.db_updates.append(
                DbUpdate(
                    table="community_curation_jobs",
                    row_id=job_id,
                    fields={"artifact_storage_backend": "object_storage", "failed_artifact_path": logical},
                )
            )
        else:
            plan.missing_local_assets.append(
                {
                    "table": "community_curation_jobs",
                    "row_id": job_id,
                    "asset_type": "failed_artifact_path",
                    "path": artifact_path_value,
                }
            )

    target_keys = plan.target_full_keys()
    for key, existing_size in cos_objects.items():
        if key not in target_keys:
            plan.orphan_cos_keys.append(key)

    expected_sizes: dict[str, int] = {}
    for item in plan.upload_files:
        expected_sizes[item.full_key] = item.size_bytes
    for item in plan.generated_uploads:
        if item.size_bytes is not None:
            expected_sizes[item.full_key] = item.size_bytes
    for key, expected_size in expected_sizes.items():
        existing_size = cos_objects.get(key)
        if existing_size is not None and int(existing_size) != int(expected_size):
            plan.conflicts.append({"key": key, "existing_size": existing_size, "expected_size": expected_size})

    data_dir = context.base_dir / "data"
    plan.cleanup_roots = [
        str(data_dir / "community_papers"),
        str(data_dir / "outputs"),
        str(data_dir / "uploads"),
        str(data_dir / "failed_tasks"),
    ]
    return plan


def _build_cos_backend_from_settings() -> CosStorageBackend:
    settings = get_settings()
    _ensure_cos_config(settings)
    return CosStorageBackend(
        bucket=settings.cos_bucket,  # type: ignore[arg-type]
        region=settings.cos_region,  # type: ignore[arg-type]
        secret_id=settings.cos_secret_id,  # type: ignore[arg-type]
        secret_key=settings.cos_secret_key,  # type: ignore[arg-type]
        base_prefix=settings.cos_base_prefix,
    )


def list_cos_objects(backend: CosStorageBackend, *, base_prefix: str) -> dict[str, int]:
    prefix = str(base_prefix or "").strip().strip("/")
    refs = backend.list_files(prefix=prefix) if prefix else _list_cos_without_prefix(backend)
    result: dict[str, int] = {}
    for ref in refs:
        key = str(ref.object_key or "").strip()
        if not key:
            continue
        try:
            size = int(ref.size_bytes or 0)
        except Exception:
            size = 0
        result[key] = size
    return result


def _list_cos_without_prefix(backend: CosStorageBackend) -> list[StoredObjectRef]:
    client = backend._get_client()
    marker: Optional[str] = None
    results: list[StoredObjectRef] = []
    while True:
        kwargs: dict[str, Any] = {"Bucket": backend.bucket}
        if marker:
            kwargs["Marker"] = marker
        response = client.list_objects(**kwargs) or {}
        contents = response.get("Contents") or []
        for item in contents:
            key = str(item.get("Key") or "").strip()
            if key and not key.endswith("/"):
                results.append(StoredObjectRef(storage_backend="object_storage", object_key=key, size_bytes=item.get("Size")))
        if response.get("IsTruncated") not in {True, "true", "True"}:
            break
        marker = response.get("NextMarker") or (contents[-1].get("Key") if contents else None)
        if not marker:
            break
    return results


def _put_bytes_via_temp(
    backend: CosStorageBackend,
    *,
    payload: bytes,
    object_key: str,
    content_type: str,
    temp_dir: Path,
) -> int:
    temp_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=temp_dir) as handle:
        handle.write(payload)
        temp_path = Path(handle.name)
    try:
        backend.put_file(local_path=temp_path, object_key=object_key, content_type=content_type, delete_local=False)
        return len(payload)
    finally:
        temp_path.unlink(missing_ok=True)


def _put_generated_archive(
    backend: CosStorageBackend,
    *,
    output_dir: Path,
    object_key: str,
    temp_dir: Path,
) -> int:
    temp_dir.mkdir(parents=True, exist_ok=True)
    archive_path = temp_dir / f"translated-source-{abs(hash((str(output_dir), object_key)))}.zip"
    try:
        if not create_translated_source_archive(output_dir, archive_path):
            raise RuntimeError(f"No translated source files found for {output_dir}")
        backend.put_file(
            local_path=archive_path,
            object_key=object_key,
            content_type="application/zip",
            delete_local=False,
        )
        return archive_path.stat().st_size
    finally:
        archive_path.unlink(missing_ok=True)


def delete_cos_orphans(backend: CosStorageBackend, keys: Sequence[str]) -> int:
    client = backend._get_client()
    deleted = 0
    for key in keys:
        client.delete_object(Bucket=backend.bucket, Key=key)
        deleted += 1
    return deleted


def upload_targets(
    backend: CosStorageBackend,
    plan: MigrationPlan,
    *,
    temp_dir: Path,
    overwrite_conflicts: bool,
) -> dict[str, Any]:
    current_cos = list_cos_objects(backend, base_prefix=backend.base_prefix)
    if plan.conflicts and not overwrite_conflicts:
        raise RuntimeError(f"Refusing upload with {len(plan.conflicts)} same-key size conflicts.")

    uploaded = 0
    skipped_same_size = 0
    uploaded_bytes = 0
    for item in plan.upload_files:
        existing_size = current_cos.get(item.full_key)
        if existing_size is not None and int(existing_size) == int(item.size_bytes):
            skipped_same_size += 1
            continue
        if existing_size is not None and not overwrite_conflicts:
            raise RuntimeError(f"Refusing to overwrite COS object with different size: {item.full_key}")
        backend.put_file(
            local_path=Path(item.local_path),
            object_key=item.object_key,
            content_type=item.content_type,
            delete_local=False,
        )
        current_cos[item.full_key] = item.size_bytes
        uploaded += 1
        uploaded_bytes += item.size_bytes
        if uploaded % 500 == 0:
            print(
                json.dumps(
                    {"progress": "upload", "uploaded": uploaded, "uploaded_bytes": uploaded_bytes},
                    ensure_ascii=False,
                ),
                flush=True,
            )

    for item in plan.generated_uploads:
        if item.kind == "task_output_manifest":
            payload = _manifest_bytes_for_output(Path(item.output_dir))
            existing_size = current_cos.get(item.full_key)
            if existing_size is not None and int(existing_size) == len(payload):
                skipped_same_size += 1
                continue
            if existing_size is not None and not overwrite_conflicts:
                raise RuntimeError(f"Refusing to overwrite COS object with different size: {item.full_key}")
            uploaded_bytes += _put_bytes_via_temp(
                backend,
                payload=payload,
                object_key=item.object_key,
                content_type=item.content_type,
                temp_dir=temp_dir,
            )
            current_cos[item.full_key] = len(payload)
            uploaded += 1
            if uploaded % 500 == 0:
                print(
                    json.dumps(
                        {"progress": "upload", "uploaded": uploaded, "uploaded_bytes": uploaded_bytes},
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        elif item.kind == "task_output_source_archive":
            existing_size = current_cos.get(item.full_key)
            if existing_size is not None and not overwrite_conflicts:
                # The dry-run manifest intentionally does not precompute archive size.
                raise RuntimeError(f"Refusing to overwrite generated archive without --overwrite-conflicts: {item.full_key}")
            archive_size = _put_generated_archive(
                backend,
                output_dir=Path(item.output_dir),
                object_key=item.object_key,
                temp_dir=temp_dir,
            )
            uploaded_bytes += archive_size
            current_cos[item.full_key] = archive_size
            uploaded += 1
            if uploaded % 500 == 0:
                print(
                    json.dumps(
                        {"progress": "upload", "uploaded": uploaded, "uploaded_bytes": uploaded_bytes},
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        else:
            raise RuntimeError(f"Unsupported generated upload kind: {item.kind}")

    return {"uploaded": uploaded, "skipped_same_size": skipped_same_size, "uploaded_bytes": uploaded_bytes}


def verify_uploaded_targets(
    backend: CosStorageBackend,
    plan: MigrationPlan,
    *,
    temp_dir: Path,
) -> dict[str, Any]:
    current_cos = list_cos_objects(backend, base_prefix=backend.base_prefix)
    missing: list[str] = []
    mismatched: list[dict[str, Any]] = []

    for item in plan.upload_files:
        existing_size = current_cos.get(item.full_key)
        if existing_size is None:
            missing.append(item.full_key)
        elif int(existing_size) != int(item.size_bytes):
            mismatched.append({"key": item.full_key, "expected_size": item.size_bytes, "existing_size": existing_size})

    for item in plan.generated_uploads:
        expected_size: Optional[int]
        if item.kind == "task_output_manifest":
            expected_size = len(_manifest_bytes_for_output(Path(item.output_dir)))
        elif item.kind == "task_output_source_archive":
            archive_path = temp_dir / f"verify-source-{abs(hash((item.output_dir, item.object_key)))}.zip"
            try:
                expected_size = archive_path.stat().st_size if create_translated_source_archive(Path(item.output_dir), archive_path) else None
            finally:
                archive_path.unlink(missing_ok=True)
        else:
            expected_size = item.size_bytes
        existing_size = current_cos.get(item.full_key)
        if existing_size is None:
            missing.append(item.full_key)
        elif expected_size is not None and int(existing_size) != int(expected_size):
            mismatched.append({"key": item.full_key, "expected_size": expected_size, "existing_size": existing_size})

    if missing or mismatched:
        raise RuntimeError(
            f"COS upload verification failed: missing={len(missing)}, mismatched={len(mismatched)}"
        )
    return {"verified_count": len(plan.upload_files) + len(plan.generated_uploads)}


def apply_db_updates(plan: MigrationPlan) -> int:
    paper_asset_updates = [item for item in plan.db_updates if item.table == "paper_assets"]
    task_updates = [item for item in plan.db_updates if item.table == "translation_tasks"]
    curation_updates = [item for item in plan.db_updates if item.table == "community_curation_jobs"]
    p0 = _placeholder(0)
    with mysql_script_connection(commit=True) as connection:
        cursor = connection.cursor()
        for item in paper_asset_updates:
            cursor.execute(
                f"update paper_assets set storage_backend = {p0}, file_path = {p0} where id = {p0}",
                (item.fields["storage_backend"], item.fields["file_path"], item.row_id),
            )
        for item in task_updates:
            fields = item.fields
            if "source_path" in fields and "output_path" in fields:
                cursor.execute(
                    f"update translation_tasks set source_path = {p0}, output_path = {p0} where task_id = {p0}",
                    (fields["source_path"], fields["output_path"], item.row_id),
                )
            elif "source_path" in fields:
                cursor.execute(
                    f"update translation_tasks set source_path = {p0} where task_id = {p0}",
                    (fields["source_path"], item.row_id),
                )
            elif "output_path" in fields:
                cursor.execute(
                    f"update translation_tasks set output_path = {p0} where task_id = {p0}",
                    (fields["output_path"], item.row_id),
                )
        for item in curation_updates:
            cursor.execute(
                f"update community_curation_jobs "
                f"set artifact_storage_backend = {p0}, failed_artifact_path = {p0} "
                f"where job_id = {p0}",
                (item.fields["artifact_storage_backend"], item.fields["failed_artifact_path"], item.row_id),
            )
    return len(plan.db_updates)


def cleanup_local_asset_roots(plan: MigrationPlan, *, base_dir: Path) -> int:
    data_dir = (base_dir / "data").resolve(strict=False)
    allowed = {
        (data_dir / "community_papers").resolve(strict=False),
        (data_dir / "outputs").resolve(strict=False),
        (data_dir / "uploads").resolve(strict=False),
        (data_dir / "failed_tasks").resolve(strict=False),
    }
    cleaned = 0
    for raw_root in plan.cleanup_roots:
        root = Path(raw_root).resolve(strict=False)
        if root not in allowed:
            raise RuntimeError(f"Refusing to clean unexpected path: {root}")
        if not root.exists():
            continue
        if not root.is_dir():
            raise RuntimeError(f"Refusing to clean non-directory asset root: {root}")
        shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        cleaned += 1
    return cleaned


def _parse_aliases(values: Sequence[str]) -> list[PathAlias]:
    aliases: list[PathAlias] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --path-alias value, expected FROM=TO: {value}")
        source, target = value.split("=", 1)
        aliases.append(PathAlias(source=source.strip(), target=target.strip()))
    return aliases


def _load_plan_inputs(backend: CosStorageBackend, context: MigrationContext) -> tuple[MigrationPlan, dict[str, int]]:
    inventory = load_inventory_from_mysql()
    cos_objects = list_cos_objects(backend, base_prefix=context.cos_base_prefix)
    plan = build_migration_plan(
        context=context,
        paper_assets=inventory["paper_assets"],
        translation_tasks=inventory["translation_tasks"],
        curation_jobs=inventory["community_curation_jobs"],
        cos_objects=cos_objects,
    )
    return plan, cos_objects


def _write_report(path: Path | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate production local assets to Tencent COS.")
    parser.add_argument(
        "--phase",
        choices=["plan", "delete-cos-orphans", "upload", "verify-uploads", "update-db", "cleanup-local"],
        default="plan",
    )
    parser.add_argument("--execute", action="store_true", help="Required for phases that change COS, DB, or local disk.")
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--base-dir", type=Path, default=None)
    parser.add_argument("--temp-dir", type=Path, default=None)
    parser.add_argument("--path-alias", action="append", default=[])
    parser.add_argument("--overwrite-conflicts", action="store_true")
    args = parser.parse_args(argv)

    settings = get_settings()
    base_dir = (args.base_dir or settings.base_dir).resolve(strict=False)
    temp_dir = (args.temp_dir or settings.storage_temp_dir / "production_asset_cos_migration").resolve(strict=False)
    context = MigrationContext(
        base_dir=base_dir,
        cos_base_prefix=str(settings.cos_base_prefix or "").strip().strip("/"),
        resolver=PathResolver(base_dir=base_dir, aliases=_parse_aliases(args.path_alias)),
    )
    backend = _build_cos_backend_from_settings()
    plan, cos_objects = _load_plan_inputs(backend, context)
    report: dict[str, Any] = {
        "phase": args.phase,
        "execute": bool(args.execute),
        "base_dir": str(base_dir),
        "cos_base_prefix": context.cos_base_prefix,
        "cos_object_count": len(cos_objects),
        "plan": plan.to_jsonable(),
        "result": None,
    }

    if args.phase == "plan":
        pass
    elif not args.execute:
        raise SystemExit(f"Phase {args.phase} requires --execute.")
    elif args.phase == "delete-cos-orphans":
        report["result"] = {"deleted": delete_cos_orphans(backend, plan.orphan_cos_keys)}
    elif args.phase == "upload":
        if plan.missing_local_assets:
            raise SystemExit(f"Refusing upload with missing local blockers: {len(plan.missing_local_assets)}")
        report["result"] = upload_targets(
            backend,
            plan,
            temp_dir=temp_dir,
            overwrite_conflicts=bool(args.overwrite_conflicts),
        )
    elif args.phase == "verify-uploads":
        report["result"] = verify_uploaded_targets(backend, plan, temp_dir=temp_dir)
    elif args.phase == "update-db":
        if plan.missing_local_assets:
            raise SystemExit(f"Refusing DB update with missing local blockers: {len(plan.missing_local_assets)}")
        if plan.conflicts and not args.overwrite_conflicts:
            raise SystemExit(f"Refusing DB update with unresolved COS conflicts: {len(plan.conflicts)}")
        report["result"] = {"verified": verify_uploaded_targets(backend, plan, temp_dir=temp_dir)}
        report["result"]["updated_rows"] = apply_db_updates(plan)
    elif args.phase == "cleanup-local":
        report["result"] = {"cleaned_roots": cleanup_local_asset_roots(plan, base_dir=base_dir)}

    _write_report(args.report_json, report)
    print(json.dumps({"summary": plan.summary(), "result": report["result"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
