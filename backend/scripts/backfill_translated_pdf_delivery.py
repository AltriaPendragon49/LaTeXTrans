from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from backend.app.services import paper_service


def run_backfill(
    *,
    paper_ids: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        paper_service.backfill_translated_pdf_delivery_assets(
            paper_ids=paper_ids,
            limit=limit,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upgrade existing community translated PDF assets into canonical trimmed delivery files.",
    )
    parser.add_argument(
        "--paper-id",
        action="append",
        dest="paper_ids",
        default=None,
        help="Optional paper id to upgrade. Repeat to target multiple papers.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of public papers to process when --paper-id is not provided.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path to write the structured backfill report JSON.",
    )
    args = parser.parse_args()

    report = run_backfill(
        paper_ids=args.paper_ids,
        limit=args.limit,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
