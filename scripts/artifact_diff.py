import argparse
import difflib
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


CORE_JSON_FILES = [
    "sections_map.json",
    "envs_map.json",
    "captions_map.json",
    "newcommands_map.json",
    "inputs_map.json",
    "task_log.json",
    "replay_bundle.json",
]

VOLATILE_FILES = {
    "audit.jsonl",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two translation artifact directories and summarize parity gaps."
    )
    parser.add_argument("--left", type=Path, required=True, help="Left artifact directory or parent directory.")
    parser.add_argument("--right", type=Path, required=True, help="Right artifact directory or parent directory.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON report instead of human-readable text.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the report. Defaults to stdout only.",
    )
    parser.add_argument(
        "--show-matching",
        action="store_true",
        help="Include matching semantic files in the text report.",
    )
    parser.add_argument(
        "--context-lines",
        type=int,
        default=3,
        help="Context lines for main TeX preview diff (default: 3).",
    )
    parser.add_argument(
        "--max-diff-lines",
        type=int,
        default=60,
        help="Maximum unified diff lines to show for main TeX (default: 60).",
    )
    return parser.parse_args(argv)


def artifact_marker_score(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return -1

    score = 0
    has_direct_marker = False
    for name in CORE_JSON_FILES:
        if (path / name).exists():
            score += 5
            has_direct_marker = True
    if any(path.glob("*.pdf")):
        score += 3
        has_direct_marker = True
    if has_direct_marker and any(path.rglob("*.tex")):
        score += 2
    if path.name.startswith(("zh_", "ch_", "en_", "ja_", "fr_", "de_")):
        score += 1
    return score


def resolve_artifact_dir(path: Path) -> Path:
    candidate = path.resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Artifact path not found: {candidate}")
    if candidate.is_file():
        candidate = candidate.parent

    if artifact_marker_score(candidate) > 0:
        return candidate

    child_scores: list[tuple[int, Path]] = []
    for child in candidate.iterdir():
        if child.is_dir():
            score = artifact_marker_score(child)
            if score > 0:
                child_scores.append((score, child))

    if not child_scores:
        raise FileNotFoundError(
            f"Could not locate artifact directory under: {candidate}"
        )

    child_scores.sort(key=lambda item: (-item[0], item[1].name))
    best_score, best_path = child_scores[0]
    if len(child_scores) > 1 and child_scores[1][0] == best_score:
        names = ", ".join(str(item[1].name) for item in child_scores[:5])
        raise ValueError(
            f"Multiple candidate artifact directories found under {candidate}: {names}"
        )
    return best_path


def short_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_items(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.values())
    return []


def summarize_generic_json(data: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "type": type(data).__name__,
    }

    items = normalize_items(data)
    summary["item_count"] = len(items)
    if not items:
        return summary

    dict_items = [item for item in items if isinstance(item, dict)]
    summary["dict_item_count"] = len(dict_items)
    if not dict_items:
        return summary

    translation_status_counts = Counter(
        item.get("translation_status")
        for item in dict_items
        if item.get("translation_status")
    )
    if translation_status_counts:
        summary["translation_status_counts"] = dict(sorted(translation_status_counts.items()))

    fallback_reason_count = sum(1 for item in dict_items if item.get("fallback_reason"))
    if fallback_reason_count:
        summary["fallback_reason_count"] = fallback_reason_count

    repair_rejection_counts = Counter(
        item.get("repair_rejection_reason")
        for item in dict_items
        if item.get("repair_rejection_reason")
    )
    if repair_rejection_counts:
        summary["repair_rejection_counts"] = dict(sorted(repair_rejection_counts.items()))

    structure_shell_only_count = sum(
        1 for item in dict_items if item.get("structure_shell_only") is True
    )
    if structure_shell_only_count:
        summary["structure_shell_only_count"] = structure_shell_only_count

    immutable_only_count = sum(
        1 for item in dict_items if item.get("immutable_only") is True
    )
    if immutable_only_count:
        summary["immutable_only_count"] = immutable_only_count

    return summary


def summarize_task_log(data: Any) -> dict[str, Any]:
    items = normalize_items(data)
    summary: dict[str, Any] = {
        "type": type(data).__name__,
        "entry_count": len(items),
    }
    events = Counter()
    last_validation: dict[str, Any] | None = None
    last_compilation: dict[str, Any] | None = None

    for item in items:
        if not isinstance(item, dict):
            continue
        event = item.get("event")
        if not event:
            continue
        events[event] += 1
        if event == "validation_completed":
            last_validation = {
                key: item.get(key)
                for key in [
                    "errors_count",
                    "initial_errors_count",
                    "final_errors_count",
                    "retry_count",
                    "fallback_count",
                    "fallback_ratio",
                    "fallback_cap",
                    "fallback_cap_mode",
                ]
                if key in item
            }
        if event in {
            "compilation_completed",
            "compilation_completed_with_warnings",
            "compilation_failed",
        }:
            last_compilation = {
                "event": event,
                "engine": item.get("engine"),
                "pdf_path": item.get("pdf_path"),
                "error_summary": item.get("error_summary"),
            }

    summary["events"] = dict(sorted(events.items()))
    if last_validation:
        summary["last_validation"] = last_validation
    if last_compilation:
        summary["last_compilation"] = last_compilation
    return summary


def summarize_replay_bundle(data: Any) -> dict[str, Any]:
    summary = summarize_generic_json(data)
    if isinstance(data, dict):
        summary["top_level_keys"] = sorted(data.keys())
        for key in ["events", "steps", "artifacts", "diagnostics"]:
            value = data.get(key)
            if isinstance(value, list):
                summary[f"{key}_count"] = len(value)
            elif isinstance(value, dict):
                summary[f"{key}_count"] = len(value)
    return summary


def summarize_json(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if path.name == "task_log.json":
        return summarize_task_log(data)
    if path.name == "replay_bundle.json":
        return summarize_replay_bundle(data)
    return summarize_generic_json(data)


def compare_json_files(left: Path | None, right: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "left_exists": left is not None and left.exists(),
        "right_exists": right is not None and right.exists(),
    }
    if not result["left_exists"] or not result["right_exists"]:
        return result

    left_summary = summarize_json(left)
    right_summary = summarize_json(right)
    result["left_summary"] = left_summary
    result["right_summary"] = right_summary
    result["equal"] = left_summary == right_summary
    return result


def build_tree_index(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.split("/")[-1] in VOLATILE_FILES:
            continue
        files[relative] = path
    return files


def compare_tree(left_root: Path, right_root: Path) -> dict[str, Any]:
    left_files = build_tree_index(left_root)
    right_files = build_tree_index(right_root)

    left_set = set(left_files)
    right_set = set(right_files)
    common = sorted(left_set & right_set)

    changed: list[dict[str, Any]] = []
    same: list[str] = []
    for relative in common:
        left_path = left_files[relative]
        right_path = right_files[relative]
        left_hash = short_hash(left_path)
        right_hash = short_hash(right_path)
        if left_hash == right_hash:
            same.append(relative)
            continue
        changed.append(
            {
                "path": relative,
                "left_size": left_path.stat().st_size,
                "right_size": right_path.stat().st_size,
                "left_hash": left_hash,
                "right_hash": right_hash,
            }
        )

    return {
        "left_count": len(left_files),
        "right_count": len(right_files),
        "common_count": len(common),
        "same_count": len(same),
        "changed_count": len(changed),
        "only_left": sorted(left_set - right_set),
        "only_right": sorted(right_set - left_set),
        "changed": changed,
    }


def resolve_task_log_pdf(root: Path) -> Path | None:
    task_log = root / "task_log.json"
    if not task_log.exists():
        return None

    try:
        entries = load_json(task_log)
    except Exception:
        return None

    for item in reversed(normalize_items(entries)):
        if not isinstance(item, dict):
            continue
        pdf_path = item.get("pdf_path")
        if not pdf_path:
            continue
        candidate = Path(pdf_path)
        if candidate.exists():
            return candidate
        normalized = str(candidate).replace("\\", "/")
        if root.name in normalized:
            suffix = normalized.split(root.name, maxsplit=1)[-1].lstrip("/\\")
            nested_candidate = root / suffix
            if nested_candidate.exists():
                return nested_candidate
    return None


def select_main_pdf(root: Path) -> Path | None:
    from_log = resolve_task_log_pdf(root)
    if from_log is not None:
        return from_log

    root_candidate = root / f"{root.name}.pdf"
    if root_candidate.exists():
        return root_candidate

    pdfs = sorted(
        [
            path
            for path in root.rglob("*.pdf")
            if "figures" not in path.parts and "images" not in path.parts
        ],
        key=lambda path: (len(path.relative_to(root).parts), path.name),
    )
    return pdfs[0] if pdfs else None


def _tex_relevance(root: Path, path: Path) -> tuple[int, int, int, str]:
    relative = path.relative_to(root)
    depth = len(relative.parts)
    try:
        sample = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        sample = ""
    has_documentclass = "\\documentclass" in sample
    has_begin_document = "\\begin{document}" in sample
    score = 0
    if has_documentclass:
        score += 4
    if has_begin_document:
        score += 4
    if path.stem == root.name:
        score += 2
    if path.name.lower().startswith("main"):
        score += 1
    return (-score, depth, -path.stat().st_size, relative.as_posix())


def select_main_tex(root: Path) -> Path | None:
    tex_files = list(root.rglob("*.tex"))
    if not tex_files:
        return None
    tex_files.sort(key=lambda path: _tex_relevance(root, path))
    return tex_files[0]


def summarize_file(path: Path | None, root: Path) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"exists": False}
    return {
        "exists": True,
        "path": path.relative_to(root).as_posix(),
        "size": path.stat().st_size,
        "hash": short_hash(path),
    }


def compare_main_tex(left_root: Path, right_root: Path, context_lines: int, max_diff_lines: int) -> dict[str, Any]:
    left = select_main_tex(left_root)
    right = select_main_tex(right_root)
    result = {
        "left": summarize_file(left, left_root),
        "right": summarize_file(right, right_root),
    }
    if left is None or right is None:
        return result

    left_text = left.read_text(encoding="utf-8", errors="ignore")
    right_text = right.read_text(encoding="utf-8", errors="ignore")
    result["identical"] = left_text == right_text
    result["left_line_count"] = len(left_text.splitlines())
    result["right_line_count"] = len(right_text.splitlines())

    if left_text != right_text:
        diff_lines = list(
            difflib.unified_diff(
                left_text.splitlines(),
                right_text.splitlines(),
                fromfile=result["left"]["path"],
                tofile=result["right"]["path"],
                n=context_lines,
                lineterm="",
            )
        )
        result["diff_line_count"] = len(diff_lines)
        result["diff_preview"] = diff_lines[:max_diff_lines]
    return result


def compare_main_pdf(left_root: Path, right_root: Path) -> dict[str, Any]:
    left = select_main_pdf(left_root)
    right = select_main_pdf(right_root)
    result = {
        "left": summarize_file(left, left_root),
        "right": summarize_file(right, right_root),
    }
    if left is None or right is None:
        return result
    result["identical"] = result["left"]["hash"] == result["right"]["hash"]
    return result


def compare_semantic_files(left_root: Path, right_root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in CORE_JSON_FILES:
        left = left_root / name
        right = right_root / name
        result[name] = compare_json_files(left, right)
    return result


def compare_artifacts(
    left_path: Path,
    right_path: Path,
    *,
    context_lines: int = 3,
    max_diff_lines: int = 60,
) -> dict[str, Any]:
    left_root = resolve_artifact_dir(left_path)
    right_root = resolve_artifact_dir(right_path)
    return {
        "left_root": str(left_root),
        "right_root": str(right_root),
        "tree": compare_tree(left_root, right_root),
        "semantic_files": compare_semantic_files(left_root, right_root),
        "main_tex": compare_main_tex(left_root, right_root, context_lines, max_diff_lines),
        "main_pdf": compare_main_pdf(left_root, right_root),
    }


def format_semantic_file(name: str, payload: dict[str, Any], show_matching: bool) -> list[str]:
    exists_left = payload.get("left_exists", False)
    exists_right = payload.get("right_exists", False)
    if not exists_left or not exists_right:
        return [f"- {name}: missing on {'left' if not exists_left else 'right'}"]

    if payload.get("equal") and not show_matching:
        return []

    marker = "match" if payload.get("equal") else "diff"
    return [
        f"- {name}: {marker}",
        f"  left={json.dumps(payload.get('left_summary', {}), ensure_ascii=False, sort_keys=True)}",
        f"  right={json.dumps(payload.get('right_summary', {}), ensure_ascii=False, sort_keys=True)}",
    ]


def render_text_report(report: dict[str, Any], show_matching: bool = False) -> str:
    tree = report["tree"]
    lines = [
        "Artifact Diff Report",
        f"left:  {report['left_root']}",
        f"right: {report['right_root']}",
        "",
        "Tree Summary",
        f"- left files: {tree['left_count']}",
        f"- right files: {tree['right_count']}",
        f"- common files: {tree['common_count']}",
        f"- changed common files: {tree['changed_count']}",
        f"- only left: {len(tree['only_left'])}",
        f"- only right: {len(tree['only_right'])}",
    ]

    if tree["only_left"]:
        lines.append(f"- only-left sample: {', '.join(tree['only_left'][:10])}")
    if tree["only_right"]:
        lines.append(f"- only-right sample: {', '.join(tree['only_right'][:10])}")
    if tree["changed"]:
        changed_preview = ", ".join(item["path"] for item in tree["changed"][:10])
        lines.append(f"- changed sample: {changed_preview}")

    lines.extend(["", "Semantic Files"])
    for name, payload in report["semantic_files"].items():
        lines.extend(format_semantic_file(name, payload, show_matching))

    lines.extend(["", "Main TeX"])
    main_tex = report["main_tex"]
    lines.append(f"- left: {json.dumps(main_tex['left'], ensure_ascii=False, sort_keys=True)}")
    lines.append(f"- right: {json.dumps(main_tex['right'], ensure_ascii=False, sort_keys=True)}")
    if "identical" in main_tex:
        lines.append(f"- identical: {main_tex['identical']}")
    if "diff_preview" in main_tex:
        lines.append("- diff preview:")
        lines.extend(f"  {line}" for line in main_tex["diff_preview"])

    lines.extend(["", "Main PDF"])
    main_pdf = report["main_pdf"]
    lines.append(f"- left: {json.dumps(main_pdf['left'], ensure_ascii=False, sort_keys=True)}")
    lines.append(f"- right: {json.dumps(main_pdf['right'], ensure_ascii=False, sort_keys=True)}")
    if "identical" in main_pdf:
        lines.append(f"- identical: {main_pdf['identical']}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = compare_artifacts(
        args.left,
        args.right,
        context_lines=args.context_lines,
        max_diff_lines=args.max_diff_lines,
    )
    content = (
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        if args.json
        else render_text_report(report, show_matching=args.show_matching)
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")

    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
