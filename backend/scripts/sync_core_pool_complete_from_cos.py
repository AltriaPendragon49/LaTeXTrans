from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import re
import shutil
import shlex
import sys
import tarfile
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Optional, Sequence

from backend.app.core.config import get_settings
from backend.app.db import get_database_dialect
from backend.app.services.storage_backend import (
    CosStorageBackend,
    LocalDiskStorageBackend,
    StorageBackend,
    StoredObjectRef,
    _ensure_cos_config,
)
from backend.scripts.mysql_script_connection import mysql_script_connection, resolve_mysql_script_config

ARXIV_ID_PATTERN = re.compile(r"(?<!\d)(\d{4}\.\d{4,5}(?:v\d+)?)(?!\d)")
_SCRIPT_PATH = Path(__file__).resolve()
if _SCRIPT_PATH.name == "<stdin>":
    _REPO_ROOT = Path.cwd()
    _BACKEND_ROOT = _REPO_ROOT / "backend"
else:
    _BACKEND_ROOT = _SCRIPT_PATH.parents[1]
    _REPO_ROOT = _SCRIPT_PATH.parents[2]

DEFAULT_COMPLETE_PATH = _BACKEND_ROOT / "arxiv_id" / "core_pool" / "complete.md"
DEFAULT_DESTINATION_ROOT = _BACKEND_ROOT / "data" / "community_papers"
DEFAULT_REMOTE_CREDENTIAL_PATH = (
    _REPO_ROOT
    / "texts"
    / "\u4e91\u90e8\u7f72\u4e0e\u8fd0\u7ef4"
    / "\u5bc6\u94a5"
    / "\u670d\u52a1\u56681.md"
)
DEFAULT_REMOTE_CONTAINER = "latextrans-backend"
DEFAULT_REMOTE_COMPLETE_PATH = "/app/backend/arxiv_id/core_pool/complete.md"
DEFAULT_REMOTE_DESTINATION_ROOT = "/app/backend/data/community_papers"
DEFAULT_REMOTE_HOST_DATA_ROOT = "/srv/LaTexTrans/backend/data"
DEFAULT_REMOTE_ARCHIVE_DIR = "/tmp"
DEFAULT_DIRECT_PREFIX_ROOTS = (
    "data/community_papers",
    "community_papers",
    "data/core_pool_complete",
    "core_pool_complete",
    "data/outputs",
    "outputs",
)
DEFAULT_SCAN_PREFIX_ROOTS = (
    "data/community_papers",
    "community_papers",
    "data/core_pool_complete",
    "core_pool_complete",
    "data/outputs",
    "outputs",
)
REQUIRED_ASSET_GROUPS = {"source", "preview", "translated"}
SUPPORTED_DB_STORAGE_BACKENDS = {"local_disk", "object_storage"}
REQUIRED_DB_ASSET_TYPES = {"source_archive", "preview_html", "translated_pdf"}
DB_ASSET_DESTINATION_GROUPS = {
    "source_archive": "source",
    "preview_html": "preview",
    "translated_pdf": "translated",
}


@dataclass(frozen=True)
class RemoteServerCredentials:
    host: str
    username: str
    password: str
    port: int = 22

    def safe_summary(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "username": self.username,
            "port": self.port,
            "password": "<redacted>",
        }


def parse_complete_arxiv_ids(markdown: str) -> list[str]:
    seen: set[str] = set()
    arxiv_ids: list[str] = []
    for match in ARXIV_ID_PATTERN.finditer(markdown):
        arxiv_id = match.group(1)
        if arxiv_id in seen:
            continue
        seen.add(arxiv_id)
        arxiv_ids.append(arxiv_id)
    return arxiv_ids


def read_complete_arxiv_ids(complete_path: Path = DEFAULT_COMPLETE_PATH) -> list[str]:
    return parse_complete_arxiv_ids(complete_path.read_text(encoding="utf-8"))


def _build_cos_storage_backend() -> StorageBackend:
    settings = get_settings()
    _ensure_cos_config(settings)
    return CosStorageBackend(
        bucket=settings.cos_bucket,  # type: ignore[arg-type]
        region=settings.cos_region,  # type: ignore[arg-type]
        secret_id=settings.cos_secret_id,  # type: ignore[arg-type]
        secret_key=settings.cos_secret_key,  # type: ignore[arg-type]
        base_prefix=settings.cos_base_prefix,
    )


def _build_storage_backend_for_record(storage_backend: str) -> StorageBackend:
    settings = get_settings()
    normalized = str(storage_backend or "").strip().lower()
    if normalized == "local_disk":
        return LocalDiskStorageBackend(root=settings.local_storage_root)
    if normalized == "object_storage":
        return _build_cos_storage_backend()
    raise ValueError(f"Unsupported asset storage backend: {storage_backend}")


def _normalize_posix(value: str | Path) -> str:
    return str(value).replace("\\", "/").strip("/")


def _extract_candidate_prefix(object_key: str) -> str | None:
    normalized = _normalize_posix(object_key)
    for marker in ("/source/", "/preview/", "/translated/"):
        index = normalized.find(marker)
        if index != -1:
            return normalized[:index]
    parent = PurePosixPath(normalized).parent.as_posix().strip("/")
    return parent or None


def _relative_destination_for_key(object_key: str, prefix: str) -> str | None:
    normalized_key = _normalize_posix(object_key)
    normalized_prefix = _normalize_posix(prefix)
    if normalized_key.startswith(f"{normalized_prefix}/"):
        relative = normalized_key[len(normalized_prefix) + 1 :]
    elif normalized_key == normalized_prefix:
        relative = PurePosixPath(normalized_key).name
    else:
        relative = PurePosixPath(normalized_key).name

    if not relative:
        return None

    for asset_group in REQUIRED_ASSET_GROUPS:
        if relative == asset_group or relative.startswith(f"{asset_group}/"):
            return relative

    file_name = PurePosixPath(relative).name
    suffix = PurePosixPath(file_name).suffix.lower()
    if file_name == "metadata.json":
        return file_name
    if file_name == "preview.html" or suffix in {".html", ".htm"}:
        return f"preview/{file_name}"
    if suffix == ".pdf":
        return f"translated/{file_name}"
    return f"source/{relative}"


def _row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


def _script_placeholder(index: int) -> str:
    if resolve_mysql_script_config() is not None or get_database_dialect() == "mysql":
        return "%s"
    return "?"


def load_latest_backend_asset_records() -> list[dict[str, Any]]:
    asset_types = sorted(REQUIRED_DB_ASSET_TYPES)
    storage_backends = sorted(SUPPORTED_DB_STORAGE_BACKENDS)
    asset_placeholders = ", ".join(_script_placeholder(index) for index in range(len(asset_types)))
    storage_placeholders = ", ".join(
        _script_placeholder(len(asset_types) + index)
        for index in range(len(storage_backends))
    )
    latest_placeholder = _script_placeholder(len(asset_types) + len(storage_backends))
    query = (
        "select "
        "papers.id as paper_id, "
        "papers.arxiv_id as arxiv_id, "
        "paper_assets.asset_type as asset_type, "
        "paper_assets.storage_backend as storage_backend, "
        "paper_assets.file_path as file_path, "
        "paper_assets.file_name as file_name, "
        "paper_assets.mime_type as mime_type, "
        "paper_assets.created_at as created_at "
        "from paper_assets "
        "join papers on papers.id = paper_assets.paper_id "
        f"where paper_assets.asset_type in ({asset_placeholders}) "
        f"and paper_assets.is_latest = {latest_placeholder} "
        f"and paper_assets.storage_backend in ({storage_placeholders}) "
        "and papers.arxiv_id is not null "
        "and papers.arxiv_id <> '' "
        "order by papers.arxiv_id asc, paper_assets.created_at desc"
    )
    with mysql_script_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (*asset_types, True, *storage_backends))
        return [_row_to_dict(row) for row in cursor.fetchall()]


def _asset_groups_for_records(records: Sequence[dict[str, Any]]) -> set[str]:
    asset_groups: set[str] = set()
    for record in records:
        group = DB_ASSET_DESTINATION_GROUPS.get(str(record.get("asset_type") or "").strip())
        if not group:
            continue
        asset_groups.add(group)
    return asset_groups


def _relative_destination_for_asset_record(record: dict[str, Any]) -> str | None:
    asset_type = str(record.get("asset_type") or "").strip()
    group = DB_ASSET_DESTINATION_GROUPS.get(asset_type)
    object_key = str(record.get("file_path") or "").strip()
    if not group or not object_key:
        return None

    file_name = str(record.get("file_name") or "").strip()
    if not file_name:
        file_name = PurePosixPath(_normalize_posix(object_key)).name
    file_name = PurePosixPath(file_name).name
    if not file_name:
        return None
    return f"{group}/{file_name}"


def _download_asset_record(
    backend: StorageBackend,
    record: dict[str, Any],
    local_path: Path,
) -> Path:
    object_key = str(record.get("file_path") or "").strip()
    storage_backend = str(record.get("storage_backend") or "").strip().lower()
    if storage_backend == "local_disk":
        source_path: Path | None = None
        try:
            source_path = backend.resolve_local_path(
                StoredObjectRef(storage_backend="local_disk", object_key=object_key)
            )
        except Exception:
            source_path = None
        if source_path is not None and source_path.is_dir():
            shutil.copytree(source_path, local_path)
            return local_path

    return backend.download_file(object_key=object_key, local_path=local_path)


def discover_complete_asset_candidates(
    asset_records: Optional[Sequence[dict[str, Any]]] = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    complete_matches: dict[str, dict[str, list[dict[str, Any]]]] = {}
    records = list(asset_records) if asset_records is not None else load_latest_backend_asset_records()
    records_by_paper: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for raw_record in records:
        record = _row_to_dict(raw_record)
        arxiv_id = str(record.get("arxiv_id") or "").strip()
        paper_id = str(record.get("paper_id") or "").strip()
        asset_type = str(record.get("asset_type") or "").strip()
        object_key = str(record.get("file_path") or "").strip()
        storage_backend = str(record.get("storage_backend") or "").strip()
        if not arxiv_id or not paper_id or asset_type not in REQUIRED_DB_ASSET_TYPES:
            continue
        if storage_backend not in SUPPORTED_DB_STORAGE_BACKENDS or not object_key:
            continue

        records_by_paper.setdefault((arxiv_id, paper_id), {})[asset_type] = record

    for (arxiv_id, paper_id), records_by_type in sorted(records_by_paper.items()):
        if not REQUIRED_DB_ASSET_TYPES.issubset(records_by_type):
            continue
        complete_matches.setdefault(arxiv_id, {})[paper_id] = [
            records_by_type[asset_type]
            for asset_type in sorted(REQUIRED_DB_ASSET_TYPES)
        ]
    return complete_matches


def write_complete_arxiv_ids(complete_path: Path, arxiv_ids: Sequence[str]) -> None:
    complete_path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{arxiv_id}\n" for arxiv_id in arxiv_ids)
    complete_path.write_text(body, encoding="utf-8")


def parse_remote_server_credentials(markdown: str) -> RemoteServerCredentials:
    host_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", markdown)
    if not host_match:
        raise ValueError("Could not find server host in credential note.")

    username_match = re.search(r"(?:user|username|\u7528\u6237)\s*[:：]\s*(\S+)", markdown, re.IGNORECASE)
    password_match = re.search(r"(?:password|\u5bc6\u7801)\s*[:：]\s*(\S+)", markdown, re.IGNORECASE)
    if password_match is None:
        password_match = re.search(r"(NiuTrans\S+)", markdown)

    if not password_match:
        raise ValueError("Could not find server password in credential note.")

    return RemoteServerCredentials(
        host=host_match.group(1),
        username=username_match.group(1) if username_match else "ubuntu",
        password=password_match.group(1),
        port=22,
    )


def read_remote_server_credentials(
    credential_path: Path = DEFAULT_REMOTE_CREDENTIAL_PATH,
) -> RemoteServerCredentials:
    return parse_remote_server_credentials(
        Path(credential_path).read_text(encoding="utf-8", errors="ignore")
    )


def build_remote_sync_command(
    *,
    container_name: str = DEFAULT_REMOTE_CONTAINER,
    complete_path: str = DEFAULT_REMOTE_COMPLETE_PATH,
    destination_root: str = DEFAULT_REMOTE_DESTINATION_ROOT,
    arxiv_ids: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
) -> str:
    parts = [
        "docker",
        "exec",
        "-i",
        "-w",
        "/app",
        container_name,
        "python",
        "-",
        "--complete-path",
        complete_path,
        "--destination-root",
        destination_root,
    ]
    for arxiv_id in arxiv_ids or ():
        parts.extend(["--arxiv-id", str(arxiv_id)])
    if limit is not None:
        parts.extend(["--limit", str(limit)])
    if force:
        parts.append("--force")
    return " ".join(shlex.quote(part) for part in parts)


def safe_extract_tar(archive: tarfile.TarFile, destination_root: Path) -> None:
    destination_root = Path(destination_root).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    for member in archive.getmembers():
        target_path = (destination_root / member.name).resolve()
        if not target_path.is_relative_to(destination_root):
            raise ValueError(f"Unsafe archive member path: {member.name}")
        if member.issym() or member.islnk():
            raise ValueError(f"Unsafe archive member link: {member.name}")
    try:
        archive.extractall(destination_root, filter="data")
    except TypeError:
        archive.extractall(destination_root)


def _build_remote_archive_script(
    *,
    arxiv_ids: Sequence[str],
    host_data_root: str,
    archive_path: str,
) -> str:
    return f"""
import json
import re
import tarfile
from pathlib import Path

arxiv_ids = json.loads({json.dumps(json.dumps(list(arxiv_ids)))})
host_data_root = Path({json.dumps(host_data_root)})
archive_path = Path({json.dumps(archive_path)})
base = host_data_root / "community_papers"
pattern = re.compile(r"^\\d{{4}}\\.\\d{{4,5}}(?:v\\d+)?$")
missing = []
archived = []
archive_path.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(archive_path, "w:gz") as archive:
    for arxiv_id in arxiv_ids:
        if not pattern.match(arxiv_id):
            raise ValueError(f"Unsafe arXiv ID: {{arxiv_id}}")
        source = (base / arxiv_id).resolve()
        if not source.exists() or not source.is_dir():
            missing.append(arxiv_id)
            continue
        if source.parent != base.resolve():
            raise ValueError(f"Resolved path escapes base: {{source}}")
        archive.add(source, arcname=arxiv_id)
        archived.append(arxiv_id)
if missing:
    archive_path.unlink(missing_ok=True)
    print(json.dumps({{"archive_path": str(archive_path), "archived_count": len(archived), "missing_dirs": missing}}, ensure_ascii=False))
    raise SystemExit(2)
print(json.dumps({{
    "archive_path": str(archive_path),
    "archived_count": len(archived),
    "arxiv_ids": archived,
    "size_bytes": archive_path.stat().st_size,
}}, ensure_ascii=False))
""".strip()


def _build_remote_cleanup_script(
    *,
    arxiv_ids: Sequence[str],
    host_data_root: str,
    archive_path: str,
) -> str:
    return f"""
import json
import re
import shutil
from pathlib import Path

arxiv_ids = json.loads({json.dumps(json.dumps(list(arxiv_ids)))})
host_data_root = Path({json.dumps(host_data_root)})
archive_path = Path({json.dumps(archive_path)})
base = (host_data_root / "community_papers").resolve()
pattern = re.compile(r"^\\d{{4}}\\.\\d{{4,5}}(?:v\\d+)?$")
deleted = []
skipped = []
for arxiv_id in arxiv_ids:
    if not pattern.match(arxiv_id):
        skipped.append(arxiv_id)
        continue
    target = (base / arxiv_id).resolve()
    if target.parent != base:
        skipped.append(arxiv_id)
        continue
    if target.exists():
        shutil.rmtree(target)
        deleted.append(arxiv_id)
archive_path.unlink(missing_ok=True)
print(json.dumps({{
    "deleted_count": len(deleted),
    "deleted_arxiv_ids": deleted,
    "skipped": skipped,
    "archive_deleted": not archive_path.exists(),
}}, ensure_ascii=False))
""".strip()


def _json_from_command_output(output: str) -> dict[str, Any]:
    text = str(output or "").strip()
    if not text:
        raise ValueError("Remote command did not return JSON output.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        snippet = text[:500]
        raise ValueError(f"Remote command returned non-JSON output: {snippet}") from exc


def _run_ssh_command(
    client: Any,
    command: str,
    *,
    input_text: Optional[str] = None,
    timeout: int = 600,
) -> dict[str, Any]:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    if input_text is not None:
        stdin.write(input_text)
        try:
            stdin.channel.shutdown_write()
        except Exception:
            stdin.close()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return {
        "code": code,
        "out": out.strip(),
        "err": err.strip(),
    }


def _connect_remote_server(credentials: RemoteServerCredentials, *, attempts: int = 3) -> Any:
    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError(
            "Remote server sync requires paramiko. Install it in the local Python environment."
        ) from exc

    last_error: Exception | None = None
    for attempt in range(max(attempts, 1)):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=credentials.host,
                port=credentials.port,
                username=credentials.username,
                password=credentials.password,
                timeout=20,
                banner_timeout=30,
                auth_timeout=20,
            )
            transport = client.get_transport()
            if transport is not None:
                transport.set_keepalive(30)
            return client
        except Exception as exc:
            last_error = exc
            try:
                client.close()
            except Exception:
                pass
            if attempt + 1 < max(attempts, 1):
                time.sleep(3)
    raise last_error or RuntimeError("Remote SSH connection failed.")


def _download_remote_file_chunked(
    credentials: RemoteServerCredentials,
    *,
    remote_path: str,
    local_path: Path,
    expected_size: Optional[int],
    chunk_size: int = 32 * 1024 * 1024,
) -> int:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if local_path.exists():
        local_path.unlink()

    if expected_size is None:
        client = _connect_remote_server(credentials)
        try:
            sftp = client.open_sftp()
            try:
                expected_size = int(sftp.stat(remote_path).st_size)
            finally:
                sftp.close()
        finally:
            client.close()

    offset = 0
    while offset < expected_size:
        read_size = min(chunk_size, expected_size - offset)
        last_error: Exception | None = None
        for _ in range(3):
            client = _connect_remote_server(credentials)
            try:
                sftp = client.open_sftp()
                try:
                    with sftp.open(remote_path, "rb") as remote_file:
                        remote_file.seek(offset)
                        chunk = remote_file.read(read_size)
                    if not chunk:
                        raise IOError(f"Remote read returned no data at offset {offset}.")
                    with local_path.open("ab") as local_file:
                        local_file.write(chunk)
                    offset += len(chunk)
                    last_error = None
                    break
                finally:
                    sftp.close()
            except Exception as exc:
                last_error = exc
                time.sleep(2)
            finally:
                client.close()
        if last_error is not None:
            raise last_error

    actual_size = local_path.stat().st_size
    if actual_size != expected_size:
        raise IOError(f"Downloaded archive size mismatch: expected {expected_size}, got {actual_size}.")
    return actual_size


def _download_remote_file_stream(
    credentials: RemoteServerCredentials,
    *,
    remote_path: str,
    local_path: Path,
    expected_size: Optional[int],
) -> int:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if local_path.exists():
        local_path.unlink()

    command = f"cat {shlex.quote(remote_path)}"
    client = _connect_remote_server(credentials)
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=3600)
        stdin.close()
        channel = stdout.channel
        with local_path.open("wb") as target:
            while True:
                if channel.recv_ready():
                    target.write(channel.recv(1024 * 1024))
                    continue
                if channel.exit_status_ready():
                    while channel.recv_ready():
                        target.write(channel.recv(1024 * 1024))
                    remainder = stdout.read()
                    if remainder:
                        target.write(remainder)
                    break
                time.sleep(0.05)
        code = channel.recv_exit_status()
        error_text = stderr.read().decode("utf-8", errors="replace").strip()
        if code != 0:
            raise RuntimeError(f"Remote file stream failed: {error_text}")
    finally:
        client.close()

    actual_size = local_path.stat().st_size
    if expected_size is not None and actual_size != expected_size:
        raise IOError(f"Downloaded archive size mismatch: expected {expected_size}, got {actual_size}.")
    return actual_size


def remote_pull_core_pool_complete_assets(
    *,
    credential_path: Path = DEFAULT_REMOTE_CREDENTIAL_PATH,
    complete_path: Path = DEFAULT_COMPLETE_PATH,
    destination_root: Path = DEFAULT_DESTINATION_ROOT,
    arxiv_ids: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
    cleanup_remote: bool = True,
    container_name: str = DEFAULT_REMOTE_CONTAINER,
    remote_complete_path: str = DEFAULT_REMOTE_COMPLETE_PATH,
    remote_destination_root: str = DEFAULT_REMOTE_DESTINATION_ROOT,
    remote_host_data_root: str = DEFAULT_REMOTE_HOST_DATA_ROOT,
    remote_archive_dir: str = DEFAULT_REMOTE_ARCHIVE_DIR,
) -> dict[str, Any]:
    credentials = read_remote_server_credentials(credential_path)
    remote_archive_path = (
        PurePosixPath(remote_archive_dir)
        / f"latextrans-core-pool-complete-{uuid.uuid4().hex}.tar.gz"
    ).as_posix()
    local_archive_path = Path(tempfile.gettempdir()) / PurePosixPath(remote_archive_path).name
    report: dict[str, Any] = {
        "mode": "remote_pull_and_clean" if cleanup_remote else "remote_pull",
        "remote_server": credentials.safe_summary(),
        "local_destination_root": str(destination_root),
        "local_complete_path": str(complete_path),
        "remote_archive_path": remote_archive_path,
    }

    client = _connect_remote_server(credentials)
    try:
        sync_command = build_remote_sync_command(
            container_name=container_name,
            complete_path=remote_complete_path,
            destination_root=remote_destination_root,
            arxiv_ids=arxiv_ids,
            limit=limit,
            force=force,
        )
        sync_result = _run_ssh_command(
            client,
            sync_command,
            input_text=Path(__file__).read_text(encoding="utf-8"),
            timeout=900,
        )
        if sync_result["code"] != 0:
            raise RuntimeError(f"Remote sync failed: {sync_result['err'] or sync_result['out']}")
        sync_report = _json_from_command_output(sync_result["out"])
        report["remote_sync"] = sync_report

        blocking_counts = {
            key: int(sync_report.get(key) or 0)
            for key in ("failed", "conflicted", "missing", "partial")
        }
        if any(blocking_counts.values()):
            raise RuntimeError(f"Remote sync was incomplete: {blocking_counts}")

        synced_arxiv_ids = [
            str(item.get("arxiv_id"))
            for item in sync_report.get("items", [])
            if item.get("status") in {"downloaded", "skipped"} and not item.get("partial")
        ]
        if not synced_arxiv_ids:
            raise RuntimeError("Remote sync did not produce any completed arXiv directories.")

        archive_result = _run_ssh_command(
            client,
            "python3 -",
            input_text=_build_remote_archive_script(
                arxiv_ids=synced_arxiv_ids,
                host_data_root=remote_host_data_root,
                archive_path=remote_archive_path,
            ),
            timeout=900,
        )
        if archive_result["code"] != 0:
            raise RuntimeError(f"Remote archive failed: {archive_result['err'] or archive_result['out']}")
        archive_report = _json_from_command_output(archive_result["out"])
        report["remote_archive"] = archive_report

        client.close()
        downloaded_archive_size = _download_remote_file_stream(
            credentials,
            remote_path=remote_archive_path,
            local_path=local_archive_path,
            expected_size=int(archive_report.get("size_bytes") or 0) or None,
        )
        report["local_archive_size_bytes"] = downloaded_archive_size

        with tarfile.open(local_archive_path, "r:gz") as archive:
            safe_extract_tar(archive, Path(destination_root))
        if arxiv_ids or limit is not None:
            existing_local_ids = (
                read_complete_arxiv_ids(Path(complete_path))
                if Path(complete_path).exists()
                else []
            )
            write_complete_arxiv_ids(
                Path(complete_path),
                sorted(set(existing_local_ids).union(synced_arxiv_ids)),
            )
        else:
            write_complete_arxiv_ids(Path(complete_path), synced_arxiv_ids)
        report["local_extracted_count"] = len(synced_arxiv_ids)
        report["local_complete_updated"] = True

        client = _connect_remote_server(credentials)
        if cleanup_remote:
            directory_cleanup_result = _run_ssh_command(
                client,
                f"docker exec -i -w /app {shlex.quote(container_name)} python -",
                input_text=_build_remote_cleanup_script(
                    arxiv_ids=synced_arxiv_ids,
                    host_data_root="/app/backend/data",
                    archive_path="/tmp/nonexistent-latextrans-core-pool-archive.tar.gz",
                ),
                timeout=900,
            )
            if directory_cleanup_result["code"] != 0:
                raise RuntimeError(
                    f"Remote directory cleanup failed: "
                    f"{directory_cleanup_result['err'] or directory_cleanup_result['out']}"
                )
            report["remote_directory_cleanup"] = _json_from_command_output(
                directory_cleanup_result["out"]
            )

        archive_cleanup_result = _run_ssh_command(
            client,
            "python3 -",
            input_text=_build_remote_cleanup_script(
                arxiv_ids=[],
                host_data_root=remote_host_data_root,
                archive_path=remote_archive_path,
            ),
            timeout=900,
        )
        if archive_cleanup_result["code"] != 0:
            raise RuntimeError(
                f"Remote archive cleanup failed: {archive_cleanup_result['err'] or archive_cleanup_result['out']}"
            )
        report["remote_archive_cleanup"] = _json_from_command_output(archive_cleanup_result["out"])
        return report
    finally:
        try:
            client.close()
        finally:
            if local_archive_path.exists():
                local_archive_path.unlink()


def _select_arxiv_ids(
    complete_arxiv_ids: Sequence[str],
    *,
    requested_arxiv_ids: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
) -> list[str]:
    if requested_arxiv_ids:
        seen: set[str] = set()
        selected = []
        for item in requested_arxiv_ids:
            arxiv_id = str(item).strip()
            if not arxiv_id or arxiv_id in seen:
                continue
            seen.add(arxiv_id)
            selected.append(arxiv_id)
    else:
        selected = list(complete_arxiv_ids)

    if limit is not None:
        return selected[: max(limit, 0)]
    return selected


def sync_core_pool_complete_assets(
    *,
    storage_backend: Optional[Any] = None,
    complete_path: Path = DEFAULT_COMPLETE_PATH,
    destination_root: Path = DEFAULT_DESTINATION_ROOT,
    arxiv_ids: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
    dry_run: bool = False,
    direct_prefix_roots: Sequence[str] = DEFAULT_DIRECT_PREFIX_ROOTS,
    scan_prefix_roots: Sequence[str] = DEFAULT_SCAN_PREFIX_ROOTS,
    asset_records: Optional[Sequence[dict[str, Any]]] = None,
    storage_backends: Optional[dict[str, StorageBackend]] = None,
) -> dict[str, Any]:
    complete_matches = discover_complete_asset_candidates(
        asset_records=asset_records,
    )
    backend_cache: dict[str, StorageBackend] = dict(storage_backends or {})
    if storage_backend is not None:
        backend_cache.setdefault("local_disk", storage_backend)
        backend_cache.setdefault("object_storage", storage_backend)
    safe_complete_arxiv_ids = sorted(
        arxiv_id for arxiv_id, matches in complete_matches.items() if len(matches) == 1
    )
    selected_arxiv_ids = _select_arxiv_ids(
        sorted(complete_matches),
        requested_arxiv_ids=arxiv_ids,
        limit=limit,
    )
    destination_root = Path(destination_root)

    report: dict[str, Any] = {
        "complete_path": str(complete_path),
        "destination_root": str(destination_root),
        "source": "database",
        "discovered": len(safe_complete_arxiv_ids),
        "requested": len(selected_arxiv_ids),
        "matched": 0,
        "would_download": 0,
        "downloaded": 0,
        "skipped": 0,
        "partial": 0,
        "conflicted": 0,
        "missing": 0,
        "failed": 0,
        "items": [],
    }
    synced_complete_arxiv_ids: list[str] = []

    for arxiv_id in selected_arxiv_ids:
        matches = complete_matches.get(arxiv_id, {})

        if not matches:
            report["missing"] += 1
            report["items"].append({"arxiv_id": arxiv_id, "status": "missing"})
            continue

        if len(matches) > 1:
            report["conflicted"] += 1
            report["items"].append(
                {
                    "arxiv_id": arxiv_id,
                    "status": "conflict",
                    "conflict_prefixes": sorted(matches.keys()),
                }
            )
            continue

        matched_prefix, refs = next(iter(matches.items()))
        report["matched"] += 1
        target_root = destination_root / arxiv_id
        downloaded_count = 0
        skipped_count = 0
        asset_groups = _asset_groups_for_records(refs)
        item_failed = False
        item_error: str | None = None

        if force and target_root.exists() and not dry_run:
            shutil.rmtree(target_root)

        for ref in sorted(refs, key=lambda item: str(item.get("file_path") or "")):
            relative_path = _relative_destination_for_asset_record(ref)
            if not relative_path:
                continue

            local_path = target_root.joinpath(*PurePosixPath(relative_path).parts)
            if local_path.exists() and not force:
                skipped_count += 1
                continue

            try:
                if not dry_run:
                    record_storage_backend = str(ref.get("storage_backend") or "").strip().lower()
                    backend = backend_cache.get(record_storage_backend)
                    if backend is None:
                        backend = _build_storage_backend_for_record(record_storage_backend)
                        backend_cache[record_storage_backend] = backend
                    _download_asset_record(backend, ref, local_path)
            except Exception as exc:
                item_failed = True
                item_error = (
                    f"{type(exc).__name__} while syncing {ref.get('asset_type')}: "
                    f"{ref.get('file_path')}: {exc}"
                )
                break
            downloaded_count += 1

        partial = not REQUIRED_ASSET_GROUPS.issubset(asset_groups)
        if partial:
            report["partial"] += 1

        if item_failed:
            status = "failed"
            report["failed"] += 1
        elif downloaded_count > 0:
            if dry_run:
                status = "would_download"
                report["would_download"] += 1
            else:
                status = "downloaded"
                report["downloaded"] += 1
        elif skipped_count > 0:
            status = "skipped"
            report["skipped"] += 1
        else:
            status = "failed"
            report["failed"] += 1

        item = {
            "arxiv_id": arxiv_id,
            "status": status,
            "matched_prefix": matched_prefix,
            "downloaded_count": downloaded_count,
            "skipped_count": skipped_count,
            "partial": partial,
        }
        if item_error:
            item["error"] = item_error
        report["items"].append(item)
        if status in {"downloaded", "skipped"} and not partial:
            synced_complete_arxiv_ids.append(arxiv_id)

    targeted_run = bool(arxiv_ids) or limit is not None
    should_update_complete = not dry_run and not targeted_run and (
        bool(synced_complete_arxiv_ids) or report["requested"] == 0
    )
    report["complete_updated"] = should_update_complete
    if not dry_run and targeted_run:
        report["complete_update_skipped_reason"] = (
            "Targeted sync requested; leaving complete.md unchanged."
        )
    elif not dry_run and not should_update_complete:
        report["complete_update_skipped_reason"] = (
            "No assets were successfully synced; leaving complete.md unchanged."
        )
    if should_update_complete:
        write_complete_arxiv_ids(Path(complete_path), sorted(synced_complete_arxiv_ids))

    return report


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover complete core-pool assets from backend records, sync recorded assets locally, and update complete.md."
    )
    parser.add_argument("--complete-path", type=Path, default=DEFAULT_COMPLETE_PATH, help="Path to backend/arxiv_id/core_pool/complete.md, updated from COS on non-dry-run.")
    parser.add_argument("--destination-root", type=Path, default=DEFAULT_DESTINATION_ROOT, help="Local root for data/community_papers/<arxiv_id>/... output.")
    parser.add_argument("--arxiv-id", action="append", dest="arxiv_ids", default=None, help="Optional arXiv ID to sync. Repeat for multiple IDs.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of arXiv IDs to process.")
    parser.add_argument("--dry-run", action="store_true", help="Report matches without downloading files.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing local files for matched arXiv IDs.")
    parser.add_argument("--remote-pull-and-clean", action="store_true", help="Run the sync on the production server, download the arXiv-ID archive locally, then delete the remote arXiv-ID output directories and temporary archive.")
    parser.add_argument("--remote-credentials", type=Path, default=DEFAULT_REMOTE_CREDENTIAL_PATH, help="Credential note used by --remote-pull-and-clean.")
    parser.add_argument("--remote-container", default=DEFAULT_REMOTE_CONTAINER, help="Backend Docker container used by --remote-pull-and-clean.")
    parser.add_argument("--remote-archive-dir", default=DEFAULT_REMOTE_ARCHIVE_DIR, help="Remote temporary directory for the transfer archive.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        if args.remote_pull_and_clean:
            if args.dry_run:
                raise ValueError("--dry-run cannot be combined with --remote-pull-and-clean.")
            report = remote_pull_core_pool_complete_assets(
                credential_path=args.remote_credentials,
                complete_path=args.complete_path,
                destination_root=args.destination_root,
                arxiv_ids=args.arxiv_ids,
                limit=args.limit,
                force=args.force,
                cleanup_remote=True,
                container_name=args.remote_container,
                remote_archive_dir=args.remote_archive_dir,
            )
        else:
            report = sync_core_pool_complete_assets(
                complete_path=args.complete_path,
                destination_root=args.destination_root,
                arxiv_ids=args.arxiv_ids,
                limit=args.limit,
                dry_run=args.dry_run,
                force=args.force,
            )
    except Exception as exc:
        error_report = {
            "error": type(exc).__name__,
            "message": str(exc),
        }
        print(json.dumps(error_report, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
