from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Optional, Sequence

from backend.app.core.config import Settings


@dataclass(frozen=True)
class StoredObjectRef:
    storage_backend: str
    object_key: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None


class StorageBackend(ABC):
    """Shared abstraction for storage backends so the factory can stay lean."""

    @abstractmethod
    def put_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: Optional[str],
        delete_local: bool,
    ) -> StoredObjectRef:
        raise NotImplementedError

    @abstractmethod
    def resolve_local_path(self, ref: StoredObjectRef) -> Path:
        raise NotImplementedError

    @abstractmethod
    def read_text(self, *, ref: StoredObjectRef, encoding: str = "utf-8") -> str:
        raise NotImplementedError

    @abstractmethod
    def list_files(self, *, prefix: str) -> list[StoredObjectRef]:
        raise NotImplementedError

    @abstractmethod
    def download_file(self, *, object_key: str, local_path: Path) -> Path:
        raise NotImplementedError

    def build_download_url(
        self,
        *,
        object_key: str,
        expires_in: int,
        params: Optional[dict[str, str]] = None,
    ) -> Optional[str]:
        return None

    def object_exists(self, *, object_key: str) -> bool:
        return False

    @staticmethod
    def _normalize_object_key(object_key: str) -> Sequence[str]:
        normalized = PurePosixPath(object_key)
        if normalized.is_absolute():
            raise ValueError("Object keys must be relative paths without leading separators.")

        parts = tuple(part for part in normalized.parts if part and part != ".")
        if not parts:
            raise ValueError("Object key must contain at least one valid path segment.")
        if any(part == ".." for part in parts):
            raise ValueError("Object keys cannot contain path traversal segments like '..'.")
        if parts[0].endswith(":"):
            raise ValueError("Object keys cannot use drive-qualified absolute paths.")
        return parts

    @staticmethod
    def _fs_path(path: Path) -> str:
        raw = os.path.abspath(os.fspath(path))
        if os.name != "nt" or raw.startswith("\\\\?\\") or len(raw) < 240:
            return raw
        if raw.startswith("\\\\"):
            return "\\\\?\\UNC\\" + raw.lstrip("\\")
        return "\\\\?\\" + raw


class LocalDiskStorageBackend(StorageBackend):
    """Simple backend that persists objects to a local filesystem root."""

    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _build_target_path(self, object_key: str) -> Path:
        parts = self._normalize_object_key(object_key)
        target = self._root.joinpath(*parts)
        resolved = target.resolve(strict=False)
        if not resolved.is_relative_to(self._root):
            raise ValueError("Resolved object path escapes the local storage root.")
        return resolved

    def put_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: Optional[str],
        delete_local: bool,
    ) -> StoredObjectRef:
        target = self._build_target_path(object_key)
        os.makedirs(self._fs_path(target.parent), exist_ok=True)
        same_path = False
        try:
            same_path = local_path.resolve(strict=False) == target.resolve(strict=False)
        except Exception:
            same_path = False
        if not same_path:
            with open(self._fs_path(local_path), "rb") as source_handle:
                with open(self._fs_path(target), "wb") as target_handle:
                    shutil.copyfileobj(source_handle, target_handle)
        if delete_local and local_path.exists() and not same_path:
            local_path.unlink()
        return StoredObjectRef(
            storage_backend="local_disk",
            object_key="/".join(self._normalize_object_key(object_key)),
            content_type=content_type,
            size_bytes=os.path.getsize(self._fs_path(target)),
        )

    def resolve_local_path(self, ref: StoredObjectRef) -> Path:
        relative = Path(*self._normalize_object_key(ref.object_key))
        return self._root.joinpath(relative)

    def read_text(self, *, ref: StoredObjectRef, encoding: str = "utf-8") -> str:
        return self.resolve_local_path(ref).read_text(encoding=encoding)

    def object_exists(self, *, object_key: str) -> bool:
        return self._build_target_path(object_key).is_file()

    def list_files(self, *, prefix: str) -> list[StoredObjectRef]:
        target = self._build_target_path(prefix)
        if not target.exists():
            return []

        files: list[Path]
        if target.is_file():
            files = [target]
        else:
            files = sorted(path for path in target.rglob("*") if path.is_file())

        results: list[StoredObjectRef] = []
        for file_path in files:
            relative = file_path.relative_to(self._root).as_posix()
            results.append(
                StoredObjectRef(
                    storage_backend="local_disk",
                    object_key=relative,
                    size_bytes=file_path.stat().st_size,
                )
            )
        return results

    def download_file(self, *, object_key: str, local_path: Path) -> Path:
        source = self._build_target_path(object_key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, local_path)
        return local_path


class CosStorageBackend(StorageBackend):
    """Tencent COS-backed storage for production object persistence."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        secret_id: str,
        secret_key: str,
        base_prefix: str,
        client: Optional[Any] = None,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.base_prefix = str(base_prefix or "").strip().strip("/")
        self._client = client

    def put_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: Optional[str],
        delete_local: bool,
    ) -> StoredObjectRef:
        full_key = self._full_object_key(object_key)
        upload_kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": full_key,
            "LocalFilePath": self._fs_path(local_path),
            "EnableMD5": False,
        }
        if content_type:
            upload_kwargs["ContentType"] = content_type
        self._get_client().upload_file(**upload_kwargs)
        size_bytes = os.path.getsize(self._fs_path(local_path))
        if delete_local and local_path.exists():
            local_path.unlink()
        return StoredObjectRef(
            storage_backend="object_storage",
            object_key=full_key,
            content_type=content_type,
            size_bytes=size_bytes,
        )

    def resolve_local_path(self, ref: StoredObjectRef) -> Path:
        raise NotImplementedError("COS objects are not stored locally.")

    def read_text(self, *, ref: StoredObjectRef, encoding: str = "utf-8") -> str:
        response = self._get_client().get_object(
            Bucket=self.bucket,
            Key=self._full_object_key(ref.object_key),
        )
        body = response["Body"].get_raw_stream().read()
        if isinstance(body, str):
            return body
        return body.decode(encoding)

    def build_download_url(
        self,
        *,
        object_key: str,
        expires_in: int,
        params: Optional[dict[str, str]] = None,
    ) -> Optional[str]:
        full_key = self._full_object_key(object_key)
        request_kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": full_key,
            "Expired": expires_in,
        }
        if params:
            request_kwargs["Params"] = params
        return self._get_client().get_presigned_download_url(
            **request_kwargs,
        )

    def list_files(self, *, prefix: str) -> list[StoredObjectRef]:
        full_prefix = self._full_object_key(prefix)
        marker: Optional[str] = None
        results: list[StoredObjectRef] = []

        while True:
            request_kwargs: dict[str, Any] = {
                "Bucket": self.bucket,
                "Prefix": full_prefix,
            }
            if marker:
                request_kwargs["Marker"] = marker

            response = self._get_client().list_objects(**request_kwargs) or {}
            contents = response.get("Contents") or []
            for item in contents:
                key = str(item.get("Key") or "").strip()
                if not key or key.endswith("/"):
                    continue
                results.append(
                    StoredObjectRef(
                        storage_backend="object_storage",
                        object_key=key,
                        size_bytes=item.get("Size"),
                    )
                )

            truncated = response.get("IsTruncated")
            if truncated not in {True, "true", "True"}:
                break

            marker = response.get("NextMarker")
            if not marker and contents:
                marker = contents[-1].get("Key")
            if not marker:
                break

        return results

    def download_file(self, *, object_key: str, local_path: Path) -> Path:
        response = self._get_client().get_object(
            Bucket=self.bucket,
            Key=self._full_object_key(object_key),
        )
        stream = response["Body"].get_raw_stream()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._fs_path(local_path), "wb") as target_handle:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                target_handle.write(chunk)
        return local_path

    def object_exists(self, *, object_key: str) -> bool:
        try:
            self._get_client().head_object(
                Bucket=self.bucket,
                Key=self._full_object_key(object_key),
            )
            return True
        except Exception:
            return False

    def _full_object_key(self, object_key: str) -> str:
        normalized = "/".join(self._normalize_object_key(object_key))
        if self.base_prefix and normalized != self.base_prefix and not normalized.startswith(f"{self.base_prefix}/"):
            return f"{self.base_prefix}/{normalized}"
        return normalized

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as exc:
            raise RuntimeError(
                "COS storage backend requires cos-python-sdk-v5 to be installed."
            ) from exc

        config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key,
            Scheme="https",
        )
        self._client = CosS3Client(config)
        return self._client


def build_storage_backend(settings: Settings) -> StorageBackend:
    mode = settings.storage_backend_mode.strip().lower()
    if mode in {"local_disk", "disk", "local"}:
        return LocalDiskStorageBackend(root=settings.local_storage_root)

    if mode == "cos":
        _ensure_cos_config(settings)
        return CosStorageBackend(
            bucket=settings.cos_bucket,  # type: ignore[arg-type]
            region=settings.cos_region,  # type: ignore[arg-type]
            secret_id=settings.cos_secret_id,  # type: ignore[arg-type]
            secret_key=settings.cos_secret_key,  # type: ignore[arg-type]
            base_prefix=settings.cos_base_prefix,
        )

    raise ValueError(f"Unsupported storage backend mode: {settings.storage_backend_mode}")


def _ensure_cos_config(settings: Settings) -> None:
    missing = []
    if not settings.cos_bucket:
        missing.append("COS_BUCKET")
    if not settings.cos_region:
        missing.append("COS_REGION")
    if not settings.cos_secret_id:
        missing.append("COS_SECRET_ID")
    if not settings.cos_secret_key:
        missing.append("COS_SECRET_KEY")

    if missing:
        raise ValueError(
            f"COS storage backend requires the following configuration to be set: {', '.join(missing)}"
        )
