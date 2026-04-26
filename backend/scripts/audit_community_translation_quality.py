from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.community_translation_quality import evaluate_directory


DEFAULT_COMMUNITY_PAPERS_ROOT = REPO_ROOT / "backend" / "data" / "community_papers"


def _configure_stdout_utf8(stdout: Any = sys.stdout) -> None:
    reconfigure = getattr(stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def _iter_paper_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def scan_community_papers(root: Path = DEFAULT_COMMUNITY_PAPERS_ROOT) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for paper_dir in _iter_paper_dirs(root):
        result = evaluate_directory(paper_dir)
        diagnostics = result.diagnostics()
        items.append(
            {
                "arxiv_id": paper_dir.name,
                "path": str(paper_dir),
                "passed": result.passed,
                "reasons": diagnostics["reasons"],
                "metrics": diagnostics["metrics"],
            }
        )
    failed = [item for item in items if not item["passed"]]
    return {
        "root": str(root),
        "total": len(items),
        "failed": len(failed),
        "items": items,
    }


def main() -> None:
    _configure_stdout_utf8()
    parser = argparse.ArgumentParser(
        description="Audit canonical community paper assets for translation quality gate failures."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_COMMUNITY_PAPERS_ROOT,
        help="Community papers root to scan. Defaults to backend/data/community_papers.",
    )
    parser.add_argument("--json-out", type=Path, default=None, help="Optional JSON report path.")
    parser.add_argument(
        "--fail-on-bad",
        action="store_true",
        help="Exit with code 2 when any paper fails the quality gate.",
    )
    args = parser.parse_args()

    report = scan_community_papers(args.root)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    try:
        print(payload)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.fail_on_bad and report["failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
