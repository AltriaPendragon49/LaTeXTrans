import argparse
import json
import re
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.latex.structure_guard import validate_project_structure
from backend.app.services.agents.validator_agent import find_long_english_prose_spans


COMPILE_FALLBACK_PENDING_STATUSES = {
    "structural_fallback_pending_compile",
    "fallback_source_compile_first",
}


JSON_FILES = [
    "inputs_map.json",
    "envs_map.json",
    "captions_map.json",
    "newcommands_map.json",
    "sections_map.json",
    "errors_report.json",
]


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _find_main_tex(bundle_root: Path) -> Optional[Path]:
    tex_files = sorted(bundle_root.rglob("*.tex"))
    if not tex_files:
        return None
    main_candidates = [path for path in tex_files if path.name == "main.tex"]
    if main_candidates:
        return main_candidates[0]
    return max(tex_files, key=lambda path: path.stat().st_size)


def _placeholder_only_chunks(sections: List[Dict[str, Any]]) -> List[str]:
    chunks: List[str] = []
    for section in sections or []:
        content = (section.get("content") or "").strip()
        if content and re.fullmatch(r"<PLACEHOLDER_[^>]+>", content):
            chunks.append(str(section.get("section", "")))
    return chunks


def _count_status(items: List[Dict[str, Any]]) -> Dict[str, int]:
    counter = Counter(str(item.get("translation_status", "<none>")) for item in items or [])
    return dict(counter)


def _invariant_fallback_sections(sections: List[Dict[str, Any]]) -> List[str]:
    return [
        str(section.get("section", ""))
        for section in sections or []
        if str(section.get("fallback_reason", "")).startswith("invariant_")
    ]


def _structure_shell_sections(sections: List[Dict[str, Any]]) -> List[str]:
    return [
        str(section.get("section", ""))
        for section in sections or []
        if bool(section.get("contains_structure_shell"))
    ]


def _long_english_span_summary(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    samples: List[Dict[str, str]] = []
    count = 0
    for section in sections or []:
        section_id = str(section.get("section", ""))
        if section_id in {"-1", "0"}:
            continue
        spans = find_long_english_prose_spans(section.get("trans_content") or "", min_words=18)
        if not spans:
            continue
        count += len(spans)
        for span in spans[:2]:
            if len(samples) >= 5:
                break
            samples.append({"section": section_id, "sample": span[:200]})
        if len(samples) >= 5:
            break
    return {"count": count, "samples": samples}


def _strip_bibliography_regions(text: str) -> str:
    if not text:
        return ""

    stripped = re.sub(
        r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
        "",
        text,
        flags=re.DOTALL,
    )
    for pattern in (
        r"\\printbibliography(?:\[[^\]]*\])?",
        r"\\bibliography\{[^}]+\}",
    ):
        match = re.search(pattern, stripped)
        if match:
            stripped = stripped[: match.start()]
    return stripped


def _long_english_span_summary_for_text(text: str) -> Dict[str, Any]:
    spans = find_long_english_prose_spans(text or "", min_words=18)
    return {
        "count": len(spans),
        "samples": [{"sample": span[:200]} for span in spans[:5]],
    }


def _final_pending_compile_fallback_sections(sections: List[Dict[str, Any]]) -> List[str]:
    return [
        str(section.get("section", ""))
        for section in sections or []
        if section.get("translation_status") in COMPILE_FALLBACK_PENDING_STATUSES
    ]


def _artifact_summary(base: Path) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"path": str(base)}
    loaded = {name: _load_json(base / name) for name in JSON_FILES}

    for name, obj in loaded.items():
        if isinstance(obj, list):
            summary[name] = {"count": len(obj)}
        elif obj is None:
            summary[name] = {"count": None}
        else:
            summary[name] = {"count": 1}

    sections = loaded.get("sections_map.json") or []
    envs = loaded.get("envs_map.json") or []
    errors = loaded.get("errors_report.json") or []

    summary["chunk_ids"] = [str(section.get("section", "")) for section in sections]
    summary["placeholder_only_chunks"] = _placeholder_only_chunks(sections)
    summary["invariant_fallback_sections"] = _invariant_fallback_sections(sections)
    summary["structure_shell_sections"] = _structure_shell_sections(sections)
    summary["section_statuses"] = _count_status(sections)
    summary["env_statuses"] = _count_status(envs)
    summary["error_types"] = dict(Counter(str(err.get("error_type", "<none>")) for err in errors))
    long_english = _long_english_span_summary(sections)
    summary["long_english_span_count"] = long_english["count"]
    summary["long_english_span_samples"] = long_english["samples"]
    summary["final_pending_compile_fallback_sections"] = _final_pending_compile_fallback_sections(sections)

    main_tex = _find_main_tex(base)
    summary["main_tex_path"] = str(main_tex) if main_tex else None
    if main_tex and main_tex.exists():
        text = main_tex.read_text(encoding="utf-8", errors="replace")
        summary["main_tex_placeholders"] = sorted(set(re.findall(r"<PLACEHOLDER_[^>]+>", text)))[:20]
        summary["main_tex_env_tokens"] = sorted(set(re.findall(r"<ENV(?:_BEGIN|_END)?_[^>]+>", text)))[:20]
        summary["structure_guard"] = validate_project_structure(str(main_tex))
        main_tex_english = _long_english_span_summary_for_text(_strip_bibliography_regions(text))
        summary["main_tex_long_english_span_count"] = main_tex_english["count"]
        summary["main_tex_long_english_span_samples"] = main_tex_english["samples"]
    else:
        summary["main_tex_placeholders"] = []
        summary["main_tex_env_tokens"] = []
        summary["structure_guard"] = {"ok": False, "message": "main tex not found"}
        summary["main_tex_long_english_span_count"] = 0
        summary["main_tex_long_english_span_samples"] = []

    pdfs = sorted(base.rglob("*.pdf"))
    summary["pdf_candidates"] = [str(path) for path in pdfs[:10]]
    summary["pdf_present"] = bool(pdfs)

    task_log = _load_json(base / "task_log.json")
    if isinstance(task_log, list) and task_log:
        summary["task_log_terminal_event"] = task_log[-1].get("event")
    else:
        summary["task_log_terminal_event"] = None

    return summary


def _paired_summary(label: str, backend_dir: Path, prototype_dir: Path) -> Dict[str, Any]:
    backend_summary = _artifact_summary(backend_dir)
    prototype_summary = _artifact_summary(prototype_dir)
    return {
        "label": label,
        "backend": backend_summary,
        "prototype": prototype_summary,
        "diff": {
            "section_count_delta": (backend_summary["sections_map.json"]["count"] or 0) - (prototype_summary["sections_map.json"]["count"] or 0),
            "error_count_delta": (backend_summary["errors_report.json"]["count"] or 0) - (prototype_summary["errors_report.json"]["count"] or 0),
            "backend_placeholder_only_chunks": backend_summary["placeholder_only_chunks"],
            "prototype_placeholder_only_chunks": prototype_summary["placeholder_only_chunks"],
        },
    }


def _markdown_report(pairs: List[Dict[str, Any]]) -> str:
    lines = ["# Backend vs Prototype Regression Audit", ""]
    for pair in pairs:
        lines.append(f"## {pair['label']}")
        lines.append("")
        lines.append(f"- Backend path: `{pair['backend']['path']}`")
        lines.append(f"- Prototype path: `{pair['prototype']['path']}`")
        lines.append(f"- Section delta: `{pair['diff']['section_count_delta']}`")
        lines.append(f"- Error delta: `{pair['diff']['error_count_delta']}`")
        lines.append(f"- Backend placeholder-only chunks: `{pair['diff']['backend_placeholder_only_chunks']}`")
        lines.append(f"- Prototype placeholder-only chunks: `{pair['diff']['prototype_placeholder_only_chunks']}`")
        lines.append(f"- Backend invariant fallback sections: `{pair['backend']['invariant_fallback_sections']}`")
        lines.append(f"- Prototype invariant fallback sections: `{pair['prototype']['invariant_fallback_sections']}`")
        lines.append(f"- Backend structure-shell sections: `{pair['backend']['structure_shell_sections']}`")
        lines.append(f"- Prototype structure-shell sections: `{pair['prototype']['structure_shell_sections']}`")
        lines.append(f"- Backend long-English span count: `{pair['backend']['long_english_span_count']}`")
        lines.append(f"- Prototype long-English span count: `{pair['prototype']['long_english_span_count']}`")
        lines.append(f"- Backend main-tex long-English span count: `{pair['backend']['main_tex_long_english_span_count']}`")
        lines.append(f"- Prototype main-tex long-English span count: `{pair['prototype']['main_tex_long_english_span_count']}`")
        lines.append(f"- Backend pending compile fallback sections: `{pair['backend']['final_pending_compile_fallback_sections']}`")
        lines.append(f"- Backend structure guard: `{pair['backend']['structure_guard']}`")
        lines.append(f"- Prototype structure guard: `{pair['prototype']['structure_guard']}`")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit backend/prototype pipeline outputs for regression analysis.")
    parser.add_argument(
        "--pair",
        action="append",
        required=True,
        help="Pair spec in the form label::backend_dir::prototype_dir",
    )
    parser.add_argument("--json-out", type=Path, default=None, help="Optional JSON output path")
    parser.add_argument("--md-out", type=Path, default=None, help="Optional Markdown output path")
    args = parser.parse_args()

    pairs: List[Dict[str, Any]] = []
    for raw_pair in args.pair:
        try:
            label, backend_raw, prototype_raw = raw_pair.split("::", 2)
        except ValueError as exc:
            raise SystemExit(f"Invalid --pair value: {raw_pair!r}") from exc
        pairs.append(_paired_summary(label, Path(backend_raw), Path(prototype_raw)))

    payload = {"pairs": pairs}
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.json_out:
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md_out:
        args.md_out.write_text(_markdown_report(pairs), encoding="utf-8")


if __name__ == "__main__":
    main()
