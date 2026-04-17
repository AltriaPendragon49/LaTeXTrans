from __future__ import annotations

import json
import logging
import mimetypes
import shutil
import zipfile
from pathlib import Path
from typing import Any, Optional

from backend.app.core.config import get_settings
from backend.app.services.storage_backend import (
    LocalDiskStorageBackend,
    StorageBackend,
    StoredObjectRef,
    build_storage_backend,
)

logger = logging.getLogger(__name__)
settings = get_settings()

OUTPUT_MANIFEST_FILENAME = "storage_manifest.json"
TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH = "_downloads/translated_source.zip"
TRANSLATED_SOURCE_SUFFIXES = {".tex", ".bib", ".cls", ".sty", ".bst"}


def _get_storage_backend() -> StorageBackend:
    return build_storage_backend(settings)


def _storage_uses_object_store(backend: StorageBackend) -> bool:
    return not isinstance(backend, LocalDiskStorageBackend)


def _normalize_stored_path(stored_path: str | Path) -> str:
    candidate = Path(stored_path)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(settings.base_dir.resolve())
        except Exception:
            return str(candidate).replace("\\", "/").strip("/")
    return str(candidate).replace("\\", "/").strip("/")


def normalize_stored_task_path(path: str | Path) -> str:
    return _normalize_stored_path(path)


def resolve_local_task_path(stored_path: str | Path) -> Path:
    candidate = Path(stored_path)
    if candidate.is_absolute():
        return candidate
    return settings.base_dir / candidate


def persist_task_directory(
    local_dir: Path,
    *,
    stored_path: str,
    delete_local: bool = False,
) -> str:
    backend = _get_storage_backend()
    local_dir = Path(local_dir)
    normalized_root = _normalize_stored_path(stored_path)

    if not local_dir.exists() or not local_dir.is_dir():
        raise FileNotFoundError(f"Task directory not found: {local_dir}")

    if not _storage_uses_object_store(backend):
        return str(local_dir)

    for file_path in sorted(path for path in local_dir.rglob("*") if path.is_file()):
        relative = file_path.relative_to(local_dir).as_posix()
        object_key = f"{normalized_root}/{relative}" if relative else normalized_root
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        backend.put_file(
            local_path=file_path,
            object_key=object_key,
            content_type=content_type,
            delete_local=False,
        )

    if delete_local and local_dir.exists():
        shutil.rmtree(local_dir)

    return normalized_root


def materialize_task_directory(
    stored_path: str,
    *,
    destination: Path,
    force: bool = False,
) -> Path:
    backend = _get_storage_backend()
    normalized_root = _normalize_stored_path(stored_path)
    destination = Path(destination)

    if not _storage_uses_object_store(backend):
        return resolve_local_task_path(stored_path)

    if destination.exists():
        if not force:
            return destination
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    refs = backend.list_files(prefix=normalized_root)
    if not refs:
        raise FileNotFoundError(f"No stored objects found for prefix: {normalized_root}")

    prefix = normalized_root.rstrip("/")
    prefixed_prefix = None
    if str(getattr(settings, "cos_base_prefix", "")).strip():
        prefixed_prefix = f"{str(settings.cos_base_prefix).strip().strip('/')}/{prefix}"
    for ref in sorted(refs, key=lambda item: item.object_key):
        object_key = str(ref.object_key or "").replace("\\", "/")
        if object_key.startswith(f"{prefix}/"):
            relative = object_key[len(prefix) + 1 :]
        elif prefixed_prefix and object_key.startswith(f"{prefixed_prefix}/"):
            relative = object_key[len(prefixed_prefix) + 1 :]
        elif object_key == prefix:
            relative = Path(object_key).name
        elif prefixed_prefix and object_key == prefixed_prefix:
            relative = Path(object_key).name
        else:
            continue
        if not relative:
            continue
        backend.download_file(object_key=ref.object_key, local_path=destination / relative)

    return destination


def materialize_task_output_asset(
    output_path: str,
    asset_name: str,
    *,
    destination_dir: Path,
    force: bool = False,
) -> Optional[Path]:
    manifest = read_task_output_manifest(output_path)
    relative_path = _manifest_relative_path_for_asset(manifest, asset_name)
    if not relative_path:
        return None

    destination_dir = Path(destination_dir)
    file_name = Path(relative_path).name
    if not file_name:
        return None

    destination = destination_dir / file_name
    if destination.exists() and not force:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)

    backend = _get_storage_backend()
    if not _storage_uses_object_store(backend):
        local_output_dir = resolve_local_task_path(output_path)
        local_asset = local_output_dir / relative_path
        if not local_asset.exists():
            raise FileNotFoundError(f"Task output asset not found: {local_asset}")
        shutil.copy2(local_asset, destination)
        return destination

    object_key = f"{_normalize_stored_path(output_path).rstrip('/')}/{relative_path}"
    backend.download_file(object_key=object_key, local_path=destination)
    return destination


def _iter_task_log_candidates(output_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    root_log = output_dir / "task_log.json"
    if root_log.is_file():
        candidates.append(root_log)
    for child in sorted(output_dir.iterdir()):
        if not child.is_dir():
            continue
        child_log = child / "task_log.json"
        if child_log.is_file():
            candidates.append(child_log)
    return candidates


def _find_translated_pdf_relative_path(output_dir: Path) -> Optional[str]:
    for log_path in _iter_task_log_candidates(output_dir):
        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for entry in reversed(entries if isinstance(entries, list) else []):
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


def _create_translated_source_archive(output_dir: Path) -> Optional[str]:
    archive_path = output_dir / TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    added = False
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in output_dir.rglob("*") if path.is_file()):
            if file_path == archive_path:
                continue
            if file_path.suffix.lower() not in TRANSLATED_SOURCE_SUFFIXES:
                continue
            archive.write(file_path, file_path.relative_to(output_dir))
            added = True

    if not added:
        archive_path.unlink(missing_ok=True)
        return None
    return TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH


def _build_output_manifest(output_dir: Path) -> dict[str, Any]:
    terminology_file = output_dir / "terminology_table.csv"
    if not terminology_file.exists():
        matches = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("terminology_table.csv"))
        terminology_relative = matches[0] if matches else None
    else:
        terminology_relative = terminology_file.relative_to(output_dir).as_posix()

    logs = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*.log") if path.is_file())

    return {
        "translated_pdf": _find_translated_pdf_relative_path(output_dir),
        "translated_source_archive": None,
        "terminology_csv": terminology_relative,
        "logs": logs,
    }


def persist_task_output_directory(
    *,
    task_id: str,
    local_output_dir: Path,
    delete_local: bool = False,
) -> str:
    output_dir = Path(local_output_dir)
    manifest = _build_output_manifest(output_dir)
    manifest["translated_source_archive"] = _create_translated_source_archive(output_dir)
    (output_dir / OUTPUT_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    stored_path = f"data/outputs/{task_id}"
    return persist_task_directory(output_dir, stored_path=stored_path, delete_local=delete_local)


def read_task_output_manifest(output_path: str) -> dict[str, Any]:
    backend = _get_storage_backend()
    manifest_rel_path = f"{_normalize_stored_path(output_path)}/{OUTPUT_MANIFEST_FILENAME}"

    if _storage_uses_object_store(backend):
        raw_text = backend.read_text(
            ref=StoredObjectRef(storage_backend="object_storage", object_key=manifest_rel_path)
        )
        return json.loads(raw_text)

    manifest_path = resolve_local_task_path(manifest_rel_path)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _manifest_relative_path_for_asset(manifest: dict[str, Any], asset_name: str) -> Optional[str]:
    if asset_name == "logs":
        logs = manifest.get("logs") or []
        return str(logs[0]).strip() if logs else None
    value = manifest.get(asset_name)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def build_task_output_download_url(
    output_path: str,
    asset_name: str,
    *,
    filename: str,
    content_type: str,
    inline: bool = False,
    expires_in: int = 600,
) -> Optional[str]:
    backend = _get_storage_backend()
    if not _storage_uses_object_store(backend):
        return None

    manifest = read_task_output_manifest(output_path)
    relative_path = _manifest_relative_path_for_asset(manifest, asset_name)
    if not relative_path:
        return None

    disposition = "inline" if inline else "attachment"
    params = {
        "response-content-disposition": f'{disposition}; filename="{filename}"',
        "response-content-type": content_type,
    }
    object_key = f"{_normalize_stored_path(output_path).rstrip('/')}/{relative_path}"
    return backend.build_download_url(
        object_key=object_key,
        expires_in=expires_in,
        params=params,
    )
