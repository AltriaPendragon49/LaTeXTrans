from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency guard
    BeautifulSoup = None  # type: ignore[assignment]

try:
    from PyPDF2 import PdfReader
except Exception:  # pragma: no cover - optional dependency guard
    PdfReader = None  # type: ignore[assignment]


QUALITY_GATE_DIAGNOSTIC_FILENAME = "community_publish_quality_gate.json"

SOURCE_FALLBACK_STATUSES = {
    "fallback_source_api_failure",
    "payload_invariant_passthrough",
    "source_passthrough",
    "source_fallback",
    "provider_failure_source_fallback",
}

HIGH_IMPORTANCE_SECTION_TOKENS = {
    "-1",
    "0",
    "title",
    "abstract",
    "intro",
    "introduction",
    "conclusion",
    "summary",
}

FATAL_PROVIDER_TOKENS = {
    "auth_failed",
    "authentication",
    "invalid_api_key",
    "unauthorized",
    "permission_denied",
    "quota_exhausted",
    "provider_quota_exhausted",
    "insufficient_quota",
    "unsupported_model",
    "model_not_found",
    "exhausted_provider_failover",
    "provider_failover_exhausted",
}


@dataclass(frozen=True)
class CommunityQualityConfig:
    fake_fallback_phrases: tuple[str, ...] = (
        "相关内容已转为简要中文表述",
        "此处内容已做保守中文降级处理",
        "此处已做保守中文降级处理",
        "此处内容已做保守中文降级处理",
        "这段内容已做保守中文降级处理",
        "已做保守中文降级",
        "翻译服务暂不可用",
        "由于模型调用失败",
        "无法生成可靠译文",
        "无法翻译该内容",
    )
    max_source_fallback_sections: int = 1
    max_short_source_fallback_chars: int = 220
    max_source_fallback_body_ratio: float = 0.08
    min_body_chars_for_source_ratio: int = 1000
    english_prose_min_words: int = 18
    english_prose_ratio: float = 0.28
    max_text_chars: int = 1_000_000


@dataclass(frozen=True)
class QualityGateReason:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    reasons: list[dict[str, Any]]
    metrics: dict[str, Any]

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema": "community_publish_quality_gate.v1",
            "passed": self.passed,
            "reasons": self.reasons,
            "metrics": self.metrics,
        }


def _reason(code: str, message: str, **details: Any) -> dict[str, Any]:
    return asdict(QualityGateReason(code=code, message=message, details=details))


def _normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def _strip_html_to_prose(html: str) -> str:
    if not html:
        return ""
    if BeautifulSoup is None:
        return re.sub(r"<[^>]+>", " ", html)

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "code", "pre", "math"]):
        tag.decompose()
    for tag in list(soup.find_all(["section", "div"])):
        heading = tag.find(["h1", "h2", "h3", "h4"])
        heading_text = heading.get_text(" ", strip=True).lower() if heading else ""
        if any(token in heading_text for token in ("references", "bibliography", "参考文献")):
            tag.decompose()
    return soup.get_text("\n", strip=True)


def _strip_ignored_non_prose_regions(text: str) -> str:
    stripped = _normalize_text(text)
    stripped = re.sub(r"https?://\S+|www\.\S+", " ", stripped)
    stripped = re.sub(r"\$.*?\$", " ", stripped, flags=re.DOTALL)
    stripped = re.sub(r"\\\[(.*?)\\\]|\\\((.*?)\\\)", " ", stripped, flags=re.DOTALL)
    stripped = re.sub(r"\[[0-9,\-\s]+\]", " ", stripped)
    stripped = re.sub(r"\([A-Z][A-Za-z]+(?: et al\.)?,?\s+\d{4}[a-z]?\)", " ", stripped)
    stripped = re.sub(
        r"\\begin\{(?:verbatim|lstlisting|thebibliography|equation|align|figure|table)\}.*?\\end\{\w+\}",
        " ",
        stripped,
        flags=re.DOTALL,
    )
    stripped = re.sub(r"\\(?:cite|ref|eqref|url|href|label|includegraphics)(?:\[[^\]]*\])?\{[^}]*\}", " ", stripped)
    return stripped


def _body_text(*, preview_html: Optional[str], pdf_text: Optional[str], output_text: Optional[str]) -> str:
    parts = []
    if preview_html:
        parts.append(_strip_html_to_prose(preview_html))
    if pdf_text:
        parts.append(_normalize_text(pdf_text))
    if output_text:
        parts.append(_normalize_text(output_text))
    return "\n".join(part for part in parts if part).strip()


def _english_words(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", text)
    filtered: list[str] = []
    for word in words:
        if len(word) <= 1:
            continue
        if word.isupper() and len(word) <= 8:
            continue
        if re.search(r"\d", word):
            continue
        filtered.append(word)
    return filtered


def _long_english_prose_spans(text: str, *, min_words: int) -> list[str]:
    stripped = _strip_ignored_non_prose_regions(text)
    chunks = re.split(r"(?:\n{2,}|[。！？])", stripped)
    spans: list[str] = []
    for chunk in chunks:
        normalized = " ".join(chunk.split())
        if not normalized:
            continue
        words = _english_words(normalized)
        if len(words) >= min_words:
            spans.append(normalized[:300])
    return spans


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text or ""))


def _source_fallback_sections(sections: Optional[Iterable[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    fallback_sections: list[dict[str, Any]] = []
    for section in sections or []:
        status = str(section.get("translation_status") or "").strip()
        fallback_reason = str(section.get("fallback_reason") or "").strip()
        if status not in SOURCE_FALLBACK_STATUSES and "source" not in fallback_reason.lower():
            continue
        section_id = str(
            section.get("section")
            or section.get("section_id")
            or section.get("chunk_id")
            or ""
        ).strip()
        content = _normalize_text(section.get("trans_content") or section.get("content"))
        fallback_sections.append(
            {
                "section": section_id,
                "status": status,
                "fallback_reason": fallback_reason,
                "chars": len(content),
                "sample": content[:200],
            }
        )
    return fallback_sections


def _is_high_importance_section(section_id: str) -> bool:
    lowered = section_id.strip().lower()
    return any(token in lowered for token in HIGH_IMPORTANCE_SECTION_TOKENS)


def _fatal_provider_hits(task: Optional[Mapping[str, Any]]) -> list[str]:
    if not isinstance(task, Mapping):
        return []
    fields = [
        task.get("failure_reason_code"),
        task.get("failure_class"),
        task.get("detail_code"),
        task.get("terminal_reason"),
        task.get("error"),
        task.get("warnings"),
    ]
    provider_state = task.get("provider_state")
    if isinstance(provider_state, Mapping):
        fields.extend(provider_state.values())
    haystack = " ".join(_normalize_text(value).lower() for value in fields if value)
    return sorted(token for token in FATAL_PROVIDER_TOKENS if token in haystack)


def evaluate_community_translation_quality(
    *,
    preview_html: Optional[str] = None,
    pdf_text: Optional[str] = None,
    output_text: Optional[str] = None,
    sections: Optional[Iterable[Mapping[str, Any]]] = None,
    task: Optional[Mapping[str, Any]] = None,
    config: Optional[CommunityQualityConfig] = None,
) -> QualityGateResult:
    resolved_config = config or CommunityQualityConfig()
    combined_text = _body_text(preview_html=preview_html, pdf_text=pdf_text, output_text=output_text)
    combined_text = combined_text[: resolved_config.max_text_chars]
    searchable = "\n".join(
        part
        for part in (
            preview_html or "",
            pdf_text or "",
            output_text or "",
            combined_text,
        )
        if part
    )
    reasons: list[dict[str, Any]] = []

    phrase_hits = [
        phrase
        for phrase in resolved_config.fake_fallback_phrases
        if phrase and phrase in searchable
    ]
    if phrase_hits:
        reasons.append(
            _reason(
                "fake_fallback_phrase",
                "Output contains fixed fake fallback translation text.",
                phrases=phrase_hits[:5],
            )
        )

    fallback_sections = _source_fallback_sections(sections)
    total_fallback_chars = sum(int(item["chars"]) for item in fallback_sections)
    body_chars = max(len(combined_text), 1)
    ratio_body_chars = max(body_chars, resolved_config.min_body_chars_for_source_ratio)
    fallback_ratio = total_fallback_chars / ratio_body_chars
    if len(fallback_sections) > resolved_config.max_source_fallback_sections:
        reasons.append(
            _reason(
                "excessive_source_fallback",
                "More than one source fallback section remains in final output.",
                sections=fallback_sections[:10],
            )
        )
    elif fallback_sections:
        fallback = fallback_sections[0]
        is_important = _is_high_importance_section(str(fallback["section"]))
        if (
            int(fallback["chars"]) > resolved_config.max_short_source_fallback_chars
            or fallback_ratio > resolved_config.max_source_fallback_body_ratio
            or is_important
        ):
            reasons.append(
                _reason(
                    "large_source_fallback",
                    "Source fallback section exceeds allowed size, ratio, or importance threshold.",
                    section=fallback,
                    fallback_ratio=fallback_ratio,
                    high_importance_section=is_important,
                )
            )

    english_spans = _long_english_prose_spans(
        combined_text,
        min_words=resolved_config.english_prose_min_words,
    )
    english_word_count = len(_english_words(_strip_ignored_non_prose_regions(combined_text)))
    cjk_present = _contains_cjk(combined_text)
    total_words = max(len(re.findall(r"\w+", _strip_ignored_non_prose_regions(combined_text))), 1)
    english_ratio = english_word_count / total_words
    if english_spans and (not cjk_present or english_ratio >= resolved_config.english_prose_ratio):
        reasons.append(
            _reason(
                "high_source_language_retention",
                "Output contains long retained English prose outside ignored technical regions.",
                english_ratio=english_ratio,
                samples=english_spans[:5],
            )
        )

    fatal_hits = _fatal_provider_hits(task)
    if fatal_hits:
        reasons.append(
            _reason(
                "fatal_provider_failure",
                "Task metadata records a fatal upstream provider state.",
                provider_tokens=fatal_hits,
            )
        )

    metrics = {
        "text_chars": len(combined_text),
        "cjk_present": cjk_present,
        "english_word_count": english_word_count,
        "english_ratio": english_ratio,
        "english_span_count": len(english_spans),
        "source_fallback_section_count": len(fallback_sections),
        "source_fallback_chars": total_fallback_chars,
        "source_fallback_ratio": fallback_ratio,
        "fatal_provider_token_count": len(fatal_hits),
    }
    return QualityGateResult(passed=not reasons, reasons=reasons, metrics=metrics)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_sections_from_directory(base: Path) -> list[dict[str, Any]]:
    loaded = _read_json(base / "sections_map.json")
    if isinstance(loaded, list):
        return [item for item in loaded if isinstance(item, dict)]
    return []


def _read_first_existing_text(candidates: Iterable[Path]) -> Optional[str]:
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
    return None


def _extract_pdf_text(pdf_path: Path) -> Optional[str]:
    if PdfReader is None or not pdf_path.exists():
        return None
    try:
        reader = PdfReader(str(pdf_path))
        chunks = []
        for page in reader.pages[:12]:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks).strip()
    except Exception:
        return None


def collect_quality_inputs_from_directory(base: Path) -> dict[str, Any]:
    html_candidates = [
        base / "preview.html",
        base / "preview" / "preview.html",
        *sorted(base.rglob("*.html")),
    ]
    tex_candidates = [
        base / "main.tex",
        *sorted(base.rglob("*.tex"), key=lambda path: path.stat().st_size if path.exists() else 0, reverse=True),
    ]
    pdf_candidates = sorted(base.rglob("*.pdf"), key=lambda path: path.stat().st_size if path.exists() else 0, reverse=True)
    return {
        "preview_html": _read_first_existing_text(html_candidates),
        "output_text": _read_first_existing_text(tex_candidates),
        "pdf_text": _extract_pdf_text(pdf_candidates[0]) if pdf_candidates else None,
        "sections": load_sections_from_directory(base),
    }


def evaluate_directory(
    base: Path,
    *,
    task: Optional[Mapping[str, Any]] = None,
    config: Optional[CommunityQualityConfig] = None,
) -> QualityGateResult:
    inputs = collect_quality_inputs_from_directory(base)
    return evaluate_community_translation_quality(
        preview_html=inputs.get("preview_html"),
        pdf_text=inputs.get("pdf_text"),
        output_text=inputs.get("output_text"),
        sections=inputs.get("sections"),
        task=task,
        config=config,
    )


def write_quality_diagnostics(base: Path, result: QualityGateResult) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    path = base / QUALITY_GATE_DIAGNOSTIC_FILENAME
    path.write_text(json.dumps(result.diagnostics(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
