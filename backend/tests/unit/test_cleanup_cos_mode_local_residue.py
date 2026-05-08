import os
import time
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

import pytest

from backend.scripts import cleanup_cos_mode_local_residue as cleanup


def test_cleanup_plan_selects_only_stale_children_under_safe_roots(tmp_path: Path):
    data_dir = tmp_path / "data"
    uploads = data_dir / "uploads"
    uploads.mkdir(parents=True)
    stale_dir = uploads / "task-old"
    stale_dir.mkdir()
    (stale_dir / "source.zip").write_bytes(b"old")
    fresh_dir = uploads / "task-new"
    fresh_dir.mkdir()
    (fresh_dir / "source.zip").write_bytes(b"new")

    old_timestamp = time.time() - 48 * 3600
    os.utime(stale_dir / "source.zip", (old_timestamp, old_timestamp))
    os.utime(stale_dir, (old_timestamp, old_timestamp))

    plan = cleanup.build_cleanup_plan(
        data_dir=data_dir,
        roots=[uploads],
        min_age_seconds=24 * 3600,
        now=time.time(),
    )

    candidate_paths = {Path(item["path"]).name for item in plan["candidates"]}
    assert candidate_paths == {"task-old"}
    assert fresh_dir.exists()
    assert uploads.exists()


def test_execute_cleanup_refuses_non_cos_mode(tmp_path: Path):
    data_dir = tmp_path / "data"
    uploads = data_dir / "uploads"
    uploads.mkdir(parents=True)
    stale_file = uploads / "old.zip"
    stale_file.write_bytes(b"old")
    old_timestamp = time.time() - 48 * 3600
    os.utime(stale_file, (old_timestamp, old_timestamp))

    with pytest.raises(cleanup.CleanupRefusedError):
        cleanup.run_cleanup(
            data_dir=data_dir,
            roots=[uploads],
            storage_backend_mode="local_disk",
            min_age_seconds=24 * 3600,
            execute=True,
            now=time.time(),
        )

    assert stale_file.exists()
