#!/usr/bin/env python3
"""Repair arXiv papers with missing/placeholder metadata by fetching from arXiv API.

Usage:
    python scripts/repair_arxiv_metadata.py [--limit 20]

The script scans papers with placeholder titles ("arXiv:XXXX.XXXXX"), missing authors,
categories, abstract, or published date, then fetches real metadata from the arXiv API.
Each successful fetch updates the paper record in the database.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Project root detection: works locally (scripts/ → repo root) and inside Docker (/app)
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent if _SCRIPT_DIR.name == "scripts" else Path("/app")
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services import paper_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("repair_metadata")


async def run_repair(limit: int, rounds: int = 1) -> dict:
    total = {"scanned": 0, "repaired": 0, "unrepaired": 0, "failed": 0}
    for r in range(0, rounds):
        if rounds > 1:
            logger.info(
                "=== Round %d/%d (limit=%d) ===",
                r + 1, rounds, limit,
            )
        result = await paper_service.repair_published_arxiv_metadata(limit=limit)
        for k in total:
            total[k] += result[k]
        logger.info(
            "Round result: scanned=%d repaired=%d unrepaired=%d failed=%d",
            result["scanned"], result["repaired"],
            result["unrepaired"], result["failed"],
        )
        if result["scanned"] == 0:
            logger.info("No more papers to repair, stopping early")
            break
    return total


def main():
    parser = argparse.ArgumentParser(description="Repair arXiv paper metadata")
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Max papers to scan per round (default 20, max 100)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Keep repairing until no more papers found",
    )
    args = parser.parse_args()

    start = time.monotonic()

    if args.all:
        total = asyncio.run(run_repair(limit=args.limit, rounds=5000))
    else:
        total = asyncio.run(run_repair(limit=args.limit, rounds=1))

    elapsed = time.monotonic() - start
    logger.info("=" * 55)
    logger.info("Done in %.0fs: scanned=%d repaired=%d unrepaired=%d failed=%d",
                elapsed, total["scanned"], total["repaired"],
                total["unrepaired"], total["failed"])


if __name__ == "__main__":
    main()
