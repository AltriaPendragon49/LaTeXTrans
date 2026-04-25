from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Optional, Sequence

from backend.app.core.config import get_settings
from backend.app.services.storage_backend import (
    CosStorageBackend,
    StorageBackend,
    StoredObjectRef,
    _ensure_cos_config,
)

ARXIV_ID_PATTERN = re.compile(r"(?<!\d)(\d{4}\.\d{4,5}(?:v\d+)?)(?!\d)")
DEFAULT_COMPLETE_PATH = Path(__file__).resolve().parents[1] / "arxiv_id" / "core_pool" / "complete.md"
DEFAULT_DESTINATION_ROOT = Path(__file__).resolve().parents[1] / "data" / "community_papers"
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
    "data/outputs",
    "outputs",
)
REQUIRED_ASSET_GROUPS = {"source", "preview", "translated"}


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


def _match_arxiv_id_in_key(object_key: str, arxiv_id: str) -> bool:
    pattern = re.compile(rf"(^|[/_.-]){re.escape(arxiv_id)}($|[/_.-])")
    return bool(pattern.search(_normalize_posix(object_key)))


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


def _collect_direct_matches(
    storage_backend: Any,
    arxiv_id: str,
    direct_prefix_roots: Sequence[str],
) -> dict[str, list[StoredObjectRef]]:
    matches: dict[str, list[StoredObjectRef]] = {}
    for root in direct_prefix_roots:
        refs = storage_backend.list_files(prefix=f"{_normalize_posix(root)}/{arxiv_id}")
        for ref in refs:
            prefix = _extract_candidate_prefix(str(ref.object_key or ""))
            if not prefix:
                continue
            matches.setdefault(prefix, []).append(ref)
    return matches


def _collect_scan_matches(
    storage_backend: Any,
    arxiv_id: str,
    scan_prefix_roots: Sequence[str],
    scan_cache: dict[str, list[StoredObjectRef]],
) -> dict[str, list[StoredObjectRef]]:
    matches: dict[str, list[StoredObjectRef]] = {}
    for root in scan_prefix_roots:
        normalized_root = _normalize_posix(root)
        refs = scan_cache.setdefault(normalized_root, storage_backend.list_files(prefix=normalized_root))
        for ref in refs:
            object_key = str(ref.object_key or "")
            if not _match_arxiv_id_in_key(object_key, arxiv_id):
                continue
            prefix = _extract_candidate_prefix(object_key)
            if not prefix:
                continue
            matches.setdefault(prefix, []).append(ref)
    return matches


def _select_arxiv_ids(
    complete_arxiv_ids: Sequence[str],
    *,
    requested_arxiv_ids: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
) -> list[str]:
    if requested_arxiv_ids:
        requested = {str(item).strip() for item in requested_arxiv_ids if str(item).strip()}
        selected = [arxiv_id for arxiv_id in complete_arxiv_ids if arxiv_id in requested]
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
) -> dict[str, Any]:
    backend = storage_backend or _build_cos_storage_backend()
    selected_arxiv_ids = _select_arxiv_ids(
        read_complete_arxiv_ids(complete_path),
        requested_arxiv_ids=arxiv_ids,
        limit=limit,
    )
    destination_root = Path(destination_root)
    scan_cache: dict[str, list[StoredObjectRef]] = {}

    report: dict[str, Any] = {
        "complete_path": str(complete_path),
        "destination_root": str(destination_root),
        "requested": len(selected_arxiv_ids),
        "matched": 0,
        "downloaded": 0,
        "skipped": 0,
        "partial": 0,
        "conflicted": 0,
        "missing": 0,
        "failed": 0,
        "items": [],
    }

    for arxiv_id in selected_arxiv_ids:
        matches = _collect_direct_matches(backend, arxiv_id, direct_prefix_roots)
        if not matches:
            matches = _collect_scan_matches(backend, arxiv_id, scan_prefix_roots, scan_cache)

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
        asset_groups: set[str] = set()

        if force and target_root.exists() and not dry_run:
            shutil.rmtree(target_root)

        for ref in sorted(refs, key=lambda item: str(item.object_key or "")):
            relative_path = _relative_destination_for_key(str(ref.object_key or ""), matched_prefix)
            if not relative_path:
                continue

            first_segment = PurePosixPath(relative_path).parts[0]
            if first_segment in REQUIRED_ASSET_GROUPS:
                asset_groups.add(first_segment)

            local_path = target_root.joinpath(*PurePosixPath(relative_path).parts)
            if local_path.exists() and not force:
                skipped_count += 1
                continue

            if not dry_run:
                backend.download_file(object_key=ref.object_key, local_path=local_path)
            downloaded_count += 1

        partial = not REQUIRED_ASSET_GROUPS.issubset(asset_groups)
        if partial:
            report["partial"] += 1

        if downloaded_count > 0:
            status = "downloaded"
            report["downloaded"] += 1
        elif skipped_count > 0:
            status = "skipped"
            report["skipped"] += 1
        else:
            status = "failed"
            report["failed"] += 1

        report["items"].append(
            {
                "arxiv_id": arxiv_id,
                "status": status,
                "matched_prefix": matched_prefix,
                "downloaded_count": downloaded_count,
                "skipped_count": skipped_count,
                "partial": partial,
            }
        )

    return report


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync core-pool complete COS assets into local arXiv-ID reading directories."
    )
    parser.add_argument("--complete-path", type=Path, default=DEFAULT_COMPLETE_PATH, help="Path to backend/arxiv_id/core_pool/complete.md.")
    parser.add_argument("--destination-root", type=Path, default=DEFAULT_DESTINATION_ROOT, help="Local root for data/community_papers/<arxiv_id>/... output.")
    parser.add_argument("--arxiv-id", action="append", dest="arxiv_ids", default=None, help="Optional arXiv ID to sync. Repeat for multiple IDs.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of arXiv IDs to process.")
    parser.add_argument("--dry-run", action="store_true", help="Report matches without downloading files.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing local files for matched arXiv IDs.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    report = sync_core_pool_complete_assets(
        complete_path=args.complete_path,
        destination_root=args.destination_root,
        arxiv_ids=args.arxiv_ids,
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
