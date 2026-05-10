#!/usr/bin/env python3
"""Pre-warm COS origin-pull cache for all arXiv IDs in the core pool.

Usage:
    docker exec latextrans-backend python3 /app/backend/prewarm_cos_cache.py

Requires the project's Python dependencies (available inside the Docker container).
"""

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("prewarm")

sys.path.insert(0, "/app")

from backend.app.core.config import get_settings
from backend.app.services.arxiv_raw_cache import (
    _get_backend,
    is_enabled,
    raw_eprint_object_key,
    build_eprint_download_url,
)


def load_arxiv_ids(file_path: str) -> list[str]:
    ids = []
    for line in Path(file_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and line[0].isdigit():
            ids.append(line)
    return ids


def prewarm_one(arxiv_id: str, settings, backend, session: requests.Session) -> dict:
    try:
        object_key = raw_eprint_object_key(arxiv_id, settings=settings)
        if backend.object_exists(object_key=object_key):
            return {"arxiv_id": arxiv_id, "status": "cached"}

        url = build_eprint_download_url(arxiv_id, settings=settings)
        if not url:
            return {"arxiv_id": arxiv_id, "status": "no_url"}

        with session.get(url, stream=True, timeout=(10, 120)) as resp:
            if resp.status_code == 200:
                for _ in resp.iter_content(chunk_size=8192):
                    break
                return {"arxiv_id": arxiv_id, "status": "triggered"}
            else:
                return {"arxiv_id": arxiv_id, "status": f"http_{resp.status_code}"}
    except Exception as e:
        return {"arxiv_id": arxiv_id, "status": "error", "detail": str(e)[:100]}


def main():
    id_file = "/app/backend/arxiv_id/core_pool/id.md"
    ids = load_arxiv_ids(id_file)
    if not ids:
        logger.error("No arXiv IDs found in %s", id_file)
        sys.exit(1)
    logger.info("Loaded %d arXiv IDs from %s", len(ids), id_file)

    settings = get_settings()
    if not is_enabled(settings=settings):
        logger.error("COS raw cache is not enabled in settings")
        sys.exit(1)

    backend = _get_backend(settings)
    if backend is None:
        logger.error("Failed to initialize COS backend")
        sys.exit(1)

    logger.info(
        "COS backend ready — bucket=%s prefix=%s",
        settings.cos_bucket,
        settings.cos_base_prefix,
    )

    max_workers = 10
    logger.info("Starting pre-warm with %d concurrent workers", max_workers)

    stats = {"cached": 0, "triggered": 0, "failed": 0, "errors": []}
    total = len(ids)
    start = time.monotonic()
    session = requests.Session()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_map = {pool.submit(prewarm_one, aid, settings, backend, session): aid for aid in ids}
        done = 0
        for fut in as_completed(fut_map):
            done += 1
            result = fut.result()
            s = result["status"]
            if s == "cached":
                stats["cached"] += 1
            elif s == "triggered":
                stats["triggered"] += 1
            else:
                stats["failed"] += 1
                stats["errors"].append(f"{result['arxiv_id']}={s}")

            if done % 100 == 0 or done == total:
                elapsed = time.monotonic() - start
                logger.info(
                    "[%d/%d] cached=%d  triggered=%d  failed=%d  (%.1f/s)",
                    done, total,
                    stats["cached"], stats["triggered"], stats["failed"],
                    done / elapsed,
                )

    elapsed = time.monotonic() - start
    logger.info("=" * 55)
    logger.info("Done: %d IDs in %.0fs (%.1f/s)", total, elapsed, total / elapsed)
    logger.info("  Already cached : %d", stats["cached"])
    logger.info("  Origin-pull    : %d", stats["triggered"])
    logger.info("  Failed         : %d", stats["failed"])
    if stats["errors"]:
        logger.info("  Sample errors  : %s", stats["errors"][:10])


if __name__ == "__main__":
    main()
