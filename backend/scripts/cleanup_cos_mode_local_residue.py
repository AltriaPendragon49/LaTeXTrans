from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import time
from typing import Any, Sequence

from backend.app.core.config import get_settings


SAFE_ROOT_NAMES = {"uploads", "outputs", "community_papers", "failed_tasks", "tmp_storage"}


class CleanupRefusedError(RuntimeError):
    pass


def _resolve(path: Path) -> Path:
    return path.resolve(strict=False)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _assert_safe_root(*, data_dir: Path, root: Path) -> Path:
    resolved_data = _resolve(data_dir)
    resolved_root = _resolve(root)
    if not _is_relative_to(resolved_root, resolved_data):
        raise CleanupRefusedError(f"Cleanup root escapes data dir: {resolved_root}")
    if resolved_root.parent != resolved_data or resolved_root.name not in SAFE_ROOT_NAMES:
        raise CleanupRefusedError(f"Cleanup root is not an approved COS residue root: {resolved_root}")
    return resolved_root


def _latest_mtime(path: Path) -> float:
    try:
        latest = path.stat().st_mtime
    except OSError:
        return 0.0
    if path.is_dir():
        for child in path.rglob("*"):
            try:
                latest = max(latest, child.stat().st_mtime)
            except OSError:
                continue
    return latest


def _path_size(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
        total = 0
        for child in path.rglob("*"):
            if child.is_file():
                try:
                    total += child.stat().st_size
                except OSError:
                    continue
        return total
    except OSError:
        return 0


def build_cleanup_plan(
    *,
    data_dir: Path,
    roots: Sequence[Path],
    min_age_seconds: int,
    now: float | None = None,
) -> dict[str, Any]:
    resolved_now = float(now if now is not None else time.time())
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    safe_roots: list[Path] = []
    for root in roots:
        try:
            safe_root = _assert_safe_root(data_dir=data_dir, root=root)
            safe_roots.append(safe_root)
        except CleanupRefusedError as exc:
            skipped.append({"path": str(root), "reason": str(exc)})
            continue
        if not safe_root.exists():
            skipped.append({"path": str(safe_root), "reason": "missing"})
            continue
        for child in sorted(safe_root.iterdir(), key=lambda item: item.name):
            child_path = _resolve(child)
            if not _is_relative_to(child_path, safe_root) or child_path == safe_root:
                skipped.append({"path": str(child), "reason": "unsafe_child"})
                continue
            latest_mtime = _latest_mtime(child)
            age_seconds = max(0, int(resolved_now - latest_mtime))
            if age_seconds < int(min_age_seconds):
                skipped.append({"path": str(child), "reason": "too_fresh", "age_seconds": age_seconds})
                continue
            candidates.append(
                {
                    "path": str(child_path),
                    "root": str(safe_root),
                    "age_seconds": age_seconds,
                    "size_bytes": _path_size(child),
                    "is_dir": child.is_dir(),
                }
            )
    return {
        "data_dir": str(_resolve(data_dir)),
        "min_age_seconds": int(min_age_seconds),
        "roots": [str(root) for root in safe_roots],
        "candidates": candidates,
        "skipped": skipped,
    }


def _delete_candidate(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def run_cleanup(
    *,
    data_dir: Path,
    roots: Sequence[Path],
    storage_backend_mode: str,
    min_age_seconds: int,
    execute: bool,
    now: float | None = None,
) -> dict[str, Any]:
    if execute and str(storage_backend_mode or "").strip().lower() != "cos":
        raise CleanupRefusedError("Execute mode requires STORAGE_BACKEND_MODE=cos.")

    plan = build_cleanup_plan(
        data_dir=data_dir,
        roots=roots,
        min_age_seconds=min_age_seconds,
        now=now,
    )
    plan["dry_run"] = not execute
    plan["deleted"] = []
    plan["errors"] = []

    if execute:
        safe_roots = [Path(root) for root in plan["roots"]]
        for item in plan["candidates"]:
            path = _resolve(Path(str(item["path"])))
            if not any(_is_relative_to(path, root) and path != root for root in safe_roots):
                plan["errors"].append({"path": str(path), "error": "candidate escaped safe roots"})
                continue
            try:
                _delete_candidate(path)
                plan["deleted"].append(item)
            except Exception as exc:
                plan["errors"].append({"path": str(path), "error": str(exc)})

    plan["summary"] = {
        "candidate_count": len(plan["candidates"]),
        "deleted_count": len(plan["deleted"]),
        "error_count": len(plan["errors"]),
        "skipped_count": len(plan["skipped"]),
    }
    return plan


def default_cleanup_roots() -> list[Path]:
    settings = get_settings()
    return [
        settings.uploads_dir,
        settings.outputs_dir,
        settings.community_papers_dir,
        settings.failed_tasks_dir,
        settings.storage_temp_dir,
    ]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run or clean stale local residue in COS mode.")
    parser.add_argument("--execute", action="store_true", help="Delete candidates. Default only reports.")
    parser.add_argument("--min-age-hours", type=float, default=24.0, help="Minimum candidate age in hours.")
    parser.add_argument("--output-report", help="Optional JSON report path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    settings = get_settings()
    report = run_cleanup(
        data_dir=settings.data_dir,
        roots=default_cleanup_roots(),
        storage_backend_mode=settings.storage_backend_mode,
        min_age_seconds=int(max(0.0, float(args.min_age_hours)) * 3600),
        execute=bool(args.execute),
    )
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_report:
        with open(args.output_report, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
