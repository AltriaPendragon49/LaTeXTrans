from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import math
import mimetypes
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin
from uuid import uuid4

import aiohttp
import httpx
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
try:
    import redis
except Exception:  # pragma: no cover - optional dependency guard
    redis = None  # type: ignore[assignment]
try:
    from PyPDF2 import PdfReader, PdfWriter
except Exception:  # pragma: no cover - optional dependency guard
    PdfReader = None  # type: ignore[assignment]
    PdfWriter = None  # type: ignore[assignment]

from backend.app.api.routes import arxiv as arxiv_route
from backend.app.api.routes import download as download_route
from backend.app.api.routes import translate as translate_route
from backend.app.api.routes import upload as upload_route
from backend.app.core.config import TaskStatus, get_settings
from backend.app.db import DatabaseUnavailableError, db_connection, get_database_dialect
from backend.app.repositories import CommunityPaperRepository, TranslationTaskRepository
from backend.app.repositories.community_paper_repository import (
    FavoriteFolderLimitError,
    FavoriteFolderNameConflictError,
    FavoriteFolderNotFoundError,
)
from backend.app.services.latex.utils import extract_abstract, extract_text_from_tex, extract_title
from backend.app.services.latex_validator import find_main_tex_file
from backend.app.services import arxiv_raw_cache
from backend.app.services import paper_thumbnail_service
from backend.app.services import paper_preview_service
from backend.app.services import task_artifact_storage
from backend.app.services.community_translation_quality import (
    QualityGateResult,
    collect_quality_inputs_from_directory,
    evaluate_community_translation_quality,
    write_quality_diagnostics,
)
from backend.app.services.runtime_pressure import admin_job_execution_enabled
from backend.app.services.agents.llm_token_pool import post_chat_completion_with_pool
from backend.app.services.storage_backend import (
    CosStorageBackend,
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
from backend.app.services.task_runtime_client import request_worker_task_cancel, worker_cancel_signal_failed
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
_preview_html_cache: Dict[str, str] = {}
_source_html_cache: Dict[str, str] = {}
_PUBLIC_EXTERNAL_LINK_CACHE: Dict[str, Dict[str, Optional[str]]] = {}
_PUBLIC_FEED_SCORE_FACTOR = 1_000_000_000
_PUBLIC_FEED_RESPONSE_REGISTRY_SUFFIX = "responses"
_PUBLIC_FEED_REBUILD_LOCK_SUFFIX = "index:rebuild:lock"
_public_feed_store: Optional["_PublicFeedRedisStore"] = None
_curation_semaphore: Optional[asyncio.Semaphore] = None
_delete_semaphore: Optional[asyncio.Semaphore] = None
_curation_job_tasks: Dict[str, asyncio.Task] = {}
_delete_job_tasks: Dict[str, asyncio.Task] = {}
_DEFAULT_ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS = 1800
_DEFAULT_ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS = 7200
ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS = settings.admin_curation_task_wait_timeout_seconds
ADMIN_CURATION_ADMISSION_TIMEOUT_SECONDS = settings.admin_curation_admission_timeout_seconds
ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS = settings.admin_curation_execution_timeout_seconds
ADMIN_CURATION_TIMEOUT_TERMINAL_REASONS = {
    "admission_timeout": "task_admission_timeout",
    "execution_timeout": "task_execution_timeout",
}
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
STRUCTURED_INSIGHT_MAX_OUTPUT_TOKENS = 1800
STRUCTURED_INSIGHT_BASE_503_SWITCH_THRESHOLD = 3
STRUCTURED_INSIGHT_READY_STATUS = "ready"
STRUCTURED_INSIGHT_PROCESSING_STATUS = "processing"
STRUCTURED_INSIGHT_NOT_READY_STATUS = "not_ready"
STRUCTURED_INSIGHT_SOURCE_MAX_CHARS = 2400
STRUCTURED_INSIGHT_RUNTIME_ARTIFACT_FILENAMES = {
    "sections_map.json",
    "envs_map.json",
    "captions_map.json",
}
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
STRUCTURED_INSIGHT_COMPLETE_ENDINGS = ("。", "！", "？", "；", ".", "!", "?", ";", "…")
STRUCTURED_INSIGHT_TRAILING_CLOSERS = tuple('”’」』）》】）)]}"\'`*')
STRUCTURED_INSIGHT_SECTION_QUESTIONS = {
    "problem": "这篇论文解决什么问题，为什么重要，现有方法的关键不足是什么？",
    "solution": "作者的核心思路是什么，方法整体是如何工作的？",
    "innovation": "论文的关键创新点有哪些，相比已有方法，本质区别在哪里？",
    "experiment": "论文如何验证方法有效性，主要结论是什么？",
    "future": "这项工作有什么潜在改进或扩展方向，对相关研究有哪些启发？",
}


class AdminCurationTaskWaitTimeout(TimeoutError):
    def __init__(self, task_id: str, timeout_reason: str):
        self.task_id = str(task_id or "").strip()
        self.timeout_reason = str(timeout_reason or "").strip() or "execution_timeout"
        self.terminal_reason = ADMIN_CURATION_TIMEOUT_TERMINAL_REASONS.get(
            self.timeout_reason,
            "task_execution_timeout",
        )
        super().__init__(f"Timed out waiting for task {self.task_id} ({self.timeout_reason})")


def _resolve_admin_curation_timeout_seconds(stage: str) -> int:
    stage_default = (
        _DEFAULT_ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS
        if stage == "admission"
        else _DEFAULT_ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS
    )
    legacy_timeout = ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS
    try:
        resolved_legacy = int(legacy_timeout)
    except (TypeError, ValueError):
        resolved_legacy = _DEFAULT_ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS

    stage_value = (
        ADMIN_CURATION_ADMISSION_TIMEOUT_SECONDS
        if stage == "admission"
        else ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS
    )
    try:
        resolved_stage = int(stage_value)
    except (TypeError, ValueError):
        resolved_stage = resolved_legacy

    if (
        resolved_stage == stage_default
        and resolved_legacy != _DEFAULT_ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS
    ):
        return resolved_legacy
    return resolved_stage


def _task_has_active_execution_started(task: Optional[Dict[str, Any]]) -> bool:
    normalized_status = str((task or {}).get("status") or "").strip().lower()
    return normalized_status in {"processing", *TERMINAL_TASK_STATUSES}


def _resolve_task_terminal_reason(task: Optional[Dict[str, Any]]) -> Optional[str]:
    if not task:
        return None
    failure_reason_code = str(task.get("failure_reason_code") or "").strip()
    if failure_reason_code:
        return failure_reason_code
    detail_code = str(task.get("detail_code") or "").strip()
    return detail_code or None
_PDF_DELIVERY_CACHE_VERSION = "v1"
_PDF_DELIVERY_MEANINGFUL_TEXT_THRESHOLD = 8
_PDF_DELIVERY_NEXT_PAGE_TEXT_THRESHOLD = 32
_PDF_DELIVERY_BLANK_PAGE_CONTENT_BYTES_THRESHOLD = 256
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
    "每个子结构需有简短标题和对应解释内容；不要输出单一长段落，也不要改成纯 bullet 列表；"
    "最后必须以完整句子和句末标点结束，不要停在小标题、短语或半句话。"
)
STRUCTURED_INSIGHT_SUGGESTED_SUBHEADINGS = {
    "problem": ["问题本质", "现有方法的局限", "为什么重要"],
    "solution": ["核心思路", "关键流程", "模块协同"],
    "innovation": ["关键创新点", "本质差异", "为什么不一样"],
    "experiment": ["核心指标", "对比结果", "实验结论"],
    "future": ["当前局限", "可改进方向", "研究启发"],
}
COMMUNITY_FEED_ABSTRACT_MAX_CHARS = 320
COMMUNITY_FEED_PUBLIC_ASSET_TYPES = {"source_archive", "source_pdf", "translated_pdf"}

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
- End with a complete sentence and terminal punctuation; never stop after a title, phrase, or half sentence.
- If the evidence is limited, say that explicitly in Chinese instead of inventing facts.
- Stay focused on the current question instead of summarizing the whole paper.
- Prefer paper-specific details over generic praise or industry-level generalities.

Return only the final Chinese passage.
""".strip()


class _PublicFeedRedisStore:
    def __init__(self) -> None:
        self._prefix = str(getattr(settings, "community_feed_redis_prefix", "feed") or "feed").strip() or "feed"
        redis_url = str(getattr(settings, "community_feed_redis_url", "") or "").strip()
        self._cache_ttl_seconds = max(1, int(getattr(settings, "community_feed_cache_ttl_seconds", 60) or 60))
        self._rebuild_lock_ttl_seconds = max(
            1,
            int(getattr(settings, "community_feed_rebuild_lock_ttl_seconds", 30) or 30),
        )
        self._client = (
            redis.Redis.from_url(redis_url, decode_responses=True)
            if redis is not None and redis_url
            else None
        )

    @property
    def available(self) -> bool:
        return self._client is not None

    def _key(self, suffix: str) -> str:
        return f"{self._prefix}:{suffix}"

    def response_key(self, *, sort: str, limit: Optional[int], offset: int) -> str:
        normalized_sort = str(sort or "latest").strip().lower() or "latest"
        normalized_limit = int(limit) if limit is not None else 0
        normalized_offset = max(0, int(offset or 0))
        return self._key(f"response:{normalized_sort}:{normalized_limit}:{normalized_offset}")

    def response_registry_key(self) -> str:
        return self._key(_PUBLIC_FEED_RESPONSE_REGISTRY_SUFFIX)

    def index_key(self, sort: str) -> str:
        normalized_sort = str(sort or "latest").strip().lower() or "latest"
        return self._key(f"index:{normalized_sort}")

    def rebuild_lock_key(self) -> str:
        return self._key(_PUBLIC_FEED_REBUILD_LOCK_SUFFIX)

    def get_cached_payload(self, *, sort: str, limit: Optional[int], offset: int) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None
        payload = self._client.get(self.response_key(sort=sort, limit=limit, offset=offset))
        if not payload:
            return None
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, dict) else None

    def set_cached_payload(self, *, sort: str, limit: Optional[int], offset: int, payload: Dict[str, Any]) -> None:
        if not self._client:
            return
        key = self.response_key(sort=sort, limit=limit, offset=offset)
        serialized = json.dumps(payload, ensure_ascii=False)
        pipeline = self._client.pipeline()
        pipeline.setex(key, self._cache_ttl_seconds, serialized)
        pipeline.sadd(self.response_registry_key(), key)
        pipeline.execute()

    def clear_cached_payloads(self) -> None:
        if not self._client:
            return
        registry_key = self.response_registry_key()
        keys = list(self._client.smembers(registry_key) or [])
        if keys:
            self._client.delete(*keys)
        self._client.delete(registry_key)

    def read_ranked_ids(self, *, sort: str, offset: int, limit: Optional[int]) -> List[str]:
        if not self._client:
            return []
        normalized_offset = max(0, int(offset or 0))
        normalized_limit = max(0, int(limit or 0))
        if normalized_limit <= 0:
            return []
        end = normalized_offset + normalized_limit - 1
        values = self._client.zrevrange(self.index_key(sort), normalized_offset, end)
        return [str(value).strip() for value in values if str(value).strip()]

    def count_ranked_ids(self, *, sort: str) -> int:
        if not self._client:
            return 0
        return int(self._client.zcard(self.index_key(sort)) or 0)

    def replace_index(self, *, sort: str, mapping: Dict[str, float]) -> None:
        if not self._client:
            return
        key = self.index_key(sort)
        temp_key = self._key(f"index:{str(sort or 'latest').strip().lower() or 'latest'}:tmp:{uuid4().hex}")
        pipeline = self._client.pipeline()
        pipeline.delete(temp_key)
        if mapping:
            pipeline.zadd(temp_key, mapping)
        pipeline.rename(temp_key, key)
        pipeline.execute()

    def upsert_ranked_paper(self, *, sort: str, paper_id: str, score: float) -> None:
        if not self._client:
            return
        self._client.zadd(self.index_key(sort), {paper_id: float(score)})

    def increment_ranked_paper(self, *, sort: str, paper_id: str, delta: float) -> None:
        if not self._client:
            return
        self._client.zincrby(self.index_key(sort), float(delta), paper_id)

    def remove_ranked_paper(self, *, paper_id: str) -> None:
        if not self._client:
            return
        pipeline = self._client.pipeline()
        for sort in ("latest", "views", "likes"):
            pipeline.zrem(self.index_key(sort), paper_id)
        pipeline.execute()

    def acquire_rebuild_lock(self) -> bool:
        if not self._client:
            return False
        return bool(
            self._client.set(
                self.rebuild_lock_key(),
                "1",
                nx=True,
                ex=self._rebuild_lock_ttl_seconds,
            )
        )


def _get_public_feed_store() -> _PublicFeedRedisStore:
    global _public_feed_store
    if _public_feed_store is None:
        _public_feed_store = _PublicFeedRedisStore()
    return _public_feed_store


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


def _get_translation_task_repository() -> TranslationTaskRepository:
    return TranslationTaskRepository()


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


_ARXIV_API_LOCK = threading.Lock()
_ARXIV_API_LAST_CALL = 0.0
_ARXIV_API_MIN_GAP = 5.0  # arXiv API: official limit is 1 req/3s, use 5s to be safe
_ARXIV_API_JITTER = 1.0  # ±1s random jitter to avoid thundering herd


def _throttle_arxiv_api():
    """Enforce a minimum gap between arXiv API requests to avoid 429 rate limiting."""
    with _ARXIV_API_LOCK:
        global _ARXIV_API_LAST_CALL
        now = time.monotonic()
        gap = now - _ARXIV_API_LAST_CALL
        if gap < _ARXIV_API_MIN_GAP:
            sleep_time = _ARXIV_API_MIN_GAP - gap + random.uniform(0, _ARXIV_API_JITTER)
            time.sleep(sleep_time)
        _ARXIV_API_LAST_CALL = time.monotonic()


def _fetch_arxiv_metadata_sync(arxiv_id: str) -> Dict[str, Any]:
    max_retries = 5
    response_text = ""
    last_error: Optional[BaseException] = None
    for attempt in range(max_retries):
        try:
            _throttle_arxiv_api()
            response = requests.get(
                "https://export.arxiv.org/api/query",
                params={"id_list": arxiv_id},
                headers={"User-Agent": "LaTexTrans/CommunityWeek1Fix"},
                timeout=15,
            )
            response.raise_for_status()
            response_text = response.text
            break
        except requests.RequestException as exc:
            last_error = exc
            status_code = getattr(exc.response, "status_code", None) if hasattr(exc, "response") and exc.response else None
            if status_code in (429, 503):
                backoff = 5.0 * (2 ** attempt)
                logger.warning(
                    "arXiv API %d for %s, waiting %.1fs before retry %d/%d",
                    status_code, arxiv_id, backoff, attempt + 1, max_retries,
                )
                time.sleep(backoff)
                continue
            if attempt >= max_retries - 1:
                raise
            time.sleep(1.0 * (attempt + 1))
    if not response_text and last_error:
        raise last_error

    root = ET.fromstring(response_text)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", namespace)
    if entry is None:
        return {}

    title = _normalize_metadata_text(entry.findtext("atom:title", default="", namespaces=namespace))
    abstract_raw = _normalize_metadata_text(entry.findtext("atom:summary", default="", namespaces=namespace))
    published = _normalize_metadata_text(entry.findtext("atom:published", default="", namespaces=namespace))
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
        "arxiv_published_at": _normalize_arxiv_published_at(published),
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
        or _is_placeholder_paper_title(title, source="arxiv")
        or not (paper.get("authors") or [])
        or not (paper.get("categories") or [])
        or not (paper.get("abstract_raw") or "").strip()
        or not paper.get("arxiv_published_at")
    )


def _is_placeholder_paper_title(title: Optional[str], *, source: Optional[str] = None) -> bool:
    normalized = _normalize_metadata_text(title)
    if not normalized:
        return True
    lowered = normalized.lower()
    if lowered in {"curated paper", "uploaded paper"}:
        return True
    if (source or "").strip() == "arxiv" and normalized.startswith("arXiv:"):
        return True
    return False


def _best_available_metadata_payload(paper: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    title = _normalize_metadata_text(str(paper.get("title") or ""))
    metadata_title = _normalize_metadata_text(metadata.get("title"))
    if metadata_title and _is_placeholder_paper_title(title, source=paper.get("source")):
        payload["title"] = metadata_title
    if metadata.get("authors") and not (paper.get("authors") or []):
        payload["authors"] = metadata["authors"]
    if metadata.get("categories") and not (paper.get("categories") or []):
        payload["categories"] = metadata["categories"]
    if metadata.get("abstract_raw") and not _normalize_metadata_text(paper.get("abstract_raw")):
        payload["abstract_raw"] = metadata["abstract_raw"]
    if metadata.get("arxiv_published_at") and not paper.get("arxiv_published_at"):
        payload["arxiv_published_at"] = metadata["arxiv_published_at"]
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
                try:
                    plain_text = _normalize_metadata_text(extract_text_from_tex(str(content)))
                except Exception:
                    continue
                if plain_text:
                    return plain_text

    return None


def _candidate_output_directories_for_task(task_id: str, *, recover_missing: bool = True) -> List[Path]:
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

    def _add_directory_children(path: Optional[Path]) -> None:
        if path is None or not path.exists() or not path.is_dir():
            return
        for child in sorted(path.iterdir()):
            if child.is_dir():
                _add_directory(child)

    task = task_manager.get_task(task_id) if task_id else None
    if task:
        output_path_raw = str(task.get("output_path") or "").strip()
        if output_path_raw:
            stored_output = _resolve_storage_path(output_path_raw)
            _add_directory(stored_output)
            if recover_missing and not stored_output.exists():
                materialized_output = _materialize_task_directory_for_asset_recovery(
                    output_path_raw,
                    task_id=task_id,
                    kind="output",
                )
                _add_directory(materialized_output)
                _add_directory_children(materialized_output)

    task_root = Path(settings.outputs_dir) / task_id
    _add_directory(task_root)
    _add_directory_children(task_root)

    return candidates


def _task_snapshot_for_artifact_recovery(task_id: str) -> Optional[Dict[str, Any]]:
    if not task_id:
        return None
    task: Optional[Dict[str, Any]] = None
    try:
        task = task_manager.get_task(task_id)
    except Exception as exc:
        logger.debug("Failed to read runtime task snapshot for %s: %s", task_id, exc)
    if task and str(task.get("output_path") or "").strip():
        return task
    try:
        persisted_task = _get_translation_task_repository().get_task(task_id)
    except Exception as exc:
        logger.debug("Failed to read persisted task snapshot for %s: %s", task_id, exc)
        persisted_task = None
    return persisted_task or task


def _relative_object_key_under_prefix(object_key: str, prefix: str) -> Optional[str]:
    normalized_key = str(object_key or "").replace("\\", "/").strip("/")
    normalized_prefix = str(prefix or "").replace("\\", "/").strip("/")
    if not normalized_key or not normalized_prefix:
        return None

    candidate_prefixes = [normalized_prefix]
    base_prefix = str(getattr(settings, "cos_base_prefix", "") or "").strip().strip("/")
    if base_prefix:
        candidate_prefixes.append(f"{base_prefix}/{normalized_prefix}")

    for candidate_prefix in dict.fromkeys(candidate_prefixes):
        if normalized_key == candidate_prefix:
            return Path(normalized_key).name
        prefix_with_slash = f"{candidate_prefix}/"
        if normalized_key.startswith(prefix_with_slash):
            return normalized_key[len(prefix_with_slash) :]
    return None


def _safe_structured_insight_recovery_destination(task_id: str) -> Path:
    safe_task_id = re.sub(r"[^0-9A-Za-z._-]+", "_", str(task_id or "shared")).strip("._-") or "shared"
    return Path(settings.storage_temp_dir) / "task_directory_recovery" / safe_task_id / "structured_insights_output"


def _materialize_structured_insight_artifacts_from_task_output(
    *,
    task_id: str,
    output_path: str,
    force: bool = False,
) -> Optional[Path]:
    normalized_output = str(output_path or "").strip()
    if not normalized_output:
        return None

    backend = _get_storage_backend()
    if not _storage_uses_object_store(backend):
        resolved = _resolve_storage_path(normalized_output)
        return resolved if resolved.exists() and resolved.is_dir() else None

    stored_root = task_artifact_storage.normalize_stored_task_path(normalized_output)
    destination = _safe_structured_insight_recovery_destination(task_id)
    if destination.exists():
        if force:
            shutil.rmtree(destination)
        elif any(destination.rglob("sections_map.json")):
            return destination

    destination.mkdir(parents=True, exist_ok=True)
    try:
        refs = backend.list_files(prefix=stored_root)
    except Exception as exc:
        logger.debug(
            "Failed to list structured insight artifacts for task %s from %s: %s",
            task_id,
            stored_root,
            exc,
        )
        return None

    downloaded = 0
    for ref in refs:
        object_key = str(ref.object_key or "").replace("\\", "/")
        if Path(object_key).name not in STRUCTURED_INSIGHT_RUNTIME_ARTIFACT_FILENAMES:
            continue
        relative = _relative_object_key_under_prefix(object_key, stored_root)
        if not relative:
            continue
        relative_path = Path(relative)
        if relative_path.is_absolute() or any(part == ".." for part in relative_path.parts):
            continue
        try:
            backend.download_file(object_key=ref.object_key, local_path=destination / relative_path)
            downloaded += 1
        except Exception as exc:
            logger.debug(
                "Failed to materialize structured insight artifact %s for task %s: %s",
                object_key,
                task_id,
                exc,
            )

    return destination if downloaded else None


def _candidate_structured_insight_recovery_directories_for_task(
    task_id: str,
    *,
    force: bool = False,
) -> List[Path]:
    task = _task_snapshot_for_artifact_recovery(task_id)
    output_path = str((task or {}).get("output_path") or "").strip()
    if not output_path:
        return []

    recovered_root = _materialize_structured_insight_artifacts_from_task_output(
        task_id=task_id,
        output_path=output_path,
        force=force,
    )
    if not recovered_root or not recovered_root.exists() or not recovered_root.is_dir():
        return []

    candidates = [recovered_root]
    candidates.extend(child for child in sorted(recovered_root.iterdir()) if child.is_dir())
    return candidates


def _candidate_runtime_cache_paths_for_task(task_id: str) -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()

    def _add_path(path: Optional[Path]) -> None:
        if path is None:
            return
        try:
            normalized = str(path.resolve(strict=False))
        except Exception:
            normalized = str(path)
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(path)

    task = task_manager.get_task(task_id) if task_id else None
    if task:
        stored_output = _resolve_storage_path(task.get("output_path") or "")
        if stored_output.name != task_id and stored_output.parent.name == task_id:
            _add_path(stored_output.parent)
        _add_path(stored_output)

    _add_path(Path(settings.outputs_dir) / task_id)
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


async def repair_published_arxiv_metadata(*, limit: int = 20) -> Dict[str, int]:
    normalized_limit = max(1, min(100, int(limit or 20)))
    repository = get_community_paper_repository()
    try:
        papers = await _run_local_repo(
            lambda: repository.list_published_arxiv_papers_needing_metadata_repair(
                limit=normalized_limit,
            )
        )
    except DatabaseUnavailableError:
        logger.warning("Local database unavailable while scanning arXiv metadata repair candidates")
        return {"scanned": 0, "repaired": 0, "unrepaired": 0, "failed": 0}
    except Exception as exc:
        logger.warning("Failed to scan arXiv metadata repair candidates: %s", exc)
        return {"scanned": 0, "repaired": 0, "unrepaired": 0, "failed": 0}

    result = {"scanned": 0, "repaired": 0, "unrepaired": 0, "failed": 0}
    for paper in papers:
        result["scanned"] += 1
        try:
            repaired = await _hydrate_arxiv_metadata_if_needed(paper)
            if _needs_arxiv_metadata_hydration(repaired):
                result["unrepaired"] += 1
            else:
                result["repaired"] += 1
        except Exception as exc:
            result["failed"] += 1
            logger.warning(
                "Failed to repair arXiv metadata for paper %s (%s): %s",
                paper.get("id"),
                paper.get("arxiv_id"),
                exc,
            )
    if result["scanned"]:
        logger.info("arXiv metadata repair scan finished: %s", result)
    return result


def _merge_arxiv_metadata(
    current_metadata: Dict[str, Any],
    fetched_metadata: Dict[str, Any],
    *,
    source: str,
) -> Dict[str, Any]:
    merged = dict(current_metadata or {})
    current_title = _normalize_metadata_text(merged.get("title"))
    fetched_title = _normalize_metadata_text(fetched_metadata.get("title"))
    if fetched_title and _is_placeholder_paper_title(current_title, source=source):
        merged["title"] = fetched_title
    if not (merged.get("authors") or []) and fetched_metadata.get("authors"):
        merged["authors"] = fetched_metadata.get("authors")
    if not (merged.get("categories") or []) and fetched_metadata.get("categories"):
        merged["categories"] = fetched_metadata.get("categories")
    if not _normalize_metadata_text(merged.get("abstract_raw")) and fetched_metadata.get("abstract_raw"):
        merged["abstract_raw"] = fetched_metadata.get("abstract_raw")
    if not _normalize_metadata_text(merged.get("arxiv_id")) and fetched_metadata.get("arxiv_id"):
        merged["arxiv_id"] = fetched_metadata.get("arxiv_id")
    return merged


async def _ensure_publishable_admin_curation_metadata(
    *,
    job: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    source_type = str(job.get("source_type") or "").strip()
    resolved = dict(metadata or {})
    if source_type != "arxiv":
        return resolved

    resolved_arxiv_id = _normalize_metadata_text(resolved.get("arxiv_id")) or _normalize_metadata_text(job.get("arxiv_id"))
    if not resolved_arxiv_id:
        raise ValueError("Admin arXiv curation publish requires arxiv_id")
    resolved["arxiv_id"] = resolved_arxiv_id

    if (
        _is_placeholder_paper_title(resolved.get("title"), source="arxiv")
        or not (resolved.get("authors") or [])
        or not (resolved.get("categories") or [])
        or not _normalize_metadata_text(resolved.get("abstract_raw"))
    ):
        fetched_metadata = await _fetch_arxiv_metadata(resolved_arxiv_id)
        resolved = _merge_arxiv_metadata(resolved, fetched_metadata, source="arxiv")

    if _is_placeholder_paper_title(resolved.get("title"), source="arxiv"):
        resolved["title"] = f"arXiv:{resolved_arxiv_id}"
    resolved["authors"] = resolved.get("authors") or []
    resolved["categories"] = resolved.get("categories") or []
    return resolved


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


async def _hydrate_public_feed_papers_if_needed(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not papers:
        return papers
    repaired = await asyncio.gather(
        *(
            _hydrate_arxiv_metadata_if_needed(paper)
            if _is_placeholder_paper_title(paper.get("title"), source=paper.get("source"))
            else asyncio.sleep(0, result=paper)
            for paper in papers
        )
    )
    return [paper or original for paper, original in zip(repaired, papers)]


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


def _materialize_task_directory_for_asset_recovery(
    stored_path: str,
    *,
    task_id: Optional[str],
    kind: str,
) -> Optional[Path]:
    normalized_path = str(stored_path or "").strip()
    if not normalized_path:
        return None
    safe_task_id = re.sub(r"[^0-9A-Za-z._-]+", "_", str(task_id or "shared")).strip("._-") or "shared"
    safe_kind = re.sub(r"[^0-9A-Za-z._-]+", "_", str(kind or "asset")).strip("._-") or "asset"
    destination = Path(settings.storage_temp_dir) / "task_directory_recovery" / safe_task_id / safe_kind
    try:
        return task_artifact_storage.materialize_task_directory(
            normalized_path,
            destination=destination,
            force=False,
        )
    except Exception as exc:
        logger.debug(
            "Failed to materialize task %s directory for %s recovery from %s: %s",
            task_id,
            safe_kind,
            normalized_path,
            exc,
        )
        return None


def _translated_pdf_delivery_cache_dir() -> Path:
    cache_dir = Path(settings.storage_temp_dir) / "translated_pdf_delivery"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _materialized_pdf_asset_cache_dir() -> Path:
    cache_dir = Path(settings.storage_temp_dir) / "materialized_pdf_assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _materialize_object_storage_pdf_asset(asset: Dict[str, Any]) -> Optional[Path]:
    object_key = str(asset.get("file_path") or "").strip()
    if not object_key:
        return None

    file_name = Path(str(asset.get("file_name") or object_key).strip() or "asset.pdf").name
    suffix = Path(file_name).suffix or ".pdf"
    cache_key = f"materialized-pdf:v1:{asset.get('id') or ''}:{object_key}:{file_name}"
    cache_path = _materialized_pdf_asset_cache_dir() / f"{hashlib.sha256(cache_key.encode('utf-8')).hexdigest()}{suffix}"
    if cache_path.exists():
        return cache_path

    backend = _get_storage_backend()
    with tempfile.NamedTemporaryFile(
        dir=_materialized_pdf_asset_cache_dir(),
        prefix="materialized-",
        suffix=suffix,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)

    try:
        backend.download_file(
            object_key=object_key,
            local_path=temp_path,
        )
        temp_path.replace(cache_path)
        return cache_path
    except Exception as exc:
        logger.debug("Failed to materialize object-storage PDF asset %s: %s", object_key, exc)
        return None
    finally:
        temp_path.unlink(missing_ok=True)


def _pdf_page_meaningful_text_units(page: Any) -> int:
    try:
        extracted = str(page.extract_text() or "")
    except Exception:
        extracted = ""
    return _pdf_text_meaningful_units(extracted)


def _pdf_text_meaningful_units(text: Optional[str]) -> int:
    extracted = str(text or "")
    if not extracted:
        return 0
    return len(re.findall(r"[A-Za-z\u4e00-\u9fff]", extracted))


def _pdf_page_content_bytes(page: Any) -> int:
    try:
        contents = page.get_contents()
        if isinstance(contents, list):
            return sum(len(content.get_data()) for content in contents if content is not None)
        if contents is None:
            return 0
        return len(contents.get_data())
    except Exception:
        return 0


def _count_leading_blank_pdf_pages(reader: Any) -> int:
    total_pages = len(getattr(reader, "pages", []))
    trim_count = 0
    while trim_count + 1 < total_pages:
        current_page = reader.pages[trim_count]
        next_page = reader.pages[trim_count + 1]
        current_text_units = _pdf_page_meaningful_text_units(current_page)
        next_text_units = _pdf_page_meaningful_text_units(next_page)
        current_content_bytes = _pdf_page_content_bytes(current_page)
        if (
            current_text_units < _PDF_DELIVERY_MEANINGFUL_TEXT_THRESHOLD
            and current_content_bytes < _PDF_DELIVERY_BLANK_PAGE_CONTENT_BYTES_THRESHOLD
            and next_text_units >= _PDF_DELIVERY_NEXT_PAGE_TEXT_THRESHOLD
        ):
            trim_count += 1
            continue
        break
    return trim_count


def _pdfinfo_page_count(pdf_path: Path) -> int:
    pdfinfo_binary = shutil.which("pdfinfo")
    if not pdfinfo_binary:
        return 0
    try:
        result = subprocess.run(
            [pdfinfo_binary, str(pdf_path)],
            check=True,
            capture_output=True,
            timeout=30,
            text=True,
        )
    except Exception:
        return 0

    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    if not match:
        return 0
    try:
        return max(int(match.group(1)), 0)
    except Exception:
        return 0


def _pdftotext_page_text(pdf_path: Path, page_number: int) -> str:
    pdftotext_binary = shutil.which("pdftotext")
    if not pdftotext_binary:
        return ""
    try:
        result = subprocess.run(
            [
                pdftotext_binary,
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                str(pdf_path),
                "-",
            ],
            check=True,
            capture_output=True,
            timeout=30,
            text=True,
        )
        return result.stdout
    except Exception:
        return ""


def _count_leading_blank_pdf_pages_with_pdftotext(pdf_path: Path) -> tuple[int, int]:
    total_pages = _pdfinfo_page_count(pdf_path)
    if total_pages <= 1:
        return 0, total_pages

    trim_count = 0
    while trim_count + 1 < total_pages:
        current_text = _pdftotext_page_text(pdf_path, trim_count + 1)
        next_text = _pdftotext_page_text(pdf_path, trim_count + 2)
        current_text_units = _pdf_text_meaningful_units(current_text)
        next_text_units = _pdf_text_meaningful_units(next_text)
        current_compact_length = len(re.sub(r"\s+", "", str(current_text or "")))
        if (
            current_text_units < _PDF_DELIVERY_MEANINGFUL_TEXT_THRESHOLD
            and current_compact_length < 16
            and next_text_units >= _PDF_DELIVERY_NEXT_PAGE_TEXT_THRESHOLD
        ):
            trim_count += 1
            continue
        break
    return trim_count, total_pages


def _write_trimmed_pdf_with_pypdf(
    *,
    reader: Any,
    trim_count: int,
    cache_path: Path,
) -> None:
    writer = PdfWriter()
    for page in reader.pages[trim_count:]:
        writer.add_page(page)
    metadata = getattr(reader, "metadata", None)
    if metadata:
        safe_metadata = {
            str(key): str(value)
            for key, value in dict(metadata).items()
            if key is not None and value is not None
        }
        if safe_metadata:
            writer.add_metadata(safe_metadata)

    with tempfile.NamedTemporaryFile(
        dir=_translated_pdf_delivery_cache_dir(),
        prefix="trimmed-",
        suffix=".pdf",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)

    try:
        with temp_path.open("wb") as output_handle:
            writer.write(output_handle)
        temp_path.replace(cache_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_trimmed_pdf_with_ghostscript(
    *,
    pdf_path: Path,
    trim_count: int,
    total_pages: int,
    cache_path: Path,
) -> bool:
    ghostscript = (
        shutil.which("gs")
        or shutil.which("gswin64c")
        or shutil.which("gswin32c")
    )
    if not ghostscript:
        return False

    with tempfile.NamedTemporaryFile(
        dir=_translated_pdf_delivery_cache_dir(),
        prefix="trimmed-gs-",
        suffix=".pdf",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)

    command = [
        ghostscript,
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=pdfwrite",
        f"-dFirstPage={trim_count + 1}",
        f"-dLastPage={total_pages}",
        f"-sOutputFile={temp_path}",
        str(pdf_path),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            timeout=120,
        )
        temp_path.replace(cache_path)
        return True
    except Exception as exc:
        logger.debug("Ghostscript PDF trim fallback failed for %s: %s", pdf_path, exc)
        return False
    finally:
        temp_path.unlink(missing_ok=True)


def _normalize_translated_pdf_leading_blank_pages(pdf_path: Path) -> Path:
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return pdf_path

    try:
        stat = pdf_path.stat()
    except Exception:
        return pdf_path

    cache_key = (
        f"{_PDF_DELIVERY_CACHE_VERSION}:{pdf_path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"
    )
    cache_path = _translated_pdf_delivery_cache_dir() / f"{hashlib.sha256(cache_key.encode('utf-8')).hexdigest()}.pdf"
    if cache_path.exists():
        return cache_path

    try:
        reader = None
        trim_count = 0
        total_pages = 0
        if PdfReader is not None:
            try:
                reader = PdfReader(str(pdf_path), strict=False)
                trim_count = _count_leading_blank_pdf_pages(reader)
                total_pages = len(reader.pages)
            except Exception:
                reader = None
                trim_count = 0
                total_pages = 0

        if reader is None:
            trim_count, total_pages = _count_leading_blank_pdf_pages_with_pdftotext(pdf_path)

        if trim_count <= 0 or total_pages <= 1:
            return pdf_path

        wrote_trimmed_pdf = False
        if reader is not None and PdfWriter is not None:
            try:
                _write_trimmed_pdf_with_pypdf(
                    reader=reader,
                    trim_count=trim_count,
                    cache_path=cache_path,
                )
                wrote_trimmed_pdf = True
            except Exception:
                wrote_trimmed_pdf = False

        if not wrote_trimmed_pdf:
            if not _write_trimmed_pdf_with_ghostscript(
                pdf_path=pdf_path,
                trim_count=trim_count,
                total_pages=total_pages,
                cache_path=cache_path,
            ):
                return pdf_path

        logger.info(
            "Trimmed %s leading blank PDF page(s) from translated asset %s",
            trim_count,
            pdf_path,
        )
        return cache_path
    except Exception as exc:
        logger.debug("Skipping translated PDF leading-page normalization for %s: %s", pdf_path, exc)
        return pdf_path


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


def invalidate_public_feed_cache() -> None:
    _get_public_feed_store().clear_cached_payloads()


def _public_feed_cache_key(*, sort: str, query: Optional[str], limit: Optional[int], offset: int) -> str:
    return _get_public_feed_store().response_key(sort=sort, limit=limit, offset=offset)


def _should_cache_public_feed(*, sort: str, query: Optional[str], limit: Optional[int], offset: int) -> bool:
    return (
        str(sort or "latest").strip().lower() in {"latest", "views", "likes"}
        and not _normalize_search_text(query)
        and limit is not None
        and int(limit) > 0
    )


def _get_cached_public_feed_payload(*, sort: str, query: Optional[str], limit: Optional[int], offset: int) -> Optional[Dict[str, Any]]:
    if not _should_cache_public_feed(sort=sort, query=query, limit=limit, offset=offset):
        return None
    cached = _get_public_feed_store().get_cached_payload(
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return dict(cached or {}) if cached else None


def _set_cached_public_feed_payload(
    *,
    sort: str,
    query: Optional[str],
    limit: Optional[int],
    offset: int,
    payload: Dict[str, Any],
) -> None:
    if not _should_cache_public_feed(sort=sort, query=query, limit=limit, offset=offset):
        return
    _get_public_feed_store().set_cached_payload(
        sort=sort,
        limit=limit,
        offset=offset,
        payload=dict(payload),
    )


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


def _preview_html_cache_key(preview_asset: Dict[str, Any]) -> Optional[str]:
    storage_backend = str(preview_asset.get("storage_backend") or "local_disk").strip().lower()
    if storage_backend == "object_storage":
        object_key = str(preview_asset.get("file_path") or "").strip()
        if not object_key:
            return None
        return "|".join(
            [
                "object_storage",
                object_key,
                str(preview_asset.get("id") or ""),
                str(preview_asset.get("created_at") or ""),
            ]
        )

    preview_path = _resolve_storage_path(preview_asset.get("file_path") or "")
    return _preview_payload_cache_key(preview_path, preview_asset)


def _read_preview_html_from_asset(preview_asset: Dict[str, Any]) -> Optional[str]:
    storage_backend = str(preview_asset.get("storage_backend") or "local_disk").strip().lower()
    cache_key = _preview_html_cache_key(preview_asset)
    if cache_key:
        cached_html = _preview_html_cache.get(cache_key)
        if cached_html is not None:
            return cached_html

    try:
        if storage_backend == "object_storage":
            object_key = str(preview_asset.get("file_path") or "").strip()
            if not object_key:
                return None
            html_content = _get_storage_backend().read_text(
                ref=StoredObjectRef(
                    storage_backend="object_storage",
                    object_key=object_key,
                    content_type=preview_asset.get("mime_type"),
                ),
                encoding="utf-8",
            )
        else:
            preview_path = _resolve_storage_path(preview_asset.get("file_path") or "")
            if not preview_path.exists():
                return None
            html_content = preview_path.read_text(encoding="utf-8")
    except Exception:
        return None

    if cache_key:
        _preview_html_cache[cache_key] = html_content
    return html_content


def _load_preview_payload(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    preview_asset: Dict[str, Any],
    allow_untranslated_zh: bool = False,
    allow_stale_reader: bool = False,
) -> Optional[Dict[str, Any]]:
    cache_key = _preview_html_cache_key(preview_asset)

    if cache_key:
        cached_payload = _preview_payload_cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    html_content = _read_preview_html_from_asset(preview_asset)
    if html_content is None:
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


def _build_preview_bootstrap_payload(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    preview_asset: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    preview_payload = _build_preview_payload(
        paper_id=paper_id,
        paper=paper,
        preview_asset=preview_asset,
    )
    if not preview_payload:
        return None
    return {
        "paper_id": paper_id,
        "task_id": preview_payload.get("task_id"),
        "asset": preview_payload.get("asset"),
        "generated_at": preview_payload.get("generated_at"),
        "fetch_url": f"/api/papers/{paper_id}/preview",
    }


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
    if asset_type == "source_pdf":
        return paper_root / "source_pdf" / safe_name
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
    archive_path = archive_root / f"{task_id or 'shared'}-{uuid4().hex[:8]}.zip"
    base_dir = source_path.name
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_path.rglob("*")):
            if not file_path.is_file():
                continue
            archive_name = (Path(base_dir) / file_path.relative_to(source_path)).as_posix()
            info = zipfile.ZipInfo(archive_name)
            try:
                date_time = time.localtime(file_path.stat().st_mtime)[:6]
            except OSError:
                date_time = (1980, 1, 1, 0, 0, 0)
            info.date_time = max(date_time, (1980, 1, 1, 0, 0, 0))
            with file_path.open("rb") as handle:
                archive.writestr(info, handle.read(), compress_type=zipfile.ZIP_DEFLATED)
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
            resolved_name = Path(source_name or f"{local_path.name}.zip").name or f"{asset_type}.zip"
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
        resolved_name = Path(source_name or f"{local_path.name}.zip").name or f"{asset_type}.zip"
        resolved_type = content_type or "application/zip"
        destination = _community_asset_destination(
            paper_id=paper_id,
            task_id=task_id,
            asset_type=asset_type,
            source_name=resolved_name,
        )

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
        "arxiv_published_at, "
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
        and str(paper.get("community_status") or "").strip()
        in {COMMUNITY_STATUS_OFFICIAL, COMMUNITY_STATUS_USER_FALLBACK}
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
        inserted = await _run_local_repo(lambda: repository.insert_paper(normalized_payload))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to insert paper into local repository: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create paper") from exc
    invalidate_public_feed_cache()
    return inserted


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
    invalidate_public_feed_cache()
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
    materialized_cleanup: Optional[Path] = None
    if not resolved_source.exists():
        materialized_source = _materialize_task_directory_for_asset_recovery(
            str(source_path),
            task_id=task_id,
            kind="source",
        )
        if not materialized_source or not materialized_source.exists():
            return None
        resolved_source = materialized_source
        materialized_cleanup = materialized_source
    source_path_name = Path(str(source_path)).name or resolved_source.name
    stored_ref, stored_name = _persist_retained_artifact(
        local_path=resolved_source,
        paper_id=paper_id,
        task_id=task_id,
        asset_type="source_archive",
        source_name=source_path_name if resolved_source.is_file() else f"{source_path_name}.zip",
        content_type=(
            mimetypes.guess_type(resolved_source.name)[0] or "application/octet-stream"
            if resolved_source.is_file()
            else None
        ),
    )
    asset = await _upsert_latest_asset(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="source_archive",
        file_path=stored_ref.object_key,
        file_name=stored_name,
        mime_type=stored_ref.content_type,
        storage_backend=stored_ref.storage_backend,
    )
    if materialized_cleanup and stored_ref.storage_backend != "local_disk":
        if task_id:
            clear_cached_runtime_artifacts(task_id, [materialized_cleanup])
        elif materialized_cleanup.exists():
            shutil.rmtree(materialized_cleanup, ignore_errors=True)
    return asset


def _source_pdf_filename(arxiv_id: str) -> str:
    normalized = str(arxiv_id or "").strip()
    safe_stem = re.sub(r"[^0-9A-Za-z._-]+", "_", normalized).strip("._-")
    return f"{safe_stem or 'source'}.pdf"


def _source_pdf_download_cache_dir() -> Path:
    cache_dir = Path(settings.storage_temp_dir) / "source_pdf_downloads"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _validate_source_pdf_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise ValueError("Downloaded source PDF is missing")
    if path.stat().st_size <= 0:
        raise ValueError("Downloaded source PDF is empty")
    with path.open("rb") as handle:
        header = handle.read(8)
    if not header.startswith(b"%PDF"):
        raise ValueError("Downloaded source PDF does not look like a PDF")


def _download_arxiv_source_pdf_to_temp(arxiv_id: str) -> Path:
    normalized_arxiv_id = str(arxiv_id or "").strip()
    if not normalized_arxiv_id:
        raise ValueError("arxiv_id is required")

    with tempfile.NamedTemporaryFile(
        dir=_source_pdf_download_cache_dir(),
        prefix="source-pdf-",
        suffix=".pdf",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)

    url = (
        arxiv_raw_cache.build_pdf_download_url(
            normalized_arxiv_id,
            filename=_source_pdf_filename(normalized_arxiv_id),
            inline=True,
        )
        or f"https://arxiv.org/pdf/{normalized_arxiv_id}"
    )
    try:
        with requests.get(
            url,
            stream=True,
            timeout=(10, 120),
            headers={"User-Agent": "LaTeXTrans-SourcePDF/1.0"},
        ) as response:
            response.raise_for_status()
            with temp_path.open("wb") as target:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        target.write(chunk)
        _validate_source_pdf_file(temp_path)
        return temp_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


async def persist_arxiv_source_pdf_asset(
    *,
    paper_id: str,
    task_id: Optional[str],
    arxiv_id: str,
) -> Dict[str, Any]:
    normalized_paper_id = str(paper_id or "").strip()
    normalized_arxiv_id = _normalize_arxiv_identifier(arxiv_id) or str(arxiv_id or "").strip()
    if not normalized_paper_id:
        raise ValueError("paper_id is required")
    if not normalized_arxiv_id:
        raise ValueError("arxiv_id is required")

    asset_map = await _fetch_asset_map_for_paper(paper_id=normalized_paper_id)
    existing_asset = asset_map.get("source_pdf")
    if existing_asset and str(existing_asset.get("file_path") or "").strip():
        return existing_asset

    if arxiv_raw_cache.is_enabled():
        source_name = _source_pdf_filename(normalized_arxiv_id)
        return await _upsert_latest_asset(
            paper_id=normalized_paper_id,
            task_id=task_id,
            asset_type="source_pdf",
            file_path=arxiv_raw_cache.raw_pdf_object_key(normalized_arxiv_id),
            file_name=source_name,
            mime_type="application/pdf",
            storage_backend="object_storage",
        )

    local_pdf = await asyncio.to_thread(_download_arxiv_source_pdf_to_temp, normalized_arxiv_id)
    try:
        source_name = _source_pdf_filename(normalized_arxiv_id)
        stored_ref, stored_name = _persist_retained_artifact(
            local_path=local_pdf,
            paper_id=normalized_paper_id,
            task_id=task_id,
            asset_type="source_pdf",
            source_name=source_name,
            content_type="application/pdf",
        )
        return await _upsert_latest_asset(
            paper_id=normalized_paper_id,
            task_id=task_id,
            asset_type="source_pdf",
            file_path=stored_ref.object_key,
            file_name=stored_name,
            mime_type=stored_ref.content_type or "application/pdf",
            storage_backend=stored_ref.storage_backend,
        )
    finally:
        local_pdf.unlink(missing_ok=True)


async def _persist_source_pdf_for_paper_if_arxiv(
    *,
    paper_id: str,
    task_id: Optional[str],
    paper: Optional[Dict[str, Any]],
    task: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    arxiv_id = (
        _normalize_arxiv_identifier((paper or {}).get("arxiv_id"))
        or _normalize_arxiv_identifier((task or {}).get("arxiv_id"))
    )
    if not arxiv_id:
        return None
    try:
        return await persist_arxiv_source_pdf_asset(
            paper_id=paper_id,
            task_id=task_id,
            arxiv_id=arxiv_id,
        )
    except Exception as exc:
        logger.warning(
            "Source PDF persistence skipped for paper %s arXiv %s: %s",
            paper_id,
            arxiv_id,
            exc,
            exc_info=True,
        )
        return None


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


def _compact_abstract_for_feed(value: Optional[str]) -> Optional[str]:
    text = _normalize_metadata_text(value)
    if not text:
        return None
    if len(text) <= COMMUNITY_FEED_ABSTRACT_MAX_CHARS:
        return text
    return text[: COMMUNITY_FEED_ABSTRACT_MAX_CHARS - 3].rstrip() + "..."


def _compact_asset_map_for_feed(
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> Optional[Dict[str, Dict[str, Any]]]:
    public_map = _public_asset_map(asset_map)
    if not public_map:
        return None
    compact_map = {
        asset_type: asset
        for asset_type, asset in public_map.items()
        if asset_type in COMMUNITY_FEED_PUBLIC_ASSET_TYPES
    }
    return compact_map or None


def _read_preview_asset_html(asset: Optional[Dict[str, Any]]) -> Optional[str]:
    if not asset:
        return None

    file_path = str(asset.get("file_path") or "").strip()
    if not file_path:
        return None

    resolved_path = _resolve_storage_path(file_path)
    if not resolved_path.exists() or not resolved_path.is_file():
        return None
    if resolved_path.suffix.lower() not in {".html", ".htm"}:
        return None

    try:
        return resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return resolved_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None
    except Exception:
        return None


def _extract_external_href_from_html(
    html_content: Optional[str],
    *,
    host_fragment: str,
) -> Optional[str]:
    normalized_host = str(host_fragment or "").strip().lower()
    if not html_content or not normalized_host:
        return None

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception:
        soup = None

    href_candidates: List[str] = []
    if soup is not None:
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            if href:
                href_candidates.append(href)

    href_candidates.extend(
        match
        for match in re.findall(r"https?://[^\s\"'<>]+", html_content)
        if match
    )

    seen: set[str] = set()
    for href in href_candidates:
        normalized_href = str(href or "").strip()
        lowered_href = normalized_href.lower()
        if not normalized_href or normalized_href in seen:
            continue
        seen.add(normalized_href)
        if not lowered_href.startswith(("http://", "https://")):
            continue
        if normalized_host not in lowered_href:
            continue
        return normalized_href

    return None


def _resolve_external_links_for_feed(
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> Dict[str, Optional[str]]:
    arxiv_id = str(paper.get("arxiv_id") or "").strip()
    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None

    preview_asset = (asset_map or {}).get("preview_html")
    cache_key = "|".join(
        [
            str(preview_asset.get("id") or "").strip() if preview_asset else "",
            str(preview_asset.get("file_path") or "").strip() if preview_asset else "",
            arxiv_url or "",
        ]
    )
    cached = _PUBLIC_EXTERNAL_LINK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    preview_html = _read_preview_asset_html(preview_asset)
    resolved = {
        "arxiv_url": arxiv_url,
        "github_url": _extract_external_href_from_html(preview_html, host_fragment="github.com"),
    }
    _PUBLIC_EXTERNAL_LINK_CACHE[cache_key] = resolved
    return resolved


def _paper_feed_summary(
    paper: Dict[str, Any],
    *,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    summary = _paper_summary(paper, asset_map=asset_map)
    external_links = _resolve_external_links_for_feed(paper, asset_map)
    summary["abstract_raw"] = _compact_abstract_for_feed(summary.get("abstract_raw"))
    summary["abstract_translated"] = _compact_abstract_for_feed(summary.get("abstract_translated"))
    summary["assets"] = _compact_asset_map_for_feed(asset_map)
    summary["arxiv_url"] = external_links.get("arxiv_url")
    summary["github_url"] = external_links.get("github_url")
    return summary


async def _fetch_viewer_state(
    paper_ids: List[str],
    *,
    user_id: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    default_state = {
        paper_id: {"liked": False, "favorited": False, "favorite_folder_count": 0}
        for paper_id in paper_ids
    }
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


async def _attach_viewer_state_to_feed_payload(
    payload: Dict[str, Any],
    *,
    viewer_user_id: Optional[str],
) -> Dict[str, Any]:
    items = list(payload.get("items") or [])
    if not items:
        return dict(payload)

    paper_ids = [str(item.get("id") or "").strip() for item in items if str(item.get("id") or "").strip()]
    viewer_states = await _fetch_viewer_state(paper_ids, user_id=viewer_user_id) if paper_ids else {}

    enriched_items: list[Dict[str, Any]] = []
    for item in items:
        normalized_item = dict(item)
        paper_id = str(item.get("id") or "").strip()
        if paper_id and viewer_states:
            normalized_item["viewer_state"] = viewer_states.get(
                paper_id,
                {"liked": False, "favorited": False, "favorite_folder_count": 0},
            )
        enriched_items.append(normalized_item)

    return {**payload, "items": enriched_items}


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


async def _store_canonical_translated_pdf_asset(
    *,
    paper_id: str,
    task_id: Optional[str],
    pdf_path: Path,
    source_name: Optional[str],
) -> tuple[Dict[str, Any], StoredObjectRef, Path]:
    delivery_pdf_path = _normalize_translated_pdf_leading_blank_pages(pdf_path)
    stored_ref, stored_name = _persist_retained_artifact(
        local_path=delivery_pdf_path,
        paper_id=paper_id,
        task_id=task_id,
        asset_type="translated_pdf",
        source_name=source_name or pdf_path.name,
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
    await _update_paper(
        paper_id,
        {
            "trans_latest_asset_pdf_id": asset.get("id"),
            "updated_at": _utc_now_iso(),
        },
    )
    return asset, stored_ref, delivery_pdf_path


async def _resolve_translated_pdf_asset(
    *,
    paper_id: str,
    task_id: str,
) -> Optional[Dict[str, Any]]:
    task = task_manager.get_task(task_id) if task_id else None
    for output_dir in _candidate_output_directories_for_task(task_id):
        pdf_path = download_route._find_translated_pdf(output_dir)
        if not pdf_path or not pdf_path.exists():
            continue
        asset, stored_ref, _delivery_pdf_path = await _store_canonical_translated_pdf_asset(
            paper_id=paper_id,
            task_id=task_id,
            pdf_path=pdf_path,
            source_name=pdf_path.name,
        )
        if stored_ref.storage_backend != "local_disk":
            clear_cached_runtime_artifacts(task_id, [pdf_path])
        return asset

    output_path = str((task or {}).get("output_path") or "").strip()
    if output_path:
        try:
            recovered_pdf = task_artifact_storage.materialize_task_output_asset(
                output_path,
                "translated_pdf",
                destination_dir=Path(settings.storage_temp_dir) / "task_output_asset_recovery" / task_id / "translated_pdf",
                force=True,
            )
        except Exception:
            recovered_pdf = None

        if recovered_pdf and recovered_pdf.exists():
            asset, stored_ref, _delivery_pdf_path = await _store_canonical_translated_pdf_asset(
                paper_id=paper_id,
                task_id=task_id,
                pdf_path=recovered_pdf,
                source_name=recovered_pdf.name,
            )
            if stored_ref.storage_backend != "local_disk":
                clear_cached_runtime_artifacts(task_id, [recovered_pdf])
            return asset

    return None


def _collect_quality_inputs_for_task(task_id: str) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "preview_html": None,
        "pdf_text": None,
        "output_text": None,
        "sections": [],
    }
    for output_dir in _candidate_output_directories_for_task(task_id):
        inputs = collect_quality_inputs_from_directory(output_dir)
        for key in ("preview_html", "pdf_text", "output_text"):
            if not merged.get(key) and inputs.get(key):
                merged[key] = inputs[key]
        if not merged["sections"] and inputs.get("sections"):
            merged["sections"] = inputs["sections"]
    return merged


def _quality_diagnostics_dir_for_task(task: Dict[str, Any], task_id: str) -> Optional[Path]:
    output_path = str((task or {}).get("output_path") or "").strip()
    if output_path:
        resolved = _resolve_storage_path(output_path)
        if resolved.exists() and resolved.is_dir():
            return resolved
    for output_dir in _candidate_output_directories_for_task(task_id):
        return output_dir
    return None


def _run_community_publish_quality_gate(*, task_id: str, task: Dict[str, Any]) -> QualityGateResult:
    inputs = _collect_quality_inputs_for_task(task_id)
    return evaluate_community_translation_quality(
        preview_html=inputs.get("preview_html"),
        pdf_text=inputs.get("pdf_text"),
        output_text=inputs.get("output_text"),
        sections=inputs.get("sections") or [],
        task=task,
    )


def _write_community_publish_quality_diagnostics(
    *,
    task_id: str,
    task: Dict[str, Any],
    result: QualityGateResult,
) -> Optional[Path]:
    diagnostics_dir = _quality_diagnostics_dir_for_task(task, task_id)
    if diagnostics_dir is None:
        return None
    try:
        return write_quality_diagnostics(diagnostics_dir, result)
    except Exception as exc:
        logger.warning("Failed to write community quality diagnostics for task %s: %s", task_id, exc)
        return None


async def backfill_translated_pdf_delivery_asset(*, paper_id: str) -> Dict[str, Any]:
    paper = await _fetch_paper_by_id(paper_id)
    if not _is_public_community_paper(paper):
        return {"paper_id": paper_id, "status": "skipped", "reason": "paper_unavailable"}

    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = asset_map.get("translated_pdf")
    if not translated_asset:
        return {"paper_id": paper_id, "status": "skipped", "reason": "translated_asset_missing"}

    resolved_pdf: Optional[Path] = None
    if translated_asset.get("storage_backend") == "object_storage":
        resolved_pdf = _materialize_object_storage_pdf_asset(translated_asset)
    else:
        candidate = _resolve_storage_path(translated_asset.get("file_path") or "")
        if candidate.exists() and candidate.is_file():
            resolved_pdf = candidate

    if resolved_pdf is None or not resolved_pdf.exists():
        return {"paper_id": paper_id, "status": "skipped", "reason": "translated_asset_unrecoverable"}

    upgraded_asset, _stored_ref, canonical_pdf_path = await _store_canonical_translated_pdf_asset(
        paper_id=paper_id,
        task_id=str(translated_asset.get("task_id") or "").strip() or None,
        pdf_path=resolved_pdf,
        source_name=str(translated_asset.get("file_name") or resolved_pdf.name),
    )
    return {
        "paper_id": paper_id,
        "status": "upgraded",
        "asset_id": upgraded_asset.get("id"),
        "canonical_file_path": str(canonical_pdf_path),
    }


async def backfill_translated_pdf_delivery_assets(
    *,
    paper_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    normalized_ids = [str(paper_id or "").strip() for paper_id in (paper_ids or []) if str(paper_id or "").strip()]
    if normalized_ids:
        target_paper_ids = normalized_ids
    else:
        repository = get_community_paper_repository()
        try:
            rows = await _run_local_repo(lambda: repository.list_public_papers())
        except DatabaseUnavailableError as exc:
            raise HTTPException(status_code=503, detail="Local database unavailable") from exc
        except Exception as exc:
            logger.warning("Failed to list public papers for translated PDF backfill: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to list public papers") from exc

        target_paper_ids = [str(row.get("id") or "").strip() for row in rows if str(row.get("id") or "").strip()]

    if limit is not None and limit >= 0:
        target_paper_ids = target_paper_ids[:limit]

    results: List[Dict[str, Any]] = []
    for target_paper_id in target_paper_ids:
        results.append(await backfill_translated_pdf_delivery_asset(paper_id=target_paper_id))

    return {
        "requested": len(target_paper_ids),
        "upgraded": sum(1 for row in results if row.get("status") == "upgraded"),
        "skipped": sum(1 for row in results if row.get("status") != "upgraded"),
        "results": results,
    }


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
    paper_id: str,
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
            "url": f"/api/papers/{paper_id}/source-pdf",
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


def _translated_preview_reader_resource(*, paper_id: str, preview_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "kind": "preview_html",
        "html_content": preview_payload.get("html_content"),
        "url": preview_payload.get("fetch_url") or f"/api/papers/{paper_id}/preview",
        "asset_id": ((preview_payload.get("asset") or {}).get("id")),
        "anchors": [],
    }


def _resolve_object_storage_signed_url(
    asset: Dict[str, Any],
    *,
    expires_in: int,
    response_params: Optional[Dict[str, str]] = None,
) -> str:
    direct_url = str(asset.get("signed_url") or "").strip()
    if direct_url:
        return direct_url

    file_path = str(asset.get("file_path") or "").strip()
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return file_path

    backend = _get_storage_backend()
    signed_url = backend.build_download_url(
        object_key=file_path,
        expires_in=expires_in,
        params=response_params,
    )
    return str(signed_url or "").strip()


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
        paper_id=paper_id,
        source_html_content=source_html_content,
        source_anchors=source_anchors,
    )
    translated_resource: Optional[Dict[str, Any]] = None
    if preview_payload:
        translated_resource = _translated_preview_reader_resource(
            paper_id=paper_id,
            preview_payload=preview_payload,
        )
        translated_resource["anchors"] = translated_anchors
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
        clear_cached_runtime_artifacts(task_id, [preview_path, target_dir])

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
    effective_advanced_config = translate_route.normalize_origin_cli_parity_advanced_config(
        request.advanced_config
    )

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
        translation_mode=effective_advanced_config.translation_mode,
        compile_strategy=effective_advanced_config.compile_strategy,
        formatting=effective_advanced_config.formatting,
    )
    task_manager.update_task(
        task_id=task_id,
        source_language=request.source_language,
        target_language=request.target_language,
        advanced_config=effective_advanced_config.model_dump(),
        config_hash=config_hash,
        user_id=context["user_id"],
    )
    task_manager.persist_task_if_needed(task_id)

    llm_config = await translate_route.build_llm_config_async(effective_advanced_config, context["user_id"])
    pool_routing_key = str(llm_config.get("pool_routing_key") or "").strip()
    if pool_routing_key:
        token_hash = hashlib.md5(pool_routing_key.encode()).hexdigest()
    else:
        token_hash = hashlib.md5((llm_config.get("api_key") or "").encode()).hexdigest()
    asyncio.create_task(
        translate_route._download_and_enqueue(
            task_id=task_id,
            arxiv_id=arxiv_id,
            user_id=context["user_id"],
            source_language=request.source_language,
            target_language=request.target_language,
            advanced_config=effective_advanced_config,
            tq=get_task_queue(),
            token_hash=token_hash,
            llm_capacity=translate_route.resolve_llm_task_capacity(llm_config),
            lane="backfill",
        )
    )
    return {"task_id": task_id, "status": "queued"}


def _translated_rank(paper: Dict[str, Any]) -> int:
    return 0 if paper.get("trans_status") == "completed" else 1


def _serialize_timestamp_value(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def _normalize_arxiv_published_at(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except Exception:
        normalized = _normalize_metadata_text(value)
        return normalized or None


def _primary_published_timestamp_value(paper: Dict[str, Any]) -> Any:
    return (
        paper.get("arxiv_published_at")
        or paper.get("official_published_at")
        or paper.get("created_at")
    )


def _timestamp_key(value: Any) -> float:
    if not value:
        return 0.0
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _views_tuple(paper: Dict[str, Any]) -> Any:
    return (
        -(paper.get("view_count") or 0),
        -_timestamp_key(_primary_published_timestamp_value(paper)),
        -_timestamp_key(paper.get("created_at")),
    )


def _latest_tuple(paper: Dict[str, Any]) -> Any:
    return (
        -_timestamp_key(_primary_published_timestamp_value(paper)),
        -_timestamp_key(paper.get("created_at")),
    )


def _likes_tuple(paper: Dict[str, Any]) -> Any:
    return (
        -(paper.get("like_count") or 0),
        -_timestamp_key(_primary_published_timestamp_value(paper)),
        -_timestamp_key(paper.get("created_at")),
    )


def _latest_rank_score(paper: Dict[str, Any]) -> float:
    return float(int(_timestamp_key(_primary_published_timestamp_value(paper)) or 0))


def _count_rank_score(*, count: Any, paper: Dict[str, Any]) -> float:
    normalized_count = int(count or 0)
    return float((normalized_count * _PUBLIC_FEED_SCORE_FACTOR) + int(_latest_rank_score(paper)))


def _paper_rank_score(paper: Dict[str, Any], sort: str) -> float:
    normalized_sort = str(sort or "latest").strip().lower()
    if normalized_sort == "views":
        return _count_rank_score(count=paper.get("view_count"), paper=paper)
    if normalized_sort == "likes":
        return _count_rank_score(count=paper.get("like_count"), paper=paper)
    return _latest_rank_score(paper)


async def _hydrate_public_feed_papers_from_ids(paper_ids: List[str]) -> List[Dict[str, Any]]:
    if not paper_ids:
        return []
    repository = get_community_paper_repository()
    fetched = await asyncio.gather(
        *[
            _run_local_repo(lambda current_paper_id=paper_id: repository.get_paper_by_id(current_paper_id))
            for paper_id in paper_ids
        ]
    )
    normalized: Dict[str, Dict[str, Any]] = {}
    for paper in fetched:
        if not paper:
            continue
        resolved = _apply_runtime_paper_override(paper) or paper
        paper_id = str(resolved.get("id") or "").strip()
        if paper_id and _is_public_community_paper(resolved):
            normalized[paper_id] = resolved
    return [normalized[paper_id] for paper_id in paper_ids if paper_id in normalized]


async def _rebuild_public_feed_indexes_from_db() -> bool:
    store = _get_public_feed_store()
    if not store.available:
        return False
    if not store.acquire_rebuild_lock():
        return False
    repository = get_community_paper_repository()
    try:
        papers = await _run_local_repo(repository.list_public_papers)
    except Exception as exc:
        logger.warning("Failed to rebuild shared public feed indexes: %s", exc)
        return False
    public_papers = [_apply_runtime_paper_override(paper) or paper for paper in papers if _is_public_community_paper(paper)]
    for sort in ("latest", "views", "likes"):
        store.replace_index(
            sort=sort,
            mapping={
                str(paper.get("id") or "").strip(): _paper_rank_score(paper, sort)
                for paper in public_papers
                if str(paper.get("id") or "").strip()
            },
        )
    store.clear_cached_payloads()
    return True


async def rebuild_public_feed_indexes_if_enabled() -> bool:
    interval_seconds = float(getattr(settings, "community_feed_rebuild_interval_seconds", 300.0) or 0.0)
    if interval_seconds <= 0:
        return False
    return await _rebuild_public_feed_indexes_from_db()


async def _list_public_papers_from_shared_feed_store(
    *,
    sort: str,
    limit: Optional[int],
    offset: int,
) -> Optional[Dict[str, Any]]:
    if not _should_cache_public_feed(sort=sort, query=None, limit=limit, offset=offset):
        return None
    store = _get_public_feed_store()
    if not store.available:
        return None
    cached = store.get_cached_payload(sort=sort, limit=limit, offset=offset)
    if cached:
        return cached
    total = store.count_ranked_ids(sort=sort)
    if total <= 0:
        rebuilt = await _rebuild_public_feed_indexes_from_db()
        if not rebuilt:
            return None
        total = store.count_ranked_ids(sort=sort)
    if total <= 0:
        return None
    paper_ids = store.read_ranked_ids(sort=sort, offset=offset, limit=limit)
    if not paper_ids:
        return {
            "items": [],
            "total": total,
            "offset": max(0, int(offset or 0)),
            "limit": limit,
            "has_more": max(0, int(offset or 0)) < total,
            "next_offset": None,
            "source_mode": "redis",
        }
    papers = await _hydrate_public_feed_papers_from_ids(paper_ids)
    paper_ids = [str(paper.get("id") or "").strip() for paper in papers if str(paper.get("id") or "").strip()]
    asset_maps = await _fetch_asset_maps_for_papers(paper_ids) if paper_ids else {}
    items = [
        _paper_feed_summary(
            paper,
            asset_map=asset_maps.get(paper["id"]),
        )
        for paper in papers
    ]
    normalized_offset = max(0, int(offset or 0))
    has_more = (normalized_offset + len(items)) < total
    payload = {
        "items": items,
        "total": total,
        "offset": normalized_offset,
        "limit": limit,
        "has_more": has_more,
        "next_offset": (normalized_offset + len(items)) if has_more else None,
        "source_mode": "redis",
    }
    store.set_cached_payload(sort=sort, limit=limit, offset=offset, payload=payload)
    return payload


async def _refresh_public_feed_rankings_for_paper(
    *,
    paper_id: str,
    like_delta: Optional[int] = None,
) -> None:
    normalized_paper_id = str(paper_id or "").strip()
    if not normalized_paper_id:
        return
    store = _get_public_feed_store()
    if not store.available:
        return
    paper = await _fetch_paper_by_id(normalized_paper_id)
    if not paper or not _is_public_community_paper(paper):
        store.remove_ranked_paper(paper_id=normalized_paper_id)
        store.clear_cached_payloads()
        return
    for sort in ("latest", "views", "likes"):
        score = _paper_rank_score(paper, sort)
        if sort == "likes" and like_delta is not None:
            # Keep the hot path narrow while still correcting drift with the canonical score write.
            store.increment_ranked_paper(sort=sort, paper_id=normalized_paper_id, delta=float(like_delta * _PUBLIC_FEED_SCORE_FACTOR))
        store.upsert_ranked_paper(sort=sort, paper_id=normalized_paper_id, score=score)
    store.clear_cached_payloads()


def _sort_papers(papers: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
    key_map = {
        "latest": _latest_tuple,
        "views": _views_tuple,
        "likes": _likes_tuple,
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
    arxiv_published_at: Optional[str] = None,
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
        "arxiv_published_at": arxiv_published_at,
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
    defer_runtime_cleanup: bool = False,
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
        source_pdf_asset = await _persist_source_pdf_for_paper_if_arxiv(
            paper_id=paper_id,
            task_id=task_id,
            paper=paper,
            task=task,
        )
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
        if (
            selected_asset
            and selected_asset.get("storage_backend") == "object_storage"
            and not defer_runtime_cleanup
        ):
            clear_cached_runtime_artifacts(
                task_id,
                _candidate_runtime_cache_paths_for_task(task_id),
            )
        _schedule_public_thumbnail_warmup(
            paper_id=paper_id,
            translated_asset=translated_asset,
        )
        return {
            "done": True,
            "status": "completed",
            "paper": paper,
            "translated_asset": translated_asset,
            "preview_asset": preview_asset,
            "source_pdf_asset": source_pdf_asset,
            "selected_asset": selected_asset,
            "needs_runtime_cleanup": bool(
                defer_runtime_cleanup
                and selected_asset
                and selected_asset.get("storage_backend") == "object_storage"
            ),
        }

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
        return {
            "done": True,
            "status": "failed",
            "paper": paper,
            "translated_asset": translated_asset,
            "preview_asset": preview_asset,
            "selected_asset": selected_asset,
        }

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
                arxiv_published_at=None,
                official_published_at=_utc_now_iso() if promote_to_official else None,
            )
        )

    sync_result = await _sync_task_assets_for_paper(
        paper_id=paper["id"],
        task_id=task_id,
        promote_to_official=promote_to_official,
        paper=paper,
    )
    if sync_result.get("status") == "quality_gate_failed":
        return {
            "paper": sync_result.get("paper") or paper,
            "published": False,
            "quality_gate": sync_result.get("quality_gate"),
        }
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
    external_links = _resolve_external_links_for_feed(paper, asset_map)
    return {
        "id": paper.get("id"),
        "source": paper.get("source"),
        "arxiv_id": paper.get("arxiv_id"),
        "arxiv_url": external_links.get("arxiv_url"),
        "github_url": external_links.get("github_url"),
        "title": paper.get("title"),
        "authors": paper.get("authors") or [],
        "categories": paper.get("categories") or [],
        "abstract_raw": paper.get("abstract_raw"),
        "abstract_translated": paper.get("abstract_translated"),
        "community_status": paper.get("community_status"),
        "trans_status": paper.get("trans_status"),
        "created_at": _serialize_timestamp_value(paper.get("created_at")),
        "arxiv_published_at": _serialize_timestamp_value(paper.get("arxiv_published_at")),
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
            arxiv_published_at=None,
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
                arxiv_published_at=metadata.get("arxiv_published_at"),
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


def _build_structured_insight_placeholder_maps(output_dir: Path) -> tuple[Dict[str, str], Dict[str, str]]:
    source_placeholder_map: Dict[str, str] = {}
    translated_placeholder_map: Dict[str, str] = {}
    for artifact_name in ("envs_map.json", "captions_map.json"):
        for item in _load_task_artifact_json(output_dir, artifact_name):
            placeholder = str(item.get("placeholder") or "").strip()
            if not placeholder:
                continue
            source_text = str(item.get("content") or item.get("trans_content") or "").strip()
            translated_text = str(item.get("trans_content") or item.get("content") or "").strip()
            if source_text:
                source_placeholder_map[placeholder] = source_text
            if translated_text:
                translated_placeholder_map[placeholder] = translated_text
    return source_placeholder_map, translated_placeholder_map


def _expand_structured_insight_placeholders(text: str, placeholder_map: Dict[str, str]) -> str:
    expanded = str(text or "")
    for placeholder, replacement in placeholder_map.items():
        expanded = expanded.replace(placeholder, replacement)
    return expanded


def _normalize_structured_insight_text(text: str) -> Optional[str]:
    try:
        plain = _normalize_multiline_text(extract_text_from_tex(str(text or "")))
    except Exception as exc:
        logger.warning("Failed to extract plain text for structured insight normalization: %s", exc)
        plain = None
    if plain:
        return plain
    return _normalize_multiline_text(text)


def _looks_like_latex_preamble_for_structured_insight(*values: str) -> bool:
    raw = "\n".join(str(value or "") for value in values if str(value or "").strip())
    if not raw:
        return False
    head = raw[:3000].lower()
    if "\\documentclass" in head or "\\begin{document}" in head:
        return True
    preamble_markers = (
        "\\usepackage",
        "\\newcommand",
        "\\renewcommand",
        "placeholder_newcommand",
        "placeholder_usepackage",
    )
    return sum(1 for marker in preamble_markers if marker in head) >= 2


def _load_structured_insight_runtime_sections_from_dirs(output_dirs: List[Path]) -> List[Dict[str, Any]]:
    for output_dir in output_dirs:
        sections = _load_task_artifact_json(output_dir, "sections_map.json")
        if not sections:
            continue
        source_placeholder_map, translated_placeholder_map = _build_structured_insight_placeholder_maps(output_dir)
        normalized_sections: List[Dict[str, Any]] = []
        for index, section in enumerate(sections):
            translated = str(section.get("trans_content") or section.get("content") or "").strip()
            source = str(section.get("content") or section.get("trans_content") or "").strip()
            if not translated and not source:
                continue
            expanded_translated = _expand_structured_insight_placeholders(translated, translated_placeholder_map)
            expanded_source = _expand_structured_insight_placeholders(source, source_placeholder_map)
            normalized_translated = _normalize_structured_insight_text(expanded_translated)
            normalized_source = _normalize_structured_insight_text(expanded_source)
            if not normalized_translated and not normalized_source:
                continue
            title = _normalize_metadata_text(section.get("title"))
            if not title and _looks_like_latex_preamble_for_structured_insight(expanded_translated, expanded_source):
                continue
            normalized_sections.append(
                {
                    "index": index,
                    "section": str(section.get("section") or "").strip() or str(index + 1),
                    "title": title,
                    "content": normalized_translated or normalized_source,
                    "translated_content": normalized_translated or normalized_source or "",
                    "source_content": normalized_source or normalized_translated or "",
                    "raw_content": expanded_translated or expanded_source,
                }
            )
        if normalized_sections:
            return normalized_sections
    return []


def _load_structured_insight_runtime_sections(task_id: str) -> List[Dict[str, Any]]:
    sections = _load_structured_insight_runtime_sections_from_dirs(
        _candidate_output_directories_for_task(task_id, recover_missing=False)
    )
    if sections:
        return sections

    sections = _load_structured_insight_runtime_sections_from_dirs(
        _candidate_structured_insight_recovery_directories_for_task(task_id, force=True)
    )
    if sections:
        return sections
    return []


def _load_structured_insight_sections_from_preview_asset(
    preview_asset: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not preview_asset:
        return []

    html_content = _read_preview_html_from_asset(preview_asset)
    if not html_content:
        return []

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception:
        return []

    article = soup.select_one("article") or soup.body
    if article is None:
        return []

    candidate_sections = article.find_all("section", recursive=False)
    if not candidate_sections:
        candidate_sections = article.find_all("section")
    if not candidate_sections:
        candidate_sections = [article]

    normalized_sections: List[Dict[str, Any]] = []
    for index, section in enumerate(candidate_sections):
        heading = section.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        title = _normalize_metadata_text(heading.get_text(" ", strip=True) if heading else None)
        text_chunks: List[str] = []
        for block in section.find_all(["p", "li", "blockquote", "figcaption"]):
            text = _normalize_metadata_text(block.get_text(" ", strip=True))
            if not text:
                continue
            if title and text == title:
                continue
            text_chunks.append(text)
        content = _normalize_multiline_text("\n\n".join(text_chunks))
        if not content:
            continue
        normalized_sections.append(
            {
                "index": index,
                "section": str(index + 1),
                "title": title,
                "content": content,
                "translated_content": content,
                "source_content": content,
                "raw_content": content,
            }
        )

    return normalized_sections


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
    content_key: str = "content",
) -> str:
    chunks: List[str] = []
    total = 0
    for section in _dedupe_structured_insight_sections(sections):
        title = _normalize_metadata_text(section.get("title"))
        content = _normalize_metadata_text(section.get(content_key) or section.get("content"))
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


def _build_structured_insight_source_packet(
    sections: List[Dict[str, Any]],
    *,
    max_chars: int,
) -> Dict[str, str]:
    source_excerpt = _compose_structured_insight_excerpt(
        sections,
        max_chars=max_chars,
        content_key="source_content",
    )
    translated_excerpt = _compose_structured_insight_excerpt(
        sections,
        max_chars=max_chars,
        content_key="translated_content",
    )
    combined_parts = []
    if translated_excerpt:
        combined_parts.append(f"中文摘录：\n{translated_excerpt}")
    if source_excerpt:
        combined_parts.append(f"原文线索：\n{source_excerpt}")
    combined_excerpt = "\n\n".join(part for part in combined_parts if part).strip()
    return {
        "translated_excerpt": translated_excerpt,
        "source_excerpt": source_excerpt,
        "combined_excerpt": combined_excerpt or translated_excerpt or source_excerpt,
    }


def _normalize_structured_insight_source_packet(source: Any) -> Dict[str, str]:
    if isinstance(source, dict):
        translated_excerpt = _normalize_multiline_text(
            str(source.get("translated_excerpt") or source.get("content") or source.get("combined_excerpt") or "")
        ) or ""
        source_excerpt = _normalize_multiline_text(
            str(source.get("source_excerpt") or "")
        ) or ""
        combined_excerpt = _normalize_multiline_text(
            str(source.get("combined_excerpt") or "")
        ) or ""
        if not combined_excerpt:
            combined_parts = []
            if translated_excerpt:
                combined_parts.append(f"中文摘录：\n{translated_excerpt}")
            if source_excerpt:
                combined_parts.append(f"原文线索：\n{source_excerpt}")
            combined_excerpt = "\n\n".join(part for part in combined_parts if part).strip()
        return {
            "translated_excerpt": translated_excerpt,
            "source_excerpt": source_excerpt,
            "combined_excerpt": combined_excerpt or translated_excerpt or source_excerpt,
        }

    normalized = _normalize_multiline_text(str(source or "")) or ""
    return {
        "translated_excerpt": normalized,
        "source_excerpt": "",
        "combined_excerpt": normalized,
    }


def _prepare_structured_insight_source_packets(
    task_id: str,
    *,
    preview_asset: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, str]]:
    sections = _load_structured_insight_runtime_sections(task_id)
    if not sections and preview_asset:
        sections = _load_structured_insight_sections_from_preview_asset(preview_asset)
    if not sections:
        return {
            section_key: {
                "translated_excerpt": "",
                "source_excerpt": "",
                "combined_excerpt": "",
            }
            for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
        }

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
        "problem": _build_structured_insight_source_packet(
            problem_sections or by_index(0, min(2, total_sections)),
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "solution": _build_structured_insight_source_packet(
            solution_sections,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "innovation": _build_structured_insight_source_packet(
            innovation_sections,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "experiment": _build_structured_insight_source_packet(
            experiment_sections_with_anchor,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
        "future": _build_structured_insight_source_packet(
            future_sections,
            max_chars=STRUCTURED_INSIGHT_SOURCE_MAX_CHARS,
        ),
    }


def _prepare_structured_insight_sources(
    task_id: str,
    *,
    preview_asset: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    packets = _prepare_structured_insight_source_packets(
        task_id,
        preview_asset=preview_asset,
    )
    return {
        section_key: _normalize_structured_insight_source_packet(packet).get("combined_excerpt") or ""
        for section_key, packet in packets.items()
    }


def _normalize_structured_insight_section(section: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "section_key": str(section.get("section_key") or "").strip(),
        "content": _normalize_multiline_text(section.get("content")),
        "status": str(section.get("status") or STRUCTURED_INSIGHT_READY_STATUS).strip() or STRUCTURED_INSIGHT_READY_STATUS,
        "updated_at": section.get("updated_at") or _utc_now_iso(),
    }
    generation_mode = str(section.get("generation_mode") or "").strip()
    if generation_mode:
        normalized["generation_mode"] = generation_mode
    if "source_excerpt_present" in section:
        normalized["source_excerpt_present"] = bool(section.get("source_excerpt_present"))
    return normalized


def _truncate_debug_text(value: Any, limit: int = 500) -> str:
    text = _normalize_metadata_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _has_structured_insight_complete_ending(content: Optional[str]) -> bool:
    normalized = _normalize_metadata_text(content)
    if not normalized:
        return False
    stripped = normalized.rstrip()
    while stripped and stripped[-1] in STRUCTURED_INSIGHT_TRAILING_CLOSERS:
        stripped = stripped[:-1].rstrip()
    return stripped.endswith(STRUCTURED_INSIGHT_COMPLETE_ENDINGS)


def _is_structured_insight_content_readable(content: Optional[str]) -> bool:
    normalized = _normalize_metadata_text(content)
    if not normalized or len(normalized) < STRUCTURED_INSIGHT_MIN_TEXT_LENGTH:
        return False
    lowered = normalized.lower()
    if any(placeholder in normalized or placeholder in lowered for placeholder in STRUCTURED_INSIGHT_FAILURE_PLACEHOLDERS):
        return False
    if not _has_structured_insight_complete_ending(normalized):
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


def _collect_invalid_structured_insight_section_keys(sections: List[Dict[str, Any]]) -> List[str]:
    invalid_keys: set[str] = set()
    seen_contents: Dict[str, str] = {}
    seen_keys: set[str] = set()

    for raw_section in sections:
        section = _normalize_structured_insight_section(raw_section)
        section_key = section["section_key"]
        if section_key not in STRUCTURED_INSIGHT_SECTION_KEYS:
            invalid_keys.add(section_key)
            continue
        seen_keys.add(section_key)
        normalized_content = _normalize_metadata_text(section.get("content")) or ""
        if not _is_structured_insight_content_readable(normalized_content):
            invalid_keys.add(section_key)
            continue
        duplicate_key = seen_contents.get(normalized_content)
        if duplicate_key is not None:
            invalid_keys.add(section_key)
            continue
        seen_contents[normalized_content] = section_key

    for section_key in STRUCTURED_INSIGHT_SECTION_KEYS:
        if section_key not in seen_keys:
            invalid_keys.add(section_key)

    return [section_key for section_key in STRUCTURED_INSIGHT_SECTION_KEYS if section_key in invalid_keys]


class _StructuredInsightBasePreferenceTracker:
    def __init__(self, llm_config: Dict[str, Any], *, threshold: int = STRUCTURED_INSIGHT_BASE_503_SWITCH_THRESHOLD) -> None:
        members = list(llm_config.get("pool_members") or [])
        self._threshold = max(1, int(threshold))
        self._known_bases: List[str] = []
        self._base_503_counts: Dict[str, int] = {}
        for member in members:
            base_url = str(member.get("base_url") or "").strip()
            if base_url and base_url not in self._known_bases:
                self._known_bases.append(base_url)

    def preferred_base_urls(self) -> tuple[str, ...]:
        if len(self._known_bases) <= 1:
            return ()
        counts = {base_url: self._base_503_counts.get(base_url, 0) for base_url in self._known_bases}
        worst_count = max(counts.values(), default=0)
        if worst_count < self._threshold:
            return ()
        ordered = sorted(
            self._known_bases,
            key=lambda base_url: (counts.get(base_url, 0), self._known_bases.index(base_url)),
        )
        best_count = counts.get(ordered[0], 0)
        if best_count >= worst_count:
            return ()
        return tuple(base_url for base_url in ordered if counts.get(base_url, 0) < worst_count)

    def record_retryable_status(self, *, member_id: str, base_url: str, status_code: int) -> tuple[str, ...]:
        before = self.preferred_base_urls()
        normalized_base = str(base_url or "").strip()
        if status_code == 503 and normalized_base:
            self._base_503_counts[normalized_base] = self._base_503_counts.get(normalized_base, 0) + 1
        after = self.preferred_base_urls()
        if after != before and after:
            logger.warning(
                "Structured insight pool now prefers bases %s after repeated 503 on %s via %s",
                list(after),
                normalized_base,
                member_id,
            )
        return after


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
    preferred_base_urls_getter: Optional[Callable[[], List[str] | tuple[str, ...]]] = None,
    on_retryable_status: Optional[Callable[[str, str, int], None]] = None,
) -> str:
    provider_url = _resolve_chat_completions_url(
        str(llm_config.get("base_url") or settings.llm_base_url or "")
    )
    provider_key = str(llm_config.get("api_key") or settings.llm_api_key or "").strip()
    provider_model = str(llm_config.get("model") or settings.llm_model or "").strip()
    if not provider_url or not provider_key or not provider_model:
        raise RuntimeError("Structured insight LLM configuration is unavailable")
    scheduler_llm_config = {
        **llm_config,
        "base_url": provider_url,
        "api_key": provider_key,
        "model": provider_model,
    }

    payload = {
        "model": provider_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    timeout = aiohttp.ClientTimeout(total=max(float(llm_config.get("timeout") or settings.llm_timeout), 10.0))

    use_system_pool = (
        str(scheduler_llm_config.get("pool_mode") or "").strip() == "system_managed"
        and bool(list(scheduler_llm_config.get("pool_members") or []))
    )
    async with aiohttp.ClientSession() as session:
        if use_system_pool:
            payload = await post_chat_completion_with_pool(
                session=session,
                llm_config=scheduler_llm_config,
                payload=payload,
                timeout=timeout,
                on_retry_message=lambda message: logger.warning(
                    "Structured insight LLM pool retry: %s",
                    message,
                ),
                preferred_base_urls_getter=preferred_base_urls_getter,
                on_retryable_status=on_retryable_status,
            )
        else:
            headers = {
                "Authorization": f"Bearer {provider_key}",
                "Content-Type": "application/json",
            }
            async with session.post(provider_url, json=payload, headers=headers, timeout=timeout) as response:
                response.raise_for_status()
                payload = await response.json()

    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Structured insight LLM response is missing choices")
    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    finish_reason = str(first_choice.get("finish_reason") or "").strip()
    if finish_reason in {"length", "content_filter"}:
        raise RuntimeError(f"Structured insight LLM response ended with finish_reason={finish_reason}")
    message = first_choice.get("message") if isinstance(first_choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Structured insight LLM response is empty")
    return content


def _build_structured_insight_source_briefs(
    sources: Dict[str, Dict[str, str]],
) -> Dict[str, List[str]]:
    briefs: Dict[str, List[str]] = {}
    running_briefs: List[str] = []
    for section_key in STRUCTURED_INSIGHT_SECTION_KEYS:
        briefs[section_key] = list(running_briefs)
        packet = _normalize_structured_insight_source_packet(sources.get(section_key))
        brief_body = _normalize_metadata_text(packet.get("translated_excerpt") or packet.get("combined_excerpt")) or ""
        if brief_body:
            running_briefs.append(f"{section_key}: {brief_body[:120]}")
    return briefs


def _build_structured_insight_admin_warning(sections: List[Dict[str, Any]]) -> Optional[str]:
    fallback_keys: List[str] = []
    fallback_without_source_keys: List[str] = []
    for section in sections:
        section_key = str(section.get("section_key") or "").strip()
        if section_key not in STRUCTURED_INSIGHT_SECTION_KEYS:
            continue
        if str(section.get("generation_mode") or "").strip() != "fallback":
            continue
        fallback_keys.append(section_key)
        if not bool(section.get("source_excerpt_present")):
            fallback_without_source_keys.append(section_key)

    if not fallback_keys:
        return None

    parts = [f"结构化解析使用兜底模板：{', '.join(fallback_keys)}。"]
    if fallback_without_source_keys:
        parts.append(f"缺少可用正文摘录：{', '.join(fallback_without_source_keys)}。")
    return " ".join(parts)


async def _generate_single_structured_insight_section(
    *,
    task_id: str,
    section_key: str,
    source_packet: Dict[str, str],
    llm_config: Dict[str, Any],
    title: str,
    abstract_raw: Optional[str],
    prior_section_summaries: List[str],
    disallowed_contents: Optional[set[str]] = None,
    allow_fallback: bool,
    base_preference_tracker: Optional[_StructuredInsightBasePreferenceTracker] = None,
) -> Dict[str, Any]:
    packet = _normalize_structured_insight_source_packet(source_packet)
    translated_excerpt = _normalize_metadata_text(packet.get("translated_excerpt")) or ""
    source_excerpt = _normalize_metadata_text(packet.get("source_excerpt")) or ""
    combined_excerpt = _normalize_metadata_text(packet.get("combined_excerpt")) or translated_excerpt or source_excerpt

    content: Optional[str] = None
    last_error: Optional[Exception] = None
    boundaries = STRUCTURED_INSIGHT_SECTION_BOUNDARIES.get(section_key, {})
    banned_contents = set(disallowed_contents or set())
    source_excerpt_present = bool(translated_excerpt or source_excerpt or combined_excerpt)
    generation_mode = "empty"

    if source_excerpt_present:
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
                        "source_excerpt_zh": translated_excerpt or combined_excerpt,
                        "source_excerpt_original": source_excerpt,
                    },
                    temperature=0.1,
                    max_tokens=STRUCTURED_INSIGHT_MAX_OUTPUT_TOKENS,
                    preferred_base_urls_getter=(
                        (lambda: list(base_preference_tracker.preferred_base_urls()))
                        if base_preference_tracker is not None
                        else None
                    ),
                    on_retryable_status=(
                        (
                            lambda member_id, base_url, status_code: base_preference_tracker.record_retryable_status(
                                member_id=member_id,
                                base_url=base_url,
                                status_code=status_code,
                            )
                        )
                        if base_preference_tracker is not None
                        else None
                    ),
                )
                normalized_content = _normalize_metadata_text(raw_content)
                if not _is_structured_insight_content_readable(normalized_content):
                    raise ValueError(f"Structured insight section {section_key} returned unreadable content")
                if normalized_content in banned_contents:
                    raise ValueError(f"Structured insight section {section_key} duplicated another module")
                content = normalized_content
                generation_mode = "llm"
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

    if not content and allow_fallback:
        content = _build_structured_insight_fallback_content(
            section_key=section_key,
            excerpt=translated_excerpt or combined_excerpt,
        )
        generation_mode = "fallback"
        if last_error is not None:
            logger.warning(
                "Using fallback structured insight content for task %s section %s after generation failure: %s",
                task_id,
                section_key,
                last_error,
            )

    return {
        "section_key": section_key,
        "content": content or "",
        "status": STRUCTURED_INSIGHT_READY_STATUS,
        "updated_at": _utc_now_iso(),
        "generation_mode": generation_mode,
        "source_excerpt_present": source_excerpt_present,
    }


async def _generate_structured_insight_sections_from_task(
    *,
    task_id: str,
    title: str,
    abstract_raw: Optional[str],
    created_by: Optional[str],
    preview_asset: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    source_packets = (
        _prepare_structured_insight_source_packets(task_id, preview_asset=preview_asset)
        if preview_asset
        else _prepare_structured_insight_source_packets(task_id)
    )
    llm_config = await _build_structured_insight_llm_config(created_by)
    has_packet_content = any(
        _normalize_structured_insight_source_packet(source_packets.get(section_key)).get("combined_excerpt")
        for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
    )
    if has_packet_content:
        normalized_sources = {
            section_key: _normalize_structured_insight_source_packet(source_packets.get(section_key))
            for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
        }
    else:
        legacy_sources = (
            _prepare_structured_insight_sources(task_id, preview_asset=preview_asset)
            if preview_asset
            else _prepare_structured_insight_sources(task_id)
        )
        normalized_sources = {
            section_key: _normalize_structured_insight_source_packet(legacy_sources.get(section_key))
            for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
        }
    source_briefs = _build_structured_insight_source_briefs(normalized_sources)
    base_preference_tracker = (
        _StructuredInsightBasePreferenceTracker(llm_config)
        if llm_config.get("pool_mode") == "system_managed" and list(llm_config.get("pool_members") or [])
        else None
    )

    first_pass = await asyncio.gather(
        *[
            _generate_single_structured_insight_section(
                task_id=task_id,
                section_key=section_key,
                source_packet=normalized_sources.get(section_key, {}),
                llm_config=llm_config,
                title=title,
                abstract_raw=abstract_raw,
                prior_section_summaries=source_briefs.get(section_key, []),
                allow_fallback=False,
                base_preference_tracker=base_preference_tracker,
            )
            for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
        ]
    )
    generated_by_key = {
        section["section_key"]: section
        for section in first_pass
    }

    for repair_round in range(STRUCTURED_INSIGHT_MAX_REPAIR_ATTEMPTS):
        ordered_sections = [
            generated_by_key.get(
                section_key,
                {
                    "section_key": section_key,
                    "content": "",
                    "status": STRUCTURED_INSIGHT_READY_STATUS,
                    "updated_at": _utc_now_iso(),
                },
            )
            for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
        ]
        invalid_keys = _collect_invalid_structured_insight_section_keys(ordered_sections)
        if not invalid_keys:
            return _validate_structured_insight_sections(ordered_sections)

        valid_briefs = [
            f"{section_key}: {(_normalize_metadata_text(generated_by_key[section_key].get('content')) or '')[:120]}"
            for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
            if section_key not in invalid_keys
            and section_key in generated_by_key
            and _is_structured_insight_content_readable(generated_by_key[section_key].get("content"))
        ]
        disallowed_contents = {
            _normalize_metadata_text(generated_by_key[section_key].get("content")) or ""
            for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
            if section_key not in invalid_keys
            and section_key in generated_by_key
            and _is_structured_insight_content_readable(generated_by_key[section_key].get("content"))
        }
        repaired_sections = await asyncio.gather(
            *[
                _generate_single_structured_insight_section(
                    task_id=task_id,
                    section_key=section_key,
                    source_packet=normalized_sources.get(section_key, {}),
                    llm_config=llm_config,
                    title=title,
                    abstract_raw=abstract_raw,
                    prior_section_summaries=valid_briefs or source_briefs.get(section_key, []),
                    disallowed_contents=disallowed_contents,
                    allow_fallback=repair_round == (STRUCTURED_INSIGHT_MAX_REPAIR_ATTEMPTS - 1),
                    base_preference_tracker=base_preference_tracker,
                )
                for section_key in invalid_keys
            ]
        )
        for section in repaired_sections:
            generated_by_key[section["section_key"]] = section

    final_sections = [
        generated_by_key.get(
            section_key,
            {
                "section_key": section_key,
                "content": "",
                "status": STRUCTURED_INSIGHT_READY_STATUS,
                "updated_at": _utc_now_iso(),
            },
        )
        for section_key in STRUCTURED_INSIGHT_SECTION_KEYS
    ]
    return _validate_structured_insight_sections(final_sections)


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
    metadata = await _ensure_publishable_admin_curation_metadata(job=job, metadata=metadata)
    paper_id = str(job.get("paper_id") or "").strip()
    resolved_arxiv_id = (
        _normalize_metadata_text(metadata.get("arxiv_id"))
        or _normalize_metadata_text(job.get("arxiv_id"))
    )
    if str(job.get("source_type") or "").strip() == "arxiv" and not resolved_arxiv_id:
        raise ValueError("Admin arXiv curation publish requires arxiv_id")
    paper = await _ensure_admin_curation_placeholder_paper(
        paper_id=paper_id,
        job=job,
        metadata=metadata,
        resolved_arxiv_id=resolved_arxiv_id,
    )

    try:
        sync_result = await _sync_task_assets_for_paper(
            paper_id=paper["id"],
            task_id=translated_task_id,
            promote_to_official=False,
            paper=paper,
            defer_runtime_cleanup=True,
        )
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        logger.warning(
            "Admin curation publish lost placeholder paper %s during asset sync for task %s; recreating and retrying once",
            paper_id,
            translated_task_id,
        )
        paper = await _ensure_admin_curation_placeholder_paper(
            paper_id=paper_id,
            job=job,
            metadata=metadata,
            resolved_arxiv_id=resolved_arxiv_id,
            force_recreate=True,
        )
        sync_result = await _sync_task_assets_for_paper(
            paper_id=paper["id"],
            task_id=translated_task_id,
            promote_to_official=False,
            paper=paper,
            defer_runtime_cleanup=True,
        )
    if sync_result.get("status") == "quality_gate_failed":
        diagnostics = sync_result.get("quality_gate") or {}
        reason_codes = [
            str(reason.get("code"))
            for reason in diagnostics.get("reasons", [])
            if isinstance(reason, dict)
        ]
        raise ValueError(f"Community publish quality gate failed: {', '.join(reason_codes) or 'unknown'}")
    paper = sync_result.get("paper") or paper
    abstract_translated = _extract_translated_abstract_from_task(translated_task_id) or paper.get("abstract_translated")
    structured_insight_sections = await _generate_structured_insight_sections_from_task(
        task_id=translated_task_id,
        title=str(metadata.get("title") or paper.get("title") or ""),
        abstract_raw=metadata.get("abstract_raw") or paper.get("abstract_raw"),
        created_by=str(job.get("created_by") or ""),
        preview_asset=sync_result.get("preview_asset"),
    )
    structured_insight_warning = _build_structured_insight_admin_warning(structured_insight_sections)
    _validate_structured_insight_sections(structured_insight_sections)
    await _upsert_structured_insight_sections(
        paper_id=paper["id"],
        sections=structured_insight_sections,
    )
    if sync_result.get("needs_runtime_cleanup"):
        clear_cached_runtime_artifacts(
            translated_task_id,
            _candidate_runtime_cache_paths_for_task(translated_task_id),
        )
    similar_source_paper = {
        **paper,
        "arxiv_id": resolved_arxiv_id,
        "title": metadata.get("title") or paper.get("title"),
        "authors": metadata.get("authors") or paper.get("authors") or [],
        "categories": metadata.get("categories") or paper.get("categories") or [],
        "abstract_raw": metadata.get("abstract_raw") or paper.get("abstract_raw"),
        "abstract_translated": abstract_translated,
        "arxiv_published_at": metadata.get("arxiv_published_at") or paper.get("arxiv_published_at"),
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
            "arxiv_published_at": metadata.get("arxiv_published_at") or paper.get("arxiv_published_at"),
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
    if structured_insight_warning:
        updated["_structured_insight_admin_warning"] = structured_insight_warning
    return updated


async def _ensure_admin_curation_placeholder_paper(
    *,
    paper_id: str,
    job: Dict[str, Any],
    metadata: Dict[str, Any],
    resolved_arxiv_id: Optional[str],
    force_recreate: bool = False,
) -> Dict[str, Any]:
    if not force_recreate:
        existing = await _fetch_paper_by_id(paper_id) if paper_id else None
        if existing is not None:
            return existing

    payload = _paper_payload(
        source=str(job.get("source_type") or "upload"),
        arxiv_id=resolved_arxiv_id,
        title=metadata.get("title") or (f"arXiv:{resolved_arxiv_id}" if resolved_arxiv_id else "Curated paper"),
        created_by=str(job.get("created_by") or ""),
        community_status=COMMUNITY_STATUS_OFFICIAL,
        authors=metadata.get("authors"),
        categories=metadata.get("categories"),
        abstract_raw=metadata.get("abstract_raw"),
        abstract_translated=None,
        task_id=None,
        arxiv_published_at=metadata.get("arxiv_published_at"),
        official_published_at=None,
        trans_status="processing",
    )
    payload["id"] = paper_id
    payload["visibility"] = "private"
    payload["status"] = "curating"
    try:
        return await _insert_paper(payload)
    except HTTPException as exc:
        if paper_id:
            existing = await _fetch_paper_by_id(paper_id)
            if existing is not None:
                logger.warning(
                    "Admin curation placeholder paper %s already exists after recreate attempt; reusing persisted row",
                    paper_id,
                )
                return existing
        raise exc


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


def _normalize_failed_artifact_path(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _get_storage_backend_instance() -> StorageBackend:
    return build_storage_backend(settings)


def _delete_object_storage_prefix(prefix: str) -> list[str]:
    backend = _get_storage_backend_instance()
    if not isinstance(backend, CosStorageBackend):
        return []

    refs = backend.list_files(prefix=prefix)
    object_keys = [str(ref.object_key or "").strip() for ref in refs if str(ref.object_key or "").strip()]
    if not object_keys:
        return []

    deleted: list[str] = []
    client = backend._get_client()
    for start in range(0, len(object_keys), 1000):
        chunk = object_keys[start : start + 1000]
        client.delete_objects(
            Bucket=backend.bucket,
            Delete={"Object": [{"Key": key} for key in chunk]},
        )
        deleted.extend(chunk)
    return deleted


def _delete_retained_failed_artifact(*, failed_artifact_path: str, artifact_storage_backend: Optional[str]) -> list[str]:
    normalized_backend = str(artifact_storage_backend or "").strip() or "local_disk"
    normalized_path = str(failed_artifact_path or "").strip()
    if not normalized_path:
        return []

    if normalized_backend == "object_storage":
        return _delete_object_storage_prefix(normalized_path)

    resolved = _resolve_storage_path(normalized_path)
    deleted = _delete_local_artifact_path(resolved)
    return [deleted] if deleted else []


def _retain_failed_artifact_reference(
    *,
    task_id: str,
    failed_output_path: Optional[str],
) -> dict[str, Optional[str]]:
    candidate_path = _resolve_storage_path(failed_output_path) if failed_output_path else Path(settings.failed_tasks_dir) / task_id
    if not candidate_path.exists():
        return {
            "failed_artifact_path": None,
            "artifact_storage_backend": None,
        }

    backend = _get_storage_backend_instance()
    if isinstance(backend, LocalDiskStorageBackend):
        return {
            "failed_artifact_path": _normalize_failed_artifact_path(candidate_path),
            "artifact_storage_backend": "local_disk",
        }

    stored_root = f"failed_tasks/{task_id}"
    if candidate_path.is_dir():
        stored_path = task_artifact_storage.persist_task_directory(
            candidate_path,
            stored_path=stored_root,
            delete_local=True,
        )
    else:
        content_type = mimetypes.guess_type(candidate_path.name)[0] or "application/octet-stream"
        backend.put_file(
            local_path=candidate_path,
            object_key=f"{stored_root}/{candidate_path.name}",
            content_type=content_type,
            delete_local=True,
        )
        stored_path = f"{stored_root}/{candidate_path.name}"
    return {
        "failed_artifact_path": _normalize_failed_artifact_path(stored_path),
        "artifact_storage_backend": "object_storage",
    }


async def _delete_placeholder_curation_paper_if_present(*, repository: Any, paper_id: str) -> list[str]:
    normalized_paper_id = str(paper_id or "").strip()
    if not normalized_paper_id:
        return []

    try:
        paper = await _fetch_paper_by_id(normalized_paper_id)
    except Exception:
        paper = None
    if not _is_private_curating_placeholder_paper(paper):
        return []

    _RUNTIME_PAPER_OVERRIDES.pop(normalized_paper_id, None)
    deleted_tables: list[str] = []
    for table_name in ADMIN_CURATION_CLEANUP_PAPER_TABLES:
        await _run_local_repo(
            lambda table_name=table_name, paper_id=normalized_paper_id: repository.delete_rows_for_papers(table_name, [paper_id])
        )
        deleted_tables.append(table_name)
    return deleted_tables


async def _hard_delete_paper_records(*, repository: Any, paper_id: str) -> None:
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
    invalidate_public_feed_cache()


async def _cleanup_failed_admin_curation_artifacts(
    *,
    repository: Any,
    job: Dict[str, Any],
    translated_task_id: str = "",
    cancel_running_task: bool,
    terminal_reason: Optional[str] = None,
    timeout_reason: Optional[str] = None,
) -> Dict[str, Any]:
    ordered_candidates = [
        str(translated_task_id or "").strip(),
        str(job.get("task_id") or "").strip(),
    ]
    task_ids = [task_id for task_id in dict.fromkeys(ordered_candidates) if task_id]
    deleted_paths: List[str] = []
    errors: List[str] = []
    failed_artifact_path: Optional[str] = None
    artifact_storage_backend: Optional[str] = None
    terminal_task_status: Optional[str] = None
    resolved_terminal_reason = str(terminal_reason or "").strip() or None
    resolved_timeout_reason = str(timeout_reason or "").strip() or None

    for task_id in task_ids:
        if cancel_running_task:
            try:
                task_manager.cancel_task(
                    task_id,
                    terminal_reason=resolved_terminal_reason,
                    timeout_reason=resolved_timeout_reason,
                )
            except Exception as exc:
                errors.append(f"Failed to cancel task {task_id}: {exc}")

        task_snapshot = task_manager.get_task(task_id) if hasattr(task_manager, "get_task") else None
        if terminal_task_status is None:
            candidate_status = str((task_snapshot or {}).get("status") or "").strip()
            if candidate_status:
                terminal_task_status = candidate_status
        if resolved_terminal_reason is None:
            resolved_terminal_reason = _resolve_task_terminal_reason(task_snapshot)
        failed_output_path = str((task_snapshot or {}).get("failed_output_path") or "").strip()
        if failed_artifact_path is None:
            try:
                retained_artifact = _retain_failed_artifact_reference(
                    task_id=task_id,
                    failed_output_path=failed_output_path or None,
                )
                failed_artifact_path = retained_artifact.get("failed_artifact_path")
                artifact_storage_backend = retained_artifact.get("artifact_storage_backend")
            except Exception as exc:
                errors.append(f"Failed to retain failed task output for {task_id}: {exc}")

    paper_id = str(job.get("paper_id") or "").strip()
    if paper_id:
        try:
            await _delete_placeholder_curation_paper_if_present(repository=repository, paper_id=paper_id)
        except Exception as exc:
            errors.append(f"Failed to delete placeholder paper {paper_id}: {exc}")

    return {
        "deleted_paths": deleted_paths,
        "errors": errors,
        "failed_artifact_path": failed_artifact_path,
        "artifact_storage_backend": artifact_storage_backend,
        "terminal_task_status": terminal_task_status,
        "terminal_reason": resolved_terminal_reason,
        "timeout_reason": resolved_timeout_reason,
    }


async def _mark_admin_curation_job_failed(
    *,
    repository: Any,
    job_id: str,
    job: Dict[str, Any],
    translated_task_id: str,
    failure_message: str,
    cancel_running_task: bool,
    terminal_reason: Optional[str] = None,
    timeout_reason: Optional[str] = None,
) -> None:
    cleanup_result = await _cleanup_failed_admin_curation_artifacts(
        repository=repository,
        job=job,
        translated_task_id=translated_task_id,
        cancel_running_task=cancel_running_task,
        terminal_reason=terminal_reason,
        timeout_reason=timeout_reason,
    )
    final_error = str(failure_message or "Curation translation failed")
    cleanup_errors = [str(error) for error in cleanup_result.get("errors", []) if str(error or "").strip()]
    if cleanup_errors:
        final_error = f"{final_error} | cleanup_warnings: {'; '.join(cleanup_errors)}"
    await _run_local_repo(
        lambda: repository.update_curation_job(
            job_id,
            {
                "status": "failed",
                "terminal_task_status": cleanup_result.get("terminal_task_status"),
                "terminal_reason": cleanup_result.get("terminal_reason") or terminal_reason,
                "timeout_reason": cleanup_result.get("timeout_reason") or timeout_reason,
                "error": final_error,
                "failed_artifact_path": cleanup_result.get("failed_artifact_path"),
                "artifact_storage_backend": cleanup_result.get("artifact_storage_backend"),
                "updated_at": _utc_now_iso(),
            },
        )
    )


def _cache_terminal_task_snapshot(task_id: str, task_snapshot: Optional[Dict[str, Any]]) -> None:
    if not task_id or not task_snapshot:
        return
    normalized_status = str(task_snapshot.get("status") or "").strip()
    if normalized_status not in TERMINAL_TASK_STATUSES:
        return
    runtime_tasks = getattr(task_manager, "_tasks", None)
    runtime_lock = getattr(task_manager, "_lock", None)
    if runtime_tasks is None or runtime_lock is None:
        return
    try:
        with runtime_lock:
            existing_snapshot = runtime_tasks.get(task_id)
            merged_snapshot = dict(existing_snapshot) if isinstance(existing_snapshot, dict) else {"task_id": task_id}
            merged_snapshot.update(task_snapshot)
            runtime_tasks[task_id] = merged_snapshot
    except Exception:
        logger.debug("Failed to cache terminal task snapshot for %s", task_id, exc_info=True)


async def _wait_for_task_terminal_state(task_id: str) -> Dict[str, Any]:
    persistent_lookup_failed = False
    persistent_reconcile_failed = False
    persistent_retry_disabled_until = 0.0
    persistent_call_timeout_seconds = 1.0
    persistent_retry_backoff_seconds = 30.0
    admission_timeout_seconds = _resolve_admin_curation_timeout_seconds("admission")
    execution_timeout_seconds = _resolve_admin_curation_timeout_seconds("execution")
    observed_execution_start = False
    current_stage_elapsed_seconds = 0

    while True:
        task = task_manager.get_task(task_id)
        if task and task.get("status") in TERMINAL_TASK_STATUSES:
            return task
        persisted_task = None
        now_monotonic = time.monotonic()
        if now_monotonic >= persistent_retry_disabled_until:
            try:
                persisted_task = await asyncio.wait_for(
                    run_db_blocking(
                        lambda: _get_translation_task_repository().get_task(task_id)
                    ),
                    timeout=persistent_call_timeout_seconds,
                )
                if persistent_lookup_failed:
                    logger.info(
                        "Admin curation wait recovered persistent task lookup for task %s",
                        task_id,
                    )
                    persistent_lookup_failed = False
                persistent_retry_disabled_until = 0.0
            except Exception as exc:
                persistent_retry_disabled_until = now_monotonic + persistent_retry_backoff_seconds
                if not persistent_lookup_failed:
                    logger.warning(
                        "Admin curation wait could not read persistent task state for %s; continuing in-memory polling: %s",
                        task_id,
                        exc,
                    )
                    persistent_lookup_failed = True
        if persisted_task:
            if (
                persisted_task.get("completed_at")
                and str(persisted_task.get("status") or "").strip() not in TERMINAL_TASK_STATUSES
            ):
                reconciliation_message = (
                    "Recovered inconsistent task state while waiting for admin curation completion"
                )
                updates = {
                    "status": TaskStatus.FAILED.value,
                    "progress": 100,
                    "message": reconciliation_message,
                    "error": persisted_task.get("error") or reconciliation_message,
                    "detail_code": "task_state_reconciled",
                }
                try:
                    await asyncio.wait_for(
                        run_db_blocking(
                            lambda: _get_translation_task_repository().update_task(task_id, updates)
                        ),
                        timeout=persistent_call_timeout_seconds,
                    )
                    if persistent_reconcile_failed:
                        logger.info(
                            "Admin curation wait recovered persistent task reconciliation for %s",
                            task_id,
                        )
                        persistent_reconcile_failed = False
                except Exception as exc:
                    persistent_retry_disabled_until = max(
                        persistent_retry_disabled_until,
                        time.monotonic() + persistent_retry_backoff_seconds,
                    )
                    if not persistent_reconcile_failed:
                        logger.warning(
                            "Admin curation wait could not persist reconciled terminal state for %s; using synthesized failed snapshot: %s",
                            task_id,
                            exc,
                        )
                        persistent_reconcile_failed = True
                persisted_task = {**persisted_task, **updates}
            if str(persisted_task.get("status") or "").strip() in TERMINAL_TASK_STATUSES:
                _cache_terminal_task_snapshot(task_id, persisted_task)
                return persisted_task
        if not observed_execution_start and (
            _task_has_active_execution_started(persisted_task)
            or _task_has_active_execution_started(task)
        ):
            observed_execution_start = True
            current_stage_elapsed_seconds = 0

        stage_timeout_seconds = (
            execution_timeout_seconds if observed_execution_start else admission_timeout_seconds
        )
        if stage_timeout_seconds > 0 and current_stage_elapsed_seconds >= stage_timeout_seconds:
            raise AdminCurationTaskWaitTimeout(
                task_id,
                "execution_timeout" if observed_execution_start else "admission_timeout",
            )
        await asyncio.sleep(1)
        current_stage_elapsed_seconds += 1


def _schedule_curation_job(job_id: str) -> None:
    if not admin_job_execution_enabled():
        return
    if job_id in _curation_job_tasks and not _curation_job_tasks[job_id].done():
        return
    task = asyncio.create_task(_run_curation_job(job_id))
    _curation_job_tasks[job_id] = task


async def _cancel_curation_job_task_if_running(job_id: str) -> bool:
    normalized_job_id = str(job_id or "").strip()
    if not normalized_job_id:
        return False
    task = _curation_job_tasks.get(normalized_job_id)
    if task is None:
        return False
    if task.done():
        _curation_job_tasks.pop(normalized_job_id, None)
        return False

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.warning("Admin curation task cancellation for %s raised: %s", normalized_job_id, exc, exc_info=True)
    finally:
        if _curation_job_tasks.get(normalized_job_id) is task:
            _curation_job_tasks.pop(normalized_job_id, None)
    return True


async def _cancel_admin_curation_translation_task_before_delete(
    task_id: str,
    *,
    terminal_reason: str = "admin_curation_deleted",
) -> bool:
    normalized_task_id = str(task_id or "").strip()
    if not normalized_task_id:
        return False

    worker_cancel_result = await request_worker_task_cancel(
        normalized_task_id,
        terminal_reason=terminal_reason,
    )
    if worker_cancel_signal_failed(worker_cancel_result):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker runtime cancellation signal failed; curation task was not deleted.",
        )
    cancelled = bool(worker_cancel_result.get("cancelled"))
    try:
        local_cancelled = task_manager.cancel_task(
            normalized_task_id,
            terminal_reason=terminal_reason,
        )
        cancelled = bool(cancelled or local_cancelled)
    except Exception as exc:
        logger.warning(
            "Failed to cancel admin curation translation task %s before delete: %s",
            normalized_task_id,
            exc,
            exc_info=True,
        )

    if cancelled:
        return True

    try:
        task_queue = get_task_queue()
        if task_queue is not None:
            return bool(task_queue.cancel_execution(normalized_task_id))
    except Exception as exc:
        logger.warning(
            "Failed to request queue skip for admin curation translation task %s before delete: %s",
            normalized_task_id,
            exc,
            exc_info=True,
        )
    return False


async def _reset_existing_admin_arxiv_curation(
    *,
    repository: Any,
    arxiv_id: str,
    existing_paper: Optional[Dict[str, Any]],
) -> None:
    normalized_arxiv_id = str(arxiv_id or "").strip()
    if not normalized_arxiv_id:
        return

    existing_jobs = await _run_local_repo(
        lambda: repository.list_curation_jobs_for_arxiv_id(normalized_arxiv_id)
    )
    if not existing_jobs and not existing_paper:
        return

    deleted_paper_ids: set[str] = set()
    deleted_task_ids: set[str] = set()

    existing_paper_id = str((existing_paper or {}).get("id") or "").strip()
    if existing_paper_id:
        await _hard_delete_paper_records(repository=repository, paper_id=existing_paper_id)
        deleted_paper_ids.add(existing_paper_id)

    for job in existing_jobs:
        job_id = str(job.get("job_id") or "").strip()
        if job_id:
            await _cancel_curation_job_task_if_running(job_id)

        job_status = str(job.get("status") or "").strip().lower()
        published_paper_id = str(job.get("published_paper_id") or "").strip()
        paper_id = str(job.get("paper_id") or "").strip()
        target_paper_id = published_paper_id or paper_id

        if job_status == "completed" or published_paper_id:
            if target_paper_id and target_paper_id not in deleted_paper_ids:
                await _hard_delete_paper_records(repository=repository, paper_id=target_paper_id)
                deleted_paper_ids.add(target_paper_id)
        else:
            failed_artifact_path = str(job.get("failed_artifact_path") or "").strip()
            if failed_artifact_path:
                _delete_retained_failed_artifact(
                    failed_artifact_path=failed_artifact_path,
                    artifact_storage_backend=str(job.get("artifact_storage_backend") or "").strip() or None,
                )

            task_id = str(job.get("task_id") or "").strip()
            if task_id and task_id not in deleted_task_ids:
                await _cancel_admin_curation_translation_task_before_delete(task_id)
                task_manager.delete_task_full(task_id)
                await _run_local_repo(lambda task_id=task_id: repository.delete_translation_tasks([task_id]))
                deleted_task_ids.add(task_id)

            if paper_id and paper_id not in deleted_paper_ids:
                await _delete_placeholder_curation_paper_if_present(repository=repository, paper_id=paper_id)
                deleted_paper_ids.add(paper_id)

        if job_id:
            await _run_local_repo(lambda job_id=job_id: repository.delete_curation_job(job_id))


def _build_completed_curation_job_update(published: Dict[str, Any]) -> Dict[str, Any]:
    paper_id = published.get("id")
    structured_warning = str(published.get("_structured_insight_admin_warning") or "").strip() or None
    return {
        "paper_id": paper_id,
        "published_paper_id": paper_id,
        "status": "completed",
        "terminal_task_status": "completed",
        "terminal_reason": None,
        "timeout_reason": None,
        "error": structured_warning,
        "failed_artifact_path": None,
        "artifact_storage_backend": None,
        "updated_at": _utc_now_iso(),
    }


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
            request.advanced_config.generate_terminology_table = False
            request.advanced_config.use_author_api = True
            request.advanced_config.community_production_translation = True
            translated_task_id = str(job.get("task_id") or "").strip()
            if str(job.get("source_type") or "") == "arxiv":
                metadata = await _fetch_arxiv_metadata(str(job.get("arxiv_id") or ""))
                if translated_task_id:
                    await _run_local_repo(
                        lambda: repository.update_curation_job(
                            job_id,
                            {
                                "task_id": translated_task_id,
                                "status": "translating",
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
                    await _run_local_repo(
                        lambda: repository.update_curation_job(
                            job_id,
                            {
                                "task_id": translated_task_id,
                                "status": "translating",
                                "updated_at": _utc_now_iso(),
                            },
                        )
                    )
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
            task = await _wait_for_task_terminal_state(translated_task_id)
            if task.get("status") not in {"completed", "completed_with_warnings"}:
                await _mark_admin_curation_job_failed(
                    repository=repository,
                    job_id=job_id,
                    job=job,
                    translated_task_id=translated_task_id,
                    failure_message=str(task.get("error") or task.get("message") or "Curation translation failed"),
                    cancel_running_task=False,
                    terminal_reason=_resolve_task_terminal_reason(task),
                )
                return

            await _run_local_repo(
                lambda: repository.update_curation_job(
                    job_id,
                    {"task_id": translated_task_id, "status": "publishing", "updated_at": _utc_now_iso()},
                )
            )
            published = await _publish_admin_curation_job(
                job=job,
                metadata=metadata,
                translated_task_id=translated_task_id,
            )
            await _run_local_repo(
                lambda: repository.update_curation_job(
                    job_id,
                    _build_completed_curation_job_update(published),
                )
            )
        except AdminCurationTaskWaitTimeout as exc:
            logger.warning("Admin curation job %s timed out while waiting for %s", job_id, translated_task_id)
            latest_task = task_manager.get_task(translated_task_id) if translated_task_id else None
            if latest_task and latest_task.get("status") in {"completed", "completed_with_warnings"}:
                await _run_local_repo(
                    lambda: repository.update_curation_job(
                        job_id,
                        {"task_id": translated_task_id, "status": "publishing", "updated_at": _utc_now_iso()},
                    )
                )
                published = await _publish_admin_curation_job(
                    job=job,
                    metadata=metadata,
                    translated_task_id=translated_task_id,
                )
                await _run_local_repo(
                    lambda: repository.update_curation_job(
                        job_id,
                        _build_completed_curation_job_update(published),
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
                    terminal_reason=_resolve_task_terminal_reason(latest_task) or exc.terminal_reason,
                    timeout_reason=exc.timeout_reason,
                )
                return
            await _mark_admin_curation_job_failed(
                repository=repository,
                job_id=job_id,
                job=job,
                translated_task_id=translated_task_id,
                failure_message=str(exc),
                cancel_running_task=bool(translated_task_id),
                terminal_reason=exc.terminal_reason,
                timeout_reason=exc.timeout_reason,
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
                    terminal_reason=_resolve_task_terminal_reason(
                        task_manager.get_task(translated_task_id) if translated_task_id else None
                    ),
                )
            except Exception:
                logger.warning("Failed to persist curation job failure for %s", job_id, exc_info=True)
        finally:
            _curation_job_tasks.pop(job_id, None)


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
        await _reset_existing_admin_arxiv_curation(
            repository=repository,
            arxiv_id=arxiv_id,
            existing_paper=existing,
        )
        paper_id = uuid4().hex
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
    if not admin_job_execution_enabled():
        return
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
            await _hard_delete_paper_records(repository=repository, paper_id=paper_id)
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


def _admin_curation_history_item(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": job.get("job_id"),
        "batch_id": job.get("batch_id"),
        "paper_id": job.get("paper_id"),
        "published_paper_id": job.get("published_paper_id"),
        "task_id": job.get("task_id"),
        "source_type": job.get("source_type"),
        "arxiv_id": job.get("arxiv_id"),
        "original_filename": job.get("original_filename"),
        "status": job.get("status"),
        "terminal_task_status": job.get("terminal_task_status"),
        "terminal_reason": job.get("terminal_reason"),
        "timeout_reason": job.get("timeout_reason"),
        "error": job.get("error"),
        "failed_artifact_path": job.get("failed_artifact_path"),
        "created_at": _serialize_timestamp_value(job.get("created_at")),
        "updated_at": _serialize_timestamp_value(job.get("updated_at")),
    }


async def list_admin_curation_jobs(
    *,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    normalized_status = str(status_filter or "").strip().lower()
    if normalized_status in {"", "all"}:
        status_filter = None
    else:
        status_filter = normalized_status

    normalized_search = str(search or "").strip()
    search = normalized_search or None

    jobs = await _run_local_repo(
        lambda: repository.list_curation_jobs(
            status_filter=status_filter,
            search=search,
        )
    )
    items = [_admin_curation_history_item(job) for job in jobs]
    return {
        "items": items,
        "total": len(items),
    }


async def delete_admin_curation_job(
    *,
    job_id: str,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    _ = current_user
    repository = get_community_paper_repository()
    job = await _run_local_repo(lambda: repository.get_curation_job(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Curation job not found")

    job_status = str(job.get("status") or "").strip().lower()
    await _cancel_curation_job_task_if_running(job_id)
    task_ids = [
        str(task_id or "").strip()
        for task_id in dict.fromkeys([job.get("task_id")])
        if str(task_id or "").strip()
    ]

    if job_status == "completed":
        paper_id = str(job.get("published_paper_id") or job.get("paper_id") or "").strip()
        if not paper_id:
            raise HTTPException(status_code=409, detail="Completed curation job missing published paper")
        await _hard_delete_paper_records(repository=repository, paper_id=paper_id)
    else:
        failed_artifact_path = str(job.get("failed_artifact_path") or "").strip()
        if failed_artifact_path:
            _delete_retained_failed_artifact(
                failed_artifact_path=failed_artifact_path,
                artifact_storage_backend=str(job.get("artifact_storage_backend") or "").strip() or None,
            )

        source_type = str(job.get("source_type") or "").strip()
        source_path_raw = str(job.get("source_path") or "").strip()
        if source_type == "upload" and source_path_raw:
            source_path = _resolve_storage_path(source_path_raw)
            if _is_task_scoped_upload_source(source_path, task_ids):
                _delete_local_artifact_path(source_path)

        for task_id in task_ids:
            await _cancel_admin_curation_translation_task_before_delete(task_id)
            task_manager.delete_task_full(task_id)
            await _run_local_repo(lambda task_id=task_id: repository.delete_translation_tasks([task_id]))

        paper_id = str(job.get("paper_id") or "").strip()
        if paper_id:
            await _delete_placeholder_curation_paper_if_present(repository=repository, paper_id=paper_id)

    await _run_local_repo(lambda: repository.delete_curation_job(job_id))
    return {
        "job_id": job.get("job_id"),
        "paper_id": job.get("published_paper_id") or job.get("paper_id"),
        "status": job.get("status"),
    }


async def batch_delete_admin_curation_jobs(
    *,
    job_ids: List[str],
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    normalized_job_ids = [
        str(job_id or "").strip()
        for job_id in dict.fromkeys(job_ids)
        if str(job_id or "").strip()
    ]
    if not normalized_job_ids:
        raise HTTPException(status_code=400, detail="At least one curation job id is required")

    deleted: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    for job_id in normalized_job_ids:
        try:
            deleted.append(
                await delete_admin_curation_job(
                    job_id=job_id,
                    current_user=current_user,
                )
            )
        except HTTPException as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                detail = detail.get("message") or detail.get("detail") or str(detail)
            elif detail is not None:
                detail = str(detail)
            failed.append(
                {
                    "job_id": job_id,
                    "status_code": exc.status_code,
                    "detail": detail,
                }
            )

    return {
        "deleted": deleted,
        "failed": failed,
        "deleted_count": len(deleted),
        "failed_count": len(failed),
    }


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
    effective_request = request.model_copy(deep=True) if hasattr(request, "model_copy") else request
    effective_request.advanced_config = translate_route.normalize_origin_cli_parity_advanced_config(
        request.advanced_config
    )

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
                source_language=effective_request.source_language,
                target_language=effective_request.target_language,
                persist_to_db=False,
            )
            task_manager.update_task(
                task_id=task_id,
                source_path=str(resolved_source_path).replace("\\", "/"),
                source_available=True,
                arxiv_id=paper.get("arxiv_id"),
                source_language=effective_request.source_language,
                target_language=effective_request.target_language,
                advanced_config=effective_request.advanced_config.model_dump(),
                user_id=context["user_id"],
            )
            task_manager.persist_task_if_needed(task_id)
            translation_result = await _enqueue_existing_task_translation(
                task_id=task_id,
                request=effective_request,
                credentials=credentials,
                current_user={"id": context["user_id"]} if context.get("user_id") else current_user,
            )
        elif paper.get("source") == "arxiv" and paper.get("arxiv_id"):
            translation_result = await _start_arxiv_paper_translation(
                paper=paper,
                request=effective_request,
                context=context,
            )
            task_id = translation_result["task_id"]
        else:
            raise HTTPException(status_code=422, detail="Paper source is unavailable for translation")
    elif paper.get("source") == "arxiv" and paper.get("arxiv_id"):
        translation_result = await _start_arxiv_paper_translation(
            paper=paper,
            request=effective_request,
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

    if translated_asset.get("storage_backend") == "object_storage":
        filename = str(translated_asset.get("file_name") or f"{paper_id}.pdf")
        mime_type = str(translated_asset.get("mime_type") or "application/pdf")
        signed_url = _resolve_object_storage_signed_url(
            translated_asset,
            expires_in=300,
            response_params={
                "response-content-disposition": f'inline; filename="{filename}"',
                "response-content-type": mime_type,
            },
        )
        if not signed_url:
            raise HTTPException(status_code=404, detail="Translated PDF object not available")
        return {
            "paper_id": paper_id,
            "asset": translated_asset,
            "signed_url": signed_url,
        }

    file_path = _resolve_storage_path(translated_asset.get("file_path") or "")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Translated PDF file not found")

    return {
        "paper_id": paper_id,
        "asset": translated_asset,
        "file_path": str(file_path),
    }


async def resolve_paper_source_pdf_preview(
    *,
    paper_id: str,
    content_disposition: str = "inline",
) -> Dict[str, Any]:
    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    task_id = str(paper.get("community_selected_task_id") or paper.get("trans_latest_task_id") or "").strip()
    preferred_arxiv_id = str(paper.get("arxiv_id") or "").strip() or None

    source_pdf_asset = asset_map.get("source_pdf")
    if source_pdf_asset and source_pdf_asset.get("file_path"):
        filename = str(source_pdf_asset.get("file_name") or "").strip()
        if not filename:
            filename = _source_pdf_filename(preferred_arxiv_id or paper_id)
        mime_type = str(source_pdf_asset.get("mime_type") or "application/pdf")
        if source_pdf_asset.get("storage_backend") == "object_storage":
            raw_cache_url = (
                arxiv_raw_cache.build_pdf_download_url(
                    preferred_arxiv_id,
                    filename=filename,
                    inline=content_disposition != "attachment",
                )
                if preferred_arxiv_id
                and arxiv_raw_cache.is_raw_pdf_object_key(
                    str(source_pdf_asset.get("file_path") or ""),
                    preferred_arxiv_id,
                )
                else None
            )
            signed_url = raw_cache_url or _resolve_object_storage_signed_url(
                source_pdf_asset,
                expires_in=300,
                response_params={
                    "response-content-disposition": f'{content_disposition}; filename="{filename}"',
                    "response-content-type": mime_type,
                },
            )
            if signed_url:
                return {
                    "paper_id": paper_id,
                    "asset": source_pdf_asset,
                    "signed_url": signed_url,
                    "filename": filename,
                }
        else:
            source_pdf_path = _resolve_storage_path(source_pdf_asset.get("file_path") or "")
            if source_pdf_path.exists() and source_pdf_path.is_file():
                return {
                    "paper_id": paper_id,
                    "asset": source_pdf_asset,
                    "file_path": str(source_pdf_path),
                    "filename": filename or source_pdf_path.name,
                }

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
        filename = _source_pdf_filename(preferred_arxiv_id)
        raw_cache_url = arxiv_raw_cache.build_pdf_download_url(
            preferred_arxiv_id,
            filename=filename,
            inline=content_disposition != "attachment",
        )
        if raw_cache_url:
            return {
                "paper_id": paper_id,
                "signed_url": raw_cache_url,
                "filename": filename,
                "arxiv_id": preferred_arxiv_id,
            }
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


async def _warm_translated_thumbnail_for_asset(*, paper_id: str, asset: Optional[Dict[str, Any]]) -> None:
    if not asset:
        return

    cache_seed = f"translated:{paper_id}:{asset.get('id') or asset.get('file_name') or paper_id}"
    if asset.get("storage_backend") == "object_storage":
        local_pdf = _materialize_object_storage_pdf_asset(asset)
        if local_pdf and local_pdf.exists():
            local_pdf = _normalize_translated_pdf_leading_blank_pages(local_pdf)
            await paper_thumbnail_service.ensure_pdf_thumbnail(
                cache_seed=cache_seed,
                file_path=str(local_pdf),
            )
            return

        filename = str(asset.get("file_name") or f"{paper_id}.pdf")
        mime_type = str(asset.get("mime_type") or "application/pdf")
        signed_url = _resolve_object_storage_signed_url(
            asset,
            expires_in=300,
            response_params={
                "response-content-disposition": f'inline; filename="{filename}"',
                "response-content-type": mime_type,
            },
        )
        if signed_url:
            await paper_thumbnail_service.ensure_pdf_thumbnail(
                cache_seed=cache_seed,
                remote_url=signed_url,
            )
        return

    file_path = _resolve_storage_path(asset.get("file_path") or "")
    if file_path.exists():
        file_path = _normalize_translated_pdf_leading_blank_pages(file_path)
        await paper_thumbnail_service.ensure_pdf_thumbnail(
            cache_seed=cache_seed,
            file_path=str(file_path),
        )


async def _warm_public_paper_thumbnails(
    *,
    paper_id: str,
    translated_asset: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        source_preview = await resolve_paper_source_pdf_preview(paper_id=paper_id)
        if source_preview.get("signed_url"):
            asset = source_preview.get("asset") or {}
            cache_seed = f"source-object:{paper_id}:{asset.get('id') or source_preview.get('filename') or paper_id}"
            await paper_thumbnail_service.ensure_pdf_thumbnail(
                cache_seed=cache_seed,
                remote_url=str(source_preview["signed_url"]),
            )
        elif source_preview.get("file_path"):
            resolved_path = Path(str(source_preview["file_path"]))
            if resolved_path.exists():
                stat = resolved_path.stat()
                await paper_thumbnail_service.ensure_pdf_thumbnail(
                    cache_seed=f"source-file:{resolved_path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}",
                    file_path=str(resolved_path),
                )
        elif source_preview.get("arxiv_id"):
            await paper_thumbnail_service.ensure_pdf_thumbnail(
                cache_seed=f"source-arxiv:{source_preview['arxiv_id']}",
                remote_url=f"https://arxiv.org/pdf/{source_preview['arxiv_id']}",
            )
    except Exception as exc:
        logger.debug("Source thumbnail warmup skipped for paper %s: %s", paper_id, exc)

    try:
        if translated_asset is None:
            translated_preview = await resolve_paper_translated_pdf_preview(paper_id=paper_id)
            translated_asset = translated_preview.get("asset")
        await _warm_translated_thumbnail_for_asset(paper_id=paper_id, asset=translated_asset)
    except Exception as exc:
        logger.debug("Translated thumbnail warmup skipped for paper %s: %s", paper_id, exc)


def _schedule_public_thumbnail_warmup(
    *,
    paper_id: str,
    translated_asset: Optional[Dict[str, Any]] = None,
) -> None:
    asyncio.create_task(
        _warm_public_paper_thumbnails(
            paper_id=paper_id,
            translated_asset=translated_asset,
        )
    )


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

    if translated_asset.get("storage_backend") == "object_storage":
        filename = str(translated_asset.get("file_name") or f"{paper_id}.pdf")
        mime_type = str(translated_asset.get("mime_type") or "application/octet-stream")
        signed_url = _resolve_object_storage_signed_url(
            translated_asset,
            expires_in=600,
            response_params={
                "response-content-disposition": f'attachment; filename="{filename}"',
                "response-content-type": mime_type,
            },
        )
        if not signed_url:
            raise HTTPException(status_code=404, detail="Translated PDF object not available")
        try:
            await _increment_paper_download_count(paper_id)
        except Exception as exc:
            logger.warning("Failed to increment download count for paper %s: %s", paper_id, exc)
        return {
            "paper_id": paper_id,
            "asset": translated_asset,
            "signed_url": signed_url,
        }

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
    offset: int = 0,
) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    normalized_limit = int(limit) if limit is not None and int(limit) > 0 else None
    normalized_offset = max(0, int(offset or 0))
    if not _normalize_search_text(q):
        cached_payload = await _list_public_papers_from_shared_feed_store(
            sort=sort,
            limit=normalized_limit,
            offset=normalized_offset,
        )
        if cached_payload is not None:
            return await _attach_viewer_state_to_feed_payload(
                cached_payload,
                viewer_user_id=viewer_user_id,
            )

    papers: List[Dict[str, Any]] = []
    source_mode = "database"
    total = 0
    try:
        if (
            normalized_limit is not None
            and hasattr(repository, "list_public_papers_page")
            and hasattr(repository, "count_public_papers")
        ):
            total = await _run_local_repo(lambda: repository.count_public_papers(query=q))
            papers = await _run_local_repo(
                lambda: repository.list_public_papers_page(
                    sort=sort,
                    query=q,
                    limit=normalized_limit,
                    offset=normalized_offset,
                )
            )
        else:
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
    if total <= 0 or normalized_limit is None or not hasattr(repository, "list_public_papers_page"):
        papers = [paper for paper in papers if _is_public_community_paper(paper)]
        papers = [paper for paper in papers if _matches_paper_query(paper, q)]
        papers = _sort_papers(papers, sort)
        total = len(papers)
        if normalized_offset:
            papers = papers[normalized_offset:]
        if normalized_limit is not None:
            papers = papers[:normalized_limit]

    papers = await _hydrate_public_feed_papers_if_needed(papers)
    paper_ids = [paper["id"] for paper in papers]
    asset_maps = await _fetch_asset_maps_for_papers(paper_ids) if paper_ids else {}
    items = [
        _paper_feed_summary(
            paper,
            asset_map=asset_maps.get(paper["id"]),
        )
        for paper in papers
    ]
    has_more = (normalized_offset + len(items)) < total
    payload = {
        "items": items,
        "total": total,
        "offset": normalized_offset,
        "limit": normalized_limit,
        "has_more": has_more,
        "next_offset": (normalized_offset + len(items)) if has_more else None,
        "source_mode": source_mode,
    }
    _set_cached_public_feed_payload(
        sort=sort,
        query=q,
        limit=normalized_limit,
        offset=normalized_offset,
        payload=payload,
    )
    return await _attach_viewer_state_to_feed_payload(
        payload,
        viewer_user_id=viewer_user_id,
    )


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
        {"liked": False, "favorited": False, "favorite_folder_count": 0},
    )
    structured_insights = _build_structured_insights_payload(
        await _fetch_structured_insight_sections(paper_id)
    )
    resolved_asset_map: Dict[str, Dict[str, Any]] = dict(asset_map or {})
    preview_bootstrap: Optional[Dict[str, Any]] = None

    preview_asset = resolved_asset_map.get("preview_html")
    if preview_asset:
        preview_bootstrap = _build_preview_bootstrap_payload(
            paper_id=paper_id,
            paper=paper,
            preview_asset=preview_asset,
        )

    if not preview_bootstrap:
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
            preview_bootstrap = _build_preview_bootstrap_payload(
                paper_id=paper_id,
                paper=paper,
                preview_asset=preview_asset,
            )
            if preview_bootstrap:
                break

    translated_asset = await _ensure_translated_pdf_asset(
        paper=paper,
        asset_map=resolved_asset_map,
    )

    if not preview_bootstrap and paper.get("trans_status") in {"completed", "completed_with_warnings"}:
        _schedule_preview_recovery(
            paper_id=paper_id,
            paper=paper,
            asset_map=resolved_asset_map,
        )

    source_html_content = (
        None
        if fast_path
        else await _fetch_sanitized_arxiv_html(str(paper.get("arxiv_id") or ""))
    )

    reader_payload = _build_reader_experience_payload(
        paper=paper,
        paper_id=paper_id,
        preview_payload=preview_bootstrap,
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
        "preview": preview_bootstrap,
        "reader_state": reader_payload["reader_state"],
        "reader": reader_payload["reader"],
        "experience": reader_payload["experience"],
        "structured_insights": structured_insights,
    }


async def get_community_paper_similar(*, paper_id: str) -> Dict[str, Any]:
    await _ensure_public_paper(paper_id)
    return {"items": await _fetch_persisted_similar_recommendations(paper_id)}


def _favorite_folder_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FavoriteFolderLimitError):
        return HTTPException(status_code=400, detail="Favorite folder limit reached")
    if isinstance(exc, FavoriteFolderNameConflictError):
        return HTTPException(status_code=409, detail="Favorite folder name already exists")
    if isinstance(exc, FavoriteFolderNotFoundError):
        return HTTPException(status_code=404, detail="Favorite folder not found")
    if isinstance(exc, ValueError) and str(exc) == "folder_name_required":
        return HTTPException(status_code=400, detail="Favorite folder name is required")
    return HTTPException(status_code=500, detail="Favorite folder operation failed")


async def list_favorite_folders(*, user_id: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        items = await _run_local_repo(lambda: repository.list_favorite_folders(user_id=user_id))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to list favorite folders for user %s: %s", user_id, exc)
        raise _favorite_folder_http_error(exc) from exc
    return {"items": items}


async def create_favorite_folder(*, user_id: str, name: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        folder = await _run_local_repo(lambda: repository.create_favorite_folder(user_id=user_id, name=name))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to create favorite folder for user %s: %s", user_id, exc)
        raise _favorite_folder_http_error(exc) from exc
    return {"folder": folder}


async def rename_favorite_folder(*, folder_id: str, user_id: str, name: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        folder = await _run_local_repo(
            lambda: repository.rename_favorite_folder(folder_id=folder_id, user_id=user_id, name=name)
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to rename favorite folder %s for user %s: %s", folder_id, user_id, exc)
        raise _favorite_folder_http_error(exc) from exc
    return {"folder": folder}


async def delete_favorite_folder(*, folder_id: str, user_id: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        affected_paper_ids = await _run_local_repo(
            lambda: repository.delete_favorite_folder(folder_id=folder_id, user_id=user_id)
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to delete favorite folder %s for user %s: %s", folder_id, user_id, exc)
        raise _favorite_folder_http_error(exc) from exc
    if affected_paper_ids:
        invalidate_public_feed_cache()
    return {"folder_id": folder_id, "deleted": True}


async def get_paper_favorite_folders(*, paper_id: str, user_id: str) -> Dict[str, Any]:
    await _ensure_public_paper(paper_id)
    repository = get_community_paper_repository()
    try:
        folders, selected_folder_ids = await asyncio.gather(
            _run_local_repo(lambda: repository.list_favorite_folders(user_id=user_id)),
            _run_local_repo(lambda: repository.list_paper_favorite_folder_ids(paper_id=paper_id, user_id=user_id)),
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to fetch favorite picker state for paper %s user %s: %s", paper_id, user_id, exc)
        raise _favorite_folder_http_error(exc) from exc
    return {
        "paper_id": paper_id,
        "items": folders,
        "selected_folder_ids": selected_folder_ids,
        "favorited": len(selected_folder_ids) > 0,
        "favorite_folder_count": len(selected_folder_ids),
    }


async def update_paper_favorite_folders(
    *,
    paper_id: str,
    user_id: str,
    folder_ids: list[str],
) -> Dict[str, Any]:
    await _ensure_public_paper(paper_id)
    repository = get_community_paper_repository()
    try:
        payload = await _run_local_repo(
            lambda: repository.sync_paper_favorite_folders(
                paper_id=paper_id,
                user_id=user_id,
                folder_ids=folder_ids,
            )
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to sync favorite folders for paper %s user %s: %s", paper_id, user_id, exc)
        raise _favorite_folder_http_error(exc) from exc
    invalidate_public_feed_cache()
    return payload


async def get_favorite_folder_papers(*, folder_id: str, user_id: str) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        folder, papers = await _run_local_repo(
            lambda: repository.list_favorite_folder_papers(folder_id=folder_id, user_id=user_id)
        )
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to list favorite folder papers for folder %s user %s: %s", folder_id, user_id, exc)
        raise _favorite_folder_http_error(exc) from exc

    paper_ids = [str(paper.get("id") or "").strip() for paper in papers if str(paper.get("id") or "").strip()]
    asset_maps = await _fetch_asset_maps_for_papers(paper_ids) if paper_ids else {}
    viewer_states = await _fetch_viewer_state(paper_ids, user_id=user_id) if paper_ids else {}
    items = [
        _paper_feed_summary(
            paper,
            asset_map=asset_maps.get(paper["id"]),
        )
        for paper in papers
    ]
    for item in items:
        paper_id = str(item.get("id") or "").strip()
        if paper_id:
            item["viewer_state"] = viewer_states.get(
                paper_id,
                {"liked": False, "favorited": False, "favorite_folder_count": 0},
            )
    return {"folder": folder, "items": items, "total": len(items)}


async def like_paper(*, paper_id: str, user_id: str) -> Dict[str, Any]:
    await _ensure_public_paper(paper_id)
    repository = get_community_paper_repository()
    try:
        like_count = await _run_local_repo(lambda: repository.like_paper(paper_id=paper_id, user_id=user_id))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to like paper %s for user %s: %s", paper_id, user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to like paper") from exc
    await _refresh_public_feed_rankings_for_paper(paper_id=paper_id, like_delta=1)
    return {"paper_id": paper_id, "liked": True, "like_count": like_count}


async def unlike_paper(*, paper_id: str, user_id: str) -> Dict[str, Any]:
    await _ensure_public_paper(paper_id)
    repository = get_community_paper_repository()
    try:
        like_count = await _run_local_repo(lambda: repository.unlike_paper(paper_id=paper_id, user_id=user_id))
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Local database unavailable") from exc
    except Exception as exc:
        logger.warning("Failed to unlike paper %s for user %s: %s", paper_id, user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to unlike paper") from exc
    await _refresh_public_feed_rankings_for_paper(paper_id=paper_id, like_delta=-1)
    return {"paper_id": paper_id, "liked": False, "like_count": like_count}


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


async def record_community_paper_view(
    *,
    paper_id: str,
    user_id: Optional[str] = None,
    anon_id: Optional[str] = None,
) -> Dict[str, Any]:
    repository = get_community_paper_repository()
    try:
        if hasattr(repository, "record_daily_view"):
            count = await _run_local_repo(
                lambda: repository.record_daily_view(
                    paper_id=paper_id,
                    user_id=user_id,
                    anon_id=anon_id,
                )
            )
        else:
            count = await _run_local_repo(lambda: repository.increment_view_count(paper_id))
    except DatabaseUnavailableError:
        count = None
    except Exception as exc:
        logger.warning("Failed to increment view count for paper %s locally: %s", paper_id, exc)
        count = None
    if count is not None:
        await _refresh_public_feed_rankings_for_paper(paper_id=paper_id)
        return {"paper_id": paper_id, "view_count": count}
    paper = await _fetch_paper_by_id(paper_id)
    if paper is None or paper.get("visibility") != "public" or paper.get("status") == "removed":
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"paper_id": paper_id, "view_count": int(paper.get("view_count") or 0)}




