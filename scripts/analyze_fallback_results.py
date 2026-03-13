import argparse
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    default_outputs = project_root / "backend" / "data" / "outputs"
    default_report = project_root / "scripts" / "clean_results2.txt"

    parser = argparse.ArgumentParser(
        description="Analyze fallback-related translation records."
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=default_outputs,
        help=f"Directory containing task output folders (default: {default_outputs})",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=default_report,
        help=f"Report file path (default: {default_report})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs_dir = args.outputs_dir.resolve()
    report_file = args.output_file.resolve()

    if not outputs_dir.exists():
        raise FileNotFoundError(f"Outputs directory not found: {outputs_dir}")

    total_blocks = 0
    fallbacks_analyzed = []

    for path in outputs_dir.rglob("*"):
        if path.name not in {"sections_map.json", "envs_map.json"} or not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = list(data.values())
        else:
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            total_blocks += 1
            status = item.get("translation_status", "")
            has_fallback_reason = "fallback_reason" in item
            if "fallback" in status or has_fallback_reason or status == "ultimate_downgrade_applied":
                item_id = item.get("id", item.get("section", "unknown"))
                message = item.get("fallback_reason", "")
                reason_tag = item.get("repair_rejection_reason")

                if status == "ultimate_downgrade_applied":
                    category = f"Ultimate Downgrade ({reason_tag})" if reason_tag else "Ultimate Downgrade"
                elif message == "invariant_raw_structure_exposed":
                    category = "Invariant Structure (Expected Pass-through)"
                else:
                    category = (
                        f"Silent Fallback ({status}) ({reason_tag})"
                        if reason_tag
                        else f"Silent Fallback (Status: {status})"
                    )

                fallbacks_analyzed.append((category, path.parent.name, item_id, message))

    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("w", encoding="utf-8") as out:
        for category, doc, idx, message in sorted(fallbacks_analyzed):
            out.write(f"[{category}] {doc} ID {idx} - {message}\n")

        out.write(f"\nTotal blocks: {total_blocks}\n")
        out.write(f"Total fallback-related: {len(fallbacks_analyzed)}\n")
        counts = Counter([entry[0] for entry in fallbacks_analyzed])
        for key, value in counts.items():
            out.write(f"{key}: {value}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
