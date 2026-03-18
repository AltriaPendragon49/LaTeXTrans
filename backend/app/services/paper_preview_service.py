from __future__ import annotations

import html
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, List


SECTION_COMMAND_PATTERN = re.compile(
    r"^\s*\\(?P<kind>section|subsection|subsubsection)\*?\{(?P<title>[^}]*)\}\s*",
    re.DOTALL,
)
PLACEHOLDER_PATTERN = re.compile(r"<PLACEHOLDER_[A-Z]+_\d+>")


def _load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _build_placeholder_map(output_dir: Path) -> Dict[str, str]:
    placeholder_map: Dict[str, str] = {}
    for filename in ("envs_map.json", "captions_map.json", "newcommands_map.json"):
        for row in _load_json(output_dir / filename):
            placeholder = str(row.get("placeholder") or "").strip()
            if not placeholder:
                continue
            content = row.get("trans_content") or row.get("content") or ""
            placeholder_map[placeholder] = str(content)
    return placeholder_map


def _replace_placeholders(text: str, placeholder_map: Dict[str, str]) -> str:
    def _replace(match: re.Match[str]) -> str:
        placeholder = match.group(0)
        return placeholder_map.get(placeholder, placeholder)

    return PLACEHOLDER_PATTERN.sub(_replace, text)


def _extract_title_and_body(text: str) -> tuple[str | None, str]:
    match = SECTION_COMMAND_PATTERN.match(text or "")
    if not match:
        return None, text.strip()
    title = match.group("title").strip() or None
    body = text[match.end() :].strip()
    return title, body


def _heading_tag(section_id: str) -> str:
    depth = max(0, str(section_id).count("_"))
    return {0: "h2", 1: "h3", 2: "h4"}.get(depth, "h4")


def _paragraphs_from_text(text: str) -> List[str]:
    cleaned = (text or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", cleaned) if chunk.strip()]


def _render_block(chunk: str) -> str:
    escaped = html.escape(chunk, quote=False)
    if chunk.lstrip().startswith("\\begin{") or "\n" in chunk:
        return f"<pre class=\"paper-preview__latex\">{escaped}</pre>"
    return f"<p>{escaped}</p>"


def _render_section(section: Dict[str, Any], placeholder_map: Dict[str, str]) -> str:
    translated = str(section.get("trans_content") or section.get("content") or "").strip()
    if not translated:
        return ""

    translated = _replace_placeholders(translated, placeholder_map)
    title, body = _extract_title_and_body(translated)
    blocks: List[str] = []

    if title:
        tag = _heading_tag(str(section.get("section") or ""))
        blocks.append(f"<{tag}>{html.escape(title, quote=False)}</{tag}>")

    for paragraph in _paragraphs_from_text(body):
        blocks.append(_render_block(paragraph))

    if not blocks:
        return ""

    return "<section class=\"paper-preview__section\">" + "".join(blocks) + "</section>"


def generate_preview_html(output_dir: Path, target_dir: Path | None = None) -> Dict[str, str]:
    output_root = Path(output_dir)
    sections = _load_json(output_root / "sections_map.json")
    if not sections:
        raise FileNotFoundError("sections_map.json not found or empty")

    placeholder_map = _build_placeholder_map(output_root)
    rendered_sections = [
        _render_section(section, placeholder_map)
        for section in sections
        if str(section.get("section")) not in {"-1", "0"}
    ]
    rendered_sections = [section for section in rendered_sections if section]
    if not rendered_sections:
        raise FileNotFoundError("No translated sections available for preview")

    html_body = "".join(rendered_sections)
    preview_root = Path(target_dir) if target_dir is not None else output_root
    preview_root.mkdir(parents=True, exist_ok=True)
    preview_path = preview_root / "preview.html"
    preview_html = (
        "<article class=\"paper-preview\" data-reader-version=\"day4\">"
        f"{html_body}"
        "</article>"
    )
    preview_path.write_text(preview_html, encoding="utf-8")

    return {
        "asset_type": "preview_html",
        "file_path": str(preview_path),
        "file_name": preview_path.name,
        "mime_type": mimetypes.guess_type(preview_path.name)[0] or "text/html",
    }
