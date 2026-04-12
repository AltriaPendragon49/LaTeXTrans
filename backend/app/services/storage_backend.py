from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional, Sequence

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
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(local_path.read_bytes())
        if delete_local and local_path.exists():
            local_path.unlink()
        return StoredObjectRef(
            storage_backend="local_disk",
            object_key="/".join(self._normalize_object_key(object_key)),
            content_type=content_type,
            size_bytes=target.stat().st_size,
        )

    def resolve_local_path(self, ref: StoredObjectRef) -> Path:
        relative = Path(*self._normalize_object_key(ref.object_key))
        return self._root.joinpath(relative)


class CosStorageBackend(StorageBackend):
    """Placeholder COS backend that keeps the config for future implementation."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        secret_id: str,
        secret_key: str,
        base_prefix: str,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.base_prefix = base_prefix

    def put_file(
        self,
        *,
        local_path: Path,
        object_key: str,
        content_type: Optional[str],
        delete_local: bool,
    ) -> StoredObjectRef:
        raise NotImplementedError("COS-backed storage is not implemented yet.")

    def resolve_local_path(self, ref: StoredObjectRef) -> Path:
        raise NotImplementedError("COS objects are not stored locally.")


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
