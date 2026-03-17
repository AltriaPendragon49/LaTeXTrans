import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from artifact_diff import compare_artifacts, resolve_artifact_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare backend and CLI artifacts with per-section/env parity details."
    )
    parser.add_argument("--cli", type=Path, required=True, help="CLI artifact directory or parent.")
    parser.add_argument("--backend", type=Path, required=True, help="Backend artifact directory or parent.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    return parser.parse_args()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item.get(key, item.get("section", ""))): item for item in items if isinstance(item, dict)}


def _collect_map_diffs(cli_root: Path, backend_root: Path, file_name: str, key: str) -> list[dict[str, Any]]:
    cli_items = _load_json(cli_root / file_name)
    backend_items = _load_json(backend_root / file_name)
    cli_index = _build_index(cli_items, key)
    backend_index = _build_index(backend_items, key)

    diffs: list[dict[str, Any]] = []
    for identifier in sorted(set(cli_index) | set(backend_index)):
        cli_item = cli_index.get(identifier)
        backend_item = backend_index.get(identifier)
        if cli_item is None or backend_item is None:
            diffs.append(
                {
                    "id": identifier,
                    "missing_on": "cli" if cli_item is None else "backend",
                }
            )
            continue

        field_diffs = {}
        for field in [
            "translation_status",
            "fallback_reason",
            "repair_rejection_reason",
            "translation_retry_count",
        ]:
            if cli_item.get(field) != backend_item.get(field):
                field_diffs[field] = {
                    "cli": cli_item.get(field),
                    "backend": backend_item.get(field),
                }

        if cli_item.get("content") != backend_item.get("content"):
            field_diffs["content_preview"] = {
                "cli": str(cli_item.get("content", "")).replace("\n", " ")[:160],
                "backend": str(backend_item.get("content", "")).replace("\n", " ")[:160],
            }

        if field_diffs:
            diffs.append({"id": identifier, "diffs": field_diffs})

    return diffs


def build_report(cli_path: Path, backend_path: Path) -> dict[str, Any]:
    cli_root = resolve_artifact_dir(cli_path)
    backend_root = resolve_artifact_dir(backend_path)
    report = compare_artifacts(cli_root, backend_root)
    report["map_diffs"] = {
        "sections_map.json": _collect_map_diffs(cli_root, backend_root, "sections_map.json", "section"),
        "envs_map.json": _collect_map_diffs(cli_root, backend_root, "envs_map.json", "placeholder"),
        "captions_map.json": _collect_map_diffs(cli_root, backend_root, "captions_map.json", "placeholder"),
    }
    return report


def main() -> int:
    args = parse_args()
    report = build_report(args.cli, args.backend)
    content = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
