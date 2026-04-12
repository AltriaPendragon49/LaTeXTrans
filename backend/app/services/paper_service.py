from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import math
import mimetypes
import re
import shutil
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from uuid import uuid4

import httpx
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.routes import arxiv as arxiv_route
from backend.app.api.routes import download as download_route
from backend.app.api.routes import translate as translate_route
from backend.app.api.routes import upload as upload_route
from backend.app.core.config import TaskStatus, get_settings
from backend.app.db import DatabaseUnavailableError, db_connection, get_database_dialect
from backend.app.repositories import CommunityPaperRepository
from backend.app.services.latex.utils import extract_abstract, extract_text_from_tex, extract_title
from backend.app.services.latex_validator import find_main_tex_file
from backend.app.services import paper_preview_service
from backend.app.services.storage_backend import (
    LocalDiskStorageBackend,
    StorageBackend,
    StoredObjectRef,
    build_storage_backend,
)
from backend.app.services.task_manager import (
    clear_cached_runtime_artifacts,
    get_task_manager,
    get_task_queue,
)
from backend.app.utils.async_blocking import run_db_blocking

logger = logging.getLogger(__name__)

task_manager = get_task_manager()
settings = get_settings()

COMMUNITY_STATUS_OFFICIAL = "official"
COMMUNITY_STATUS_USER_FALLBACK = "user_fallback"
_RUNTIME_PAPER_OVERRIDES: Dict[str, Dict[str, Any]] = {}
TERMINAL_TASK_STATUSES = {
    "completed",
    "completed_with_warnings",
    "failed",
    "failed_compilation",
    "structure_invalid",
}
_preview_recovery_inflight: set[str] = set()
_detail_repair_inflight: set[str] = set()
_preview_payload_cache: Dict[str, Dict[str, Any]] = {}
_source_html_cache: Dict[str, str] = {}
_curation_semaphore: Optional[asyncio.Semaphore] = None
_delete_semaphore: Optional[asyncio.Semaphore] = None
_curation_job_tasks: Dict[str, asyncio.Task] = {}
_delete_job_tasks: Dict[str, asyncio.Task] = {}
ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS = 900
ADMIN_CURATION_CLEANUP_PAPER_TABLES = (
    "comments",
    "paper_assets",
    "paper_likes",
    "paper_favorites",
    "community_structured_insights",
    "community_similar_recommendations",
    "papers",
)
STRUCTURED_INSIGHT_SECTION_KEYS = (
    "problem",
    "solution",
    "innovation",
    "experiment",
    "future",
)
STRUCTURED_INSIGHT_MIN_TEXT_LENGTH = 80
STRUCTURED_INSIGHT_MAX_REPAIR_ATTEMPTS = 2
STRUCTURED_INSIGHT_READY_STATUS = "ready"
STRUCTURED_INSIGHT_PROCESSING_STATUS = "processing"
STRUCTURED_INSIGHT_NOT_READY_STATUS = "not_ready"
STRUCTURED_INSIGHT_SOURCE_MAX_CHARS = 2400
STRUCTURED_INSIGHT_DEFAULT_BLOCK_HEADING = "核心内容"
STRUCTURED_INSIGHT_FAILURE_PLACEHOLDERS = (
    "暂时无法生成",
    "生成失败",
    "请参考摘要",
    "信息不足",
    "暂无内容",
    "not_ready",
    "pending",
    "processing",
)
STRUCTURED_INSIGHT_SECTION_QUESTIONS = {
    "problem": "这篇论文解决什么问题，为什么重要，现有方法的关键不足是什么？",
    "solution": "作者的核心思路是什么，方法整体是如何工作的？",
    "innovation": "论文的关键创新点有哪些，相比已有方法，本质区别在哪里？",
    "experiment": "论文如何验证方法有效性，主要结论是什么？",
    "future": "这项工作有什么潜在改进或扩展方向，对相关研究有哪些启发？",
}
STRUCTURED_INSIGHT_SECTION_FALLBACK_LABELS = {
    "problem": "论文要解决的问题与现有方法不足",
    "solution": "论文的核心思路与整体流程",
    "innovation": "论文相对已有方法的关键创新",
    "experiment": "论文中的实验验证与主要结论",
    "future": "论文的潜在扩展方向与研究启发",
}
STRUCTURED_INSIGHT_SECTION_BOUNDARIES = {
    "problem": {
        "must_cover": "说明论文要解决的核心问题、该问题的重要性，以及已有方法的关键不足；优先使用论文中明确写出的定义、难点和研究动机。",
        "avoid": "不要详细展开作者方法，不要提前总结实验结果，不要写成泛泛的总述，不要用行业常识替代论文自己的问题陈述。",
        "section_focus": "聚焦论文自己如何定义问题、为什么重要、现有方法到底卡在哪里。",
    },
    "solution": {
        "must_cover": "说明作者的核心思路、整体 pipeline，以及关键步骤之间如何衔接；用论文里的方法机制解释它是怎么工作的。",
        "avoid": "不要描述系统的使用方式（如CLI、Web平台），不要写 CLI、Web、平台相关使用方式，不要写产品功能、部署流程，不要把输出 PDF、源码、日志等产品功能当成方法本身，不要只堆术语或模块名而不解释作用。",
        "section_focus": "聚焦方法如何工作、关键环节如何协作、各机制为什么这样串起来。",
    },
    "innovation": {
        "must_cover": "说明论文真正的创新点，以及它和已有方法相比本质上新在哪里；用可核验的差异解释创新，而不是靠宣传性判断。",
        "avoid": "不要只是换句话重复 solution，不要只说效果更好或提出了一个新方法，不要使用'首个'、'首次'、'无损'、'质的不同'这类强断言；同时避免使用“首次”“首个”“质的突破”等强判断，除非提供内容明确这样表述。",
        "section_focus": "聚焦论文和已有方法的差异来自结构、流程、目标或能力边界的哪里。",
    },
    "experiment": {
        "must_cover": "说明论文如何验证方法有效性，包括关键数据、指标、设置，以及实验最后证明了什么、优于哪些方法、优势体现在哪类能力上；如果论文中有实验数值、对比结果、提升幅度，请优先写出。",
        "avoid": "不要只罗列实验设置，不要只说做了实验且有效，要明确结论，优先做结果导向的解读。",
        "section_focus": "聚焦实验结果如何支撑论文主张，而不是仅复述评测流程。",
    },
    "future": {
        "must_cover": "说明论文暴露的真实局限、潜在扩展方向，以及对相关研究的启发；优先依据论文明确提到的局限、讨论或结论。",
        "avoid": "不要脱离论文内容自由发挥，不要只写空泛愿景，不要扩展出论文未出现的研究建议。",
        "section_focus": "聚焦论文自己承认的限制与自然延伸出的下一步，而不是额外脑补。",
    },
}
STRUCTURED_INSIGHT_GROUNDING_REQUIREMENTS = (
    "只基于提供的论文内容回答，不要补充输入里没有出现的具体事实；"
    "优先使用论文中明确写出的目标、方法、结果、局限与比较；"
    "避免用行业常识补全、避免空泛背景铺陈。"
)
STRUCTURED_INSIGHT_STYLE_REQUIREMENTS = (
    "使用中文面向读者解释，只输出正文，不要输出 JSON、标题、编号或项目列表。"
    "优先写论文特有的信息，控制在一到两段内，避免模板化套话。"
)
STRUCTURED_INSIGHT_ANTI_REPETITION_REQUIREMENTS = (
    "避免与其他模块重复，尤其不要把别的模块已经展开的内容原样再说一遍。"
)
STRUCTURED_INSIGHT_DENSITY_REQUIREMENTS = {
    "default": "保持段落式输出，以解释和压缩信息为主，不要改成 bullet 列表或密集条目堆叠。",
    "experiment": "以段落为主；如果论文里有清晰的指标、数值、对比结果，可加入至多 2~3 条很短的信息点，帮助读者快速扫描关键信息，但不要把整段写成列表。",
}
STRUCTURED_INSIGHT_STRUCTURE_REQUIREMENTS = (
    "输出应采用轻结构化形式：先写一行总结句，再写2~4个子结构段；"
    "每个子结构需有简短标题和对应解释内容；不要输出单一长段落，也不要改成纯 bullet 列表。"
)
STRUCTURED_INSIGHT_SUGGESTED_SUBHEADINGS = {
    "problem": ["问题本质", "现有方法的局限", "为什么重要"],
    "solution": ["核心思路", "关键流程", "模块协同"],
    "innovation": ["关键创新点", "本质差异", "为什么不一样"],
    "experiment": ["核心指标", "对比结果", "实验结论"],
    "future": ["当前局限", "可改进方向", "研究启发"],
}

STRUCTURED_INSIGHT_FINAL_SYSTEM_PROMPT = """
You are the paper-guide writer for PaperX community papers.
You will receive translated Chinese excerpts from one paper module.
Write exactly one Chinese explanatory passage for readers.

Rules:
- Output Chinese only.
- Ground the answer strictly in the provided excerpt.
- Use only supported claims from the provided excerpt and avoid filling gaps with general domain knowledge.
- Do not output JSON, headings, or markdown fences.
- Keep paragraph-first output; only when the style_requirements and density_requirements explicitly allow it may you use at most 2-3 short bullet-like lines.
- Prefer a summary sentence followed by 2-4 titled mini-sections; use plain text short titles rather than markdown headings.
- Write normal prose that is easy for readers to understand.
- If the evidence is limited, say that explicitly in Chinese instead of inventing facts.
- Stay focused on the current question instead of summarizing the whole paper.
- Prefer paper-specific details over generic praise or industry-level generalities.

Return only the final Chinese passage.
""".strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_curation_semaphore() -> asyncio.Semaphore:
    global _curation_semaphore
    if _curation_semaphore is None:
        _curation_semaphore = asyncio.Semaphore(max(1, int(getattr(settings, "community_curation_max_concurrent", 2))))
    return _curation_semaphore


def _get_delete_semaphore() -> asyncio.Semaphore:
    global _delete_semaphore
    if _delete_semaphore is None:
        _delete_semaphore = asyncio.Semaphore(1)
    return _delete_semaphore


def get_community_paper_repository() -> CommunityPaperRepository:
    return CommunityPaperRepository()


async def _run_local_repo(operation):
    return await asyncio.to_thread(operation)


async def _run_db_blocking_with_retry(
    operation_name: str,
    operation,
    *,
    retries: int = 3,
) -> Any:
    for attempt in range(retries + 1):
        try:
            return await run_db_blocking(operation)
        except (
            httpx.RemoteProtocolError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.ConnectError,
            httpx.NetworkError,
            httpx.TransportError,
            httpx.TimeoutException,
        ):
            if attempt >= retries:
                raise
            logger.warning(
                "Transient local database transport issue during %s; retrying (%s/%s)",
                operation_name,
                attempt + 1,
                retries + 1,
            )
            await asyncio.sleep(0.3 * (attempt + 1))


def _normalize_metadata_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = " ".join(str(value).split()).strip()
    return normalized or None


def _normalize_arxiv_identifier(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_metadata_text(value)
    if not normalized:
        return None
    return re.sub(r"v\d+$", "", normalized)


def _resolve_chat_completions_url(raw_url: Optional[str]) -> Optional[str]:
    normalized = str(raw_url or "").strip().rstrip("/")
    if not normalized:
        return None
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    text = str(raw_text or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _count_cjk_characters(value: Optional[str]) -> int:
    text = _normalize_metadata_text(value) or ""
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))


def _looks_untranslated_for_zh(value: Optional[str]) -> bool:
    text = _normalize_metadata_text(value) or ""
    if not text:
        return True
    cjk_count = _count_cjk_characters(text)
    letter_count = len(re.findall(r"[A-Za-z]", text))
    if cjk_count >= 8:
        return False
    if cjk_count > 0 and letter_count == 0:
        return False
    if cjk_count > 0 and (cjk_count / max(letter_count, 1)) >= 0.08:
        return False
    return letter_count >= 20


def _preview_html_looks_untranslated_for_zh(html_content: Optional[str]) -> bool:
    if not html_content:
        return True

    try:
        text = BeautifulSoup(html_content, "html.parser").get_text(" ", strip=True)
    except Exception:
        text = html_content

    return _looks_untranslated_for_zh(text)


def _normalize_legacy_preview_math_blocks(html_content: str) -> str:
    if not html_content:
        return html_content
    normalized = html_content
    if "paper-preview__latex" in normalized:
        normalized = re.sub(
            r'<pre class="paper-preview__latex">([\s\S]*?)</pre>',
            r'<div class="paper-preview__math-block">\1</div>',
            normalized,
            flags=re.DOTALL,
        )

    if "paper-preview__command-block" in normalized:
        omitted_note = (
            "<div class=\"paper-preview__note\">"
            "LaTeX source snippet omitted in HTML preview. Please refer to the PDF version."
            "</div>"
        )

        def _replace_command_block(match: re.Match[str]) -> str:
            command_body = match.group("body") or ""
            if not re.search(r"\\(?:begin|end)\{|\\includegraphics(?:\[[^\]]*\])?\{|\\[A-Za-z]{2,}", command_body):
                return match.group(0)
            return omitted_note

        normalized = re.sub(
            r'<div class="paper-preview__command-block">\s*<code>(?P<body>[\s\S]*?)</code>\s*</div>',
            _replace_command_block,
            normalized,
            flags=re.DOTALL,
        )

    # Legacy previews sometimes leaked table/layout TeX commands directly into table cells.
    # Strip these source tokens so readers do not see raw TeX in rendered HTML.
    normalized = re.sub(
        r"\\begin\{(?:table\*?|tabular\*?|tabulary|center)\}(?:\{[^}]*\})?",
        " ",
        normalized,
    )
    normalized = re.sub(r"\\end\{(?:table\*?|tabular\*?|tabulary|center)\}", " ", normalized)
    normalized = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}", " ", normalized)

    def _sanitize_table_cell(match: re.Match[str]) -> str:
        opening, body, closing = match.group(1), match.group(2), match.group(3)
        if "\\" not in body:
            return match.group(0)
        if not re.search(
            r"\\(?:multirow|multicolumn|resizebox|tabular|tabulary|cmidrule(?:\([^)]*\))?|cline|hline|toprule|midrule|bottomrule)\b|\[1\.1pt\]",
            body,
        ):
            return match.group(0)
        cleaned = body
        cleaned = re.sub(
            r"\\(?:multirow|multicolumn|resizebox|tabular|tabulary|cmidrule(?:\([^)]*\))?|cline|hline|toprule|midrule|bottomrule)\b(?:\{[^}]*\})*",
            " ",
            cleaned,
        )
        cleaned = re.sub(r"\\[A-Za-z]{2,}", " ", cleaned)
        cleaned = cleaned.replace("{", " ").replace("}", " ")
        cleaned = re.sub(r"\[1\.1pt\]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            cleaned = "LaTeX source omitted"
        return f"{opening}{cleaned}{closing}"

    normalized = re.sub(
        r"(<t[hd][^>]*>)([\s\S]*?)(</t[hd]>)",
        _sanitize_table_cell,
        normalized,
        flags=re.DOTALL,
    )
    return normalized


def _preview_asset_has_translated_content(preview_asset: Optional[Dict[str, Any]]) -> bool:
    if not preview_asset:
        return False

    preview_path = _resolve_storage_path(preview_asset.get("file_path") or "")
    if not preview_path.exists():
        return False

    try:
        html_content = preview_path.read_text(encoding="utf-8")
    except Exception:
        return False

    if _preview_html_needs_refresh(html_content):
        return False

    return not _preview_html_looks_untranslated_for_zh(html_content)


def _should_replace_translated_abstract(
    current_value: Optional[str],
    candidate_value: Optional[str],
    raw_abstract: Optional[str],
) -> bool:
    current = _normalize_metadata_text(current_value)
    candidate = _normalize_metadata_text(candidate_value)
    raw = _normalize_metadata_text(raw_abstract)
    if not candidate:
        return False
    if not current:
        return True
    if current == candidate:
        return False
    if raw and current == raw:
        return True
    if _looks_untranslated_for_zh(current) and _count_cjk_characters(candidate) > 0:
        return True
    return False


def _fetch_arxiv_metadata_sync(arxiv_id: str) -> Dict[str, Any]:
    response = requests.get(
        "https://export.arxiv.org/api/query",
        params={"id_list": arxiv_id},
        headers={"User-Agent": "LaTexTrans/CommunityWeek1Fix"},
        timeout=15,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", namespace)
    if entry is None:
        return {}

    title = _normalize_metadata_text(entry.findtext("atom:title", default="", namespaces=namespace))
    abstract_raw = _normalize_metadata_text(entry.findtext("atom:summary", default="", namespaces=namespace))
    authors = [
        _normalize_metadata_text(author.findtext("atom:name", default="", namespaces=namespace))
        for author in entry.findall("atom:author", namespace)
    ]
    categories = []
    for category in entry.findall("atom:category", namespace):
        term = _normalize_metadata_text(category.attrib.get("term"))
        if term and term not in categories:
            categories.append(term)

    return {
        "title": title,
        "authors": [author for author in authors if author],
        "categories": categories,
        "abstract_raw": abstract_raw,
    }


_SIMILARITY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "between",
    "by",
    "despite",
    "existing",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "modern",
    "of",
    "on",
    "or",
    "over",
    "paper",
    "progress",
    "propose",
    "proposed",
    "proposes",
    "recent",
    "remarkable",
    "show",
    "showing",
    "shows",
    "study",
    "that",
    "the",
    "their",
    "them",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "toward",
    "towards",
    "under",
    "use",
    "used",
    "using",
    "via",
    "we",
    "with",
    "within",
    "without",
    "based",
}


def _tokenize_similarity_text(value: Optional[str]) -> List[str]:
    normalized = _normalize_search_text(value)
    if not normalized:
        return []
    tokens = re.findall(r"[a-z][a-z0-9\-]{1,}|[\u4e00-\u9fff]{2,}", normalized)
    return [token for token in tokens if token not in _SIMILARITY_STOPWORDS]


def _build_similarity_query_terms(*, title: Optional[str], abstract: Optional[str], limit: int = 12) -> List[str]:
    selected: List[str] = []
    seen: set[str] = set()
    for raw_text in (title or "", abstract or ""):
        for token in _tokenize_similarity_text(raw_text):
            if token in seen:
                continue
            seen.add(token)
            selected.append(token)
            if len(selected) >= limit:
                return selected
    return selected


def _build_similarity_document_tokens(paper: Dict[str, Any]) -> List[str]:
    parts = [
        paper.get("title"),
        paper.get("abstract_raw"),
        paper.get("abstract_translated"),
        paper.get("arxiv_id"),
        " ".join(str(category) for category in (paper.get("categories") or [])),
        " ".join(
            str(author.get("name") if isinstance(author, dict) else author)
            for author in (paper.get("authors") or [])
        ),
    ]
    return _tokenize_similarity_text(" ".join(str(part) for part in parts if part))


def _collect_similarity_overlap_terms(query_terms: List[str], document_tokens: List[str]) -> List[str]:
    document_token_set = set(document_tokens)
    return [token for token in query_terms if token in document_token_set]


def _build_similarity_candidate_document_tokens(candidate: Dict[str, Any]) -> List[str]:
    parts = [
        candidate.get("title"),
        candidate.get("abstract"),
        candidate.get("arxiv_id"),
        " ".join(str(category) for category in (candidate.get("_categories") or [])),
    ]
    return _tokenize_similarity_text(" ".join(str(part) for part in parts if part))


def _merge_similarity_candidates(
    *,
    existing: Optional[Dict[str, Any]],
    incoming: Dict[str, Any],
) -> Dict[str, Any]:
    if existing is None:
        merged = dict(incoming)
        merged["_categories"] = list(dict.fromkeys(incoming.get("_categories") or []))
        return merged

    merged = dict(existing)
    if incoming.get("community_paper_id") and not merged.get("community_paper_id"):
        merged["community_paper_id"] = incoming.get("community_paper_id")
        merged["link_type"] = "community"

    if not merged.get("title") and incoming.get("title"):
        merged["title"] = incoming.get("title")
    if len(str(incoming.get("abstract") or "")) > len(str(merged.get("abstract") or "")):
        merged["abstract"] = incoming.get("abstract")
    if not merged.get("arxiv_url") and incoming.get("arxiv_url"):
        merged["arxiv_url"] = incoming.get("arxiv_url")

    merged_categories = list(dict.fromkeys((merged.get("_categories") or []) + (incoming.get("_categories") or [])))
    merged["_categories"] = merged_categories
    return merged


async def _normalize_similarity_candidate(
    *,
    candidate: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    candidate_arxiv_id = _normalize_arxiv_identifier(candidate.get("arxiv_id")) or ""
    candidate_title = _normalize_metadata_text(candidate.get("title")) or ""
    candidate_abstract = _normalize_metadata_text(candidate.get("abstract")) or ""
    if not candidate_title or not candidate_abstract:
        return None

    community_paper_id = str(candidate.get("community_paper_id") or "").strip() or None
    categories = [
        _normalize_metadata_text(item) or ""
        for item in (candidate.get("_categories") if isinstance(candidate.get("_categories"), list) else [])
    ]
    categories = [item for item in categories if item]

    if candidate_arxiv_id and not community_paper_id:
        community_paper = await _fetch_paper_by_arxiv_id(candidate_arxiv_id)
        if community_paper and _is_public_community_paper(community_paper):
            community_paper_id = str(community_paper.get("id") or "").strip() or None
            categories = categories or [
                _normalize_metadata_text(item) or ""
                for item in (
                    community_paper.get("categories") if isinstance(community_paper.get("categories"), list) else []
                )
            ]
            categories = [item for item in categories if item]

    return {
        "arxiv_id": candidate_arxiv_id,
        "title": candidate_title,
        "abstract": candidate_abstract,
        "arxiv_url": str(candidate.get("arxiv_url") or (f"https://arxiv.org/abs/{candidate_arxiv_id}" if candidate_arxiv_id else "")).strip(),
        "community_paper_id": community_paper_id,
        "link_type": "community" if community_paper_id else "arxiv",
        "_categories": categories,
    }


def _score_similarity_result_candidate(
    *,
    query_terms: List[str],
    document_tokens: List[str],
    candidate: Dict[str, Any],
    bm25_score: float,
    current_categories: List[str],
) -> Optional[float]:
    document_overlap_terms = _collect_similarity_overlap_terms(query_terms, document_tokens)
    title_tokens = set(_tokenize_similarity_text(candidate.get("title")))
    title_overlap_terms = [token for token in document_overlap_terms if token in title_tokens]
    category_overlap = len(set(current_categories).intersection(candidate.get("_categories") or []))
    if len(document_overlap_terms) < 2 and len(title_overlap_terms) < 2 and not (title_overlap_terms and category_overlap > 0):
        return None

    final_score = _score_local_similarity_candidate(
        query_terms=query_terms,
        paper={
            "title": candidate.get("title"),
            "categories": candidate.get("_categories") or [],
        },
        bm25_score=bm25_score,
        current_categories=current_categories,
    )
    return final_score if final_score > 0 else None


def _compute_bm25_scores(query_terms: List[str], documents: List[List[str]]) -> List[float]:
    if not query_terms or not documents:
        return [0.0 for _ in documents]

    document_frequencies: Dict[str, int] = {}
    for document in documents:
        for token in set(document):
            document_frequencies[token] = document_frequencies.get(token, 0) + 1

    avgdl = sum(len(document) for document in documents) / max(len(documents), 1)
    avgdl = avgdl or 1.0
    total_documents = len(documents)
    k1 = 1.5
    b = 0.75
    scores: List[float] = []
    unique_query_terms = list(dict.fromkeys(query_terms))
    for document in documents:
        if not document:
            scores.append(0.0)
            continue
        term_counts: Dict[str, int] = {}
        for token in document:
            term_counts[token] = term_counts.get(token, 0) + 1
        doc_length = len(document)
        score = 0.0
        for term in unique_query_terms:
            frequency = term_counts.get(term, 0)
            if frequency <= 0:
                continue
            df = document_frequencies.get(term, 0)
            idf = math.log(1 + ((total_documents - df + 0.5) / (df + 0.5)))
            numerator = frequency * (k1 + 1)
            denominator = frequency + k1 * (1 - b + b * (doc_length / avgdl))
            score += idf * (numerator / denominator)
        scores.append(score)
    return scores


def _score_local_similarity_candidate(
    *,
    query_terms: List[str],
    paper: Dict[str, Any],
    bm25_score: float,
    current_categories: List[str],
) -> float:
    title_tokens = set(_tokenize_similarity_text(paper.get("title")))
    category_overlap = len(set(current_categories).intersection(paper.get("categories") or []))
    title_overlap = sum(1 for token in query_terms if token in title_tokens)
    return bm25_score + (title_overlap * 0.8) + (category_overlap * 1.5)


def _select_arxiv_similarity_terms(*, title: Optional[str], abstract: Optional[str], limit: int = 6) -> List[str]:
    selected: List[str] = []
    seen: set[str] = set()

    for raw_text in (title or "", abstract or ""):
        candidates = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", raw_text)
        for candidate in candidates:
            normalized = candidate.lower()
            if normalized in _SIMILARITY_STOPWORDS:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append(candidate)
            if len(selected) >= limit:
                return selected
    return selected


async def _fetch_local_bm25_similar_candidates(
    *,
    paper: Dict[str, Any],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        candidates = await _run_local_repo(repository.list_public_papers)
    except DatabaseUnavailableError:
        candidates = []
    except Exception as exc:
        logger.warning("Failed to list local public papers for BM25 similarity on %s: %s", paper.get("id"), exc)
        candidates = []

    candidates = [_apply_runtime_paper_override(candidate) or candidate for candidate in candidates]
    current_paper_id = str(paper.get("id") or "").strip()
    current_arxiv_id = _normalize_arxiv_identifier(paper.get("arxiv_id")) or ""
    filtered_candidates = []
    for candidate in candidates:
        if not _is_public_community_paper(candidate):
            continue
        candidate_id = str(candidate.get("id") or "").strip()
        candidate_arxiv_id = _normalize_arxiv_identifier(candidate.get("arxiv_id")) or ""
        if candidate_id == current_paper_id:
            continue
        if current_arxiv_id and candidate_arxiv_id == current_arxiv_id:
            continue
        filtered_candidates.append(candidate)

    query_terms = _build_similarity_query_terms(
        title=paper.get("title"),
        abstract=paper.get("abstract_raw") or paper.get("abstract_translated"),
    )
    if not query_terms or not filtered_candidates:
        return []

    documents = [_build_similarity_document_tokens(candidate) for candidate in filtered_candidates]
    bm25_scores = _compute_bm25_scores(query_terms, documents)
    current_categories = [
        _normalize_metadata_text(item) or ""
        for item in (paper.get("categories") if isinstance(paper.get("categories"), list) else [])
    ]
    current_categories = [item for item in current_categories if item]

    ranked_candidates: List[Dict[str, Any]] = []
    for candidate, document_tokens, bm25_score in zip(filtered_candidates, documents, bm25_scores):
        document_overlap_terms = _collect_similarity_overlap_terms(query_terms, document_tokens)
        title_tokens = set(_tokenize_similarity_text(candidate.get("title")))
        title_overlap_terms = [token for token in document_overlap_terms if token in title_tokens]
        category_overlap = len(set(current_categories).intersection(candidate.get("categories") or []))
        if len(document_overlap_terms) < 2 and not (title_overlap_terms and category_overlap > 0):
            continue

        final_score = _score_local_similarity_candidate(
            query_terms=query_terms,
            paper=candidate,
            bm25_score=bm25_score,
            current_categories=current_categories,
        )
        if final_score <= 0:
            continue
        candidate_arxiv_id = _normalize_arxiv_identifier(candidate.get("arxiv_id")) or ""
        ranked_candidates.append(
            {
                "arxiv_id": candidate_arxiv_id,
                "title": _normalize_metadata_text(candidate.get("title")) or "",
                "abstract": _normalize_metadata_text(
                    candidate.get("abstract_raw") or candidate.get("abstract_translated")
                )
                or "",
                "arxiv_url": f"https://arxiv.org/abs/{candidate_arxiv_id}" if candidate_arxiv_id else "",
                "community_paper_id": str(candidate.get("id") or "").strip() or None,
                "link_type": "community",
                "_categories": candidate.get("categories") if isinstance(candidate.get("categories"), list) else [],
                "_score": final_score,
            }
        )

    ranked_candidates.sort(key=lambda item: (-float(item["_score"]), item["title"]))
    return [
        {
            "arxiv_id": item["arxiv_id"],
            "title": item["title"],
            "abstract": item["abstract"],
            "arxiv_url": item["arxiv_url"],
            "community_paper_id": item["community_paper_id"],
            "link_type": "community",
            "_categories": item.get("_categories") or [],
        }
        for item in ranked_candidates[:limit]
    ]


def _build_arxiv_similarity_queries(
    *,
    query_terms: List[str],
    categories: Optional[List[str]],
) -> List[str]:
    if not query_terms:
        return []

    groups: List[List[str]] = []
    groups.append(query_terms)
    if len(query_terms) > 1:
        groups.append(query_terms[1:])
    if len(query_terms) > 2:
        groups.append(query_terms[:2])

    primary_category = _normalize_metadata_text((categories or [None])[0])
    queries: List[str] = []
    seen: set[str] = set()
    for group in groups:
        if not group:
            continue
        joined = " OR ".join(f'all:"{term}"' for term in group)
        candidates = []
        if primary_category:
            candidates.append(f"(cat:{primary_category}) AND ({joined})")
        candidates.append(joined)
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            queries.append(candidate)
    if primary_category and f"cat:{primary_category}" not in seen:
        queries.append(f"cat:{primary_category}")
    return queries


def _score_arxiv_similarity_candidate(
    *,
    query_terms: List[str],
    current_categories: Optional[List[str]],
    candidate_title: str,
    candidate_abstract: str,
    candidate_categories: List[str],
) -> int:
    normalized_title = (candidate_title or "").lower()
    normalized_abstract = (candidate_abstract or "").lower()
    score = 0
    for term in query_terms:
        normalized_term = term.lower()
        if normalized_term in normalized_title:
            score += 4
        elif normalized_term in normalized_abstract:
            score += 2
    if current_categories and set(current_categories).intersection(candidate_categories):
        score += 3
    return score


def _fetch_arxiv_similar_candidates_sync(
    *,
    arxiv_id: Optional[str],
    title: Optional[str],
    abstract: Optional[str],
    categories: Optional[List[str]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    query_terms = _select_arxiv_similarity_terms(title=title, abstract=abstract)
    if not query_terms:
        return []

    current_arxiv_id = _normalize_arxiv_identifier(arxiv_id) or ""
    current_title = _normalize_metadata_text(title) or ""
    current_categories = [_normalize_metadata_text(item) or "" for item in (categories or [])]
    current_categories = [item for item in current_categories if item]
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    best_items: Dict[str, Dict[str, Any]] = {}
    ordered_ids: List[str] = []

    for search_query in _build_arxiv_similarity_queries(query_terms=query_terms, categories=current_categories):
        response = requests.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": search_query,
                "start": 0,
                "max_results": max(limit * 4, 20),
                "sortBy": "relevance",
                "sortOrder": "descending",
            },
            headers={"User-Agent": "LaTexTrans/CommunitySimilar"},
            timeout=15,
        )
        response.raise_for_status()

        root = ET.fromstring(response.text)
        query_found_new_item = False
        for entry in root.findall("atom:entry", namespace):
            entry_id = _normalize_metadata_text(entry.findtext("atom:id", default="", namespaces=namespace)) or ""
            candidate_arxiv_id = _normalize_arxiv_identifier(entry_id.rsplit("/", 1)[-1])
            candidate_title = _normalize_metadata_text(
                entry.findtext("atom:title", default="", namespaces=namespace)
            )
            candidate_abstract = _normalize_metadata_text(
                entry.findtext("atom:summary", default="", namespaces=namespace)
            )
            candidate_categories = [
                _normalize_metadata_text(category.attrib.get("term"))
                for category in entry.findall("atom:category", namespace)
            ]
            candidate_categories = [item for item in candidate_categories if item]
            if not candidate_arxiv_id or not candidate_title or not candidate_abstract:
                continue
            if current_arxiv_id and candidate_arxiv_id == current_arxiv_id:
                continue
            if current_title and candidate_title == current_title:
                continue

            scored_item = {
                "arxiv_id": candidate_arxiv_id,
                "title": candidate_title,
                "abstract": candidate_abstract,
                "arxiv_url": f"https://arxiv.org/abs/{candidate_arxiv_id}",
                "_categories": candidate_categories,
                "_score": _score_arxiv_similarity_candidate(
                    query_terms=query_terms,
                    current_categories=current_categories,
                    candidate_title=candidate_title,
                    candidate_abstract=candidate_abstract,
                    candidate_categories=candidate_categories,
                ),
            }
            previous = best_items.get(candidate_arxiv_id)
            if previous is None:
                ordered_ids.append(candidate_arxiv_id)
                best_items[candidate_arxiv_id] = scored_item
                query_found_new_item = True
            elif scored_item["_score"] > previous["_score"]:
                best_items[candidate_arxiv_id] = scored_item

        if query_found_new_item and len(best_items) >= limit:
            break

    ranked_items = sorted(
        (best_items[item_id] for item_id in ordered_ids if item_id in best_items),
        key=lambda item: (-int(item.get("_score") or 0), item["title"]),
    )
    return [
        {
            "arxiv_id": item["arxiv_id"],
            "title": item["title"],
            "abstract": item["abstract"],
            "arxiv_url": item["arxiv_url"],
            "_categories": item.get("_categories") or [],
        }
        for item in ranked_items[:limit]
    ]


async def _fetch_arxiv_similar_candidates(
    *,
    arxiv_id: Optional[str],
    title: Optional[str],
    abstract: Optional[str],
    categories: Optional[List[str]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    try:
        return await asyncio.to_thread(
            _fetch_arxiv_similar_candidates_sync,
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            categories=categories,
            limit=limit,
        )
    except Exception as exc:
        logger.warning("Failed to fetch arXiv similar candidates for %s: %s", arxiv_id or title or "paper", exc)
        return []


async def _generate_similar_recommendations_for_paper(
    *,
    paper: Dict[str, Any],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    current_arxiv_id = _normalize_arxiv_identifier(paper.get("arxiv_id")) or ""
    current_title = _normalize_metadata_text(paper.get("title")) or ""
    query_terms = _build_similarity_query_terms(
        title=paper.get("title"),
        abstract=paper.get("abstract_raw") or paper.get("abstract_translated"),
    )
    if not query_terms:
        return []

    current_categories = [
        _normalize_metadata_text(item) or ""
        for item in (paper.get("categories") if isinstance(paper.get("categories"), list) else [])
    ]
    current_categories = [item for item in current_categories if item]

    local_items = await _fetch_local_bm25_similar_candidates(paper=paper, limit=max(limit * 2, 20))
    arxiv_candidates = await _fetch_arxiv_similar_candidates(
        arxiv_id=current_arxiv_id or None,
        title=paper.get("title"),
        abstract=paper.get("abstract_raw") or paper.get("abstract_translated"),
        categories=paper.get("categories") if isinstance(paper.get("categories"), list) else None,
        limit=max(limit * 2, 20),
    )

    merged_candidates: Dict[str, Dict[str, Any]] = {}
    for raw_candidate in [*local_items, *arxiv_candidates]:
        candidate = await _normalize_similarity_candidate(candidate=raw_candidate)
        if candidate is None:
            continue
        candidate_arxiv_id = candidate.get("arxiv_id") or ""
        candidate_title = candidate.get("title") or ""
        if candidate_arxiv_id and current_arxiv_id and candidate_arxiv_id == current_arxiv_id:
            continue
        if candidate_title and current_title and candidate_title == current_title:
            continue
        candidate_key = candidate_arxiv_id or candidate_title.lower()
        merged_candidates[candidate_key] = _merge_similarity_candidates(
            existing=merged_candidates.get(candidate_key),
            incoming=candidate,
        )

    if not merged_candidates:
        return []

    merged_items = list(merged_candidates.values())
    documents = [_build_similarity_candidate_document_tokens(candidate) for candidate in merged_items]
    bm25_scores = _compute_bm25_scores(query_terms, documents)

    ranked_items: List[Dict[str, Any]] = []
    for candidate, document_tokens, bm25_score in zip(merged_items, documents, bm25_scores):
        final_score = _score_similarity_result_candidate(
            query_terms=query_terms,
            document_tokens=document_tokens,
            candidate=candidate,
            bm25_score=bm25_score,
            current_categories=current_categories,
        )
        if final_score is None:
            continue
        ranked_items.append({**candidate, "_score": final_score})

    ranked_items.sort(key=lambda item: (-float(item["_score"]), item["title"]))
    return [
        {
            "arxiv_id": item["arxiv_id"],
            "title": item["title"],
            "abstract": item["abstract"],
            "arxiv_url": item["arxiv_url"],
            "community_paper_id": item["community_paper_id"],
            "link_type": item["link_type"],
        }
        for item in ranked_items[:limit]
    ]


async def _fetch_arxiv_metadata(arxiv_id: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_fetch_arxiv_metadata_sync, arxiv_id)
    except Exception as exc:
        logger.warning("Failed to fetch arXiv metadata for %s: %s", arxiv_id, exc)
        return {}


def _needs_arxiv_metadata_hydration(paper: Dict[str, Any]) -> bool:
    if paper.get("source") != "arxiv" or not paper.get("arxiv_id"):
        return False
    title = str(paper.get("title") or "").strip()
    return (
        not title
        or title.startswith("arXiv:")
        or not (paper.get("authors") or [])
        or not (paper.get("categories") or [])
        or not (paper.get("abstract_raw") or "").strip()
    )


def _best_available_metadata_payload(paper: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    title = _normalize_metadata_text(str(paper.get("title") or ""))
    metadata_title = _normalize_metadata_text(metadata.get("title"))
    if metadata_title and (not title or title.startswith("arXiv:")):
        payload["title"] = metadata_title
    if metadata.get("authors") and not (paper.get("authors") or []):
        payload["authors"] = metadata["authors"]
    if metadata.get("categories") and not (paper.get("categories") or []):
        payload["categories"] = metadata["categories"]
    if metadata.get("abstract_raw") and not _normalize_metadata_text(paper.get("abstract_raw")):
        payload["abstract_raw"] = metadata["abstract_raw"]
    return payload


def _extract_plaintext_abstract_from_directory(directory: Path) -> Optional[str]:
    if not directory.exists():
        return None

    main_tex = find_main_tex_file(directory)
    if main_tex and Path(main_tex).exists():
        try:
            latex = Path(main_tex).read_text(encoding="utf-8")
            abstract = extract_abstract(latex)
            if abstract not in {"No abstract", "No title", ""}:
                plain_text = _normalize_metadata_text(extract_text_from_tex(abstract))
                if plain_text:
                    return plain_text
        except Exception:
            pass

    envs_map_path = directory / "envs_map.json"
    if envs_map_path.exists():
        try:
            env_rows = json.loads(envs_map_path.read_text(encoding="utf-8"))
        except Exception:
            env_rows = []
        if isinstance(env_rows, list):
            for row in env_rows:
                if str(row.get("env_name") or "").strip() != "abstract":
                    continue
                content = row.get("trans_content") or row.get("content") or ""
                plain_text = _normalize_metadata_text(extract_text_from_tex(str(content)))
                if plain_text:
                    return plain_text

    return None


def _candidate_output_directories_for_task(task_id: str) -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()

    def _add_directory(path: Optional[Path]) -> None:
        if path is None:
            return
        try:
            normalized = str(path.resolve())
        except Exception:
            normalized = str(path)
        if normalized in seen:
            return
        seen.add(normalized)
        if path.exists() and path.is_dir():
            candidates.append(path)

    task = task_manager.get_task(task_id) if task_id else None
    if task:
        stored_output = _resolve_storage_path(task.get("output_path") or "")
        _add_directory(stored_output)

    task_root = Path(settings.outputs_dir) / task_id
    _add_directory(task_root)
    if task_root.exists() and task_root.is_dir():
        for child in sorted(task_root.iterdir()):
            if child.is_dir():
                _add_directory(child)

    return candidates


def _extract_translated_abstract_from_task(task_id: str) -> Optional[str]:
    for output_dir in _candidate_output_directories_for_task(task_id):
        abstract = _extract_plaintext_abstract_from_directory(output_dir)
        if abstract:
            return abstract
    return None


async def _hydrate_arxiv_metadata_if_needed(paper: Dict[str, Any]) -> Dict[str, Any]:
    if not _needs_arxiv_metadata_hydration(paper):
        return paper

    metadata = await _fetch_arxiv_metadata(str(paper.get("arxiv_id")))
    payload = _best_available_metadata_payload(paper, metadata)
    if not payload:
        return paper

    payload["updated_at"] = _utc_now_iso()
    return await _update_paper(str(paper["id"]), payload)


async def _hydrate_translated_abstract_if_needed(
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    current_abstract = _normalize_metadata_text(paper.get("abstract_translated"))
    if current_abstract and not _looks_untranslated_for_zh(current_abstract):
        return paper

    for task_id in _candidate_task_ids_for_asset_recovery(paper, asset_map):
        abstract_translated = _extract_translated_abstract_from_task(task_id)
        if _should_replace_translated_abstract(
            current_abstract,
            abstract_translated,
            paper.get("abstract_raw"),
        ):
            return await _update_paper(
                str(paper["id"]),
                {
                    "abstract_translated": abstract_translated,
                    "updated_at": _utc_now_iso(),
                },
            )

    return paper


async def _repair_public_detail_in_background(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> None:
    if paper_id in _detail_repair_inflight:
        return

    _detail_repair_inflight.add(paper_id)
    try:
        repaired = await _hydrate_arxiv_metadata_if_needed(paper)
        await _hydrate_translated_abstract_if_needed(repaired, asset_map=asset_map)
    except Exception as exc:
        logger.warning("Failed to repair public detail for paper %s: %s", paper_id, exc)
    finally:
        _detail_repair_inflight.discard(paper_id)


def _schedule_public_detail_repair(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> bool:
    needs_metadata = _needs_arxiv_metadata_hydration(paper)
    current_abstract = _normalize_metadata_text(paper.get("abstract_translated"))
    needs_translated_abstract = not current_abstract or _looks_untranslated_for_zh(current_abstract)

    if paper_id in _detail_repair_inflight:
        return False

    if not needs_metadata and not needs_translated_abstract:
        return False

    asyncio.create_task(
        _repair_public_detail_in_background(
            paper_id=paper_id,
            paper=paper,
            asset_map=asset_map,
        )
    )
    return True


def _resolve_storage_path(stored_path: Optional[str]) -> Path:
    if not stored_path:
        return Path("")

    raw_path = str(stored_path).strip()
    if not raw_path:
        return Path("")

    candidate = Path(raw_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    normalized = raw_path
    if re.match(r"^[A-Za-z]:[\\/]", normalized):
        normalized = normalized[3:]
    normalized = normalized.replace("\\", "/")
    path_parts = [part for part in normalized.split("/") if part]
    lowered_parts = [part.lower() for part in path_parts]

    if "backend" in lowered_parts:
        backend_index = lowered_parts.index("backend")
        remapped = settings.base_dir.joinpath(*path_parts[backend_index + 1 :])
        if remapped.exists():
            return remapped

    if "data" in lowered_parts:
        data_index = lowered_parts.index("data")
        remapped = (settings.base_dir / "data").joinpath(*path_parts[data_index + 1 :])
        if remapped.exists():
            return remapped

    if "community_papers" in lowered_parts:
        papers_index = lowered_parts.index("community_papers")
        remapped = settings.community_papers_dir.joinpath(*path_parts[papers_index + 1 :])
        if remapped.exists():
            return remapped

    if candidate.is_absolute():
        return candidate
    return settings.base_dir / candidate


def _normalize_search_text(value: Optional[str]) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _matches_paper_query(paper: Dict[str, Any], query: Optional[str]) -> bool:
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        return True

    searchable_parts = [
        paper.get("title"),
        paper.get("arxiv_id"),
        paper.get("abstract_raw"),
        paper.get("abstract_translated"),
        " ".join(str(category) for category in (paper.get("categories") or [])),
        " ".join(
            str(author.get("name") if isinstance(author, dict) else author)
            for author in (paper.get("authors") or [])
        ),
    ]
    haystack = _normalize_search_text(" ".join(part for part in searchable_parts if part))
    return normalized_query in haystack


def _load_baseline_seed_rows() -> List[Dict[str, Any]]:
    baseline_path = getattr(settings, "community_baseline_seed_path", None)
    if not baseline_path:
        return []

    path = Path(baseline_path)
    if not path.exists():
        logger.warning("Community baseline seed file is configured but missing: %s", path)
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse community baseline seed file %s: %s", path, exc)
        return []

    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []

    normalized_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized = dict(row)
        normalized.setdefault("visibility", "public")
        normalized.setdefault("status", "published")
        normalized_rows.append(normalized)
    return normalized_rows


def _apply_runtime_paper_override(paper: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if paper is None:
        return None
    paper_id = str(paper.get("id") or "").strip()
    override = _RUNTIME_PAPER_OVERRIDES.get(paper_id)
    if not override:
        return paper
    merged = dict(paper)
    merged.update(override)
    return merged


def _preview_asset_needs_refresh(preview_path: Path) -> bool:
    if not preview_path.exists():
        return True

    try:
        html_content = preview_path.read_text(encoding="utf-8")
    except Exception:
        return True

    return _preview_html_needs_refresh(html_content)


def _preview_html_needs_refresh(html_content: str) -> bool:
    stale_markers = (
        'data-reader-version="reader-v1"',
        'data-reader-version="reader-v2"',
        'data-reader-version="reader-v3"',
        'data-reader-version="reader-v4"',
        'data-reader-version="reader-v5"',
        'data-reader-version="reader-v6"',
        'data-reader-version="reader-v7"',
        'data-reader-version="reader-v8"',
        'data-reader-version="day4"',
        "paper-preview__block--latex",
        "<pre class=\"paper-preview__latex\">",
        "\\begin{document}",
        "\\clearpage",
        "\\begin{figure",
        "\\begin{tabular",
        "\\includegraphics",
        "paper-preview__command-block\"><code>\\",
        "\\begin{algorithm",
        "\\begin{quote}",
        "\\end{quote}",
        "\\begin{snugshade",
        "\\end{snugshade",
        "\\paragraph{",
        "\\section*{",
        "\\subsection*{",
        "\\subsubsection*{",
        "\\PARR{",
        "\\renewcommand",
        "\\setcounter{",
        "\\defn{",
        "\\textup{",
        "\\cite[",
        "\\lettrine[",
        "\\flushright{",
        "\\KwData",
        "\\SetAlgoLined",
        "\\For{",
        "\\multirow{",
        "\\resizebox{",
        "\\hdashline",
        "\\textsubscript{",
        "[1.1pt]",
        "LNCE=",
        "<PLACEHOLDER_",
        "<PROTECTED_",
    )
    if any(marker in html_content for marker in stale_markers):
        return True

    current_marker = f'data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}"'
    if current_marker in html_content:
        return False

    version_match = re.search(r'data-reader-version="([^"]+)"', html_content)
    if version_match:
        return version_match.group(1) != paper_preview_service.PREVIEW_READER_VERSION

    return False


def _preview_payload_cache_key(
    preview_path: Path,
    preview_asset: Dict[str, Any],
) -> Optional[str]:
    if not preview_path.exists():
        return None

    try:
        stat_result = preview_path.stat()
    except OSError:
        return None

    resolved_path = preview_path.resolve() if hasattr(preview_path, "resolve") else preview_path
    st_mtime_ns = getattr(stat_result, "st_mtime_ns", None)
    if st_mtime_ns is None:
        st_mtime = getattr(stat_result, "st_mtime", None)
        st_mtime_ns = int(float(st_mtime) * 1_000_000_000) if st_mtime is not None else 0
    st_size = getattr(stat_result, "st_size", 0)

    return "|".join(
        [
            str(resolved_path),
            str(preview_asset.get("id") or ""),
            str(preview_asset.get("created_at") or ""),
            str(st_mtime_ns),
            str(st_size),
        ]
    )


def _load_preview_payload(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    preview_asset: Dict[str, Any],
    allow_untranslated_zh: bool = False,
    allow_stale_reader: bool = False,
) -> Optional[Dict[str, Any]]:
    preview_path = _resolve_storage_path(preview_asset.get("file_path") or "")
    if not preview_path.exists():
        return None

    cache_key = _preview_payload_cache_key(preview_path, preview_asset)
    if cache_key:
        cached_payload = _preview_payload_cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    try:
        html_content = preview_path.read_text(encoding="utf-8")
    except Exception:
        return None
    html_content = _normalize_legacy_preview_math_blocks(html_content)

    if not allow_stale_reader and _preview_html_needs_refresh(html_content):
        return None
    if not allow_untranslated_zh and _preview_html_looks_untranslated_for_zh(html_content):
        return None

    payload = {
        "paper_id": paper_id,
        "task_id": preview_asset.get("task_id") or paper.get("community_selected_task_id"),
        "asset": _serialize_public_asset(preview_asset),
        "html_content": html_content.replace("<script", "&lt;script"),
        "generated_at": _serialize_timestamp_value(preview_asset.get("created_at")),
    }
    if cache_key:
        _preview_payload_cache[cache_key] = payload
    return payload


def _build_preview_payload(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    preview_asset: Dict[str, Any],
    allow_untranslated_zh: bool = False,
    allow_stale_reader: bool = False,
) -> Optional[Dict[str, Any]]:
    return _load_preview_payload(
        paper_id=paper_id,
        paper=paper,
        preview_asset=preview_asset,
        allow_untranslated_zh=allow_untranslated_zh,
        allow_stale_reader=allow_stale_reader,
    )


async def _recover_preview_asset_in_background(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> None:
    if paper_id in _preview_recovery_inflight:
        return

    _preview_recovery_inflight.add(paper_id)
    try:
        current_asset_map = asset_map or {}
        for task_id in _candidate_task_ids_for_asset_recovery(paper, current_asset_map):
            preview_asset = await _resolve_preview_html_asset(
                paper=paper,
                paper_id=paper_id,
                task_id=task_id,
                asset_map=current_asset_map,
            )
            if preview_asset:
                return
    except Exception as exc:
        logger.warning("Failed to recover preview asset for paper %s: %s", paper_id, exc)
    finally:
        _preview_recovery_inflight.discard(paper_id)


def _schedule_preview_recovery(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> bool:
    if paper_id in _preview_recovery_inflight:
        return False

    if paper.get("trans_status") not in {"completed", "completed_with_warnings"}:
        return False

    if not _candidate_task_ids_for_asset_recovery(paper, asset_map):
        return False

    asyncio.create_task(
        _recover_preview_asset_in_background(
            paper_id=paper_id,
            paper=paper,
            asset_map=asset_map,
        )
    )
    return True


def _store_relative_path(path: Path | str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate).replace("\\", "/")

    try:
        relative = candidate.resolve().relative_to(settings.base_dir.resolve())
        return str(relative).replace("\\", "/")
    except Exception:
        return str(candidate).replace("\\", "/")


def _community_library_root(paper_id: str) -> Path:
    root = settings.community_papers_dir / paper_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _community_asset_destination(
    *,
    paper_id: str,
    task_id: Optional[str],
    asset_type: str,
    source_name: str,
) -> Path:
    paper_root = _community_library_root(paper_id)
    safe_name = Path(source_name or asset_type).name or asset_type
    if asset_type == "source_archive":
        return paper_root / "source" / safe_name
    if asset_type == "translated_pdf":
        filename = f"{task_id or 'latest'}-{safe_name}" if task_id else safe_name
        return paper_root / "translated" / filename
    if asset_type == "preview_html":
        filename = f"{task_id or 'latest'}-{safe_name}" if task_id else safe_name
        return paper_root / "preview" / filename
    return paper_root / asset_type / safe_name


def _copy_into_community_library(source_path: Path, destination_path: Path) -> Path:
    try:
        if source_path.resolve() == destination_path.resolve():
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            return destination_path
    except FileNotFoundError:
        pass

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        if destination_path.is_dir():
            shutil.rmtree(destination_path)
        else:
            destination_path.unlink()

    if source_path.is_dir():
        shutil.copytree(source_path, destination_path)
    else:
        shutil.copy2(source_path, destination_path)
    return destination_path


def _get_storage_backend() -> StorageBackend:
    return build_storage_backend(settings)


def _storage_uses_object_store(backend: StorageBackend) -> bool:
    return not isinstance(backend, LocalDiskStorageBackend)


def _storage_object_key_from_destination(destination_path: Path) -> str:
    relative_path = _store_relative_path(destination_path)
    if settings.storage_backend_mode.strip().lower() != "cos":
        return relative_path

    normalized_prefix = str(settings.cos_base_prefix or "").strip().strip("/")
    normalized_relative = relative_path.lstrip("/")
    if not normalized_prefix:
        return normalized_relative
    return f"{normalized_prefix}/{normalized_relative}"


def _archive_directory_for_storage(
    *,
    source_path: Path,
    task_id: Optional[str],
) -> Path:
    archive_root = settings.storage_temp_dir / "staged_archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    archive_base = archive_root / f"{task_id or 'shared'}-{uuid4().hex[:8]}"
    archive_path = Path(
        shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=source_path.parent,
            base_dir=source_path.name,
        )
    )
    return archive_path


def _persist_retained_artifact(
    *,
    local_path: Path,
    paper_id: str,
    task_id: Optional[str],
    asset_type: str,
    source_name: str,
    content_type: Optional[str],
) -> tuple[StoredObjectRef, str]:
    backend = _get_storage_backend()
    destination = _community_asset_destination(
        paper_id=paper_id,
        task_id=task_id,
        asset_type=asset_type,
        source_name=source_name,
    )

    if isinstance(backend, LocalDiskStorageBackend):
        staged_path = local_path
        staged_cleanup: Optional[Path] = None
        resolved_name = Path(source_name or local_path.name).name or asset_type
        resolved_type = content_type
        if local_path.is_dir():
            staged_path = _archive_directory_for_storage(
                source_path=local_path,
                task_id=task_id,
            )
            staged_cleanup = staged_path
            resolved_name = staged_path.name
            resolved_type = content_type or "application/zip"
            destination = _community_asset_destination(
                paper_id=paper_id,
                task_id=task_id,
                asset_type=asset_type,
                source_name=resolved_name,
            )
        stored = backend.put_file(
            local_path=staged_path,
            object_key=_store_relative_path(destination),
            content_type=resolved_type,
            delete_local=False,
        )
        if staged_cleanup and staged_cleanup.exists():
            staged_cleanup.unlink()
        return stored, resolved_name

    staged_path = local_path
    staged_cleanup: Optional[Path] = None
    resolved_name = Path(source_name or local_path.name).name or asset_type
    resolved_type = content_type
    if local_path.is_dir():
        staged_path = _archive_directory_for_storage(
            source_path=local_path,
            task_id=task_id,
        )
        staged_cleanup = staged_path
        resolved_name = staged_path.name
        resolved_type = content_type or "application/zip"

    stored = backend.put_file(
        local_path=staged_path,
        object_key=_storage_object_key_from_destination(destination),
        content_type=resolved_type,
        delete_local=False,
    )
    if staged_cleanup and staged_cleanup.exists():
        staged_cleanup.unlink()
    return stored, resolved_name


async def resolve_submitter_context(
    current_user: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(current_user, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await resolve_submitter_context_by_user_id(str(user_id))


async def resolve_submitter_context_by_user_id(user_id: str) -> Dict[str, Any]:
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _query_roles() -> List[str]:
        placeholder = "?" if get_database_dialect() == "sqlite" else "%s"
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"select role from user_roles where user_id = {placeholder} order by role asc",
                (normalized_user_id,),
            )
            rows = cursor.fetchall() or []
        roles: List[str] = []
        for row in rows:
            if isinstance(row, dict):
                role = row.get("role")
            else:
                try:
                    role = row["role"]
                except Exception:
                    role = None
            if role is not None:
                roles.append(str(role))
        return roles

    try:
        local_roles = await _run_local_repo(_query_roles)
    except DatabaseUnavailableError:
        local_roles = []
    except Exception as exc:
        logger.warning("Failed to resolve submitter roles for %s from local auth: %s", normalized_user_id, exc)
        local_roles = []

    roles = sorted(
        {
            str(role).strip()
            for role in local_roles
            if str(role).strip() in {"admin", "moderator"}
        }
    )
    return {
        "user_id": normalized_user_id,
        "roles": roles,
        "is_admin": any(role in {"admin", "moderator"} for role in roles),
    }


def _paper_select_clause() -> str:
    return (
        "id, source, arxiv_id, title, authors, categories, abstract_raw, "
        "abstract_translated, visibility, status, trans_status, created_by, "
        "trans_latest_task_id, trans_latest_asset_pdf_id, like_count, favorite_count, "
        "comment_count, view_count, download_count, created_at, updated_at, "
        "community_status, community_selected_task_id, community_selected_asset_id, "
        "official_published_at"
    )


async def _fetch_paper_by_id(paper_id: str) -> Optional[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        local_row = await _run_local_repo(lambda: repository.get_paper_by_id(paper_id))
    except DatabaseUnavailableError:
        local_row = None
    except Exception as exc:
        logger.warning("Failed to fetch paper %s from local repository: %s", paper_id, exc)
        local_row = None
    if local_row is not None:
        return _apply_runtime_paper_override(local_row)
    return None


def _extract_plaintext_title_from_directory(directory: Path) -> Optional[str]:
    if not directory.exists():
        return None

    main_tex = find_main_tex_file(directory)
    if main_tex and Path(main_tex).exists():
        try:
            latex = Path(main_tex).read_text(encoding="utf-8")
            title = extract_title(latex)
            if title not in {"No title", "No abstract", ""}:
                plain_text = _normalize_metadata_text(extract_text_from_tex(title))
                if plain_text:
                    return plain_text
        except Exception:
            pass

    return None


def _is_public_community_paper(paper: Optional[Dict[str, Any]]) -> bool:
    if not paper:
        return False
    return (
        str(paper.get("visibility") or "").strip() == "public"
        and str(paper.get("status") or "").strip() == "published"
        and str(paper.get("community_status") or "").strip() == COMMUNITY_STATUS_OFFICIAL
        and str(paper.get("trans_status") or "").strip() == "completed"
    )


async def _fetch_structured_insight_sections(paper_id: str) -> List[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        return await _run_local_repo(lambda: repository.list_structured_insight_sections(paper_id))
    except DatabaseUnavailableError:
        return []
    except Exception as exc:
        logger.warning("Failed to fetch structured insight sections for paper %s: %s", paper_id, exc)
        return []


async def _fetch_persisted_similar_recommendations(paper_id: str) -> List[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        rows = await _run_local_repo(lambda: repository.list_similar_recommendations(paper_id))
    except DatabaseUnavailableError:
        return []
    except Exception as exc:
        logger.warning("Failed to fetch persisted similar recommendations for paper %s: %s", paper_id, exc)
        return []

    return [
        {
            "arxiv_id": str(row.get("arxiv_id") or ""),
            "title": str(row.get("title") or ""),
            "abstract": str(row.get("abstract") or ""),
            "arxiv_url": str(row.get("arxiv_url") or ""),
            "community_paper_id": row.get("community_paper_id"),
            "link_type": str(row.get("link_type") or "arxiv"),
        }
        for row in rows
        if str(row.get("title") or "").strip()
    ]


async def _replace_persisted_similar_recommendations(*, paper_id: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        rows = await _run_local_repo(lambda: repository.replace_similar_recommendations(paper_id=paper_id, items=items))
    except DatabaseUnavailableError:
        logger.warning("Persisted similar recommendations require database availability for paper %s", paper_id)
        raise
    except Exception as exc:
        logger.warning("Failed to persist similar recommendations for paper %s: %s", paper_id, exc)
        raise

    return [
        {
            "arxiv_id": str(row.get("arxiv_id") or ""),
            "title": str(row.get("title") or ""),
            "abstract": str(row.get("abstract") or ""),
            "arxiv_url": str(row.get("arxiv_url") or ""),
            "community_paper_id": row.get("community_paper_id"),
            "link_type": str(row.get("link_type") or "arxiv"),
        }
        for row in rows
        if str(row.get("title") or "").strip()
    ]


def _empty_structured_insight_section(section_key: str) -> Dict[str, Any]:
    return {
        "section_key": section_key,
        "content": None,
        "raw_content": None,
        "summary": None,
        "blocks": [],
        "status": STRUCTURED_INSIGHT_NOT_READY_STATUS,
        "updated_at": None,
    }


def _normalize_multiline_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    normalized = text.strip()
    return normalized or None


def _structured_insight_known_titles(section_key: str) -> List[str]:
    ordered_titles: List[str] = []
    for title in STRUCTURED_INSIGHT_SUGGESTED_SUBHEADINGS.get(section_key, []):
        normalized = _normalize_metadata_text(title)
        if normalized and normalized not in ordered_titles:
            ordered_titles.append(normalized)
    for titles in STRUCTURED_INSIGHT_SUGGESTED_SUBHEADINGS.values():
        for title in titles:
            normalized = _normalize_metadata_text(title)
            if normalized and normalized not in ordered_titles:
                ordered_titles.append(normalized)
    return ordered_titles


def _split_structured_insight_content(section_key: str, content: Optional[str]) -> Dict[str, Any]:
    raw_content = _normalize_multiline_text(content)
    if not raw_content:
        return {
            "raw_content": None,
            "summary": None,
            "blocks": [],
        }

    titles = _structured_insight_known_titles(section_key)
    if not titles:
        return {
            "raw_content": raw_content,
            "summary": None,
            "blocks": [
                {
                    "heading": STRUCTURED_INSIGHT_DEFAULT_BLOCK_HEADING,
                    "content": raw_content,
                }
            ],
        }

    title_pattern = "|".join(re.escape(title) for title in sorted(titles, key=len, reverse=True))
    matcher = re.compile(
        rf"(?:(?<=^)|(?<=\n)|(?<=\s))(?:\*\*|__)?(?P<title>{title_pattern})(?:\*\*|__)?(?:\s*[：:])?",
        flags=re.MULTILINE,
    )
    matches = list(matcher.finditer(raw_content))
    if not matches:
        return {
            "raw_content": raw_content,
            "summary": None,
            "blocks": [
                {
                    "heading": STRUCTURED_INSIGHT_DEFAULT_BLOCK_HEADING,
                    "content": raw_content,
                }
            ],
        }

    summary = raw_content[: matches[0].start()].strip() or None
    blocks: List[Dict[str, str]] = []
    for index, match in enumerate(matches):
        heading = _normalize_metadata_text(match.group("title"))
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_content)
        body = raw_content[match.end() : body_end].strip()
        if not heading or not body:
            continue
        blocks.append(
            {
                "heading": heading,
                "content": body,
            }
        )

    if not blocks:
        blocks = [
            {
                "heading": STRUCTURED_INSIGHT_DEFAULT_BLOCK_HEADING,
                "content": raw_content,
            }
        ]

    return {
        "raw_content": raw_content,
        "summary": summary,
        "blocks": blocks,
    }


def _build_structured_insight_response_section(section: Dict[str, Any]) -> Dict[str, Any]:
    normalized_section = _normalize_structured_insight_section(section)
    normalized_content = _split_structured_insight_content(
        normalized_section["section_key"],
        normalized_section.get("content"),
    )
    return {
        **normalized_section,
        **normalized_content,
    }


def _build_structured_insights_payload(
    sections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    section_map = {
        str(section.get("section_key") or "").strip(): _build_structured_insight_response_section(dict(section))
        for section in sections
        if str(section.get("section_key") or "").strip()
    }
    ordered_sections = [
        section_map.get(section_key, _empty_structured_insight_section(section_key))
        for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
    ]
    statuses = {str(section.get("status") or "").strip() for section in ordered_sections}
    all_ready = all(status == STRUCTURED_INSIGHT_READY_STATUS for status in statuses if status)
    all_readable = all(_is_structured_insight_content_readable(section.get("content")) for section in ordered_sections)
    if ordered_sections and all_ready and all_readable:
        state = STRUCTURED_INSIGHT_READY_STATUS
    elif STRUCTURED_INSIGHT_PROCESSING_STATUS in statuses or "queued" in statuses:
        state = STRUCTURED_INSIGHT_PROCESSING_STATUS
    else:
        state = STRUCTURED_INSIGHT_NOT_READY_STATUS
    return {
        "state": state,
        "sections": ordered_sections,
    }


async def _fetch_paper_by_arxiv_id(arxiv_id: str) -> Optional[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        local_row = await _run_local_repo(lambda: repository.get_paper_by_arxiv_id(arxiv_id))
    except DatabaseUnavailableError:
        local_row = None
    except Exception as exc:
        logger.warning("Failed to fetch arXiv paper %s from local repository: %s", arxiv_id, exc)
        local_row = None
    if local_row is not None:
        return _apply_runtime_paper_override(local_row)
    return None


async def _fetch_paper_by_title(*, title: str, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        local_row = await _run_local_repo(
            lambda: repository.get_paper_by_title(title=title, source=source)
        )
    except DatabaseUnavailableError:
        local_row = None
    except Exception as exc:
        logger.warning("Failed to fetch paper by title from local repository: %s", exc)
        local_row = None
    if local_row is not None:
        return local_row
    return None


async def _insert_paper(payload: Dict[str, Any]) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    normalized_payload = dict(payload)
    normalized_payload.setdefault("id", f"paper-{uuid4().hex}")
    normalized_payload.setdefault("created_at", _utc_now_iso())
    normalized_payload.setdefault("updated_at", normalized_payload["created_at"])
    try:
        return await _run_local_repo(lambda: repository.insert_paper(normalized_payload))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to insert paper into local repository: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create paper") from exc


async def _update_paper(paper_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        local_row = await _run_local_repo(lambda: repository.update_paper(paper_id, payload))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to update paper %s in local repository: %s", paper_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update paper") from exc
    if local_row is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _apply_runtime_paper_override(local_row)


async def _fetch_asset_rows_for_paper(paper_id: str) -> List[Dict[str, Any]]:
    repository = get_community_paper_repository()
    try:
        return await _run_local_repo(lambda: repository.list_latest_assets_for_paper(paper_id))
    except DatabaseUnavailableError:
        pass
    except Exception as exc:
        logger.warning("Failed to fetch asset rows for paper %s from local repository: %s", paper_id, exc)

    return []


async def _fetch_asset_map_for_paper(*, paper_id: str) -> Dict[str, Dict[str, Any]]:
    rows = await _fetch_asset_rows_for_paper(paper_id)
    asset_map: Dict[str, Dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: item.get("created_at") or "", reverse=True):
        asset_type = row.get("asset_type")
        if asset_type and asset_type not in asset_map:
            asset_map[str(asset_type)] = row
    return asset_map


async def _upsert_latest_asset(
    *,
    paper_id: str,
    task_id: Optional[str],
    asset_type: str,
    file_path: str,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    storage_backend: str = "local_disk",
) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    resolved_name = file_name or Path(file_path).name
    resolved_mime = mime_type or mimetypes.guess_type(resolved_name)[0] or "application/octet-stream"
    try:
        return await _run_local_repo(
            lambda: repository.upsert_latest_asset(
                paper_id=paper_id,
                task_id=task_id,
                asset_type=asset_type,
                file_path=file_path,
                file_name=resolved_name,
                mime_type=resolved_mime,
                storage_backend=storage_backend,
            )
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to upsert latest asset %s for paper %s locally: %s", asset_type, paper_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {asset_type}") from exc


async def _fetch_latest_assets(paper_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not paper_ids:
        return {}

    repository = get_community_paper_repository()
    try:
        rows = await _run_local_repo(lambda: repository.list_latest_assets_for_papers(paper_ids))
        latest_by_paper: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            latest_by_paper.setdefault(str(row["paper_id"]), row)
        return latest_by_paper
    except DatabaseUnavailableError:
        pass
    except Exception as exc:
        logger.warning("Failed to fetch latest assets from local repository: %s", exc)

    return {}


async def _fetch_asset_maps_for_papers(
    paper_ids: List[str],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    if not paper_ids:
        return {}

    repository = get_community_paper_repository()
    try:
        rows = await _run_local_repo(lambda: repository.list_latest_assets_for_papers(paper_ids))
        asset_maps: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for row in rows:
            paper_id = row.get("paper_id")
            asset_type = row.get("asset_type")
            if not paper_id or not asset_type:
                continue
            by_type = asset_maps.setdefault(str(paper_id), {})
            by_type.setdefault(str(asset_type), row)
        return asset_maps
    except DatabaseUnavailableError:
        pass
    except Exception as exc:
        logger.warning("Failed to fetch asset maps from local repository: %s", exc)

    return {}


async def _create_source_asset(
    *,
    paper_id: str,
    task_id: Optional[str],
    source_path: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not source_path:
        return None
    resolved_source = _resolve_storage_path(source_path)
    if not resolved_source.exists():
        return None
    stored_ref, stored_name = _persist_retained_artifact(
        local_path=resolved_source,
        paper_id=paper_id,
        task_id=task_id,
        asset_type="source_archive",
        source_name=resolved_source.name if resolved_source.is_file() else f"{resolved_source.name}.zip",
        content_type="application/zip" if resolved_source.is_file() else None,
    )
    return await _upsert_latest_asset(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="source_archive",
        file_path=stored_ref.object_key,
        file_name=stored_name,
        mime_type=stored_ref.content_type,
        storage_backend=stored_ref.storage_backend,
    )


def _serialize_latest_asset(asset: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not asset:
        return None
    return {
        "id": asset.get("id"),
        "task_id": asset.get("task_id"),
        "asset_type": asset.get("asset_type"),
        "file_name": asset.get("file_name"),
        "mime_type": asset.get("mime_type"),
        "created_at": _serialize_timestamp_value(asset.get("created_at")),
    }


def _serialize_public_asset(asset: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return _serialize_latest_asset(asset)


def _select_latest_asset_from_map(asset_map: Optional[Dict[str, Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    if not asset_map:
        return None
    for preferred_type in ("preview_html", "translated_pdf", "preview_pdf", "source_archive"):
        asset = asset_map.get(preferred_type)
        if asset:
            return asset
    return None


def _normalize_paper_state_from_assets(
    paper: Dict[str, Any],
    *,
    latest_asset: Optional[Dict[str, Any]] = None,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    normalized = dict(paper)
    selected_latest_asset = latest_asset or _select_latest_asset_from_map(asset_map)
    translated_asset: Optional[Dict[str, Any]] = None
    if asset_map:
        preview_asset = asset_map.get("preview_html")
        if _preview_asset_has_translated_content(preview_asset):
            translated_asset = preview_asset
        else:
            translated_asset = asset_map.get("translated_pdf")
    if (
        translated_asset is None
        and selected_latest_asset
        and selected_latest_asset.get("asset_type") in {"preview_html", "translated_pdf"}
        and (
            selected_latest_asset.get("asset_type") != "preview_html"
            or _preview_asset_has_translated_content(selected_latest_asset)
        )
    ):
        translated_asset = selected_latest_asset

    if translated_asset:
        normalized["trans_status"] = "completed"
        if translated_asset.get("task_id"):
            normalized["community_selected_task_id"] = translated_asset.get("task_id")
        if translated_asset.get("id"):
            normalized["community_selected_asset_id"] = translated_asset.get("id")
    elif str(normalized.get("trans_status") or "") in {"completed", "completed_with_warnings"}:
        normalized["trans_status"] = "failed"

    if _looks_untranslated_for_zh(normalized.get("abstract_translated")):
        normalized["abstract_translated"] = None

    return normalized


def _candidate_task_ids_for_asset_recovery(
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[str]:
    candidates: List[str] = []
    if asset_map:
        for asset_type in ("preview_html", "translated_pdf", "source_archive"):
            asset = asset_map.get(asset_type)
            task_id = asset.get("task_id") if asset else None
            if task_id and task_id not in candidates:
                candidates.append(str(task_id))
    for task_id in (paper.get("trans_latest_task_id"), paper.get("community_selected_task_id")):
        if task_id and task_id not in candidates:
            candidates.append(str(task_id))
    return candidates


def _candidate_source_directories_for_preview(
    *,
    paper_id: str,
    task_id: str,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()

    def _add(path: Optional[Path]) -> None:
        if path is None:
            return
        try:
            normalized = str(path.resolve())
        except Exception:
            normalized = str(path)
        if normalized in seen:
            return
        seen.add(normalized)
        if path.exists() and path.is_dir():
            candidates.append(path)

    if asset_map:
        source_asset = asset_map.get("source_archive")
        if source_asset and source_asset.get("file_path"):
            _add(_resolve_storage_path(source_asset.get("file_path")))

    task = task_manager.get_task(task_id) if task_id else None
    if task:
        _add(_resolve_storage_path(task.get("source_path") or ""))

    paper_source_root = _community_library_root(paper_id) / "source"
    _add(paper_source_root)
    if paper_source_root.exists():
        for child in sorted(paper_source_root.iterdir()):
            if child.is_dir():
                _add(child)

    for output_dir in _candidate_output_directories_for_task(task_id):
        _add(output_dir)
        _add(output_dir.parent)

    return candidates


def _public_asset_map(asset_map: Optional[Dict[str, Dict[str, Any]]]) -> Optional[Dict[str, Dict[str, Any]]]:
    if not asset_map:
        return None
    return {
        asset_type: serialized
        for asset_type, asset in asset_map.items()
        if (serialized := _serialize_public_asset(asset)) is not None
    }


async def _fetch_viewer_state(
    paper_ids: List[str],
    *,
    user_id: Optional[str],
) -> Dict[str, Dict[str, bool]]:
    default_state = {paper_id: {"liked": False, "favorited": False} for paper_id in paper_ids}
    if not user_id or not paper_ids:
        return default_state

    repository = get_community_paper_repository()
    try:
        return await _run_local_repo(lambda: repository.get_viewer_state(paper_ids, user_id=user_id))
    except DatabaseUnavailableError:
        pass
    except Exception as exc:
        logger.warning("Failed to fetch viewer paper state from local repository: %s", exc)

    return default_state


def _download_token_secret() -> str:
    return (
        settings.community_download_token_secret
        or settings.encryption_key
        or settings.llm_api_key
    )


def _sign_download_token(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_token = base64.urlsafe_b64encode(serialized).decode("utf-8").rstrip("=")
    signature = hmac.new(
        _download_token_secret().encode("utf-8"),
        serialized,
        hashlib.sha256,
    ).digest()
    signature_token = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_token}.{signature_token}"


def _decode_download_token(token: str) -> Dict[str, Any]:
    try:
        payload_token, signature_token = token.split(".", 1)
        payload_bytes = base64.urlsafe_b64decode(payload_token + "=" * (-len(payload_token) % 4))
        expected_signature = hmac.new(
            _download_token_secret().encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).digest()
        provided_signature = base64.urlsafe_b64decode(
            signature_token + "=" * (-len(signature_token) % 4)
        )
    except Exception as exc:
        raise HTTPException(status_code=403, detail=f"Invalid download token: {exc}") from exc

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(status_code=403, detail="Invalid download token signature")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=403, detail=f"Invalid download token payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=403, detail="Invalid download token payload")

    expires_at = int(payload.get("exp") or 0)
    if expires_at <= int(time.time()):
        raise HTTPException(status_code=410, detail="Download token expired")
    return payload


async def _increment_paper_download_count(paper_id: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        count = await _run_local_repo(lambda: repository.increment_download_count(paper_id))
    except DatabaseUnavailableError:
        count = None
    except Exception as exc:
        logger.warning("Failed to increment download count for paper %s locally: %s", paper_id, exc)
        count = None
    if count is not None:
        return {"paper_id": paper_id, "download_count": count}

    paper = await _fetch_paper_by_id(paper_id)
    if not _is_public_community_paper(paper):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"paper_id": paper_id, "download_count": int(paper.get("download_count") or 0)}


async def _resolve_translated_pdf_asset(
    *,
    paper_id: str,
    task_id: str,
) -> Optional[Dict[str, Any]]:
    for output_dir in _candidate_output_directories_for_task(task_id):
        pdf_path = download_route._find_translated_pdf(output_dir)
        if not pdf_path or not pdf_path.exists():
            continue
        stored_ref, stored_name = _persist_retained_artifact(
            local_path=pdf_path,
            paper_id=paper_id,
            task_id=task_id,
            asset_type="translated_pdf",
            source_name=pdf_path.name,
            content_type="application/pdf",
        )

        asset = await _upsert_latest_asset(
            paper_id=paper_id,
            task_id=task_id,
            asset_type="translated_pdf",
            file_path=stored_ref.object_key,
            file_name=stored_name,
            mime_type=stored_ref.content_type or "application/pdf",
            storage_backend=stored_ref.storage_backend,
        )
        if stored_ref.storage_backend != "local_disk":
            clear_cached_runtime_artifacts(task_id, [pdf_path])
        await _update_paper(
            paper_id,
            {
                "trans_latest_asset_pdf_id": asset.get("id"),
                "updated_at": _utc_now_iso(),
            },
        )
        return asset

    return None


async def _ensure_translated_pdf_asset(
    *,
    paper: Dict[str, Any],
    asset_map: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    translated_asset = asset_map.get("translated_pdf")
    if translated_asset:
        return translated_asset

    for task_id in _candidate_task_ids_for_asset_recovery(paper, asset_map):
        translated_asset = await _resolve_translated_pdf_asset(
            paper_id=str(paper["id"]),
            task_id=task_id,
        )
        if translated_asset:
            asset_map["translated_pdf"] = translated_asset
            return translated_asset

    return None


async def _fetch_sanitized_arxiv_html(arxiv_id: str) -> Optional[str]:
    normalized = str(arxiv_id or "").strip()
    if not normalized:
        return None

    cached = _source_html_cache.get(normalized)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"https://arxiv.org/html/{normalized}",
                headers={"User-Agent": "LaTeXTrans-Community-Reader/1.0"},
            )
            response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "lxml")
    for selector in (
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        ".ltx_page_navbar",
        ".ltx_page_header",
        ".ltx_page_footer",
        ".ltx_role_toc",
        ".ltx_role_footnote",
        ".ltx_note_mark",
        ".ltx_dates",
        ".ltx_classification",
    ):
        for node in soup.select(selector):
            node.decompose()

    article = soup.select_one("article") or soup.select_one("main") or soup.body
    if article is None:
        return None

    for child in list(article.children):
        if isinstance(child, NavigableString):
            child.extract()
            continue
        if not isinstance(child, Tag):
            continue
        child_classes = set(child.get("class", []))
        starts_reading_content = (
            child.name in {"h1", "h2"}
            or child.name == "section"
            or "ltx_abstract" in child_classes
            or "ltx_authors" in child_classes
            or "ltx_title" in child_classes
            or any(cls.startswith("ltx_section") for cls in child_classes)
        )
        if starts_reading_content:
            break
        child.decompose()

    for text_node in list(article.find_all(string=lambda value: isinstance(value, str) and "\\WarningFilter" in value)):
        parent = text_node.parent
        if parent and parent is not article:
            parent.decompose()
        else:
            text_node.extract()

    article_classes = article.get("class", [])
    article["class"] = [*dict.fromkeys([*article_classes, "latextrans-source-article"])]
    article["data-reader-origin"] = "arxiv"

    base_html_url = f"https://arxiv.org/html/{normalized}/"
    for image in article.select("img[src]"):
        src = str(image.get("src") or "").strip()
        if src and not src.startswith(("#", "data:", "http://", "https://")):
            image["src"] = urljoin(base_html_url, src)

    for source in article.select("source[srcset]"):
        srcset = str(source.get("srcset") or "").strip()
        if srcset and not srcset.startswith(("#", "data:", "http://", "https://")):
            source["srcset"] = urljoin(base_html_url, srcset)

    for link in article.select("a[href]"):
        href = str(link.get("href") or "").strip()
        if href and not href.startswith(("#", "mailto:", "javascript:", "http://", "https://")):
            link["href"] = urljoin(base_html_url, href)

    html_content = str(article)
    _source_html_cache[normalized] = html_content
    return html_content


def _source_reader_resource(
    *,
    paper: Dict[str, Any],
    source_html_content: Optional[str] = None,
    source_anchors: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    arxiv_id = str(paper.get("arxiv_id") or "").strip()
    if arxiv_id:
        if source_html_content:
            return {
                "kind": "source_html",
                "html_content": source_html_content,
                "url": f"https://arxiv.org/html/{arxiv_id}",
                "anchors": list(source_anchors or []),
            }
        return {
            "kind": "source_pdf",
            "html_content": None,
            "url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            "anchors": list(source_anchors or []),
        }
    return None


def _translated_pdf_reader_resource(*, paper_id: str, asset: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "kind": "translated_pdf",
        "html_content": None,
        "url": f"/api/papers/{paper_id}/translated-pdf",
        "asset_id": asset.get("id"),
    }


def _extract_reader_anchors_from_html(html_content: Optional[str]) -> List[Dict[str, Any]]:
    if not html_content:
        return []

    try:
        root = BeautifulSoup(html_content, "html.parser")
    except Exception:
        return []

    anchors: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def _register(anchor_id: Any, kind: str, label: Any = None) -> None:
        normalized_id = str(anchor_id or "").strip()
        if not normalized_id or normalized_id in seen:
            return
        seen.add(normalized_id)
        entry: Dict[str, Any] = {"anchor_id": normalized_id, "kind": kind}
        normalized_label = _normalize_metadata_text(label)
        if normalized_label:
            entry["label"] = normalized_label
        anchors.append(entry)

    for section in root.select("section[data-section-id]"):
        section_id = section.get("data-section-id")
        heading = section.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        _register(section_id, "section", heading.get_text(" ", strip=True) if heading else None)

    for block in root.select("[data-block-id]"):
        _register(block.get("data-block-id"), "block")

    for heading in root.select("section[id],h1[id],h2[id],h3[id],h4[id],h5[id],h6[id]"):
        _register(heading.get("id"), "section", heading.get_text(" ", strip=True))

    return anchors[:400]


def _build_reader_experience_payload(
    *,
    paper: Dict[str, Any],
    paper_id: str,
    preview_payload: Optional[Dict[str, Any]],
    translated_asset: Optional[Dict[str, Any]],
    source_html_content: Optional[str] = None,
) -> Dict[str, Any]:
    source_anchors = _extract_reader_anchors_from_html(source_html_content)
    translated_anchors = _extract_reader_anchors_from_html(
        str(preview_payload.get("html_content") or "") if preview_payload else None
    )
    source_resource = _source_reader_resource(
        paper=paper,
        source_html_content=source_html_content,
        source_anchors=source_anchors,
    )
    translated_resource: Optional[Dict[str, Any]] = None
    if preview_payload:
        translated_resource = {
            "kind": "preview_html",
            "html_content": preview_payload.get("html_content"),
            "url": None,
            "anchors": translated_anchors,
        }
    elif translated_asset:
        translated_resource = _translated_pdf_reader_resource(
            paper_id=paper_id,
            asset=translated_asset,
        )

    available_modes: List[str] = []
    if source_resource:
        available_modes.append("source")
    if translated_resource:
        available_modes.append("translated")
    if not available_modes:
        available_modes.append("source")

    trans_status = str(paper.get("trans_status") or "")
    if translated_resource:
        stage_label = "中文版已准备好"
        failure_type = None
        can_leave_hint = None
        preferred_mode = "translated"
        resolved_reader_state = "translated_ready"
    elif trans_status in {"queued", "processing"}:
        stage_label = "正在生成中文版本"
        failure_type = None
        can_leave_hint = "你可以先阅读，完成后会自动更新"
        preferred_mode = "source"
        resolved_reader_state = "warming" if source_resource else "unavailable"
    elif source_resource and trans_status in {"completed", "completed_with_warnings"}:
        stage_label = "Reader upgrade in progress"
        failure_type = None
        can_leave_hint = "Reader content is refreshing in the background."
        preferred_mode = "source"
        resolved_reader_state = "warming"
    elif source_resource and trans_status in {"failed", "failed_compilation", "structure_invalid"}:
        stage_label = "英文阅读仍可用"
        failure_type = "translation_failed"
        can_leave_hint = None
        preferred_mode = "source"
        resolved_reader_state = "source_ready"
    elif source_resource:
        stage_label = "已准备英文阅读"
        failure_type = None
        can_leave_hint = None
        preferred_mode = "source"
        resolved_reader_state = "source_ready"
    else:
        stage_label = "暂时无法完成中文生成"
        failure_type = "translation_failed" if trans_status in TERMINAL_TASK_STATUSES else None
        can_leave_hint = None
        preferred_mode = "source"
        resolved_reader_state = "unavailable"

    return {
        "reader_state": "ready" if resolved_reader_state in {"source_ready", "translated_ready"} else resolved_reader_state,
        "reader": {
            "preferred_mode": preferred_mode,
            "available_modes": available_modes,
            "source": source_resource,
            "translated": translated_resource,
            "active_anchor_id": (
                (translated_anchors[0].get("anchor_id") if translated_anchors else None)
                or (source_anchors[0].get("anchor_id") if source_anchors else None)
            ),
            "state": resolved_reader_state,
        },
        "experience": {
            "stage_label": stage_label,
            "can_leave_hint": can_leave_hint,
            "failure_type": failure_type,
        },
    }


async def _resolve_preview_html_asset(
    *,
    paper: Dict[str, Any],
    paper_id: str,
    task_id: str,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    preview_asset: Optional[Dict[str, str]] = None
    backend = _get_storage_backend()
    target_dir = (
        settings.storage_temp_dir / "preview_generation" / paper_id
        if _storage_uses_object_store(backend)
        else _community_library_root(paper_id) / "preview"
    )
    source_dirs = _candidate_source_directories_for_preview(
        paper_id=paper_id,
        task_id=task_id,
        asset_map=asset_map,
    )
    for output_dir in _candidate_output_directories_for_task(task_id):
        try:
            preview_asset = paper_preview_service.generate_preview_html(
                output_dir,
                target_dir=target_dir,
                source_dirs=source_dirs,
                paper_metadata={
                    "title": paper.get("title"),
                    "authors": paper.get("authors") or [],
                },
            )
            break
        except FileNotFoundError:
            continue

    if not preview_asset:
        return None

    preview_path = Path(preview_asset["file_path"])
    stored_ref, stored_name = _persist_retained_artifact(
        local_path=preview_path,
        paper_id=paper_id,
        task_id=task_id,
        asset_type="preview_html",
        source_name=preview_asset["file_name"],
        content_type=preview_asset["mime_type"],
    )
    if stored_ref.storage_backend != "local_disk":
        clear_cached_runtime_artifacts(task_id, [preview_path])

    return await _upsert_latest_asset(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="preview_html",
        file_path=stored_ref.object_key,
        file_name=stored_name,
        mime_type=stored_ref.content_type,
        storage_backend=stored_ref.storage_backend,
    )


async def _enqueue_existing_task_translation(
    *,
    task_id: str,
    request: translate_route.TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials],
    current_user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = await translate_route.start_translation(
        task_id=task_id,
        request=request,
        credentials=credentials,
        current_user=current_user,
    )
    return {"task_id": response.task_id, "status": response.status}


async def _start_arxiv_paper_translation(
    *,
    paper: Dict[str, Any],
    request: translate_route.TranslateRequest,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    arxiv_id = paper.get("arxiv_id")
    if not arxiv_id:
        raise HTTPException(status_code=422, detail="Paper source is unavailable for translation")

    task_id = task_manager.create_task(
        source_type="arxiv",
        arxiv_id=arxiv_id,
        user_id=context["user_id"],
        source_language=request.source_language,
        target_language=request.target_language,
        persist_to_db=False,
    )
    config_hash = translate_route.compute_config_hash(
        arxiv_id=arxiv_id,
        source_language=request.source_language,
        target_language=request.target_language,
        translation_mode=request.advanced_config.translation_mode,
        compile_strategy=request.advanced_config.compile_strategy,
        formatting=request.advanced_config.formatting,
    )
    task_manager.update_task(
        task_id=task_id,
        source_language=request.source_language,
        target_language=request.target_language,
        advanced_config=request.advanced_config.model_dump(),
        config_hash=config_hash,
        user_id=context["user_id"],
    )
    task_manager.persist_task_if_needed(task_id)

    llm_config = await translate_route.build_llm_config_async(request.advanced_config, context["user_id"])
    token_hash = hashlib.md5((llm_config.get("api_key") or "").encode()).hexdigest()
    asyncio.create_task(
        translate_route._download_and_enqueue(
            task_id=task_id,
            arxiv_id=arxiv_id,
            user_id=context["user_id"],
            source_language=request.source_language,
            target_language=request.target_language,
            advanced_config=request.advanced_config,
            tq=get_task_queue(),
            token_hash=token_hash,
        )
    )
    return {"task_id": task_id, "status": "queued"}


def _community_rank(paper: Dict[str, Any]) -> int:
    return 0 if paper.get("community_status") == COMMUNITY_STATUS_OFFICIAL else 1


def _translated_rank(paper: Dict[str, Any]) -> int:
    return 0 if paper.get("trans_status") == "completed" else 1


def _serialize_timestamp_value(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def _timestamp_key(value: Any) -> float:
    if not value:
        return 0.0
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _hot_tuple(paper: Dict[str, Any]) -> Any:
    return (
        _community_rank(paper),
        -(paper.get("view_count") or 0),
        -(paper.get("like_count") or 0),
        -_timestamp_key(paper.get("created_at")),
    )


def _latest_tuple(paper: Dict[str, Any]) -> Any:
    return (
        _community_rank(paper),
        -_timestamp_key(paper.get("official_published_at")),
        -_timestamp_key(paper.get("created_at")),
    )


def _translated_tuple(paper: Dict[str, Any]) -> Any:
    return (
        _community_rank(paper),
        _translated_rank(paper),
        -_timestamp_key(paper.get("official_published_at")),
        -_timestamp_key(paper.get("created_at")),
    )


def _sort_papers(papers: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
    key_map = {
        "latest": _latest_tuple,
        "translated": _translated_tuple,
        "hot": _hot_tuple,
    }
    key = key_map.get(sort, _latest_tuple)
    return sorted(papers, key=key)


def _paper_payload(
    *,
    source: str,
    title: str,
    created_by: Optional[str],
    community_status: str,
    authors: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    abstract_raw: Optional[str] = None,
    abstract_translated: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    task_id: Optional[str] = None,
    selected_asset_id: Optional[str] = None,
    official_published_at: Optional[str] = None,
    trans_status: str = "queued",
) -> Dict[str, Any]:
    return {
        "source": source,
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors or [],
        "categories": categories or [],
        "abstract_raw": abstract_raw,
        "abstract_translated": abstract_translated,
        "visibility": "public",
        "status": "published",
        "trans_status": trans_status,
        "created_by": created_by,
        "trans_latest_task_id": task_id,
        "community_status": community_status,
        "community_selected_task_id": task_id,
        "community_selected_asset_id": selected_asset_id,
        "official_published_at": official_published_at,
    }


async def resolve_community_admission(
    *,
    submitter_context: Dict[str, Any],
    source_type: str,
    arxiv_id: Optional[str],
) -> Dict[str, Any]:
    is_admin = submitter_context["is_admin"]
    if source_type == "upload" or not arxiv_id:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL if is_admin else COMMUNITY_STATUS_USER_FALLBACK,
            "admission_result": "created",
            "existing_paper": None,
            "should_create": True,
        }

    existing = await _fetch_paper_by_arxiv_id(arxiv_id)
    if not existing:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL if is_admin else COMMUNITY_STATUS_USER_FALLBACK,
            "admission_result": "created",
            "existing_paper": None,
            "should_create": True,
        }

    if is_admin:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "admission_result": "created",
            "existing_paper": existing,
            "should_create": False,
        }

    if existing.get("community_status") == COMMUNITY_STATUS_OFFICIAL:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "admission_result": "reused_existing_official",
            "existing_paper": existing,
            "should_create": False,
        }

    return {
        "community_status": COMMUNITY_STATUS_USER_FALLBACK,
        "admission_result": "reused_existing_fallback",
        "existing_paper": existing,
        "should_create": False,
    }


def _task_source_for_community(task: Dict[str, Any]) -> str:
    return "arxiv" if task.get("arxiv_id") or task.get("source_type") == "arxiv" else "upload"


def _derive_task_title(task: Dict[str, Any]) -> str:
    arxiv_id = task.get("arxiv_id")
    if arxiv_id:
        return f"arXiv:{arxiv_id}"

    output_dir = _resolve_storage_path(task.get("output_path"))
    if output_dir.exists():
        pdf_path = download_route._find_translated_pdf(output_dir)
        if pdf_path and pdf_path.exists():
            return pdf_path.stem

    source_path = _resolve_storage_path(task.get("source_path"))
    if source_path.name:
        return source_path.stem if source_path.is_file() else source_path.name
    return "Uploaded paper"


async def _find_publish_target_for_task(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    arxiv_id = task.get("arxiv_id")
    if arxiv_id:
        return await _fetch_paper_by_arxiv_id(str(arxiv_id))
    return await _fetch_paper_by_title(
        title=_derive_task_title(task),
        source=_task_source_for_community(task),
    )


async def _sync_task_assets_for_paper(
    *,
    paper_id: str,
    task_id: str,
    promote_to_official: bool,
    paper: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    task = task_manager.get_task(task_id)
    if not task:
        return {"done": False, "status": None}

    source_asset_id: Optional[str] = None
    if task.get("source_available") and task.get("source_path"):
        asset = await _create_source_asset(
            paper_id=paper_id,
            task_id=task_id,
            source_path=task.get("source_path"),
        )
        task_status = task.get("status")
        update_payload: Dict[str, Any] = {"updated_at": _utc_now_iso()}
        if task_status == "pending":
            update_payload["trans_status"] = "not_started"
        else:
            update_payload["trans_status"] = "processing" if task_status == "processing" else "queued"
            update_payload["community_selected_task_id"] = task_id
        if asset:
            source_asset_id = asset.get("id")
            update_payload["community_selected_asset_id"] = source_asset_id
        if promote_to_official:
            update_payload["community_status"] = COMMUNITY_STATUS_OFFICIAL
            update_payload["official_published_at"] = _utc_now_iso()
        paper = await _update_paper(paper_id, update_payload)
        if task_status == "pending":
            return {"done": True, "status": "pending", "paper": paper}

    if task.get("status") in {"completed", "completed_with_warnings"}:
        if not paper:
            paper = await _fetch_paper_by_id(paper_id)
        if not paper:
            return {"done": True, "status": "paper_missing"}
        translated_asset = await _resolve_translated_pdf_asset(
            paper_id=paper_id,
            task_id=task_id,
        )
        preview_asset = await _resolve_preview_html_asset(
            paper=paper,
            paper_id=paper_id,
            task_id=task_id,
        )
        selected_asset = preview_asset or translated_asset
        update_payload = {
            "trans_status": "completed",
            "community_selected_task_id": task_id,
            "community_selected_asset_id": (
                selected_asset.get("id") if selected_asset else source_asset_id
            ),
            "updated_at": _utc_now_iso(),
        }
        if promote_to_official:
            update_payload["community_status"] = COMMUNITY_STATUS_OFFICIAL
            update_payload["official_published_at"] = _utc_now_iso()
        paper = await _update_paper(paper_id, update_payload)
        return {"done": True, "status": "completed", "paper": paper}

    if task.get("status") in TERMINAL_TASK_STATUSES:
        if not paper:
            paper = await _fetch_paper_by_id(paper_id)
        if not paper:
            return {"done": True, "status": "paper_missing"}
        translated_asset = await _resolve_translated_pdf_asset(
            paper_id=paper_id,
            task_id=task_id,
        )
        preview_asset = await _resolve_preview_html_asset(
            paper=paper,
            paper_id=paper_id,
            task_id=task_id,
        )
        selected_asset = preview_asset or translated_asset
        paper = await _update_paper(
            paper_id,
            {
                "trans_status": "failed",
                "community_selected_task_id": task_id,
                **(
                    {"community_selected_asset_id": selected_asset.get("id")}
                    if selected_asset and selected_asset.get("id")
                    else {}
                ),
                "updated_at": _utc_now_iso(),
            },
        )
        return {"done": True, "status": "failed", "paper": paper}

    return {"done": False, "status": task.get("status")}


async def ensure_task_published_to_community_library(
    *,
    task_id: str,
    promote_to_official: bool = False,
) -> Optional[Dict[str, Any]]:
    task = task_manager.get_task(task_id)
    if not task or not task.get("user_id"):
        return None

    if task.get("status") not in {"completed", "completed_with_warnings"}:
        return None

    existing = await _find_publish_target_for_task(task)
    if (
        existing
        and existing.get("community_status") == COMMUNITY_STATUS_OFFICIAL
        and existing.get("trans_status") == "completed"
        and not promote_to_official
    ):
        return {"paper": existing, "published": False}

    if existing:
        paper = await _update_paper(
            existing["id"],
            {
                "trans_status": "processing",
                "trans_latest_task_id": task_id,
                "community_selected_task_id": task_id,
                "updated_at": _utc_now_iso(),
                **(
                    {
                        "community_status": COMMUNITY_STATUS_OFFICIAL,
                        "official_published_at": _utc_now_iso(),
                    }
                    if promote_to_official
                    else {}
                ),
            },
        )
    else:
        paper = await _insert_paper(
            _paper_payload(
                source=_task_source_for_community(task),
                arxiv_id=task.get("arxiv_id"),
                title=_derive_task_title(task),
                created_by=task["user_id"],
                community_status=(
                    COMMUNITY_STATUS_OFFICIAL if promote_to_official else COMMUNITY_STATUS_USER_FALLBACK
                ),
                task_id=task_id,
                official_published_at=_utc_now_iso() if promote_to_official else None,
            )
        )

    sync_result = await _sync_task_assets_for_paper(
        paper_id=paper["id"],
        task_id=task_id,
        promote_to_official=promote_to_official,
        paper=paper,
    )
    return {"paper": sync_result.get("paper") or paper, "published": True}


async def watch_task_and_publish_community_library(
    *,
    task_id: str,
    promote_to_official: bool = False,
) -> None:
    for _ in range(180):
        task = task_manager.get_task(task_id)
        if task:
            if task.get("status") in {"completed", "completed_with_warnings"}:
                await ensure_task_published_to_community_library(
                    task_id=task_id,
                    promote_to_official=promote_to_official,
                )
                return
            if task.get("status") in TERMINAL_TASK_STATUSES:
                return
        await asyncio.sleep(2)


async def _watch_task_and_sync_asset(
    *,
    paper_id: str,
    task_id: str,
    promote_to_official: bool,
) -> None:
    for _ in range(180):
        result = await _sync_task_assets_for_paper(
            paper_id=paper_id,
            task_id=task_id,
            promote_to_official=promote_to_official,
        )
        if result.get("done"):
            return
        await asyncio.sleep(2)


async def mark_paper_translation_failed_by_task(task_id: str) -> int:
    normalized_task_id = str(task_id or "").strip()
    if not normalized_task_id:
        return 0
    repository = get_community_paper_repository()
    try:
        return await _run_local_repo(lambda: repository.mark_translation_failed_by_task(normalized_task_id))
    except DatabaseUnavailableError:
        return 0
    except Exception as exc:
        logger.warning("Failed to mark paper translation failed for task %s locally: %s", normalized_task_id, exc)
        return 0


async def resume_inflight_paper_translation_watchers() -> Dict[str, Any]:
    """
    Recreate in-memory paper watchers for tasks still marked queued/processing.
    """
    repository = get_community_paper_repository()
    try:
        rows = await _run_local_repo(repository.list_inflight_translation_papers)
    except DatabaseUnavailableError:
        return {"resumed_watchers": 0}
    except Exception as exc:
        logger.warning("Failed to load inflight paper watchers from local repository: %s", exc)
        rows = []

    resumed_watchers = 0
    for row in rows:
        paper_id = str(row.get("id") or "").strip()
        task_id = str(row.get("community_selected_task_id") or "").strip()
        if not paper_id or not task_id:
            continue
        asyncio.create_task(
            _watch_task_and_sync_asset(
                paper_id=paper_id,
                task_id=task_id,
                promote_to_official=row.get("community_status") == COMMUNITY_STATUS_OFFICIAL,
            )
        )
        resumed_watchers += 1

    return {"resumed_watchers": resumed_watchers}


def _paper_summary(
    paper: Dict[str, Any],
    *,
    latest_asset: Optional[Dict[str, Any]] = None,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
    viewer_state: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    paper = _normalize_paper_state_from_assets(
        paper,
        latest_asset=latest_asset,
        asset_map=asset_map,
    )
    selected_latest_asset = latest_asset or _select_latest_asset_from_map(asset_map)
    return {
        "id": paper.get("id"),
        "source": paper.get("source"),
        "arxiv_id": paper.get("arxiv_id"),
        "title": paper.get("title"),
        "authors": paper.get("authors") or [],
        "categories": paper.get("categories") or [],
        "abstract_raw": paper.get("abstract_raw"),
        "abstract_translated": paper.get("abstract_translated"),
        "community_status": paper.get("community_status"),
        "trans_status": paper.get("trans_status"),
        "created_at": _serialize_timestamp_value(paper.get("created_at")),
        "official_published_at": _serialize_timestamp_value(paper.get("official_published_at")),
        "community_selected_task_id": paper.get("community_selected_task_id"),
        "community_selected_asset_id": paper.get("community_selected_asset_id"),
        "visibility": paper.get("visibility"),
        "status": paper.get("status"),
        "like_count": paper.get("like_count"),
        "favorite_count": paper.get("favorite_count"),
        "comment_count": paper.get("comment_count"),
        "view_count": paper.get("view_count"),
        "download_count": paper.get("download_count"),
        "latest_asset": _serialize_latest_asset(selected_latest_asset),
        "assets": _public_asset_map(asset_map),
        "viewer_state": viewer_state,
    }


async def submit_uploaded_paper(
    *,
    file: UploadFile,
    credentials: Optional[HTTPAuthorizationCredentials],
    current_user: Optional[Dict[str, Any]] = None,
    source_language: str = "en",
    target_language: str = "zh",
) -> Dict[str, Any]:
    context = await resolve_submitter_context(current_user)
    upload_response = await upload_route.upload_file(
        file=file,
        credentials=credentials,
        current_user=current_user,
    )

    community_status = (
        COMMUNITY_STATUS_OFFICIAL if context["is_admin"] else COMMUNITY_STATUS_USER_FALLBACK
    )
    official_published_at = _utc_now_iso() if context["is_admin"] else None

    paper = await _insert_paper(
        _paper_payload(
            source="upload",
            arxiv_id=None,
            title=Path(file.filename or "upload").stem or "Uploaded paper",
            created_by=context["user_id"],
            community_status=community_status,
            task_id=upload_response.task_id,
            official_published_at=official_published_at,
            trans_status="not_started",
        )
    )

    asset = await _create_source_asset(
        paper_id=paper["id"],
        task_id=upload_response.task_id,
        source_path=upload_response.source_path,
    )
    if asset:
        paper = await _update_paper(
            paper["id"],
            {
                "trans_status": "not_started",
                "community_selected_asset_id": asset["id"],
                "updated_at": _utc_now_iso(),
            },
        )

    return {
        "paper": _paper_summary(paper, latest_asset=asset),
        "task": {
            "task_id": upload_response.task_id,
            "status": upload_response.status,
        },
        "admission_result": "created",
    }


async def submit_arxiv_paper(
    *,
    arxiv_id: str,
    credentials: Optional[HTTPAuthorizationCredentials],
    current_user: Optional[Dict[str, Any]] = None,
    source_language: str = "en",
    target_language: str = "zh",
) -> Dict[str, Any]:
    del source_language, target_language

    if current_user is None:
        context = {"user_id": None, "roles": [], "is_admin": False}
    else:
        context = await resolve_submitter_context(current_user)
    admission = await resolve_community_admission(
        submitter_context=context,
        source_type="arxiv",
        arxiv_id=arxiv_id,
    )
    existing = admission["existing_paper"]

    if existing and not context["is_admin"]:
        latest_asset = (
            await _fetch_latest_assets([existing["id"]])
        ).get(existing["id"])
        return {
            "paper": _paper_summary(existing, latest_asset=latest_asset),
            "task": {"task_id": None, "status": None},
            "admission_result": admission["admission_result"],
        }

    arxiv_response = await arxiv_route.download_arxiv(
        request=arxiv_route.ArxivRequest(arxiv_id=arxiv_id),
        credentials=credentials,
        current_user=current_user,
    )
    metadata = await _fetch_arxiv_metadata(arxiv_id)

    if existing:
        update_payload: Dict[str, Any] = {
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "trans_status": "not_started",
            "trans_latest_task_id": None,
            "community_selected_task_id": None,
            "official_published_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        update_payload.update(_best_available_metadata_payload(existing, metadata))
        paper = await _update_paper(existing["id"], update_payload)
        admission_result = "created"
    else:
        paper = await _insert_paper(
            _paper_payload(
                source="arxiv",
                arxiv_id=arxiv_id,
                title=metadata.get("title") or f"arXiv:{arxiv_id}",
                created_by=context["user_id"],
                community_status=admission["community_status"],
                authors=metadata.get("authors"),
                categories=metadata.get("categories"),
                abstract_raw=metadata.get("abstract_raw"),
                task_id=None,
                official_published_at=_utc_now_iso() if context["is_admin"] else None,
                trans_status="not_started",
            )
        )
        admission_result = admission["admission_result"]

    asyncio.create_task(
        _watch_task_and_sync_asset(
            paper_id=paper["id"],
            task_id=arxiv_response.task_id,
            promote_to_official=context["is_admin"],
        )
    )

    return {
        "paper": _paper_summary(paper),
        "task": {
            "task_id": arxiv_response.task_id,
            "status": "processing",
        },
        "admission_result": admission_result,
    }


def _normalize_curation_arxiv_ids(arxiv_ids: List[str]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for raw_value in arxiv_ids:
        value = str(raw_value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _serialize_curation_batch_status(items: List[Dict[str, Any]]) -> str:
    statuses = {str(item.get("status") or "").strip() for item in items}
    if not items:
        return "queued"
    if statuses == {"completed"}:
        return "completed"
    if statuses.issubset({"failed", "retry"}):
        return "failed"
    if any(status in statuses for status in {"processing", "translating", "publishing"}):
        return "processing"
    if "failed" in statuses or "retry" in statuses:
        return "failed"
    return "queued"


def _curation_batch_payload(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    batch_id = str(items[0].get("batch_id") or "").strip() if items else ""
    return {
        "batch_id": batch_id,
        "status": _serialize_curation_batch_status(items),
        "items": [
            {
                "job_id": item.get("job_id"),
                "paper_id": item.get("paper_id"),
                "source_type": item.get("source_type"),
                "arxiv_id": item.get("arxiv_id"),
                "original_filename": item.get("original_filename"),
                "status": item.get("status"),
                "error": item.get("error"),
            }
            for item in items
        ],
    }


async def get_admin_curation_batch(*, batch_id: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        items = await _run_local_repo(lambda: repository.list_curation_jobs_for_batch(batch_id))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    if not items:
        raise HTTPException(status_code=404, detail="Curation batch not found")
    return _curation_batch_payload(items)


async def _upsert_structured_insight_sections(
    *,
    paper_id: str,
    sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    repository = get_community_paper_repository()
    stored: List[Dict[str, Any]] = []
    for section in sections:
        payload = dict(section)
        payload["paper_id"] = paper_id
        stored.append(await _run_local_repo(lambda payload=payload: repository.upsert_structured_insight_section(payload)))
    return stored


def _load_task_artifact_json(output_dir: Path, artifact_name: str) -> List[Dict[str, Any]]:
    artifact_path = output_dir / artifact_name
    if not artifact_path.exists():
        return []
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def _build_structured_insight_placeholder_map(output_dir: Path) -> Dict[str, str]:
    placeholder_map: Dict[str, str] = {}
    for artifact_name in ("envs_map.json", "captions_map.json"):
        for item in _load_task_artifact_json(output_dir, artifact_name):
            placeholder = str(item.get("placeholder") or "").strip()
            if not placeholder:
                continue
            translated = str(item.get("trans_content") or item.get("content") or "").strip()
            if translated:
                placeholder_map[placeholder] = translated
    return placeholder_map


def _expand_structured_insight_placeholders(text: str, placeholder_map: Dict[str, str]) -> str:
    expanded = str(text or "")
    for placeholder, replacement in placeholder_map.items():
        expanded = expanded.replace(placeholder, replacement)
    return expanded


def _normalize_structured_insight_text(text: str) -> Optional[str]:
    plain = _normalize_multiline_text(extract_text_from_tex(str(text or "")))
    if plain:
        return plain
    return _normalize_multiline_text(text)


def _load_structured_insight_translated_sections(task_id: str) -> List[Dict[str, Any]]:
    for output_dir in _candidate_output_directories_for_task(task_id):
        sections = _load_task_artifact_json(output_dir, "sections_map.json")
        if not sections:
            continue
        placeholder_map = _build_structured_insight_placeholder_map(output_dir)
        normalized_sections: List[Dict[str, Any]] = []
        for index, section in enumerate(sections):
            translated = str(section.get("trans_content") or section.get("content") or "").strip()
            if not translated:
                continue
            expanded = _expand_structured_insight_placeholders(translated, placeholder_map)
            normalized = _normalize_structured_insight_text(expanded)
            if not normalized:
                continue
            title = _normalize_metadata_text(section.get("title"))
            normalized_sections.append(
                {
                    "index": index,
                    "section": str(section.get("section") or "").strip() or str(index + 1),
                    "title": title,
                    "content": normalized,
                    "raw_content": expanded,
                }
            )
        if normalized_sections:
            return normalized_sections
    return []


def _structured_insight_section_buckets(title: Optional[str], content: Optional[str]) -> set[str]:
    normalized_title = str(title or "").strip().lower()
    normalized_content = str(content or "").strip().lower()
    if not normalized_title and not normalized_content:
        return set()

    bucket_keywords = {
        "abstract": ("abstract", "摘要"),
        "introduction": ("introduction", "intro", "background", "motivation", "prelim", "引言", "背景", "概述"),
        "contribution": ("contribution", "contributions", "novelty", "our approach", "贡献", "创新", "主要贡献"),
        "method": ("method", "approach", "framework", "model", "algorithm", "architecture", "design", "方法", "模型", "算法", "框架"),
        "experiment": ("experiment", "evaluation", "setup", "benchmark", "ablation", "实验", "评测", "设置"),
        "result": ("result", "results", "analysis", "finding", "findings", "outcome", "结果", "分析", "结论"),
        "conclusion": ("conclusion", "discussion", "limitation", "future", "结论", "讨论", "局限", "未来"),
    }

    matched = {
        bucket
        for bucket, keywords in bucket_keywords.items()
        if any(keyword in normalized_title for keyword in keywords)
    }
    raw_content = str(content or "")
    contribution_markers = (
        "本文贡献如下",
        "主要贡献如下",
        "我们的贡献如下",
        "our contributions are",
        "the main contributions are",
    )
    result_markers = (
        "提升",
        "优于",
        "领先",
        "improves by",
        "outperforms",
        "achieves better",
    )
    if any(marker in raw_content for marker in contribution_markers):
        matched.add("contribution")
    if "结果" in raw_content and any(marker in raw_content for marker in result_markers):
        matched.add("result")
    return matched


def _dedupe_structured_insight_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_indexes: set[int] = set()
    ordered: List[Dict[str, Any]] = []
    for section in sections:
        index = int(section.get("index") or 0)
        if index in seen_indexes:
            continue
        seen_indexes.add(index)
        ordered.append(section)
    return ordered


def _compose_structured_insight_excerpt(
    sections: List[Dict[str, Any]],
    *,
    max_chars: int,
) -> str:
    chunks: List[str] = []
    total = 0
    for section in _dedupe_structured_insight_sections(sections):
        title = _normalize_metadata_text(section.get("title"))
        content = _normalize_metadata_text(section.get("content"))
        if not content:
            continue
        chunk = f"【{title}】\n{content}" if title else content
        remaining = max_chars - total
        if remaining <= 0:
            break
        if len(chunk) > remaining:
            chunk = chunk[:remaining].rstrip()
        chunks.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return "\n\n".join(chunk for chunk in chunks if chunk).strip()


def _prepare_structured_insight_sources(task_id: str) -> Dict[str, str]:
    sections = _load_structured_insight_translated_sections(task_id)
    if not sections:
        return {section_key: "" for section_key in STRUCTURED_INSIGHT_SECTION_KEYS}

    classified = [
        {
            **section,
            "buckets": _structured_insight_section_buckets(section.get("title"), section.get("content")),
        }
        for section in sections
    ]

    def pick(*bucket_names: str) -> List[Dict[str, Any]]:
        selected = [
            section
            for section in classified
            if set(bucket_names) & set(section.get("buckets") or set())
        ]
        return _dedupe_structured_insight_sections(selected)

    def by_index(start: int, end: int) -> List[Dict[str, Any]]:
        return classified[max(0, start):max(0, min(len(classified), end))]

    abstract_sections = pick("abstract")
    introduction_sections = pick("introduction")
    contribution_sections = pick("contribution")
    method_sections = pick("method")
    experiment_sections = pick("experiment")
    result_sections = pick("result")
    conclusion_sections = pick("conclusion")

    total_sections = len(classified)
    middle_start = max((total_sections // 2) - 1, 0)
    abstract_anchor_sections = abstract_sections or by_index(0, min(1, total_sections))
    problem_sections = abstract_anchor_sections + introduction_sections
    solution_sections = abstract_anchor_sections + (method_sections or by_index(middle_start, min(middle_start + 2, total_sections)))
    innovation_sections = abstract_anchor_sections + (
        contribution_sections
        or method_sections[:1]
        or introduction_sections[:1]
        or by_index(0, min(3, total_sections))
    )
    prioritized_experiment_sections = _dedupe_structured_insight_sections(result_sections + experiment_sections)
    experiment_sections_with_anchor = abstract_anchor_sections + (
        prioritized_experiment_sections or by_index(max(total_sections - 3, 0), total_sections)
    )
    future_sections = abstract_anchor_sections + (
        conclusion_sections or by_index(max(total_sections - 2, 0), total_sections)
    )

    return {
        "problem": _compose_structured_insight_excerpt(
            problem_sections or by_index(0, min(2, total_sections)),
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "solution": _compose_structured_insight_excerpt(
            solution_sections,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "innovation": _compose_structured_insight_excerpt(
            innovation_sections,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "experiment": _compose_structured_insight_excerpt(
            experiment_sections_with_anchor,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "future": _compose_structured_insight_excerpt(
            future_sections,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
    }


def _normalize_structured_insight_section(section: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "section_key": str(section.get("section_key") or "").strip(),
        "content": _normalize_multiline_text(section.get("content")),
        "status": str(section.get("status") or STRUCTURED_INSIGHT_READY_STATUS).strip() or STRUCTURED_INSIGHT_READY_STATUS,
        "updated_at": section.get("updated_at") or _utc_now_iso(),
    }


def _truncate_debug_text(value: Any, limit: int = 500) -> str:
    text = _normalize_metadata_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _is_structured_insight_content_readable(content: Optional[str]) -> bool:
    normalized = _normalize_metadata_text(content)
    if not normalized or len(normalized) < STRUCTURED_INSIGHT_MIN_TEXT_LENGTH:
        return False
    lowered = normalized.lower()
    if any(placeholder in normalized or placeholder in lowered for placeholder in STRUCTURED_INSIGHT_FAILURE_PLACEHOLDERS):
        return False
    return _count_cjk_characters(normalized) >= 24


def _build_structured_insight_fallback_content(*, section_key: str, excerpt: str) -> str:
    label = STRUCTURED_INSIGHT_SECTION_FALLBACK_LABELS.get(section_key, "论文相关内容")
    normalized_excerpt = _normalize_metadata_text(excerpt) or ""
    snippet = normalized_excerpt[:220].rstrip("，。；;,. ")
    base_content: str
    if snippet:
        base_content = (
            f"根据论文的中文内容，关于{label}，可以先这样理解：{snippet}。"
            "这一段导读基于当前可用的翻译片段整理而成，重点是帮助读者快速抓住论文在这一模块里真正强调的信息，"
            "后续如果需要更细的论证细节，仍然可以回到对应章节继续核对。"
        )
    else:
        base_content = (
            f"根据论文的中文内容，关于{label}，当前仍然可以从已翻译正文中提炼出一条基础判断："
            "作者在这一部分提供了与论文主线直接相关的说明，只是现有摘录不足以支持更细的逐点展开。"
            "因此这里先给出可展示的导读文本，帮助读者建立整体理解，再结合原文段落补充具体细节。"
        )
    if len(base_content) < STRUCTURED_INSIGHT_MIN_TEXT_LENGTH:
        base_content = (
            f"{base_content} 这也意味着该模块已经具备最基本的可读性，可以作为发布时的兜底内容。"
        )
    return base_content


def _validate_structured_insight_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    section_map: Dict[str, Dict[str, Any]] = {}
    seen_contents: Dict[str, str] = {}
    for raw_section in sections:
        section = _normalize_structured_insight_section(raw_section)
        section_key = section["section_key"]
        if section_key not in STRUCTURED_INSIGHT_SECTION_KEYS:
            raise ValueError(f"Unsupported structured insight section: {section_key}")
        if not _is_structured_insight_content_readable(section.get("content")):
            raise ValueError(f"Structured insight section {section_key} is unreadable")
        normalized_content = _normalize_metadata_text(section.get("content")) or ""
        duplicate_key = seen_contents.get(normalized_content)
        if duplicate_key is not None:
            raise ValueError(
                f"Structured insight section {section_key} duplicates section {duplicate_key}"
            )
        seen_contents[normalized_content] = section_key
        section_map[section_key] = section

    missing = [section_key for section_key in STRUCTURED_INSIGHT_SECTION_KEYS if section_key not in section_map]
    if missing:
        raise ValueError(f"Missing structured insight sections: {', '.join(missing)}")

    return [section_map[section_key] for section_key in STRUCTURED_INSIGHT_SECTION_KEYS]


async def _build_structured_insight_llm_config(user_id: Optional[str]) -> Dict[str, Any]:
    default_request = translate_route.TranslateRequest(source_language="en", target_language="zh")
    return await translate_route.build_llm_config_async(default_request.advanced_config, user_id)


async def _call_structured_insight_llm(
    *,
    llm_config: Dict[str, Any],
    system_prompt: str,
    user_payload: Dict[str, Any],
    temperature: float = 0.1,
    max_tokens: int = 3000,
) -> str:
    provider_url = _resolve_chat_completions_url(
        str(llm_config.get("base_url") or settings.llm_base_url or "")
    )
    provider_key = str(llm_config.get("api_key") or settings.llm_api_key or "").strip()
    provider_model = str(llm_config.get("model") or settings.llm_model or "").strip()
    if not provider_url or not provider_key or not provider_model:
        raise RuntimeError("Structured insight LLM configuration is unavailable")

    async with httpx.AsyncClient(timeout=max(float(llm_config.get("timeout") or settings.llm_timeout), 10.0)) as client:
        response = await client.post(
            provider_url,
            json={
                "model": provider_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
            headers={
                "Authorization": f"Bearer {provider_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        payload = response.json()

    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Structured insight LLM response is missing choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Structured insight LLM response is empty")
    return content


async def _generate_structured_insight_sections_from_task(
    *,
    task_id: str,
    title: str,
    abstract_raw: Optional[str],
    created_by: Optional[str],
) -> List[Dict[str, Any]]:
    sources = _prepare_structured_insight_sources(task_id)
    llm_config = await _build_structured_insight_llm_config(created_by)
    generated_sections: List[Dict[str, Any]] = []
    prior_section_summaries: List[str] = []

    for section_key in STRUCTURED_INSIGHT_SECTION_KEYS:
        excerpt = _normalize_metadata_text(sources.get(section_key)) or ""
        content: Optional[str] = None
        last_error: Optional[Exception] = None
        boundaries = STRUCTURED_INSIGHT_SECTION_BOUNDARIES.get(section_key, {})

        if excerpt:
            for attempt in range(STRUCTURED_INSIGHT_MAX_REPAIR_ATTEMPTS + 1):
                try:
                    raw_content = await _call_structured_insight_llm(
                        llm_config=llm_config,
                        system_prompt=STRUCTURED_INSIGHT_FINAL_SYSTEM_PROMPT,
                        user_payload={
                            "title": _normalize_metadata_text(title),
                            "abstract_raw": _normalize_metadata_text(abstract_raw),
                            "section_key": section_key,
                            "question": STRUCTURED_INSIGHT_SECTION_QUESTIONS[section_key],
                            "must_cover": boundaries.get("must_cover"),
                            "avoid": boundaries.get("avoid"),
                            "section_focus": boundaries.get("section_focus"),
                            "grounding_requirements": STRUCTURED_INSIGHT_GROUNDING_REQUIREMENTS,
                            "style_requirements": STRUCTURED_INSIGHT_STYLE_REQUIREMENTS,
                            "density_requirements": STRUCTURED_INSIGHT_DENSITY_REQUIREMENTS.get(
                                section_key,
                                STRUCTURED_INSIGHT_DENSITY_REQUIREMENTS["default"],
                            ),
                            "structure_requirements": STRUCTURED_INSIGHT_STRUCTURE_REQUIREMENTS,
                            "suggested_subheadings": STRUCTURED_INSIGHT_SUGGESTED_SUBHEADINGS.get(section_key, []),
                            "anti_repetition_requirements": STRUCTURED_INSIGHT_ANTI_REPETITION_REQUIREMENTS,
                            "avoid_repeat_hint": "避免重复前面模块已经讲清的内容，重点回答当前问题。",
                            "previous_module_briefs": list(prior_section_summaries),
                            "source_excerpt_zh": excerpt,
                        },
                        temperature=0.1,
                        max_tokens=1200,
                    )
                    normalized_content = _normalize_metadata_text(raw_content)
                    if not _is_structured_insight_content_readable(normalized_content):
                        raise ValueError(f"Structured insight section {section_key} returned unreadable content")
                    content = normalized_content
                    break
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Structured insight generation failed for task %s section %s (attempt %s/%s): %s",
                        task_id,
                        section_key,
                        attempt + 1,
                        STRUCTURED_INSIGHT_MAX_REPAIR_ATTEMPTS + 1,
                        exc,
                    )

        if not content:
            content = _build_structured_insight_fallback_content(section_key=section_key, excerpt=excerpt)
            if last_error is not None:
                logger.warning(
                    "Using fallback structured insight content for task %s section %s after generation failure: %s",
                    task_id,
                    section_key,
                    last_error,
                )

        generated_sections.append(
            {
                "section_key": section_key,
                "content": content,
                "status": STRUCTURED_INSIGHT_READY_STATUS,
                "updated_at": _utc_now_iso(),
            }
        )
        normalized_content = _normalize_metadata_text(content) or ""
        if normalized_content:
            prior_section_summaries.append(f"{section_key}: {normalized_content[:120]}")

    return _validate_structured_insight_sections(generated_sections)


def _archive_metadata_from_source_path(source_path: Path, fallback_title: str) -> Dict[str, Any]:
    scan_root = source_path.parent if source_path.is_file() else source_path
    title = _extract_plaintext_title_from_directory(scan_root) or fallback_title
    abstract_raw = _extract_plaintext_abstract_from_directory(scan_root)
    inferred_arxiv = None
    task_match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", str(source_path))
    if task_match:
        inferred_arxiv = task_match.group(1)
    return {
        "title": title,
        "abstract_raw": abstract_raw,
        "arxiv_id": inferred_arxiv,
        "authors": [],
        "categories": [],
    }


async def _publish_admin_curation_job(
    *,
    job: Dict[str, Any],
    metadata: Dict[str, Any],
    translated_task_id: str,
) -> Dict[str, Any]:
    paper_id = str(job.get("paper_id") or "").strip()
    existing = await _fetch_paper_by_id(paper_id) if paper_id else None
    paper = existing
    resolved_arxiv_id = (
        _normalize_metadata_text(metadata.get("arxiv_id"))
        or _normalize_metadata_text(job.get("arxiv_id"))
        or _normalize_metadata_text((paper or {}).get("arxiv_id"))
    )
    if str(job.get("source_type") or "").strip() == "arxiv" and not resolved_arxiv_id:
        raise ValueError("Admin arXiv curation publish requires arxiv_id")
    if paper is None:
        payload = _paper_payload(
            source=str(job.get("source_type") or "upload"),
            arxiv_id=resolved_arxiv_id,
            title=metadata.get("title") or "Curated paper",
            created_by=str(job.get("created_by") or ""),
            community_status=COMMUNITY_STATUS_OFFICIAL,
            authors=metadata.get("authors"),
            categories=metadata.get("categories"),
            abstract_raw=metadata.get("abstract_raw"),
            abstract_translated=None,
            task_id=None,
            official_published_at=None,
            trans_status="processing",
        )
        payload["id"] = paper_id
        payload["visibility"] = "private"
        payload["status"] = "curating"
        paper = await _insert_paper(payload)

    sync_result = await _sync_task_assets_for_paper(
        paper_id=paper["id"],
        task_id=translated_task_id,
        promote_to_official=False,
        paper=paper,
    )
    paper = sync_result.get("paper") or paper
    abstract_translated = _extract_translated_abstract_from_task(translated_task_id) or paper.get("abstract_translated")
    structured_insight_sections = await _generate_structured_insight_sections_from_task(
        task_id=translated_task_id,
        title=str(metadata.get("title") or paper.get("title") or ""),
        abstract_raw=metadata.get("abstract_raw") or paper.get("abstract_raw"),
        created_by=str(job.get("created_by") or ""),
    )
    _validate_structured_insight_sections(structured_insight_sections)
    await _upsert_structured_insight_sections(
        paper_id=paper["id"],
        sections=structured_insight_sections,
    )
    similar_source_paper = {
        **paper,
        "arxiv_id": resolved_arxiv_id,
        "title": metadata.get("title") or paper.get("title"),
        "authors": metadata.get("authors") or paper.get("authors") or [],
        "categories": metadata.get("categories") or paper.get("categories") or [],
        "abstract_raw": metadata.get("abstract_raw") or paper.get("abstract_raw"),
        "abstract_translated": abstract_translated,
        "trans_status": "completed",
        "community_status": COMMUNITY_STATUS_OFFICIAL,
    }
    similar_recommendations = await _generate_similar_recommendations_for_paper(
        paper=similar_source_paper,
        limit=10,
    )
    await _replace_persisted_similar_recommendations(
        paper_id=paper["id"],
        items=similar_recommendations,
    )
    updated = await _update_paper(
        paper["id"],
        {
            "arxiv_id": resolved_arxiv_id,
            "title": metadata.get("title") or paper.get("title"),
            "authors": metadata.get("authors") or paper.get("authors") or [],
            "categories": metadata.get("categories") or paper.get("categories") or [],
            "abstract_raw": metadata.get("abstract_raw") or paper.get("abstract_raw"),
            "abstract_translated": abstract_translated,
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "trans_status": "completed",
            "trans_latest_task_id": translated_task_id,
            "community_selected_task_id": translated_task_id,
            "visibility": "public",
            "status": "published",
            "official_published_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        },
    )
    return updated


def _is_private_curating_placeholder_paper(paper: Optional[Dict[str, Any]]) -> bool:
    if not paper:
        return False
    return (
        str(paper.get("status") or "").strip() == "curating"
        and str(paper.get("visibility") or "").strip() == "private"
    )


def _is_task_scoped_upload_source(source_path: Path, task_ids: List[str]) -> bool:
    try:
        resolved_source = source_path.resolve()
        uploads_root = Path(settings.uploads_dir).resolve()
    except Exception:
        return False
    if resolved_source.parent != uploads_root:
        return False
    return resolved_source.name in {task_id for task_id in task_ids if task_id}


def _delete_local_artifact_path(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return str(path)


async def _cleanup_failed_admin_curation_artifacts(
    *,
    repository: Any,
    job: Dict[str, Any],
    translated_task_id: str = "",
    cancel_running_task: bool,
) -> Dict[str, Any]:
    ordered_candidates = [
        str(translated_task_id or "").strip(),
        str(job.get("task_id") or "").strip(),
    ]
    task_ids = [task_id for task_id in dict.fromkeys(ordered_candidates) if task_id]
    deleted_paths: List[str] = []
    errors: List[str] = []

    for task_id in task_ids:
        if cancel_running_task:
            try:
                task_manager.cancel_task(task_id)
            except Exception as exc:
                errors.append(f"Failed to cancel task {task_id}: {exc}")

        task_snapshot = task_manager.get_task(task_id) if hasattr(task_manager, "get_task") else None
        failed_output_path = str((task_snapshot or {}).get("failed_output_path") or "").strip()
        if failed_output_path:
            try:
                deleted = _delete_local_artifact_path(Path(failed_output_path))
                if deleted:
                    deleted_paths.append(deleted)
            except Exception as exc:
                errors.append(f"Failed to delete failed task output for {task_id}: {exc}")
        else:
            fallback_failed_path = Path(settings.failed_tasks_dir) / task_id
            try:
                deleted = _delete_local_artifact_path(fallback_failed_path)
                if deleted:
                    deleted_paths.append(deleted)
            except Exception as exc:
                errors.append(f"Failed to delete fallback failed task output for {task_id}: {exc}")

        try:
            cleanup_result = task_manager.delete_task_full(task_id)
        except Exception as exc:
            errors.append(f"Failed to delete task artifacts for {task_id}: {exc}")
        else:
            deleted_paths.extend(
                [str(path) for path in cleanup_result.get("deleted_dirs", []) if str(path or "").strip()]
            )
            errors.extend(
                [str(error) for error in cleanup_result.get("errors", []) if str(error or "").strip()]
            )

        try:
            await _run_local_repo(lambda task_id=task_id: repository.delete_translation_tasks([task_id]))
        except Exception as exc:
            errors.append(f"Failed to delete translation task row for {task_id}: {exc}")

    source_type = str(job.get("source_type") or "").strip()
    source_path_raw = str(job.get("source_path") or "").strip()
    if source_type == "upload" and source_path_raw:
        source_path = _resolve_storage_path(source_path_raw)
        if _is_task_scoped_upload_source(source_path, task_ids):
            try:
                deleted = _delete_local_artifact_path(source_path)
                if deleted:
                    deleted_paths.append(deleted)
            except Exception as exc:
                errors.append(f"Failed to delete upload source path {source_path}: {exc}")

    paper_id = str(job.get("paper_id") or "").strip()
    if paper_id:
        try:
            paper = await _fetch_paper_by_id(paper_id)
        except Exception as exc:
            paper = None
            errors.append(f"Failed to load paper {paper_id} for cleanup: {exc}")
        if _is_private_curating_placeholder_paper(paper):
            _RUNTIME_PAPER_OVERRIDES.pop(paper_id, None)
            for table_name in ADMIN_CURATION_CLEANUP_PAPER_TABLES:
                try:
                    await _run_local_repo(
                        lambda table_name=table_name, paper_id=paper_id: repository.delete_rows_for_papers(table_name, [paper_id])
                    )
                except Exception as exc:
                    errors.append(f"Failed to delete {table_name} rows for paper {paper_id}: {exc}")

    return {
        "deleted_paths": deleted_paths,
        "errors": errors,
    }


async def _mark_admin_curation_job_failed(
    *,
    repository: Any,
    job_id: str,
    job: Dict[str, Any],
    translated_task_id: str,
    failure_message: str,
    cancel_running_task: bool,
) -> None:
    cleanup_result = await _cleanup_failed_admin_curation_artifacts(
        repository=repository,
        job=job,
        translated_task_id=translated_task_id,
        cancel_running_task=cancel_running_task,
    )
    final_error = str(failure_message or "Curation translation failed")
    cleanup_errors = [str(error) for error in cleanup_result.get("errors", []) if str(error or "").strip()]
    if cleanup_errors:
        final_error = f"{final_error} | cleanup_warnings: {'; '.join(cleanup_errors)}"
    await _run_local_repo(
        lambda: repository.update_curation_job(
            job_id,
            {"status": "failed", "error": final_error, "updated_at": _utc_now_iso()},
        )
    )


async def _wait_for_task_terminal_state(task_id: str) -> Dict[str, Any]:
    for _ in range(ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS):
        task = task_manager.get_task(task_id)
        if task and task.get("status") in TERMINAL_TASK_STATUSES:
            return task
        await asyncio.sleep(1)
    raise TimeoutError(f"Timed out waiting for task {task_id}")


def _schedule_curation_job(job_id: str) -> None:
    if job_id in _curation_job_tasks and not _curation_job_tasks[job_id].done():
        return
    task = asyncio.create_task(_run_curation_job(job_id))
    _curation_job_tasks[job_id] = task


async def _run_curation_job(job_id: str) -> None:
    repository = get_community_paper_repository()
    async with _get_curation_semaphore():
        job: Dict[str, Any] = {}
        metadata: Dict[str, Any] = {}
        translated_task_id = ""
        try:
            job = await _run_local_repo(lambda: repository.get_curation_job(job_id))
            if not job:
                return
            await _run_local_repo(
                lambda: repository.update_curation_job(
                    job_id,
                    {"status": "processing", "error": None, "updated_at": _utc_now_iso()},
                )
            )
            context = await resolve_submitter_context_by_user_id(str(job.get("created_by") or ""))
            request = translate_route.TranslateRequest(
                source_language=str(job.get("source_language") or "en"),
                target_language=str(job.get("target_language") or "zh"),
            )
            translated_task_id = str(job.get("task_id") or "").strip()
            if str(job.get("source_type") or "") == "arxiv":
                metadata = await _fetch_arxiv_metadata(str(job.get("arxiv_id") or ""))
                if translated_task_id:
                    await _run_local_repo(
                        lambda: repository.update_curation_job(
                            job_id,
                            {
                                "task_id": translated_task_id,
                                "status": "publishing",
                                "error": None,
                                "updated_at": _utc_now_iso(),
                            },
                        )
                    )
                else:
                    await _run_local_repo(
                        lambda: repository.update_curation_job(
                            job_id,
                            {"status": "translating", "updated_at": _utc_now_iso()},
                        )
                    )
                    translation_result = await _start_arxiv_paper_translation(
                        paper={"source": "arxiv", "arxiv_id": job.get("arxiv_id")},
                        request=request,
                        context=context,
                    )
                    translated_task_id = translation_result["task_id"]
            else:
                source_path = _resolve_storage_path(str(job.get("source_path") or ""))
                metadata = _archive_metadata_from_source_path(
                    source_path,
                    fallback_title=str(job.get("original_filename") or "Uploaded paper"),
                )
                existing_task_id = str(job.get("task_id") or "").strip()
                if not existing_task_id:
                    raise RuntimeError("Missing source task for upload curation job")
                await _run_local_repo(
                    lambda: repository.update_curation_job(
                        job_id,
                        {"status": "translating", "updated_at": _utc_now_iso()},
                    )
                )
                translation_result = await _enqueue_existing_task_translation(
                    task_id=existing_task_id,
                    request=request,
                    credentials=None,
                    current_user={"id": context["user_id"]},
                )
                translated_task_id = translation_result["task_id"]

            await _run_local_repo(
                lambda: repository.update_curation_job(
                    job_id,
                    {"task_id": translated_task_id, "status": "publishing", "updated_at": _utc_now_iso()},
                )
            )
            task = await _wait_for_task_terminal_state(translated_task_id)
            if task.get("status") not in {"completed", "completed_with_warnings"}:
                await _mark_admin_curation_job_failed(
                    repository=repository,
                    job_id=job_id,
                    job=job,
                    translated_task_id=translated_task_id,
                    failure_message=str(task.get("error") or task.get("message") or "Curation translation failed"),
                    cancel_running_task=False,
                )
                return

            published = await _publish_admin_curation_job(
                job=job,
                metadata=metadata,
                translated_task_id=translated_task_id,
            )
            await _run_local_repo(
                lambda: repository.update_curation_job(
                    job_id,
                    {
                        "paper_id": published.get("id"),
                        "status": "completed",
                        "error": None,
                        "updated_at": _utc_now_iso(),
                    },
                )
            )
        except TimeoutError as exc:
            logger.warning("Admin curation job %s timed out while waiting for %s", job_id, translated_task_id)
            latest_task = task_manager.get_task(translated_task_id) if translated_task_id else None
            if latest_task and latest_task.get("status") in {"completed", "completed_with_warnings"}:
                published = await _publish_admin_curation_job(
                    job=job,
                    metadata=metadata,
                    translated_task_id=translated_task_id,
                )
                await _run_local_repo(
                    lambda: repository.update_curation_job(
                        job_id,
                        {
                            "paper_id": published.get("id"),
                            "status": "completed",
                            "error": None,
                            "updated_at": _utc_now_iso(),
                        },
                    )
                )
                return
            if latest_task and latest_task.get("status") in TERMINAL_TASK_STATUSES:
                await _mark_admin_curation_job_failed(
                    repository=repository,
                    job_id=job_id,
                    job=job,
                    translated_task_id=translated_task_id,
                    failure_message=str(
                        latest_task.get("error")
                        or latest_task.get("message")
                        or exc
                    ),
                    cancel_running_task=False,
                )
                return
            await _mark_admin_curation_job_failed(
                repository=repository,
                job_id=job_id,
                job=job,
                translated_task_id=translated_task_id,
                failure_message=str(exc),
                cancel_running_task=True,
            )
        except Exception as exc:
            logger.warning("Admin curation job %s failed: %s", job_id, exc, exc_info=True)
            try:
                await _mark_admin_curation_job_failed(
                    repository=repository,
                    job_id=job_id,
                    job=job,
                    translated_task_id=translated_task_id,
                    failure_message=str(exc),
                    cancel_running_task=bool(translated_task_id),
                )
            except Exception:
                logger.warning("Failed to persist curation job failure for %s", job_id, exc_info=True)


async def submit_admin_arxiv_curation_batch(
    *,
    arxiv_ids: List[str],
    current_user: Dict[str, Any],
    source_language: str = "en",
    target_language: str = "zh",
) -> Dict[str, Any]:
    normalized_ids = _normalize_curation_arxiv_ids(arxiv_ids)
    if not normalized_ids:
        raise HTTPException(status_code=400, detail="At least one arXiv ID is required")

    repository = get_community_paper_repository()
    batch_id = f"curation-batch-{uuid4().hex}"
    created_at = _utc_now_iso()
    items: List[Dict[str, Any]] = []
    for arxiv_id in normalized_ids:
        existing = await _fetch_paper_by_arxiv_id(arxiv_id)
        paper_id = str(existing.get("id") or uuid4().hex) if existing else uuid4().hex
        job_payload = {
            "job_id": f"curation-job-{uuid4().hex}",
            "batch_id": batch_id,
            "paper_id": paper_id,
            "source_type": "arxiv",
            "arxiv_id": arxiv_id,
            "original_filename": None,
            "source_path": None,
            "task_id": None,
            "source_language": source_language,
            "target_language": target_language,
            "status": "queued",
            "error": None,
            "created_by": str(current_user.get("id") or ""),
            "created_at": created_at,
            "updated_at": created_at,
        }
        stored = await _run_local_repo(lambda job_payload=job_payload: repository.insert_curation_job(job_payload))
        items.append(stored)
        _schedule_curation_job(str(stored.get("job_id") or ""))
    return _curation_batch_payload(items)


async def submit_admin_upload_curation_batch(
    *,
    files: List[UploadFile],
    current_user: Dict[str, Any],
    source_language: str = "en",
    target_language: str = "zh",
) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one archive is required")

    repository = get_community_paper_repository()
    batch_id = f"curation-batch-{uuid4().hex}"
    created_at = _utc_now_iso()
    items: List[Dict[str, Any]] = []
    for file in files:
        upload_response = await upload_route.upload_file(
            file=file,
            credentials=None,
            current_user=current_user,
        )
        source_path = _resolve_storage_path(upload_response.source_path)
        metadata = _archive_metadata_from_source_path(
            source_path,
            fallback_title=Path(file.filename or "upload").stem or "Uploaded paper",
        )
        existing = None
        if metadata.get("arxiv_id"):
            existing = await _fetch_paper_by_arxiv_id(str(metadata["arxiv_id"]))
        if existing is None and metadata.get("title"):
            existing = await _fetch_paper_by_title(
                title=str(metadata["title"]),
                source="upload",
            )
        paper_id = str(existing.get("id") or uuid4().hex) if existing else uuid4().hex
        job_payload = {
            "job_id": f"curation-job-{uuid4().hex}",
            "batch_id": batch_id,
            "paper_id": paper_id,
            "source_type": "upload",
            "arxiv_id": metadata.get("arxiv_id"),
            "original_filename": file.filename,
            "source_path": upload_response.source_path,
            "task_id": upload_response.task_id,
            "source_language": source_language,
            "target_language": target_language,
            "status": "queued",
            "error": None,
            "created_by": str(current_user.get("id") or ""),
            "created_at": created_at,
            "updated_at": created_at,
        }
        stored = await _run_local_repo(lambda job_payload=job_payload: repository.insert_curation_job(job_payload))
        items.append(stored)
        _schedule_curation_job(str(stored.get("job_id") or ""))
    return _curation_batch_payload(items)


def _delete_job_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": job.get("job_id"),
        "paper_id": job.get("paper_id"),
        "status": job.get("status"),
    }


def _schedule_delete_job(job_id: str) -> None:
    if job_id in _delete_job_tasks and not _delete_job_tasks[job_id].done():
        return
    task = asyncio.create_task(_run_delete_job(job_id))
    _delete_job_tasks[job_id] = task


async def _run_delete_job(job_id: str) -> None:
    repository = get_community_paper_repository()
    async with _get_delete_semaphore():
        try:
            job = await _run_local_repo(lambda: repository.get_delete_job(job_id))
            if not job:
                return
            attempt_count = int(job.get("attempt_count") or 0) + 1
            await _run_local_repo(
                lambda: repository.update_delete_job(
                    job_id,
                    {
                        "status": "running",
                        "attempt_count": attempt_count,
                        "last_error": None,
                        "updated_at": _utc_now_iso(),
                    },
                )
            )
            paper_id = str(job.get("paper_id") or "").strip()
            if not paper_id:
                raise RuntimeError("Delete job missing paper_id")

            community_dir = settings.community_papers_dir / paper_id
            if community_dir.exists():
                shutil.rmtree(community_dir, ignore_errors=False)

            asset_task_ids = await _run_local_repo(lambda: repository.list_asset_task_ids_for_papers([paper_id]))
            comment_ids = await _run_local_repo(lambda: repository.list_comment_ids_for_papers([paper_id]))
            report_ids = await _run_local_repo(
                lambda: repository.list_report_ids_for_targets(target_type="paper", target_ids=[paper_id])
            )
            if comment_ids:
                report_ids.extend(
                    await _run_local_repo(
                        lambda: repository.list_report_ids_for_targets(target_type="comment", target_ids=comment_ids)
                    )
                )
            report_ids = [report_id for report_id in report_ids if str(report_id or "").strip()]
            if report_ids:
                await _run_local_repo(
                    lambda: repository.delete_rows_by_ids("moderation_actions", id_column="report_id", row_ids=report_ids)
                )
                await _run_local_repo(
                    lambda: repository.delete_rows_by_ids("reports", id_column="id", row_ids=report_ids)
                )

            for table_name in [
                "comments",
                "paper_assets",
                "paper_likes",
                "paper_favorites",
                "community_structured_insights",
                "community_similar_recommendations",
            ]:
                await _run_local_repo(lambda table_name=table_name: repository.delete_rows_for_papers(table_name, [paper_id]))

            cleaned_task_ids = [str(task_id or "").strip() for task_id in asset_task_ids if str(task_id or "").strip()]
            for task_id in cleaned_task_ids:
                task_manager.delete_task_full(task_id)
            if cleaned_task_ids:
                await _run_local_repo(lambda: repository.delete_translation_tasks(cleaned_task_ids))

            await _run_local_repo(lambda: repository.delete_rows_for_papers("papers", [paper_id]))
            await _run_local_repo(
                lambda: repository.update_delete_job(
                    job_id,
                    {"status": "completed", "last_error": None, "updated_at": _utc_now_iso()},
                )
            )
        except Exception as exc:
            logger.warning("Community delete job %s failed: %s", job_id, exc, exc_info=True)
            try:
                await _run_local_repo(
                    lambda: repository.update_delete_job(
                        job_id,
                        {
                            "status": "retry",
                            "last_error": str(exc),
                            "updated_at": _utc_now_iso(),
                        },
                    )
                )
            except Exception:
                logger.warning("Failed to persist delete-job failure for %s", job_id, exc_info=True)


async def delete_community_paper_admin(
    *,
    paper_id: str,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    paper = await _fetch_paper_by_id(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    repository = get_community_paper_repository()
    existing_job = await _run_local_repo(lambda: repository.get_delete_job_by_paper_id(paper_id))
    if existing_job and str(existing_job.get("status") or "") in {"queued", "running", "retry"}:
        return _delete_job_payload(existing_job)

    await _update_paper(
        paper_id,
        {
            "visibility": "private",
            "status": "deleting",
            "updated_at": _utc_now_iso(),
        },
    )
    job_payload = {
        "job_id": f"delete-job-{uuid4().hex}",
        "paper_id": paper_id,
        "status": "queued",
        "attempt_count": 0,
        "last_error": None,
        "created_by": str(current_user.get("id") or ""),
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }
    stored = await _run_local_repo(lambda: repository.insert_delete_job(job_payload))
    _schedule_delete_job(str(stored.get("job_id") or ""))
    return _delete_job_payload(stored)


async def resume_pending_admin_curation_jobs() -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        jobs = await _run_local_repo(repository.list_pending_curation_jobs)
    except Exception as exc:
        logger.warning("Failed to load pending admin curation jobs: %s", exc)
        return {"resumed_curation_jobs": 0}
    for job in jobs:
        _schedule_curation_job(str(job.get("job_id") or ""))
    return {"resumed_curation_jobs": len(jobs)}


async def resume_pending_delete_jobs() -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        jobs = await _run_local_repo(repository.list_pending_delete_jobs)
    except Exception as exc:
        logger.warning("Failed to load pending delete jobs: %s", exc)
        return {"resumed_delete_jobs": 0}
    for job in jobs:
        _schedule_delete_job(str(job.get("job_id") or ""))
    return {"resumed_delete_jobs": len(jobs)}


async def _ensure_public_paper(paper_id: str) -> Dict[str, Any]:
    paper = await _fetch_paper_by_id(paper_id)
    if not _is_public_community_paper(paper):
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


async def start_paper_translation(
    *,
    paper_id: str,
    request: translate_route.TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials],
    submitter_user_id: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if submitter_user_id:
        context = await resolve_submitter_context_by_user_id(submitter_user_id)
    elif current_user is None:
        context = {"user_id": None, "roles": [], "is_admin": False}
    else:
        context = await resolve_submitter_context(current_user)
    paper = await _ensure_public_paper(paper_id)

    active_task_id = paper.get("community_selected_task_id")
    if active_task_id and paper.get("trans_status") in {"queued", "processing"}:
        return {
            "paper_id": paper_id,
            "task_id": active_task_id,
            "status": paper.get("trans_status"),
            "reused_existing_task": True,
            "processing_url": f"/processing?taskId={active_task_id}",
        }

    try:
        asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    except HTTPException as exc:
        if exc.status_code == 503 and exc.detail == "Local database unavailable":
            asset_map = {}
        else:
            raise
    source_asset = asset_map.get("source_archive")
    if source_asset and source_asset.get("file_path"):
        resolved_source_path = _resolve_storage_path(source_asset["file_path"])
        if resolved_source_path.exists():
            task_id = task_manager.create_task(
                source_type=paper.get("source") or "upload",
                arxiv_id=paper.get("arxiv_id"),
                user_id=context["user_id"],
                source_language=request.source_language,
                target_language=request.target_language,
                persist_to_db=False,
            )
            task_manager.update_task(
                task_id=task_id,
                source_path=str(resolved_source_path).replace("\\", "/"),
                source_available=True,
                arxiv_id=paper.get("arxiv_id"),
                source_language=request.source_language,
                target_language=request.target_language,
                advanced_config=request.advanced_config.model_dump(),
                user_id=context["user_id"],
            )
            task_manager.persist_task_if_needed(task_id)
            translation_result = await _enqueue_existing_task_translation(
                task_id=task_id,
                request=request,
                credentials=credentials,
            )
        elif paper.get("source") == "arxiv" and paper.get("arxiv_id"):
            translation_result = await _start_arxiv_paper_translation(
                paper=paper,
                request=request,
                context=context,
            )
            task_id = translation_result["task_id"]
        else:
            raise HTTPException(status_code=422, detail="Paper source is unavailable for translation")
    elif paper.get("source") == "arxiv" and paper.get("arxiv_id"):
        translation_result = await _start_arxiv_paper_translation(
            paper=paper,
            request=request,
            context=context,
        )
        task_id = translation_result["task_id"]
    else:
        raise HTTPException(status_code=422, detail="Paper source is unavailable for translation")

    await _update_paper(
        paper_id,
        {
            "trans_status": translation_result["status"],
            "trans_latest_task_id": translation_result["task_id"],
            "community_selected_task_id": translation_result["task_id"],
            "updated_at": _utc_now_iso(),
        },
    )
    asyncio.create_task(
        _watch_task_and_sync_asset(
            paper_id=paper_id,
            task_id=translation_result["task_id"],
            promote_to_official=context["is_admin"],
        )
    )
    return {
        "paper_id": paper_id,
        "task_id": translation_result["task_id"],
        "status": translation_result["status"],
        "reused_existing_task": False,
        "processing_url": f"/processing?taskId={translation_result['task_id']}",
    }


async def get_paper_preview(*, paper_id: str) -> Dict[str, Any]:
    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    preview_asset = asset_map.get("preview_html")
    original_preview_asset = preview_asset
    preview_payload = (
        _build_preview_payload(
            paper_id=paper_id,
            paper=paper,
            preview_asset=preview_asset,
        )
        if preview_asset
        else None
    )
    if preview_payload:
        return preview_payload
    if preview_asset:
        preview_asset = None

    if not preview_asset:
        for task_id in _candidate_task_ids_for_asset_recovery(paper, asset_map):
            preview_asset = await _resolve_preview_html_asset(
                paper=paper,
                paper_id=paper_id,
                task_id=task_id,
                asset_map=asset_map,
            )
            if preview_asset:
                break

    preview_payload = (
        _build_preview_payload(
            paper_id=paper_id,
            paper=paper,
            preview_asset=preview_asset,
        )
        if preview_asset
        else None
    )
    if preview_payload:
        return preview_payload

    for candidate_asset in (preview_asset, original_preview_asset):
        if not candidate_asset:
            continue
        fallback_payload = _build_preview_payload(
            paper_id=paper_id,
            paper=paper,
            preview_asset=candidate_asset,
            allow_untranslated_zh=True,
            allow_stale_reader=True,
        )
        if fallback_payload:
            logger.info(
                "Serving fallback preview payload for paper %s from asset %s despite untranslated-zh heuristic",
                paper_id,
                candidate_asset.get("id"),
            )
            return fallback_payload

    raise HTTPException(status_code=404, detail="Preview file not found")


async def create_paper_download_session(*, paper_id: str) -> Dict[str, Any]:
    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = await _ensure_translated_pdf_asset(paper=paper, asset_map=asset_map)
    if not translated_asset:
        raise HTTPException(status_code=404, detail="Translated PDF not available")

    expires_at = int(time.time()) + 300
    token = _sign_download_token(
        {
            "v": 1,
            "paper_id": paper_id,
            "asset_id": translated_asset.get("id"),
            "exp": expires_at,
        }
    )
    return {
        "paper_id": paper_id,
        "asset_id": translated_asset.get("id"),
        "download_url": f"/api/papers/{paper_id}/download?token={token}",
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
    }


async def resolve_paper_translated_pdf_preview(*, paper_id: str) -> Dict[str, Any]:
    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = await _ensure_translated_pdf_asset(paper=paper, asset_map=asset_map)
    if not translated_asset:
        raise HTTPException(status_code=404, detail="Translated PDF not available")

    file_path = _resolve_storage_path(translated_asset.get("file_path") or "")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Translated PDF file not found")

    return {
        "paper_id": paper_id,
        "asset": translated_asset,
        "file_path": str(file_path),
    }


async def resolve_paper_source_pdf_preview(*, paper_id: str) -> Dict[str, Any]:
    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    task_id = str(paper.get("community_selected_task_id") or paper.get("trans_latest_task_id") or "").strip()
    preferred_arxiv_id = str(paper.get("arxiv_id") or "").strip() or None

    source_asset = asset_map.get("source_archive")
    if source_asset and source_asset.get("file_path"):
        source_path = _resolve_storage_path(source_asset.get("file_path") or "")
        if source_path.is_file() and source_path.suffix.lower() == ".pdf":
            return {
                "paper_id": paper_id,
                "file_path": str(source_path),
                "filename": source_path.name,
            }

    for source_dir in _candidate_source_directories_for_preview(
        paper_id=paper_id,
        task_id=task_id,
        asset_map=asset_map,
    ):
        candidates = download_route._collect_original_pdf_candidates(source_dir)
        if not candidates:
            continue
        selected = download_route._pick_best_source_pdf(
            source_dir,
            candidates,
            preferred_stem=preferred_arxiv_id,
        )
        if selected and selected.exists():
            return {
                "paper_id": paper_id,
                "file_path": str(selected),
                "filename": selected.name,
            }

    if preferred_arxiv_id:
        return {
            "paper_id": paper_id,
            "arxiv_id": preferred_arxiv_id,
        }

    if task_id:
        return {
            "paper_id": paper_id,
            "legacy_task_id": task_id,
        }

    raise HTTPException(status_code=404, detail="Source PDF not available")


async def resolve_paper_download(*, paper_id: str, token: str) -> Dict[str, Any]:
    payload = _decode_download_token(token)
    if payload.get("paper_id") != paper_id:
        raise HTTPException(status_code=403, detail="Download token does not match paper")

    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = await _ensure_translated_pdf_asset(paper=paper, asset_map=asset_map)
    if not translated_asset:
        raise HTTPException(status_code=404, detail="Translated PDF not available")
    if payload.get("asset_id") != translated_asset.get("id"):
        raise HTTPException(status_code=403, detail="Download token does not match asset")

    file_path = _resolve_storage_path(translated_asset.get("file_path") or "")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Translated PDF file not found")

    try:
        await _increment_paper_download_count(paper_id)
    except Exception as exc:
        logger.warning("Failed to increment download count for paper %s: %s", paper_id, exc)
    return {
        "paper_id": paper_id,
        "asset": translated_asset,
        "file_path": str(file_path),
    }


async def list_community_papers(
    *,
    sort: str = "latest",
    q: Optional[str] = None,
    viewer_user_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    papers: List[Dict[str, Any]] = []
    source_mode = "database"
    try:
        papers = await _run_local_repo(repository.list_public_papers)
    except DatabaseUnavailableError:
        papers = []
    except Exception as exc:
        logger.warning("Failed to list community papers from local repository: %s", exc)
        papers = []

    if not papers:
        logger.warning(
            "Local community repository returned no readable public rows; returning empty community list"
        )

    papers = [_apply_runtime_paper_override(paper) or paper for paper in papers]
    papers = [paper for paper in papers if _is_public_community_paper(paper)]
    papers = [paper for paper in papers if _matches_paper_query(paper, q)]
    papers = _sort_papers(papers, sort)
    if limit is not None and limit > 0:
        papers = papers[:limit]

    paper_ids = [paper["id"] for paper in papers]
    asset_maps = await _fetch_asset_maps_for_papers(paper_ids) if paper_ids else {}
    items = [
        _paper_summary(
            paper,
            asset_map=asset_maps.get(paper["id"]),
        )
        for paper in papers
    ]
    return {"items": items, "total": len(items), "source_mode": source_mode}


async def get_community_paper_detail(
    *,
    paper_id: str,
    viewer_user_id: Optional[str] = None,
    fast_path: bool = False,
) -> Dict[str, Any]:
    paper = await _fetch_paper_by_id(paper_id)
    if not _is_public_community_paper(paper):
        raise HTTPException(status_code=404, detail="Paper not found")

    asset_map: Optional[Dict[str, Dict[str, Any]]] = None
    latest_asset: Optional[Dict[str, Any]] = None
    try:
        asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
        latest_asset = _select_latest_asset_from_map(asset_map)
    except Exception as exc:
        logger.warning("Failed to fetch full asset map for paper %s: %s", paper_id, exc)
        asset_map = None
        try:
            latest_asset = (await _fetch_latest_assets([paper_id])).get(paper_id)
        except Exception:
            latest_asset = None
    if fast_path:
        _schedule_public_detail_repair(
            paper_id=paper_id,
            paper=paper,
            asset_map=asset_map,
        )
    else:
        paper = await _hydrate_arxiv_metadata_if_needed(paper)
        paper = await _hydrate_translated_abstract_if_needed(
            paper,
            asset_map=asset_map,
        )
    viewer_state = (await _fetch_viewer_state([paper_id], user_id=viewer_user_id)).get(
        paper_id,
        {"liked": False, "favorited": False},
    )
    structured_insights = _build_structured_insights_payload(
        await _fetch_structured_insight_sections(paper_id)
    )
    resolved_asset_map: Dict[str, Dict[str, Any]] = dict(asset_map or {})
    preview_payload: Optional[Dict[str, Any]] = None

    preview_asset = resolved_asset_map.get("preview_html")
    if preview_asset:
        preview_payload = _build_preview_payload(
            paper_id=paper_id,
            paper=paper,
            preview_asset=preview_asset,
        )

    if not preview_payload:
        for task_id in _candidate_task_ids_for_asset_recovery(paper, resolved_asset_map):
            preview_asset = await _resolve_preview_html_asset(
                paper=paper,
                paper_id=paper_id,
                task_id=task_id,
                asset_map=resolved_asset_map,
            )
            if not preview_asset:
                continue
            resolved_asset_map["preview_html"] = preview_asset
            preview_payload = _build_preview_payload(
                paper_id=paper_id,
                paper=paper,
                preview_asset=preview_asset,
            )
            if preview_payload:
                break

    translated_asset = await _ensure_translated_pdf_asset(
        paper=paper,
        asset_map=resolved_asset_map,
    )

    if not preview_payload and paper.get("trans_status") in {"completed", "completed_with_warnings"}:
        _schedule_preview_recovery(
            paper_id=paper_id,
            paper=paper,
            asset_map=resolved_asset_map,
        )

    source_html_content = await _fetch_sanitized_arxiv_html(str(paper.get("arxiv_id") or ""))

    reader_payload = _build_reader_experience_payload(
        paper=paper,
        paper_id=paper_id,
        preview_payload=preview_payload,
        translated_asset=translated_asset,
        source_html_content=source_html_content,
    )

    return {
        "paper": _paper_summary(
            paper,
            latest_asset=latest_asset,
            asset_map=resolved_asset_map,
            viewer_state=viewer_state,
        ),
        "preview": preview_payload,
        "reader_state": reader_payload["reader_state"],
        "reader": reader_payload["reader"],
        "experience": reader_payload["experience"],
        "structured_insights": structured_insights,
    }


async def get_community_paper_similar(*, paper_id: str) -> Dict[str, Any]:
    await _ensure_public_paper(paper_id)
    return {"items": await _fetch_persisted_similar_recommendations(paper_id)}


async def import_or_reuse_paper(*, source: str, arxiv_id: str) -> Dict[str, Any]:
    """
    Import an external paper into the community library, or reuse an existing one.

    This is a minimal bridge for the community agent / homepage agent to perform
    鈥滈潤榛樺鍏モ€? It prefers reusing existing papers when possible.
    """
    # 濡傛灉宸叉湁瀵瑰簲 arxiv_id 鐨?paper锛屽垯鐩存帴澶嶇敤
    existing = await _fetch_paper_by_arxiv_id(arxiv_id)
    if existing is not None:
        return {
            "paper_id": existing["id"],
            "reused": True,
            "imported": False,
            "reader_state": "source_ready",
        }

    # Otherwise create a new paper through the existing submit flow.
    payload = await submit_arxiv_paper(
        arxiv_id=arxiv_id,
        credentials=None,
        source_language="en",
        target_language="zh",
    )
    paper = payload["paper"]
    return {
        "paper_id": paper["id"],
        "reused": False,
        "imported": True,
        "reader_state": "source_ready",
    }


async def record_community_paper_view(*, paper_id: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        count = await _run_local_repo(lambda: repository.increment_view_count(paper_id))
    except DatabaseUnavailableError:
        count = None
    except Exception as exc:
        logger.warning("Failed to increment view count for paper %s locally: %s", paper_id, exc)
        count = None
    if count is not None:
        return {"paper_id": paper_id, "view_count": count}
    paper = await _fetch_paper_by_id(paper_id)
    if paper is None or paper.get("visibility") != "public" or paper.get("status") == "removed":
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"paper_id": paper_id, "view_count": int(paper.get("view_count") or 0)}




