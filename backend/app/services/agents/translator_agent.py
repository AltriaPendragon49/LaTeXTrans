from typing import Dict, Any, List, Optional, Callable, Tuple
from .base_tool_agent import BaseToolAgent
from .validator_agent import ERROR_TYPE_A, ERROR_TYPE_B, ERROR_TYPE_C, ERROR_TYPE_C1, ERROR_TYPE_C2, ValidatorAgent
from .pipeline_schema import FallbackReport
from .pipeline_invariants import (
    HardFreezeProtocolViolation,
    PipelineInvariantViolation,
    SpeculativeRepairForbiddenError,
    assert_no_raw_structure,
)
from . import global_llm_semaphore
import backend.app.services.latex.prompts as pm
from backend.app.services.latex.utils import *
from backend.app.services.latex.utils import (
    mask_residual_structure_tokens,
    mask_sensitive_commands,
    unmask_sensitive_commands,
)
from backend.app.core.timezone_utils import get_cst_now
from backend.app.core.config import settings
from .llm_runtime import (
    build_llm_client_timeout,
    resolve_llm_max_concurrent_requests,
    resolve_llm_timeout,
)
from pathlib import Path
import os
import re
import regex
import asyncio
import aiohttp
import time
import pandas as pd
import logging
import json
from datetime import datetime, timezone
from difflib import SequenceMatcher
from collections import Counter
try:
    from backend.app.services.latex.token_estimator import (
        estimate_tokens_v1,
        safe_limit_v1,
        SAFE_LIMIT_DIGEST_V1,
        SAFE_LIMIT_ID_V1,
        TOKEN_ESTIMATOR_DIGEST_V1,
        TOKEN_ESTIMATOR_ID_V1,
    )
except Exception:
    # Fallback to keep runtime deterministic even if the helper module is unavailable.
    from hashlib import sha256
    from math import ceil, floor

    TOKEN_ESTIMATOR_ID_V1 = "estimate_tokens_v1"
    SAFE_LIMIT_ID_V1 = "safe_limit_v1"
    TOKEN_ESTIMATOR_DIGEST_V1 = sha256(
        f"{TOKEN_ESTIMATOR_ID_V1}:ceil(len(utf8_bytes)/3)".encode("utf-8")
    ).hexdigest()
    SAFE_LIMIT_DIGEST_V1 = sha256(
        f"{SAFE_LIMIT_ID_V1}:max(1, floor(model_context_tokens*0.7)-prompt_reserve_tokens)".encode("utf-8")
    ).hexdigest()

    def estimate_tokens_v1(text: str) -> int:
        if not text:
            return 0
        return int(ceil(len(text.encode("utf-8")) / 3.0))

    def safe_limit_v1(model_context_tokens: int, prompt_reserve_tokens: int) -> int:
        ctx = max(int(model_context_tokens or 0), 0)
        reserve = max(int(prompt_reserve_tokens or 0), 0)
        return max(1, int(floor(ctx * 0.7) - reserve))

logger = logging.getLogger(__name__)


class TranslatorAgent(BaseToolAgent):
    STATUS_TRANSLATED = "translated"
    STATUS_TRANSLATED_AFTER_NOOP_RETRY = "translated_after_noop_retry"
    STATUS_FALLBACK_SOURCE_COMPILE_FIRST = "fallback_source_compile_first"
    STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE = "structural_fallback_pending_compile"
    STATUS_FALLBACK_SOURCE_API_FAILURE = "fallback_source_api_failure"
    STATUS_PAYLOAD_INVARIANT_PASSTHROUGH = "payload_invariant_passthrough"
    STATUS_SOURCE_PASS_THROUGH = "source_pass_through"
    STATUS_IMMUTABLE_PASSTHROUGH = "immutable_passthrough"
    STATUS_REPAIR_SKIPPED_NON_TRANSLATABLE = "repair_skipped_non_translatable"
    STATUS_MATH_PRESERVED = "math_preserved"
    FALLBACK_SUBTYPE_NONE = "none"
    FALLBACK_SUBTYPE_MATH_ENV = "math_env_fallback"
    FALLBACK_SUBTYPE_LIST_ENV = "list_env_fallback"
    FALLBACK_SUBTYPE_OTHER_ENV = "other_env_fallback"
    GENERIC_TEXT_ENVS = frozenset({
        "abstract",
        "promptbox",
        "quote",
        "quotation",
        "remark",
        "proof",
        "definition",
        "example",
        "theorem",
        "lemma",
        "proposition",
        "corollary",
    })
    _RESCUE_PLACEHOLDER_RE = re.compile(r"(<PLACEHOLDER_[A-Z0-9_]+>)")
    _RESCUE_TOKEN_RE = re.compile(
        r"(<(?:PLACEHOLDER|PROTECTED_CMD|ENV(?:_BEGIN|_END)?|ITEM|EQROW|EQCOMMENT|INLMATH)_[^>]+>)"
    )
    _RESCUE_FRAGMENT_RE = re.compile(
        r".+?(?:[。！？!?;；](?:\s+|$)|[.:：](?=\s|$)(?:\s+|$)|\n|$)",
        re.S,
    )
    _TERMINAL_NO_RETRY_STATUSES = frozenset({
        STATUS_TRANSLATED,
        STATUS_TRANSLATED_AFTER_NOOP_RETRY,
        STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
        STATUS_SOURCE_PASS_THROUGH,
        STATUS_IMMUTABLE_PASSTHROUGH,
        STATUS_MATH_PRESERVED,
    })

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        """Safely coerce env/config style values to bool."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return default

    def __init__(self, 
                 config: Dict[str, Any], 
                 trans_mode: int = 0,
                 project_dir: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 errors_report: Optional[List[Dict]] = None,
                 generate_terminology: bool = False,
                 on_progress: Optional[Callable[[int, str], None]] = None,
                 ):
        super().__init__(agent_name="TranslatorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.update_term = config.get("update_term", False)
        self.model = config["llm_config"].get("model", "gpt-4o")
        self.base_url = config["llm_config"].get("base_url", None)
        self.API_KEY = config["llm_config"].get("api_key", None)
        self.user_term = config.get("user_term", None)
        self.target_language = config.get("target_language", "ch")
        self.category = config.get("category", None)
        self.project_dir = project_dir  # Project path for parsing
        self.output_dir = output_dir  # Output directory for parsed files
        self.fail_section_nums = []
        self.fail_caption_phs = []
        self.fail_env_phs = []
        self.have_fail_parts = False
        self.errors_report = errors_report if errors_report is not None else []
        self.trans_mode = trans_mode if trans_mode is not None else 0
        self.generate_terminology = generate_terminology
        self.terminology_table = []  # 瀛樺偍鏈瀵? [(婧愭湳璇? 璇戞湳璇?, ...]
        self.term_dict = {}
        self.request_timeout_seconds = resolve_llm_timeout(config, default=settings.llm_timeout)
        self.llm_max_concurrent_requests = resolve_llm_max_concurrent_requests(
            config,
            default=settings.llm_max_concurrent_requests,
        )
        self.summary = ''
        self.prev_text = ''
        self.prev_transed_text = ''
        self.currant_content = ''
        self.enable_compile_first_structural_fallback = self._coerce_bool(
            config.get("enable_compile_first_structural_fallback", False),
            default=False,
        )
        self.enable_post_compile_target_language_fallback = self._coerce_bool(
            config.get("enable_post_compile_target_language_fallback", True),
            default=True,
        )
        self.structural_fallback_cap = float(config.get("structural_fallback_ratio_cap", 0.10) or 0.10)
        self.structural_fallback_cap_mode = str(config.get("structural_fallback_cap_mode", "soft") or "soft").lower()
        if self.structural_fallback_cap_mode not in {"soft", "hard"}:
            self.structural_fallback_cap_mode = "soft"
        self.structural_fallback_count = 0
        self.structural_fallback_candidate_count = 0
        self.structural_fallback_denominator = 0
        self.structural_fallback_ratio = 0.0
        self.structural_fallback_warning: Optional[str] = None
        self._structural_validator: Optional[ValidatorAgent] = None
        self._section_retry_counts: Dict[str, int] = {}
        self._c1_retried_parts: set[str] = set()
        self._api_fallback_parts: Dict[str, str] = {}
        self.c1_retry_enforced_once = False
        self.structural_fallback_parts: List[str] = []
        self.noop_sections: List[str] = []
        self.payload_invariant_sections: List[str] = []
        self._oversize_downgrade_events: List[Dict[str, Any]] = []
        # eliminate-silent-fallback: structured fallback reports for repair loop
        self.fallback_reports: List[FallbackReport] = []
        (
            self.model_context_tokens,
            self.prompt_reserve_tokens,
            self.safe_input_limit,
        ) = self._resolve_safe_limit_config()

    @staticmethod
    def _part_retry_key(part_type: str, identifier: str) -> str:
        return f"part:{part_type}:{identifier}"

    @staticmethod
    def _resolve_positive_int(value: Any, default: int) -> int:
        try:
            parsed = int(value)
            return parsed if parsed > 0 else int(default)
        except (TypeError, ValueError):
            return int(default)

    def _resolve_safe_limit_config(self) -> Tuple[int, int, int]:
        llm_cfg = self.config.get("llm_config", {}) or {}
        default_context = 128000
        default_reserve = 4096

        model_context_tokens = self._resolve_positive_int(
            self.config.get("model_context_tokens")
            or self.config.get("llm_context_tokens")
            or llm_cfg.get("model_context_tokens")
            or llm_cfg.get("context_window")
            or llm_cfg.get("max_context_tokens"),
            default_context,
        )
        prompt_reserve_tokens = self._resolve_positive_int(
            self.config.get("prompt_reserve_tokens")
            or self.config.get("llm_prompt_reserve_tokens")
            or llm_cfg.get("prompt_reserve_tokens")
            or llm_cfg.get("reserve_tokens"),
            default_reserve,
        )
        safe_input_limit = safe_limit_v1(model_context_tokens, prompt_reserve_tokens)
        return model_context_tokens, prompt_reserve_tokens, safe_input_limit

    @staticmethod
    def _extract_chunk_index(section_id: str) -> Optional[int]:
        if not section_id:
            return None
        m = re.search(r"_chunk_(\d+)$", section_id)
        if not m:
            return None
        try:
            return int(m.group(1))
        except (TypeError, ValueError):
            return None

    def _evaluate_oversize_downgrade(self, section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not section.get("oversize_no_safe_boundary"):
            return None
        content = section.get("content", "") or ""
        estimated_tokens = estimate_tokens_v1(content)
        if estimated_tokens <= self.safe_input_limit:
            return None

        section_id = str(section.get("section", ""))
        return {
            "section_id": section_id,
            "chunk_id": self._extract_chunk_index(section_id),
            "strategy": "source_pass_through",
            "reason": "oversize_no_safe_boundary",
            "token_estimator_id": TOKEN_ESTIMATOR_ID_V1,
            "token_estimator_digest": TOKEN_ESTIMATOR_DIGEST_V1,
            "estimated_tokens": estimated_tokens,
            "safe_limit_id": SAFE_LIMIT_ID_V1,
            "safe_limit_digest": SAFE_LIMIT_DIGEST_V1,
            "model_context_tokens": self.model_context_tokens,
            "prompt_reserve_tokens": self.prompt_reserve_tokens,
            "safe_input_limit": self.safe_input_limit,
        }

    def _record_oversize_downgrade(self, metadata: Dict[str, Any]) -> None:
        if not metadata:
            return
        event = {
            "timestamp": get_cst_now().isoformat(),
            "event": "oversize_chunk_downgraded",
            **metadata,
        }
        self._oversize_downgrade_events.append(event)
        # eliminate-silent-fallback: emit structured FallbackReport for repair loop
        try:
            report = FallbackReport(
                fallback_kind="oversize_downgrade",
                chunk_scope=str(metadata.get("section_id", "")),
                root_cause=str(metadata.get("reason", "oversize_no_safe_boundary")),
                validation_evidence=None,
                translated_text=None,
            )
            self.fallback_reports.append(report)
        except Exception as _fr_exc:
            logger.warning("Failed to emit FallbackReport for oversize downgrade: %s", _fr_exc)

    def _flush_oversize_downgrade_events(self) -> None:
        if not self._oversize_downgrade_events or not self.output_dir:
            return

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        events = list(self._oversize_downgrade_events)
        self._oversize_downgrade_events.clear()

        task_log_path = output_dir / "task_log.json"
        task_logs: List[Dict[str, Any]] = []
        if task_log_path.exists():
            try:
                loaded = json.loads(task_log_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    task_logs = loaded
            except Exception as exc:
                logger.warning("Failed to load existing task log for oversize events: %s", exc)
        task_logs.extend(events)
        try:
            task_log_path.write_text(
                json.dumps(task_logs, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to persist oversize task log events: %s", exc)

        replay_path = output_dir / "replay_bundle.json"
        replay_bundle: Dict[str, Any] = {}
        if replay_path.exists():
            try:
                loaded = json.loads(replay_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    replay_bundle = loaded
            except Exception as exc:
                logger.warning("Failed to load replay bundle for oversize events: %s", exc)

        replay_bundle.setdefault("replay_version", "v1")
        replay_bundle.setdefault("token_estimator_id", TOKEN_ESTIMATOR_ID_V1)
        replay_bundle.setdefault("token_estimator_digest", TOKEN_ESTIMATOR_DIGEST_V1)
        replay_bundle.setdefault("safe_limit_id", SAFE_LIMIT_ID_V1)
        replay_bundle.setdefault("safe_limit_digest", SAFE_LIMIT_DIGEST_V1)
        replay_bundle.setdefault("model_context_tokens", self.model_context_tokens)
        replay_bundle.setdefault("prompt_reserve_tokens", self.prompt_reserve_tokens)
        replay_bundle.setdefault("safe_input_limit", self.safe_input_limit)
        replay_bundle.setdefault("oversize_chunk_downgrades", [])
        if isinstance(replay_bundle["oversize_chunk_downgrades"], list):
            replay_bundle["oversize_chunk_downgrades"].extend(events)
        else:
            replay_bundle["oversize_chunk_downgrades"] = list(events)
        try:
            replay_path.write_text(
                json.dumps(replay_bundle, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to persist replay bundle oversize events: %s", exc)

    def _mark_api_fallback(self, part_type: str, identifier: str, reason: str) -> None:
        key = self._part_retry_key(part_type, identifier)
        self._api_fallback_parts[key] = reason

    def _clear_api_fallback(self, part_type: str, identifier: str) -> None:
        key = self._part_retry_key(part_type, identifier)
        self._api_fallback_parts.pop(key, None)

    @staticmethod
    def _normalize_llm_failure_identifier(part_type: str, identifier: str) -> str:
        normalized = str(identifier or "").strip()
        if not normalized:
            return normalized
        if part_type == "env":
            env_row_match = re.match(r"part:env:(<[^>]+>):", normalized)
            if env_row_match:
                return env_row_match.group(1)
        return normalized.split(":", 1)[0]

    def _recompute_have_fail_parts(self) -> None:
        self.have_fail_parts = bool(
            self.fail_section_nums or self.fail_caption_phs or self.fail_env_phs
        )

    def _clear_llm_part_failure(self, part_type: str, identifier: str) -> None:
        normalized = self._normalize_llm_failure_identifier(part_type, identifier)
        if not normalized:
            self._recompute_have_fail_parts()
            return
        if part_type == "sec":
            self.fail_section_nums = [item for item in self.fail_section_nums if item != normalized]
        elif part_type == "cap":
            self.fail_caption_phs = [item for item in self.fail_caption_phs if item != normalized]
        else:
            self.fail_env_phs = [item for item in self.fail_env_phs if item != normalized]
        self._recompute_have_fail_parts()

    def _clear_llm_part_failure_if_terminal(self, part_type: str, identifier: str, status: Optional[str]) -> None:
        if status in self._TERMINAL_NO_RETRY_STATUSES:
            self._clear_llm_part_failure(part_type, identifier)

    def _record_noop_section(self, section_id: str) -> None:
        if section_id not in self.noop_sections:
            self.noop_sections.append(section_id)

    def _record_payload_invariant_section(self, section_id: str) -> None:
        if section_id not in self.payload_invariant_sections:
            self.payload_invariant_sections.append(section_id)

    def _sync_section_retry_count(self, section_id: str, section: Dict[str, Any]) -> None:
        if section_id not in self._section_retry_counts:
            raw = section.get("translation_retry_count", 0)
            try:
                self._section_retry_counts[section_id] = int(raw or 0)
            except (TypeError, ValueError):
                self._section_retry_counts[section_id] = 0

    def _increment_section_retry_count(self, section_id: str, delta: int = 1) -> None:
        current = int(self._section_retry_counts.get(section_id, 0) or 0)
        self._section_retry_counts[section_id] = current + max(delta, 0)

    def _update_section_metadata(
        self,
        section: Dict[str, Any],
        *,
        status: Optional[str] = None,
        no_op_detected: Optional[bool] = None,
        fallback_reason: Optional[str] = None,
    ) -> None:
        section_id = str(section.get("section", ""))
        if not section_id:
            return
        self._sync_section_retry_count(section_id, section)
        section["translation_retry_count"] = int(self._section_retry_counts.get(section_id, 0) or 0)
        if status:
            section["translation_status"] = status
        if no_op_detected is not None:
            section["no_op_detected"] = bool(no_op_detected)
        if fallback_reason:
            section["fallback_reason"] = fallback_reason
        elif status in {
            self.STATUS_TRANSLATED,
            self.STATUS_TRANSLATED_AFTER_NOOP_RETRY,
            self.STATUS_IMMUTABLE_PASSTHROUGH,
        }:
            section.pop("fallback_reason", None)
        self._clear_llm_part_failure_if_terminal("sec", section_id, section.get("translation_status"))

    def _update_env_metadata(
        self,
        env: Dict[str, Any],
        *,
        status: Optional[str] = None,
        fallback_reason: Optional[str] = None,
        fallback_subtype: Optional[str] = None,
        row_fallback_count: Optional[int] = None,
    ) -> None:
        if status:
            env["translation_status"] = status
        if fallback_reason:
            env["fallback_reason"] = fallback_reason
        elif status in {self.STATUS_TRANSLATED, self.STATUS_MATH_PRESERVED}:
            env.pop("fallback_reason", None)
        if fallback_subtype is not None:
            env["fallback_subtype"] = fallback_subtype
        if row_fallback_count is not None:
            env["row_fallback_count"] = max(int(row_fallback_count), 0)
        elif "row_fallback_count" not in env:
            env["row_fallback_count"] = 0
        self._clear_llm_part_failure_if_terminal(
            "env",
            str(env.get("placeholder", "")),
            env.get("translation_status"),
        )

    @staticmethod
    def _normalize_env_name(env_name: str) -> str:
        return (env_name or "").strip().lower()

    def _is_generic_text_env(self, env_name: str) -> bool:
        normalized = self._normalize_env_name(env_name)
        if normalized in self.GENERIC_TEXT_ENVS:
            return True
        if normalized.endswith("*") and normalized[:-1] in self.GENERIC_TEXT_ENVS:
            return True
        return False

    @staticmethod
    def _split_env_wrapper(content: str, env_name: str) -> Optional[Tuple[str, str, str]]:
        if not content or not env_name:
            return None
        pattern = re.compile(
            rf"(?s)\A(?P<head>\s*\\begin\{{{re.escape(env_name)}\}}(?:\s*\[[^\]]*\])?\s*)(?P<body>.*?)(?P<tail>\s*\\end\{{{re.escape(env_name)}\}}\s*)\Z"
        )
        match = pattern.match(content)
        if not match:
            return None
        return match.group("head"), match.group("body"), match.group("tail")

    def _is_immutable_section(self, section: Dict[str, Any]) -> bool:
        return bool(section.get("immutable_only")) or (
            section.get("translation_status") == self.STATUS_IMMUTABLE_PASSTHROUGH
        )

    @staticmethod
    def _get_section_translation_core(section: Dict[str, Any]) -> str:
        if "core_translatable_content" in section:
            return section.get("core_translatable_content") or ""
        return section.get("content", "") or ""

    @staticmethod
    def _section_has_structure_shell(section: Dict[str, Any]) -> bool:
        return bool(section.get("contains_structure_shell"))

    @staticmethod
    def _get_section_chunk_role(section: Dict[str, Any]) -> str:
        return str(section.get("chunk_role") or "normal")

    @classmethod
    def _is_document_root_section_chunk(cls, section: Dict[str, Any]) -> bool:
        if cls._get_section_chunk_role(section) == "document_root":
            return True
        content = section.get("content", "") or ""
        return bool(re.search(r"\\document(?:class|style)\b", content))

    @classmethod
    def _reassemble_section_translation(cls, section: Dict[str, Any], translated_core: str) -> str:
        if not cls._section_has_structure_shell(section):
            return translated_core
        return (
            f"{section.get('leading_structure_shell', '') or ''}"
            f"{translated_core or ''}"
            f"{section.get('trailing_structure_shell', '') or ''}"
        )

    @staticmethod
    def _is_payload_invariant_reason(reason: Optional[str]) -> bool:
        return str(reason or "").startswith("invariant_")

    def _infer_env_fallback_subtype(self, env: Dict[str, Any]) -> str:
        env_name = self._normalize_env_name(str(env.get("env_name", "")))
        if env_name in {"eqnarray", "eqnarray*"}:
            return self.FALLBACK_SUBTYPE_MATH_ENV
        if env_name in {"enumerate", "enumerate*", "itemize", "itemize*"}:
            return self.FALLBACK_SUBTYPE_LIST_ENV
        return self.FALLBACK_SUBTYPE_OTHER_ENV

    @staticmethod
    def _has_unrestored_env_artifacts(text: Optional[str]) -> bool:
        candidate = text or ""
        return "<ENV_RESTORE_FAILED>" in candidate or bool(
            re.search(r"<ENV(?:_BEGIN|_END)?_[^>]+>", candidate)
        )

    async def _retry_env_translation_on_restore_artifacts(
        self,
        *,
        env: Dict[str, Any],
        text: str,
        placeholder: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str] = None,
    ) -> Optional[str]:
        retry_hint = (
            "Previous output leaked internal placeholder tokens such as "
            "<ENV_BEGIN_...> or <ENV_END_...>. Translate the same content again into the "
            "target language, keep LaTeX commands unchanged, and do not output any "
            "angle-bracket placeholder tokens."
        )
        combined_error = f"{error_message}\n{retry_hint}" if error_message else retry_hint
        retried = await self._request_env_translation(
            env=env,
            text=text,
            placeholder=placeholder,
            session=session,
            error_message=combined_error,
        )
        if self._has_unrestored_env_artifacts(retried):
            return None
        return retried

    async def _recover_generic_text_env_body_as_plain_text(
        self,
        *,
        env: Dict[str, Any],
        text: str,
        placeholder: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str] = None,
    ) -> Optional[str]:
        recovery_hint = (
            "Previous environment-specific translation attempts failed structural restoration. "
            "Translate only the plain natural-language body into the target language. "
            "Do not output any synthetic placeholder tokens or environment boundary markers."
        )
        prompt_suffix = f"\n[Recovery Requirement]\n{recovery_hint}"
        if error_message:
            prompt_suffix += f"\n{error_message}"

        recovered = ""
        if self.trans_mode == 1:
            retry_part = {
                "content": text,
                "trans_content": env.get("trans_content", text),
            }
            recovered = await self._request_llm_for_retrans_error_parts(
                self.prompts["retrans_error_parts_system_prompt"],
                part=retry_part,
                error_message=recovery_hint if not error_message else f"{error_message}\n{recovery_hint}",
                fail_part=placeholder,
                type="env",
                session=session,
            )
        elif self.trans_mode == 2 and self.term_dict:
            recovered = await self._request_llm_for_trans_with_terms(
                self.prompts["section_system_prompt_with_dict"] + prompt_suffix,
                text,
                fail_part=placeholder,
                type="env",
                session=session,
            )
        else:
            recovered = await self._request_llm_for_trans(
                self.prompts["section_system_prompt"] + prompt_suffix,
                text,
                fail_part=placeholder,
                type="env",
                session=session,
            )

        if not isinstance(recovered, str):
            return None
        if not recovered:
            return None
        if self._has_unrestored_env_artifacts(recovered):
            return None
        if self._is_source_preserved_translation(text, recovered):
            return None
        return recovered

    async def _rescue_generic_text_env_by_paragraph(
        self,
        *,
        text: str,
        placeholder: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str] = None,
    ) -> Optional[str]:
        return await self._rescue_plain_text_by_paragraph(
            text=text,
            identifier=placeholder,
            part_type="env",
            session=session,
            error_message=error_message,
            prompt_key="section_system_prompt",
            prompt_key_with_terms="section_system_prompt_with_dict",
        )

    async def _rescue_plain_text_by_paragraph(
        self,
        *,
        text: str,
        identifier: str,
        part_type: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str] = None,
        prompt_key: str = "section_system_prompt",
        prompt_key_with_terms: Optional[str] = None,
    ) -> Optional[str]:
        normalized = (text or "").replace("\r\n", "\n")
        if not normalized.strip():
            return None

        paragraph_hint = (
            "Previous attempts preserved the source text or violated protected-token invariants. "
            "Translate each paragraph into the target language. "
            "Do not copy the English source. Keep LaTeX commands unchanged."
        )
        prompt_suffix = f"\n[Paragraph Rescue]\n{paragraph_hint}"
        if error_message:
            prompt_suffix += f"\n{error_message}"

        pieces = re.split(r"(\n\s*\n+)", normalized)
        rescued: List[str] = []
        translated_any = False

        for idx, piece in enumerate(pieces):
            if not piece or re.fullmatch(r"\n\s*\n+", piece):
                rescued.append(piece)
                continue
            if not piece.strip():
                rescued.append(piece)
                continue

            part_fail_key = f"{identifier}:paragraph:{idx}"
            rescued_piece = await self._translate_plain_text_rescue_piece(
                piece=piece,
                fail_part=part_fail_key,
                part_type=part_type,
                session=session,
                error_message=error_message,
                paragraph_hint=paragraph_hint,
                prompt_suffix=prompt_suffix,
                prompt_key=prompt_key,
                prompt_key_with_terms=prompt_key_with_terms,
            )
            if rescued_piece is None:
                rescued_piece = await self._translate_masked_plain_text_rescue_piece(
                    piece=piece,
                    fail_part=f"{part_fail_key}:masked",
                    part_type=part_type,
                    session=session,
                    error_message=error_message,
                    prompt_suffix=prompt_suffix,
                    prompt_key=prompt_key,
                    prompt_key_with_terms=prompt_key_with_terms,
                )
            if rescued_piece is None:
                rescued_piece = await self._rescue_plain_text_by_fragment(
                    text=piece,
                    identifier=part_fail_key,
                    part_type=part_type,
                    session=session,
                    error_message=error_message,
                    paragraph_hint=paragraph_hint,
                    prompt_suffix=prompt_suffix,
                    prompt_key=prompt_key,
                    prompt_key_with_terms=prompt_key_with_terms,
                )
            if rescued_piece is None:
                return None

            rescued.append(rescued_piece)
            translated_any = translated_any or not self._is_source_preserved_translation(piece, rescued_piece)

        combined = "".join(rescued)
        if not translated_any:
            return None
        if self._has_unrestored_env_artifacts(combined):
            return None
        if self._is_source_preserved_translation(text, combined):
            return None
        return combined

    @staticmethod
    def _prepare_plain_text_rescue_text(text: str) -> Tuple[str, Dict[str, Any]]:
        isolated_math_text, math_map = isolate_math_spans(text)
        isolated_env_text, env_map = isolate_env_blocks(isolated_math_text)
        masked_text, mask_mapping = mask_sensitive_commands(isolated_env_text)
        masked_text, mask_mapping = mask_residual_structure_tokens(
            masked_text,
            mapping=mask_mapping,
        )
        preprocessed_text = preprocess_risky_tokens(masked_text, math_map)
        return preprocessed_text, {
            "math_map": math_map,
            "env_map": env_map,
            "mask_mapping": mask_mapping,
        }

    @staticmethod
    def _restore_plain_text_rescue_text(text: str, context: Dict[str, Any]) -> str:
        math_map = context.get("math_map", {}) if context else {}
        env_map = context.get("env_map", {}) if context else {}
        mask_mapping = context.get("mask_mapping", {}) if context else {}
        try:
            unmasked = unmask_sensitive_commands(text, mask_mapping)
        except Exception:
            unmasked = text

        try:
            env_restored = restore_env_blocks(unmasked, env_map)
        except Exception:
            env_restored = unmasked

        try:
            return restore_inline_math(env_restored, math_map)
        except Exception:
            return env_restored

    @classmethod
    def _should_passthrough_rescue_fragment(cls, piece: str) -> bool:
        stripped = (piece or "").strip()
        if not stripped:
            return True
        if cls._RESCUE_TOKEN_RE.fullmatch(stripped):
            return True
        return re.search(r"[A-Za-z\u4e00-\u9fff]", stripped) is None

    @classmethod
    def _split_plain_text_rescue_fragments(cls, text: str) -> List[str]:
        if not text:
            return []
        pieces: List[str] = []
        for chunk in cls._RESCUE_TOKEN_RE.split(text):
            if not chunk:
                continue
            if cls._RESCUE_TOKEN_RE.fullmatch(chunk):
                pieces.append(chunk)
                continue
            subchunks = [match.group(0) for match in cls._RESCUE_FRAGMENT_RE.finditer(chunk)]
            pieces.extend(subchunks or [chunk])
        return pieces

    async def _translate_plain_text_rescue_piece(
        self,
        *,
        piece: str,
        fail_part: str,
        part_type: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str],
        paragraph_hint: str,
        prompt_suffix: str,
        prompt_key: str,
        prompt_key_with_terms: Optional[str],
    ) -> Optional[str]:
        if self._should_passthrough_rescue_fragment(piece):
            return piece

        leading_ws_match = re.match(r"^\s*", piece)
        trailing_ws_match = re.search(r"\s*$", piece)
        leading_ws = leading_ws_match.group(0) if leading_ws_match else ""
        trailing_ws = trailing_ws_match.group(0) if trailing_ws_match else ""

        if self.trans_mode == 1:
            retry_part = {
                "content": piece,
                "trans_content": piece,
            }
            rescued_piece = await self._request_llm_for_retrans_error_parts(
                self.prompts["retrans_error_parts_system_prompt"],
                part=retry_part,
                error_message=paragraph_hint if not error_message else f"{error_message}\n{paragraph_hint}",
                fail_part=fail_part,
                type=part_type,
                session=session,
            )
        elif self.trans_mode == 2 and prompt_key_with_terms and self.term_dict:
            rescued_piece = await self._request_llm_for_trans_with_terms(
                self.prompts[prompt_key_with_terms] + prompt_suffix,
                piece,
                fail_part=fail_part,
                type=part_type,
                session=session,
            )
        else:
            rescued_piece = await self._request_llm_for_trans(
                self.prompts[prompt_key] + prompt_suffix,
                piece,
                fail_part=fail_part,
                type=part_type,
                session=session,
            )

        allow_force_retry = (
            ":fragment:" in str(fail_part)
            or (
                "\\" not in piece
                and "<PLACEHOLDER_" not in piece
                and "<PROTECTED_CMD_" not in piece
            )
        )
        if allow_force_retry and self._is_source_preserved_translation(piece, rescued_piece):
            force_retry_hint = (
                f"{prompt_suffix}\n"
                "[Force Translation]\n"
                "The previous fragment remained in the source language. "
                "Translate this fragment into the target language now. "
                "Do not copy the English source text."
            )
            retry_fail_part = f"{fail_part}:force"
            if self.trans_mode == 1:
                retry_part = {
                    "content": piece,
                    "trans_content": piece,
                }
                rescued_piece = await self._request_llm_for_retrans_error_parts(
                    self.prompts["retrans_error_parts_system_prompt"],
                    part=retry_part,
                    error_message=force_retry_hint if not error_message else f"{error_message}\n{force_retry_hint}",
                    fail_part=retry_fail_part,
                    type=part_type,
                    session=session,
                )
            elif self.trans_mode == 2 and prompt_key_with_terms and self.term_dict:
                rescued_piece = await self._request_llm_for_trans_with_terms(
                    self.prompts[prompt_key_with_terms] + force_retry_hint,
                    piece,
                    fail_part=retry_fail_part,
                    type=part_type,
                    session=session,
                )
            else:
                rescued_piece = await self._request_llm_for_trans(
                    self.prompts[prompt_key] + force_retry_hint,
                    piece,
                    fail_part=retry_fail_part,
                    type=part_type,
                    session=session,
                )

        if not isinstance(rescued_piece, str) or not rescued_piece.strip():
            return None
        if leading_ws or trailing_ws:
            rescued_piece = f"{leading_ws}{rescued_piece.strip()}{trailing_ws}"
        if self._has_unrestored_env_artifacts(rescued_piece):
            return None
        if self._is_source_preserved_translation(piece, rescued_piece):
            return None
        return rescued_piece

    async def _translate_masked_plain_text_rescue_piece(
        self,
        *,
        piece: str,
        fail_part: str,
        part_type: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str],
        prompt_suffix: str,
        prompt_key: str,
        prompt_key_with_terms: Optional[str],
    ) -> Optional[str]:
        masked_piece, rescue_context = self._prepare_plain_text_rescue_text(piece)
        if not masked_piece.strip():
            return None

        if self.trans_mode == 1:
            retry_part = {
                "content": masked_piece,
                "trans_content": masked_piece,
            }
            translated_masked_piece = await self._request_llm_for_retrans_error_parts(
                self.prompts["retrans_error_parts_system_prompt"],
                part=retry_part,
                error_message=error_message or prompt_suffix,
                fail_part=fail_part,
                type=part_type,
                session=session,
            )
        elif self.trans_mode == 2 and prompt_key_with_terms and self.term_dict:
            translated_masked_piece = await self._request_llm_for_trans_with_terms(
                self.prompts[prompt_key_with_terms] + prompt_suffix,
                masked_piece,
                fail_part=fail_part,
                type=part_type,
                session=session,
            )
        else:
            translated_masked_piece = await self._request_llm_for_trans(
                self.prompts[prompt_key] + prompt_suffix,
                masked_piece,
                fail_part=fail_part,
                type=part_type,
                session=session,
            )

        if not isinstance(translated_masked_piece, str) or not translated_masked_piece.strip():
            return None

        restored_piece = self._restore_plain_text_rescue_text(
            translated_masked_piece,
            rescue_context,
        )
        if self._has_unrestored_env_artifacts(restored_piece):
            return None
        if self._is_source_preserved_translation(piece, restored_piece):
            return None
        return restored_piece

    async def _rescue_plain_text_by_fragment(
        self,
        *,
        text: str,
        identifier: str,
        part_type: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str],
        paragraph_hint: str,
        prompt_suffix: str,
        prompt_key: str,
        prompt_key_with_terms: Optional[str],
    ) -> Optional[str]:
        masked_text, rescue_context = self._prepare_plain_text_rescue_text(text)
        fragments = self._split_plain_text_rescue_fragments(masked_text)
        translatable_fragments = [
            fragment for fragment in fragments if not self._should_passthrough_rescue_fragment(fragment)
        ]
        if len(translatable_fragments) <= 1:
            return None

        rescued: List[str] = []
        translated_any = False
        for idx, fragment in enumerate(fragments):
            if self._should_passthrough_rescue_fragment(fragment):
                rescued.append(fragment)
                continue
            rescued_fragment = await self._translate_plain_text_rescue_piece(
                piece=fragment,
                fail_part=f"{identifier}:fragment:{idx}",
                part_type=part_type,
                session=session,
                error_message=error_message,
                paragraph_hint=paragraph_hint,
                prompt_suffix=prompt_suffix,
                prompt_key=prompt_key,
                prompt_key_with_terms=prompt_key_with_terms,
            )
            if rescued_fragment is None:
                return None
            translated_any = translated_any or not self._is_source_preserved_translation(fragment, rescued_fragment)
            rescued.append(rescued_fragment)

        combined = "".join(rescued)
        restored = self._restore_plain_text_rescue_text(combined, rescue_context)
        if not translated_any:
            return None
        if self._has_unrestored_env_artifacts(restored):
            return None
        if self._is_source_preserved_translation(text, restored):
            return None
        return restored

    @staticmethod
    def _env_row_retry_key(placeholder: str, row_idx: int) -> str:
        return f"part:env:{placeholder}:row:{row_idx}"

    @staticmethod
    def _is_noop_translation(original: str, translated: str) -> bool:
        if not original or not translated:
            return False
        normalized_src = re.sub(r"\s+", " ", original).strip()
        normalized_tgt = re.sub(r"\s+", " ", translated).strip()
        if not normalized_src or not normalized_tgt:
            return False
        similarity = SequenceMatcher(None, normalized_src, normalized_tgt).ratio()
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", translated))
        en_words = len(re.findall(r"\b[A-Za-z]{3,}\b", translated))
        return similarity >= 0.97 and cjk_count < 16 and en_words >= 80

    @classmethod
    def _is_source_preserved_translation(cls, original: str, translated: str) -> bool:
        if not original or not translated:
            return False
        normalized_src = re.sub(r"\s+", " ", original).strip()
        normalized_tgt = re.sub(r"\s+", " ", translated).strip()
        if not normalized_src or not normalized_tgt:
            return False
        return normalized_src == normalized_tgt or cls._is_noop_translation(original, translated)

    def _prepare_llm_payload_text(self, text: str) -> Tuple[str, Dict[str, Any]]:
        isolated_math_text, math_map = isolate_math_spans(text)
        isolated_env_text, env_map = isolate_env_blocks(isolated_math_text)
        masked_text, mask_mapping = mask_sensitive_commands(isolated_env_text)
        masked_text, mask_mapping = mask_residual_structure_tokens(
            masked_text,
            mapping=mask_mapping,
        )
        preprocessed_text = preprocess_risky_tokens(masked_text, math_map)
        masked_text = preprocessed_text
        frozen_text, hard_freeze_context = freeze_protected_tokens(masked_text)
        return frozen_text, {
            "math_map": math_map,
            "env_map": env_map,
            "mask_mapping": mask_mapping,
            "hard_freeze_request_nonce": hard_freeze_context.get("request_nonce", ""),
            "hard_freeze_token_map": hard_freeze_context.get("token_map", {}),
            "hard_freeze_token_sequence": hard_freeze_context.get("token_sequence", []),
            "hard_freeze_audit_entries": hard_freeze_context.get("audit_entries", []),
        }

    def _restore_llm_output_text(self, raw_text: str, context: Dict[str, Any]) -> str:
        math_map = context.get("math_map", {}) if context else {}
        env_map = context.get("env_map", {}) if context else {}
        mask_mapping = context.get("mask_mapping", {}) if context else {}
        hard_freeze_token_map = context.get("hard_freeze_token_map", {}) if context else {}
        hard_freeze_token_sequence = context.get("hard_freeze_token_sequence", []) if context else []
        try:
            verify_hard_freeze_token_stream(raw_text, hard_freeze_token_sequence)
            hard_freeze_restored = restore_hard_freeze_tokens(raw_text, hard_freeze_token_map)
        except Exception as exc:
            raise HardFreezeProtocolViolation(str(exc)) from exc
        try:
            unmasked = unmask_sensitive_commands(hard_freeze_restored, mask_mapping)
        except Exception:
            unmasked = hard_freeze_restored

        try:
            env_restored = restore_env_blocks(unmasked, env_map)
        except Exception as env_exc:
            logger.warning("LLM env restoration failed: %s", env_exc)
            env_restored = f"{unmasked}\n<ENV_RESTORE_FAILED>"

        try:
            return restore_inline_math(env_restored, math_map)
        except Exception:
            return env_restored

    def _register_llm_part_failure(self, part_type: str, identifier: str) -> None:
        normalized = self._normalize_llm_failure_identifier(part_type, identifier)
        if not normalized:
            self._recompute_have_fail_parts()
            return
        if part_type == "sec":
            if normalized not in self.fail_section_nums:
                self.fail_section_nums.append(normalized)
        elif part_type == "cap":
            if normalized not in self.fail_caption_phs:
                self.fail_caption_phs.append(normalized)
        else:
            if normalized not in self.fail_env_phs:
                self.fail_env_phs.append(normalized)
        self._recompute_have_fail_parts()

    def _resolve_api_fallback_status(
        self,
        reason: Optional[str],
        *,
        default_success_status: str = STATUS_TRANSLATED,
    ) -> str:
        if not reason:
            return default_success_status
        if self._is_payload_invariant_reason(reason):
            return self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH
        return self.STATUS_FALLBACK_SOURCE_API_FAILURE

    def _should_skip_fail_part_retry(self, part: Dict[str, Any]) -> bool:
        status = str(part.get("translation_status") or "")
        return status in {
            self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
            self.STATUS_SOURCE_PASS_THROUGH,
            self.STATUS_IMMUTABLE_PASSTHROUGH,
        }

    def _update_caption_metadata(
        self,
        caption: Dict[str, Any],
        *,
        status: Optional[str] = None,
        fallback_reason: Optional[str] = None,
    ) -> None:
        if status:
            caption["translation_status"] = status
        if fallback_reason:
            caption["fallback_reason"] = fallback_reason
        elif status in {
            self.STATUS_TRANSLATED,
            self.STATUS_TRANSLATED_AFTER_NOOP_RETRY,
            self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
        }:
            caption.pop("fallback_reason", None)
        self._clear_llm_part_failure_if_terminal(
            "cap",
            str(caption.get("placeholder", "")),
            caption.get("translation_status"),
        )

    @staticmethod
    def _sanitize_retrans_error_message(error_message: str) -> str:
        text = error_message or ""
        # Ensure diagnostic context never leaks raw structural delimiters.
        text = text.replace(r"\begin{", "<BEGIN_TOKEN{")
        text = text.replace(r"\end{", "<END_TOKEN{")
        text = re.sub(r"(?<!\\)\$", r"\\$", text)
        return text

    async def _call_llm_with_freeze(
        self,
        *,
        system_prompt: str,
        user_text: str,
        fail_part: str,
        part_type: str,
        session: aiohttp.ClientSession,
        fallback_text: str,
        include_glossary: bool = False,
        user_prefix: str = "",
    ) -> str:
        prepared_text, llm_context = self._prepare_llm_payload_text(user_text)
        user_content = f"{user_prefix}{prepared_text}"
        assert_no_raw_structure(user_content, context=f"translator:{part_type}:{fail_part}")

        system_content = system_prompt
        if include_glossary:
            system_content = (
                f"{system_prompt}\n"
                "When translating, you must strictly use the following glossary for substitution. "
                "This is the highest priority rule to ensure the consistency of terms throughout the text.\n"
                f"<Glossary>:\n{self.term_dict}\n"
                "Now, please translate the following new paragraph. Maintain the terminology from the glossary provided."
            )

        payload = {
            "model": f"{self.model}",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192,
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json",
        }

        _timeout = build_llm_client_timeout(self.config, default=self.request_timeout_seconds)
        # ── Rate-limit (429) handling ────────────────────────────────────────
        # NOTE: global_llm_semaphore is an INFRA GUARD only (prevents system
        # overload). It has no authority over Phase 2 business scheduling.
        # 429 retry is strictly bounded: at most MAX_429_RETRIES attempts.
        # After that, we fall back to source text. Infinite retry is FORBIDDEN.
        MAX_429_RETRIES = 3
        rate_limit_hits = 0
        network_failures = 0

        while rate_limit_hits <= MAX_429_RETRIES and network_failures <= 3:
            try:
                async with global_llm_semaphore:  # Infra Guard — system survival only
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            rate_limit_hits += 1
                            if rate_limit_hits > MAX_429_RETRIES:
                                logger.warning(
                                    f"⚠ API rate limited (429) for {fail_part}: exceeded max retries "
                                    f"({MAX_429_RETRIES}). Returning fallback."
                                )
                                self._register_llm_part_failure(part_type, str(fail_part))
                                self._mark_api_fallback(part_type, str(fail_part), "api_request_failed_429_max_retries")
                                return fallback_text
                            retry_after_raw = response.headers.get("Retry-After", "")
                            wait = min(int(retry_after_raw) if retry_after_raw.isdigit() else 10, 30)
                            logger.warning(
                                f"⚠ API rate limited (429) for {fail_part}, "
                                f"waiting {wait}s (attempt {rate_limit_hits}/{MAX_429_RETRIES})"
                            )
                            self.update_progress(
                                -1,
                                f"API rate limited, waiting {wait}s (attempt {rate_limit_hits}/{MAX_429_RETRIES})",
                            )
                            await asyncio.sleep(wait)
                            continue
                        else:
                            response.raise_for_status()
                            result = await response.json()
                            raw_result = result["choices"][0]["message"]["content"].strip()
                            restored = self._restore_llm_output_text(raw_result, llm_context)
                            self._log_protection_actions(
                                llm_context.get("mask_mapping", {}),
                                fail_part,
                                hard_freeze_entries=llm_context.get("hard_freeze_audit_entries", []),
                            )
                            self._clear_api_fallback(part_type, str(fail_part))
                            return restored
            except PipelineInvariantViolation:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if isinstance(exc, aiohttp.ClientResponseError) and exc.status in (400, 401, 403, 404):
                    logger.error(
                        f"❌ Fatal API error {exc.status} for {fail_part}: "
                        f"{getattr(exc, 'message', str(exc))}. Aborting retries."
                    )
                    self._register_llm_part_failure(part_type, str(fail_part))
                    self._mark_api_fallback(part_type, str(fail_part), f"api_request_failed_http_{exc.status}")
                    return fallback_text

                network_failures += 1
                backoff = 5 * (2 ** (network_failures - 1))
                if network_failures < 3:
                    logger.warning(
                        f"LLM request attempt {network_failures}/3 failed for {fail_part}: {exc}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)
                else:
                    self._register_llm_part_failure(part_type, str(fail_part))
                    logger.error(
                        f"❌ Failed to translate text after 3 attempts, returning fallback for {fail_part}. {exc}"
                    )
                    self._mark_api_fallback(part_type, str(fail_part), "api_request_failed_after_3_attempts")
                    return fallback_text

        # Should not normally be reached; defensive fallback
        self._register_llm_part_failure(part_type, str(fail_part))
        self._mark_api_fallback(part_type, str(fail_part), "api_request_failed_429_max_retries")
        return fallback_text


    def _escape_bare_underscores_in_text_mode(self, text: str) -> str:
        if not text or "_" not in text:
            return text

        validator_cls = ValidatorAgent
        placeholder_spans = validator_cls._extract_placeholder_spans(text)
        env_placeholder_spans = validator_cls._extract_env_placeholder_spans(text)
        item_placeholder_spans = validator_cls._extract_item_placeholder_spans(text)
        eqrow_placeholder_spans = validator_cls._extract_eqrow_placeholder_spans(text)
        safe_arg_spans = validator_cls._extract_safe_command_arg_spans(text)
        math_regions = validator_cls._extract_math_regions(text)
        math_spans = [(s, e) for s, e, _ in math_regions]

        def _in_any_span(index: int, spans: List[tuple]) -> bool:
            for s, e in spans:
                if s <= index < e:
                    return True
            return False

        return re.sub(
            r"(?<!\\)_",
            lambda m: (
                "_"
                if _in_any_span(m.start(), placeholder_spans)
                or _in_any_span(m.start(), env_placeholder_spans)
                or _in_any_span(m.start(), item_placeholder_spans)
                or _in_any_span(m.start(), eqrow_placeholder_spans)
                or _in_any_span(m.start(), safe_arg_spans)
                or _in_any_span(m.start(), math_spans)
                else r"\_"
            ),
            text,
        )

    async def execute(self, error_retry_count=0, Maxtry=3):

        self.prompts = pm.create_prompts(self.config["source_language"], self.config["target_language"])
        self.add_placeholder()
        self.build_term_dict()

        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")

        # Debug log for trans_mode
        logger.info(f"TranslatorAgent executing with trans_mode={self.trans_mode}")

        if self.trans_mode == 0 or self.trans_mode == 2:
            logger.info(f"Starting translating for project: {os.path.basename(self.project_dir)}")
            self.update_progress(5, f"Starting translating for project: {os.path.basename(self.project_dir)}")

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(self.llm_max_concurrent_requests)

                async def process_section(i, sec):
                    async with sem:
                        translated = await self.translate(sec, envs, captions, session)
                        return i, translated

                tasks = [process_section(i, sec) for i, sec in enumerate(sections)]

                completed = 0
                total = len(tasks)

                for future in asyncio.as_completed(tasks):
                    i, translated_section = await future
                    sections[i] = translated_section
                    
                    completed += 1
                    progress = int(5 + 90 * completed / total)
                    self.update_progress(progress, f"Translated {completed}/{total} sections")

                    # Save progress
                    self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                    self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                    self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                self.update_progress(95, "Validating translation results")

                await self._val_fail_parts(Maxtry=Maxtry,
                                     sections=sections,
                                     captions=captions,
                                     envs=envs,
                                     session=session)

                logger.info("Successfully translated sections!")
                self.update_progress(100, "Successfully translated sections!")

        elif self.trans_mode == 1:
            self._reset_structural_fallback_metrics()
            async with aiohttp.ClientSession() as session:
                error_parts = [error_part["num_or_ph"] for error_part in self.errors_report]
                logger.info(f"Starting retranslating for error parts: {error_parts}, attempt {error_retry_count + 1}/{Maxtry}")
                
                await self._retranslate_error_parts(secs=sections,
                                                    caps=captions,
                                                    envs=envs,
                                                    session=session)

                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                self.fail_section_nums.clear()
                self.fail_caption_phs.clear()
                self.fail_env_phs.clear()
                self.have_fail_parts = False

                await self._val_fail_parts(Maxtry=Maxtry,
                                           sections=sections,
                                           captions=captions,
                                           envs=envs,
                                           session=session)

            logger.info("Successfully retranslated error parts!")

        elif self.trans_mode == 3:
            # Quick scan mode: translate only abstract and conclusion
            logger.info(f"Starting quick scan mode for project: {os.path.basename(self.project_dir)}")
            self.update_progress(5, f"Quick scan mode: translating abstract and conclusion only")

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(self.llm_max_concurrent_requests)

                # 1. Translate abstract environment (in envs)
                abstract_translated = False
                for i, env in enumerate(envs):
                    if env.get("env_name", "").lower() == "abstract" and env.get("need_trans", False):
                        logger.info("Translating abstract environment")
                        self.update_progress(20, "Translating abstract...")
                        envs[i] = await self._translate_env(env, session)
                        abstract_translated = True
                        break

                if not abstract_translated:
                    logger.warning("No abstract environment found to translate")

                # 2. Find and translate conclusion section(s)
                conclusion_patterns = [
                    r'\\section\*?\{[Cc]onclusion[s]?\}',
                    r'\\section\*?\{[Ss]ummary\}',
                    r'\\section\*?\{[Cc]oncluding [Rr]emarks?\}',
                    r'\\section\*?\{[Ff]inal [Rr]emarks?\}',
                ]
                
                conclusion_sections = []
                for i, sec in enumerate(sections):
                    content = sec.get("content", "")
                    for pattern in conclusion_patterns:
                        if re.search(pattern, content):
                            conclusion_sections.append(i)
                            break

                logger.info(f"Found {len(conclusion_sections)} conclusion section(s)")
                self.update_progress(40, f"Found {len(conclusion_sections)} conclusion section(s)")

                # Translate conclusion sections
                async def process_conclusion_section(i, sec):
                    async with sem:
                        translated = await self.translate(sec, envs, captions, session)
                        return i, translated

                if conclusion_sections:
                    tasks = [process_conclusion_section(i, sections[i]) for i in conclusion_sections]
                    completed = 0
                    total = len(tasks)

                    for future in asyncio.as_completed(tasks):
                        i, translated_section = await future
                        sections[i] = translated_section
                        completed += 1
                        progress = int(40 + 50 * completed / total)
                        self.update_progress(progress, f"Translated {completed}/{total} conclusion sections")

                # 3. For all other sections, copy content to trans_content (skip translation)
                for i, sec in enumerate(sections):
                    if i not in conclusion_sections and "trans_content" not in sec:
                        sec["trans_content"] = sec["content"]

                # For all other envs, copy content to trans_content
                for env in envs:
                    if env.get("env_name", "").lower() != "abstract" and "trans_content" not in env:
                        env["trans_content"] = env["content"]

                # For all captions, copy content to trans_content if not translated
                for cap in captions:
                    if "trans_content" not in cap:
                        cap["trans_content"] = cap["content"]

                # Save results
                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                logger.info("Quick scan mode completed: abstract and conclusion translated")
                self.update_progress(100, "Quick scan completed: abstract and conclusion translated")
        
        # Save terminology table if enabled
        if self.generate_terminology and self.terminology_table:
            self._save_terminology_table()
            logger.info(f"Terminology table generated with {len(self.terminology_table)} terms")

        # Persist deterministic oversize downgrade evidence for replay and observability.
        self._flush_oversize_downgrade_events()

    def _section_has_translatable_content(self, content: str) -> bool:
        """
        Check if a section (especially section 0) contains translatable text.
        Returns True if there's meaningful text content after \begin{document}.
        """
        # Remove placeholders to check for actual text
        text = re.sub(r'<PLACEHOLDER_[A-Z]+_\d+>', '', content)
        # Remove LaTeX commands that don't contain translatable text
        text = re.sub(r'\\(documentclass|usepackage|author|affiliation|email|date|maketitle|newpage|setcounter|makeatletter|makeatother|label|ref|eqref|cite|bibliography|bibliographystyle)\b[^\n]*', '', text)
        # Remove begin/end document
        text = re.sub(r'\\(begin|end)\{document\}', '', text)
        # Remove comments
        text = re.sub(r'%[^\n]*', '', text)
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Check if there's substantial text content (more than just LaTeX markup)
        # Look for actual words (at least 50 characters of text content)
        return len(text) > 50

    async def translate(self,
                        section: Dict[str, Any],
                        envs: List[Dict[str, Any]],
                        captions: List[Dict[str, Any]],
                        session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Translates the input data.

        Uses a 3-phase concurrent approach:
          Phase 1: Translate section body (single await, sequential).
          Phase 2: Translate all referenced environments concurrently via asyncio.gather.
                   Caption placeholders inside envs are also discovered here.
          Phase 3: Translate all referenced captions concurrently via asyncio.gather.
        """
        placeholder_pattern_cap = r"<PLACEHOLDER_CAP_\d+>"
        placeholder_pattern_env = r"<PLACEHOLDER_ENV_\d+>"
        placeholders_cap = re.findall(placeholder_pattern_cap, section["content"])
        placeholders_env = re.findall(placeholder_pattern_env, section["content"])

        # 鈹€鈹€ Phase 1: Translate section body 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
        if self._is_immutable_section(section):
            section = section.copy()
            section["trans_content"] = section.get("content", "")
            section["translated"] = False
            self._update_section_metadata(
                section,
                status=self.STATUS_IMMUTABLE_PASSTHROUGH,
                no_op_detected=False,
            )
        # Document-root / preamble chunks are source-safe only and must never
        # be routed through normal prose translation, even when chunked.
        # Section 0 may contain main body text, translate if it has translatable content.
        elif self._is_document_root_section_chunk(section):
            section = section.copy()
            section["trans_content"] = section.get("content", "")
            section["translated"] = False
            self._update_section_metadata(
                section,
                status=self.STATUS_IMMUTABLE_PASSTHROUGH,
                no_op_detected=False,
            )
        elif section["section"] == "0":
            section_payload = self._get_section_translation_core(section)
            if self._section_has_translatable_content(section_payload):
                logger.info(f"Section 0 contains translatable content, translating...")
                section = await self._translate_section(section, session)
            # else: no translatable content, keep original
        else:
            section = await self._translate_section(section, session)

        if (
            section.get("translation_status") == self.STATUS_SOURCE_PASS_THROUGH
            or (
                section.get("translated") is False
                and section.get("downgrade_reason") == "oversize_no_safe_boundary"
            )
        ):
            # Hard constraint: oversize source-pass-through chunks bypass
            # env/caption secondary translation chains.
            assert section.get("trans_content", "") == section.get("content", "")
            return section

        # 鈹€鈹€ Phase 2: Translate all environments concurrently 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
        # Build a lookup: placeholder 鈫?index in envs list.
        env_ph_to_idx = {env["placeholder"]: i for i, env in enumerate(envs)}

        async def _translate_env_by_ph(placeholder: str):
            idx = env_ph_to_idx.get(placeholder)
            if idx is None:
                return
            env = envs[idx]
            # Discover captions embedded inside this env's content.
            cap_phs_in_env = re.findall(placeholder_pattern_cap, env["content"])
            placeholders_cap.extend(cap_phs_in_env)
            envs[idx] = await self._translate_env(env, session)

        if placeholders_env:
            await asyncio.gather(*[_translate_env_by_ph(ph) for ph in placeholders_env])

        # 鈹€鈹€ Phase 3: Translate all captions concurrently 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
        # Remove duplicates while preserving order (captions from section + from envs).
        placeholders_cap = list(dict.fromkeys(placeholders_cap))

        cap_ph_to_idx = {cap["placeholder"]: i for i, cap in enumerate(captions)}

        async def _translate_caption_by_ph(placeholder: str):
            idx = cap_ph_to_idx.get(placeholder)
            if idx is None:
                return
            captions[idx] = await self._translate_caption(captions[idx], session)

        if placeholders_cap:
            await asyncio.gather(*[_translate_caption_by_ph(ph) for ph in placeholders_cap])

        return section
    
    async def _val_fail_parts(self, sections, captions, envs, Maxtry, session: aiohttp.ClientSession, fail_retry_count=0) -> str:
            while fail_retry_count < Maxtry and self.have_fail_parts:
                fail_parts = self.fail_section_nums + self.fail_caption_phs + self.fail_env_phs
                if fail_retry_count == Maxtry:
                    logger.error(f"Failed to translate {fail_parts}")
                    break
                    
                logger.info(f"Retranslating fail parts: {fail_parts}, attempt {fail_retry_count+1}/{Maxtry}")
                
                await self._retranslate_fail_parts(secs=sections,
                                            caps=captions,
                                            envs=envs,
                                            session=session)
                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)
                
                fail_retry_count += 1

    async def _retranslate_fail_parts(self,
                                secs: List[Dict[str, Any]], 
                                caps: List[Dict[str, Any]], 
                                envs: List[Dict[str, Any]],
                                session: aiohttp.ClientSession) -> Any:
        # Local import to avoid circular deps at module load.
        from backend.app.services.translation.downgrade_handler import DOWNGRADE_STATUS
        sec_nums = self.fail_section_nums[:]
        cap_phs = self.fail_caption_phs[:]
        env_phs = self.fail_env_phs[:]
        self.fail_section_nums.clear()
        self.fail_caption_phs.clear()
        self.fail_env_phs.clear()
        self.have_fail_parts = False

        sec_dict = {s["section"]: i for i, s in enumerate(secs)}
        cap_dict = {c["placeholder"]: i for i, c in enumerate(caps)}
        env_dict = {e["placeholder"]: i for i, e in enumerate(envs)}

        if sec_nums:
            self.log(f"Retranslating for {sec_nums}")
            for sec_num in sec_nums:
                if sec_num in sec_dict:
                    i = sec_dict[sec_num]
                    # Document-root / preamble chunks are never retranslatable.
                    if self._is_document_root_section_chunk(secs[i]):
                        continue
                    if self._should_skip_fail_part_retry(secs[i]):
                        logger.info("Maxtry guard: skipping payload-safe section %s", sec_num)
                        continue
                    # Section 0 should be translated only if it has translatable content.
                    if sec_num == "0" and not self._section_has_translatable_content(secs[i]["content"]):
                        continue
                    # ── Phase 3 Guard: skip deterministically downgraded sections ──
                    if secs[i].get("translation_status") == DOWNGRADE_STATUS:
                        logger.info("Maxtry guard: skipping downgraded section %s", sec_num)
                        continue
                    if self._is_immutable_section(secs[i]):
                        logger.info("Maxtry guard: skipping immutable passthrough section %s", sec_num)
                        continue
                    secs[i] = await self._translate_section(secs[i], session)
            # else:
            #     print(f"[Warning] Section {sec_num} not found.")
        if cap_phs:
            self.log(f"Retranslating for {cap_phs}")
            for cap_ph in cap_phs:
                if cap_ph in cap_dict:
                    i = cap_dict[cap_ph]
                    if self._should_skip_fail_part_retry(caps[i]):
                        logger.info("Maxtry guard: skipping payload-safe caption %s", cap_ph)
                        continue
                    # ── Phase 3 Guard: skip deterministically downgraded captions ──
                    if caps[i].get("translation_status") == DOWNGRADE_STATUS:
                        logger.info("Maxtry guard: skipping downgraded caption %s", cap_ph)
                        continue
                    caps[i] = await self._translate_caption(caps[i], session)
            # else:
            #     print(f"[Warning] Caption placeholder {cap_ph} not found.")
        if env_phs:
            self.log(f"Retranslating for {env_phs}")
            for env_ph in env_phs:
                if env_ph in env_dict:
                    i = env_dict[env_ph]
                    if self._should_skip_fail_part_retry(envs[i]):
                        logger.info("Maxtry guard: skipping payload-safe env %s", env_ph)
                        continue
                    # ── Phase 3 Guard: skip deterministically downgraded envs ──────
                    # Envs with DOWNGRADE_STATUS are final (Phase 2 queue timeout or
                    # 429 limit). Maxtry MUST NOT re-consume their repair opportunity.
                    if envs[i].get("translation_status") == DOWNGRADE_STATUS:
                        logger.info("Maxtry guard: skipping downgraded env %s", env_ph)
                        continue
                    envs[i] = await self._translate_env(envs[i], session)
            # else:
            #     print(f"[Warning] Environment placeholder {env_ph} not found.")

    def _reset_structural_fallback_metrics(self) -> None:
        self.structural_fallback_count = 0
        self.structural_fallback_candidate_count = 0
        self.structural_fallback_denominator = 0
        self.structural_fallback_ratio = 0.0
        self.structural_fallback_warning = None
        self.structural_fallback_parts = []

    def _compute_structural_fallback_denominator(self, secs: List[Dict], caps: List[Dict], envs: List[Dict]) -> int:
        sec_count = 0
        for sec in secs:
            sec_id = str(sec.get("section"))
            if sec_id == "-1":
                continue
            if sec_id == "0" and not self._section_has_translatable_content(sec.get("content", "")):
                continue
            sec_count += 1

        env_count = 0
        for env in envs:
            if env.get("need_trans", True):
                env_count += 1

        denominator = sec_count + len(caps) + env_count
        return max(denominator, 1)

    def _finalize_structural_fallback_metrics(self) -> None:
        if self.structural_fallback_denominator <= 0:
            self.structural_fallback_ratio = 0.0
        else:
            self.structural_fallback_ratio = self.structural_fallback_count / self.structural_fallback_denominator

        if self.structural_fallback_ratio > self.structural_fallback_cap:
            self.structural_fallback_warning = (
                f"Compile-first structural fallback ratio {self.structural_fallback_ratio:.2%} "
                f"exceeds cap {self.structural_fallback_cap:.2%} "
                f"(mode={self.structural_fallback_cap_mode})"
            )
            logger.warning(self.structural_fallback_warning)

    def _get_structural_validator(self) -> ValidatorAgent:
        if self._structural_validator is None:
            self._structural_validator = ValidatorAgent(
                config=self.config,
                project_dir=self.project_dir,
                output_dir=self.output_dir,
            )
        return self._structural_validator

    def _validate_part_after_structural_fix(self, part: Dict) -> Optional[Dict]:
        """Re-validate one part immediately after structural fix."""
        try:
            validator = self._get_structural_validator()
            return validator._validate(part)
        except Exception as exc:
            logger.warning("Immediate post-fix validation failed: %s", exc)
            return {"math_error": f"post_fix_validation_failed: {exc}"}

    @staticmethod
    def _summarize_structural_errors(error_report: Dict) -> str:
        keys = ["command_error", "ph_error", "bracket_error", "math_error", "global_ph_error"]
        items = []
        for key in keys:
            val = error_report.get(key)
            if val:
                first_line = str(val).splitlines()[0]
                items.append(f"{key}={first_line}")
        return "; ".join(items) if items else "unknown_error"

    @staticmethod
    def _is_level_a_related_error(error_report: Dict[str, Any]) -> bool:
        payload = " ".join(
            str(error_report.get(k, ""))
            for k in ("command_error", "ph_error", "bracket_error", "math_error", "global_ph_error")
        ).lower()
        return (
            "level_a_env_placeholder_residual" in payload
            or "env_boundary_mismatch" in payload
            or "env_restore_failed" in payload
            or "<env_restore_failed>" in payload
        )

    def _apply_compile_first_fallback(self, part: Dict, error: Dict, recheck_report: Optional[Dict] = None) -> bool:
        """Mark a part for post-compile target-language fallback when structural fix remains unsafe."""
        self.structural_fallback_candidate_count += 1
        identifier = error.get("num_or_ph", "?")
        reason = self._summarize_structural_errors(recheck_report or error)

        projected_ratio = (self.structural_fallback_count + 1) / max(self.structural_fallback_denominator, 1)
        self.structural_fallback_count += 1
        if identifier not in self.structural_fallback_parts:
            self.structural_fallback_parts.append(identifier)

        if "section" in part:
            err_type = str(error.get("error_type", "C2"))
            reason_tag = "math_delimiter_mismatch" if "math_delimiter_mismatch" in reason else "structural_validation_failed"
            fallback_reason = f"compile_first_structural_fallback:{err_type}_{reason_tag}"
            self._update_section_metadata(
                part,
                status=self.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE,
                fallback_reason=fallback_reason,
            )
        elif "env_name" in part:
            err_type = str(error.get("error_type", "C2"))
            fallback_reason = f"compile_first_structural_fallback:{err_type}_{reason}"
            self._update_env_metadata(
                part,
                status=self.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE,
                fallback_reason=fallback_reason,
                fallback_subtype=self._infer_env_fallback_subtype(part),
            )

        logger.warning(
            "Post-compile fallback candidate recorded for part %s (reason: %s)",
            identifier,
            reason,
        )

        if projected_ratio > self.structural_fallback_cap:
            self.structural_fallback_warning = (
                f"Compile-first structural fallback ratio {projected_ratio:.2%} "
                f"exceeds cap {self.structural_fallback_cap:.2%} (mode={self.structural_fallback_cap_mode})"
            )
            logger.warning(self.structural_fallback_warning)

        return True

    async def _retranslate_error_parts(self, secs, caps, envs, session) -> Any:
        """
        Retranslate error parts with A/B/C error type routing:
        - Type A (resource missing): Apply degradation, keep existing translation
        - Type B (recoverable): Allow one translation retry
        - Type C (structural): Apply algorithmic fix without LLM retry
        """
        sem = asyncio.Semaphore(self.llm_max_concurrent_requests)
        completed = 0
        total = len(self.errors_report)
        self.structural_fallback_denominator = self._compute_structural_fallback_denominator(secs, caps, envs)

        # Group errors by type for efficient processing
        type_a_errors = []
        type_b_errors = []
        type_c1_errors = []  # C1: local/contained -- 1 LLM retry then deterministic fix
        type_c2_errors = []  # C2: global/structural -- deterministic fix only, no LLM retry

        for error_report in self.errors_report:
            error_type = error_report.get("error_type", ERROR_TYPE_B)
            if error_type == ERROR_TYPE_A:
                type_a_errors.append(error_report)
            elif error_type in (ERROR_TYPE_C1,):
                type_c1_errors.append(error_report)
            elif error_type in (ERROR_TYPE_C, ERROR_TYPE_C2):
                # ERROR_TYPE_C is legacy (pre-subclassification) -- treat as C2
                type_c2_errors.append(error_report)
            else:
                type_b_errors.append(error_report)

        logger.info(
            f"Error classification: A={len(type_a_errors)}, B={len(type_b_errors)}, "
            f"C1={len(type_c1_errors)}, C2={len(type_c2_errors)}"
        )

        # Process Type A errors: Degradation (keep existing translation, log warning)
        for error in type_a_errors:
            logger.warning(f"Type A error (degradation): {error.get('num_or_ph')} - keeping existing translation")
            completed += 1
            progress_pct = int(100 * completed / total) if total > 0 else 100
            self.update_progress(progress_pct, f"Processed {completed}/{total} (A:degraded)")

        # Process Type C2 errors: no speculative repair; direct compile-first fallback.
        for error in type_c2_errors:
            part = self._find_part_by_error(error, secs, caps, envs)
            if part:
                self._apply_compile_first_fallback(part, error, recheck_report=error)
            completed += 1
            progress_pct = int(100 * completed / total) if total > 0 else 100
            self.update_progress(progress_pct, f"Processed {completed}/{total} (C2:fallback)")

        # Process Type C1 errors: 1 controlled LLM retry, then deterministic fix
        async def process_type_c1_error(error_report):
            """C1: try a single targeted LLM retry with restoration instructions, then fix."""
            async with sem:
                if self._is_level_a_related_error(error_report):
                    part = self._find_part_by_error(error_report, secs, caps, envs)
                    if part:
                        self._apply_compile_first_fallback(part, error_report, recheck_report=error_report)
                    return
                part = self._find_part_by_error(error_report, secs, caps, envs)
                if part and part.get("translation_status") == self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH:
                    logger.info("Skipping C1 retry for payload-invariant passthrough part: %s", error_report.get("num_or_ph"))
                    return
                ph_error = error_report.get("ph_error", "")
                math_error = error_report.get("math_error", "")
                completeness_error = error_report.get("completeness_error", "")
                restoration_hint = (
                    "CRITICAL: Restore all LaTeX placeholders and math delimiters exactly as in the source. "
                )
                if ph_error:
                    restoration_hint += f"Missing elements: {ph_error}. "
                if math_error:
                    restoration_hint += f"Math issue: {math_error}."
                if completeness_error:
                    restoration_hint += f" Completeness issue: {completeness_error}."

                part_type = error_report["part"]
                identifier = error_report["num_or_ph"]
                part_key = self._part_retry_key(part_type, identifier)
                attempted_llm_retry = False

                # Enforce "max 1 LLM retry per part" for C1 end-to-end.
                if part_key in self._c1_retried_parts:
                    self.c1_retry_enforced_once = True
                    logger.info("C1 retry already consumed for %s, skipping additional LLM retry", part_key)
                else:
                    # Reserve retry slot before awaiting to avoid duplicate retries under concurrency.
                    self._c1_retried_parts.add(part_key)
                    retried = False
                    if part_type == "sec":
                        for i, sec in enumerate(secs):
                            if identifier == sec["section"]:
                                secs[i] = await self._translate_section(
                                    section=sec, error_message=restoration_hint, session=session
                                )
                                retried = True
                                break
                    elif part_type == "env":
                        for i, env in enumerate(envs):
                            if identifier == env["placeholder"]:
                                envs[i] = await self._translate_env(
                                    env=env, error_message=restoration_hint, session=session
                                )
                                retried = True
                                break
                    elif part_type == "cap":
                        for i, cap in enumerate(caps):
                            if identifier == cap["placeholder"]:
                                caps[i] = await self._translate_caption(
                                    caption=cap, error_message=restoration_hint, session=session
                                )
                                retried = True
                                break

                    if not retried:
                        self._c1_retried_parts.discard(part_key)
                        logger.warning("C1 retry: part not found: %s", identifier)
                        return
                    attempted_llm_retry = True

                # After the LLM retry, route directly to compile-first fallback if still broken.
                part = self._find_part_by_error(error_report, secs, caps, envs)
                if part:
                    recheck_report = self._validate_part_after_structural_fix(part)
                    if recheck_report:
                        self._apply_compile_first_fallback(part, error_report, recheck_report=recheck_report)
                    else:
                        if attempted_llm_retry:
                            logger.info("C1 part resolved by LLM retry: %s", identifier)
                        else:
                            logger.info("C1 part resolved without additional LLM retry: %s", identifier)

        tasks_c1 = [process_type_c1_error(error) for error in type_c1_errors]
        for future in asyncio.as_completed(tasks_c1):
            await future
            completed += 1
            progress_pct = int(100 * completed / total) if total > 0 else 100
            self.update_progress(progress_pct, f"Processed {completed}/{total} (C1:retry+fallback)")

        # Process Type B errors: Translation retry (existing logic)
        async def process_type_b_error(error_report):
            async with sem:
                part = self._find_part_by_error(error_report, secs, caps, envs)
                if part and part.get("translation_status") == self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH:
                    logger.info("Skipping Type B retry for payload-invariant passthrough part: %s", error_report.get("num_or_ph"))
                    return False
                error_message = []
                if "command_error" in error_report:
                    error_message.append(error_report["command_error"])
                if "ph_error" in error_report:
                    error_message.append(error_report["ph_error"])
                if "bracket_error" in error_report:
                    error_message.append(error_report["bracket_error"])
                if "completeness_error" in error_report:
                    error_message.append(error_report["completeness_error"])
                if "global_ph_error" in error_report:
                    error_message.append(error_report["global_ph_error"])
                error_message = "\n".join(error_message)

                part_type = error_report["part"]
                identifier = error_report["num_or_ph"]

                if part_type == "sec":
                    for i, sec in enumerate(secs):
                        if identifier == sec["section"]:
                            secs[i] = await self._translate_section(
                                section=sec, error_message=error_message, session=session
                            )
                            return True
                elif part_type == "env":
                    for i, env in enumerate(envs):
                        if identifier == env["placeholder"]:
                            envs[i] = await self._translate_env(
                                env=env, error_message=error_message, session=session
                            )
                            return True
                elif part_type == "cap":
                    for i, cap in enumerate(caps):
                        if identifier == cap["placeholder"]:
                            caps[i] = await self._translate_caption(
                                caption=cap, error_message=error_message, session=session
                            )
                            return True
                return False

        tasks_type_b = [process_type_b_error(error) for error in type_b_errors]
        for future in asyncio.as_completed(tasks_type_b):
            await future
            completed += 1
            progress_pct = int(100 * completed / total) if total > 0 else 100
            self.update_progress(progress_pct, f"Retranslated {completed}/{total} (B:retry)")

        self._finalize_structural_fallback_metrics()
        logger.info(
            "Completed retranslation of error parts (fallback_count=%d, ratio=%.4f, cap=%.4f, mode=%s)",
            self.structural_fallback_count,
            self.structural_fallback_ratio,
            self.structural_fallback_cap,
            self.structural_fallback_cap_mode,
        )
    
    def _find_part_by_error(self, error: Dict, secs: List, caps: List, envs: List) -> Optional[Dict]:
        """Find the part (section/caption/env) referenced by an error report."""
        part_type = error.get("part")
        identifier = error.get("num_or_ph")
        
        if part_type == "sec":
            for sec in secs:
                if sec["section"] == identifier:
                    return sec
        elif part_type == "env":
            for env in envs:
                if env["placeholder"] == identifier:
                    return env
        elif part_type == "cap":
            for cap in caps:
                if cap["placeholder"] == identifier:
                    return cap
        return None
    
    def _apply_structural_fix(self, part: Dict, error: Dict) -> bool:
        """
        Apply non-speculative local normalization for structural errors.
        NOTE: speculative structural repair is forbidden by invariant.
        """
        original = part.get("content", "")
        translated = part.get("trans_content", "")

        if not translated:
            # No translation exists, use original as fallback
            part["trans_content"] = original
            return True

        try:
            # Keep only safe normalization that does not inject structure tokens.
            fixed = self._fix_missing_commands(original, translated)
            fixed = self._escape_bare_underscores_in_text_mode(fixed)

            part["trans_content"] = fixed
            return True

        except Exception as e:
            if isinstance(e, PipelineInvariantViolation):
                raise
            logger.warning(f"Structural fix failed: {e}")
            # Fallback: keep existing translation if available
            if translated:
                return True
            part["trans_content"] = original
            return True

    
    def _fix_missing_commands(self, original: str, translated: str) -> str:
        """Restore missing LaTeX commands from original to translated content."""
        # Extract commands with regex
        cmd_pattern = r'\\([a-zA-Z]+)(?:\{[^}]*\})*'
        
        original_cmds = re.findall(cmd_pattern, original)
        translated_cmds = re.findall(cmd_pattern, translated)
        
        original_counter = Counter(original_cmds)
        translated_counter = Counter(translated_cmds)
        
        # Find missing commands
        for cmd, count in original_counter.items():
            trans_count = translated_counter.get(cmd, 0)
            if trans_count < count:
                # Command is missing in translation, log but don't modify
                # (Complex insertion could break LaTeX structure)
                logger.debug(f"Missing command \\{cmd}: expected {count}, found {trans_count}")
        
        return translated
    
    def _fix_missing_placeholders(self, original: str, translated: str) -> str:
        """Spec invariant: speculative placeholder repair must be unreachable."""
        raise SpeculativeRepairForbiddenError(
            "forbidden: speculative repair in _fix_missing_placeholders"
        )

    async def _translate_section(self, section: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:

        transed_section = section.copy()
        section_num = str(section.get("section", ""))
        previous_context = section.get("previous_context")
        source_content = section.get("content", "") or ""
        translatable_content = self._get_section_translation_core(section)
        self._sync_section_retry_count(section_num, transed_section)

        if self._is_immutable_section(section):
            transed_section["trans_content"] = section.get("content", "")
            transed_section["translated"] = False
            self._update_section_metadata(
                transed_section,
                status=self.STATUS_IMMUTABLE_PASSTHROUGH,
                no_op_detected=False,
            )
            return transed_section

        if section.get("oversize_no_safe_boundary"):
            # Persist deterministic gate inputs for audit/replay even when the
            # section does not trigger downgrade.
            estimated_tokens = estimate_tokens_v1(section.get("content", "") or "")
            transed_section["token_estimator_id"] = TOKEN_ESTIMATOR_ID_V1
            transed_section["token_estimator_digest"] = TOKEN_ESTIMATOR_DIGEST_V1
            transed_section["estimated_tokens"] = int(estimated_tokens)
            transed_section["safe_limit_id"] = SAFE_LIMIT_ID_V1
            transed_section["safe_limit_digest"] = SAFE_LIMIT_DIGEST_V1
            transed_section["model_context_tokens"] = int(self.model_context_tokens)
            transed_section["prompt_reserve_tokens"] = int(self.prompt_reserve_tokens)
            transed_section["safe_input_limit"] = int(self.safe_input_limit)

        oversize_downgrade = self._evaluate_oversize_downgrade(section)
        if oversize_downgrade:
            transed_section["trans_content"] = section.get("content", "")
            transed_section["translated"] = False
            transed_section["downgrade_reason"] = "oversize_no_safe_boundary"
            transed_section["oversize_downgrade_strategy"] = "source_pass_through"
            transed_section["oversize_no_safe_boundary"] = True
            transed_section["token_estimator_id"] = TOKEN_ESTIMATOR_ID_V1
            transed_section["token_estimator_digest"] = TOKEN_ESTIMATOR_DIGEST_V1
            transed_section["estimated_tokens"] = int(oversize_downgrade["estimated_tokens"])
            transed_section["safe_limit_id"] = SAFE_LIMIT_ID_V1
            transed_section["safe_limit_digest"] = SAFE_LIMIT_DIGEST_V1
            transed_section["model_context_tokens"] = int(self.model_context_tokens)
            transed_section["prompt_reserve_tokens"] = int(self.prompt_reserve_tokens)
            transed_section["safe_input_limit"] = int(self.safe_input_limit)
            self._update_section_metadata(
                transed_section,
                status=self.STATUS_SOURCE_PASS_THROUGH,
                no_op_detected=False,
                fallback_reason="oversize_no_safe_boundary",
            )
            self._record_oversize_downgrade(oversize_downgrade)
            assert transed_section.get("translation_status") == self.STATUS_SOURCE_PASS_THROUGH
            assert transed_section.get("translated") is False
            return transed_section

        async def fetch_translation(use_context: bool, extra_instruction: Optional[str] = None) -> Optional[str]:
            ctx = previous_context if use_context else None
            prompt_suffix = ""
            if error_message:
                prompt_suffix += f"\n[Error Correction Requirement]\n{error_message}"
            if extra_instruction:
                prompt_suffix += f"\n[Strict Translation Requirement]\n{extra_instruction}"

            if self.trans_mode in (0, 3):
                return await self._request_llm_for_trans(
                    self.prompts["section_system_prompt"] + prompt_suffix,
                    translatable_content,
                    fail_part=section_num,
                    type="sec",
                    session=session,
                    previous_context=ctx,
                )
            if self.trans_mode == 2:
                if not self.term_dict:
                    return await self._request_llm_for_trans(
                        self.prompts["section_system_prompt"] + prompt_suffix,
                        translatable_content,
                        fail_part=section_num,
                        type="sec",
                        session=session,
                        previous_context=ctx,
                    )
                return await self._request_llm_for_trans_with_terms(
                    self.prompts["section_system_prompt_with_dict"] + prompt_suffix,
                    translatable_content,
                    fail_part=section_num,
                    type="sec",
                    session=session,
                    previous_context=ctx,
                )
            return None

        if self.trans_mode in [0, 2, 3]:
            result = await fetch_translation(use_context=True)

            if result and "<REFERENCE_CONTEXT>" in result:
                logger.warning(f"Prompt leakage detected in {section_num}. Retrying with context.")
                self._increment_section_retry_count(section_num)
                result = await fetch_translation(use_context=True)

                if result and "<REFERENCE_CONTEXT>" in result:
                    logger.warning(f"Persistent leakage in {section_num}. Downgrading context.")
                    self._increment_section_retry_count(section_num)
                    result = await fetch_translation(use_context=False)

            translated_text = result if result is not None else translatable_content
            no_op_detected = False
            no_op_retry_success = False
            api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("sec", section_num))
            payload_invariant_passthrough = self._is_payload_invariant_reason(api_fallback_reason)

            if (
                not payload_invariant_passthrough
                and self._is_noop_translation(translatable_content, translated_text)
            ):
                no_op_detected = True
                self._record_noop_section(section_num)
                self._increment_section_retry_count(section_num)
                force_retry_hint = (
                    "The previous output is too similar to the source and appears untranslated. "
                    "Translate all natural-language English sentences into the target language. "
                    "Keep LaTeX commands/placeholders/math unchanged."
                )
                retry_result = await fetch_translation(use_context=False, extra_instruction=force_retry_hint)
                if retry_result is not None:
                    translated_text = retry_result
                no_op_retry_success = not self._is_noop_translation(
                    translatable_content,
                    translated_text,
                )

            api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("sec", section_num))
            payload_invariant_passthrough = self._is_payload_invariant_reason(api_fallback_reason)
            if (
                payload_invariant_passthrough
                and self._is_source_preserved_translation(translatable_content, translated_text)
            ):
                rescued_text = await self._rescue_plain_text_by_paragraph(
                    text=translatable_content,
                    identifier=section_num,
                    part_type="sec",
                    session=session,
                    error_message="Previous whole-section attempt violated protected-token invariants.",
                    prompt_key="section_system_prompt",
                    prompt_key_with_terms="section_system_prompt_with_dict",
                )
                if rescued_text is not None:
                    translated_text = rescued_text
                    self._clear_api_fallback("sec", section_num)
                    api_fallback_reason = None
                    payload_invariant_passthrough = False

            env_restore_preserved_source = self._has_unrestored_env_artifacts(translated_text)
            if env_restore_preserved_source:
                translated_text = translatable_content

            transed_section["trans_content"] = self._reassemble_section_translation(
                section,
                translated_text,
            )
            status = self.STATUS_TRANSLATED
            fallback_reason = None
            if env_restore_preserved_source:
                status = self.STATUS_FALLBACK_SOURCE_API_FAILURE
                fallback_reason = "section_env_restore_preserved_source"
            elif api_fallback_reason:
                status = (
                    self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH
                    if payload_invariant_passthrough
                    else self.STATUS_FALLBACK_SOURCE_API_FAILURE
                )
                fallback_reason = api_fallback_reason
                if payload_invariant_passthrough:
                    self._record_payload_invariant_section(section_num)
            elif no_op_detected and no_op_retry_success:
                status = self.STATUS_TRANSLATED_AFTER_NOOP_RETRY

            self._update_section_metadata(
                transed_section,
                status=status,
                no_op_detected=no_op_detected,
                fallback_reason=fallback_reason,
            )

        elif self.trans_mode == 1:
            self._increment_section_retry_count(section_num)
            retrans_content = await self._request_llm_for_retrans_error_parts(
                self.prompts["retrans_error_parts_system_prompt"],
                part=transed_section,
                error_message=error_message,
                fail_part=section_num,
                type="sec",
                session=session,
            )
            env_restore_preserved_source = self._has_unrestored_env_artifacts(retrans_content)
            transed_section["trans_content"] = (
                section.get("content", "") if env_restore_preserved_source else retrans_content
            )
            api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("sec", section_num))
            payload_invariant_passthrough = self._is_payload_invariant_reason(api_fallback_reason)
            if payload_invariant_passthrough:
                self._record_payload_invariant_section(section_num)
            self._update_section_metadata(
                transed_section,
                status=(
                    self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH
                    if payload_invariant_passthrough
                    else (
                        self.STATUS_FALLBACK_SOURCE_API_FAILURE
                        if (env_restore_preserved_source or api_fallback_reason)
                        else self.STATUS_TRANSLATED
                    )
                ),
                no_op_detected=bool(transed_section.get("no_op_detected", False)),
                fallback_reason=(
                    "section_env_restore_preserved_source"
                    if env_restore_preserved_source
                    else api_fallback_reason
                ),
            )

        if self.trans_mode == 2:
            try:
                if self.update_term == True:
                    src_text = self._extract_text_from_tex(transed_section["content"])
                    tgt_text = self._extract_text_from_tex(transed_section.get("trans_content") or transed_section["content"])
                    term_text = await self._request_llm_for_extract_terms(
                        self.prompts["extract_terminology_system_prompt"],
                        src_text,
                        tgt_text,
                        session=session,
                    )
                    self._updated_term_dict_v2(term_text)
            except Exception:
                return transed_section

        if self.generate_terminology and self.trans_mode != 2:
            try:
                src_text = self._extract_text_from_tex(transed_section["content"])
                tgt_text = self._extract_text_from_tex(transed_section.get("trans_content") or transed_section["content"])
                terms = await self._extract_terminology_from_translation(src_text, tgt_text, session)
                if terms:
                    self.terminology_table.extend(terms)
            except Exception as e:
                logger.warning(f"Failed to extract terminology from section: {e}")

        return transed_section

    async def _translate_caption(self, caption: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        """
        Translates the captions of the input data.
        """
        transed_caption = caption.copy()
        placeholder = caption["placeholder"]
        if self.trans_mode == 0:
            transed_caption["trans_content"] = await self._request_llm_for_trans(self.prompts["caption_system_prompt"],
                                                        caption["content"],
                                                        fail_part=placeholder,
                                                        type="cap",
                                                        session=session
                                                        )
        elif self.trans_mode == 1:
            # Keep mode-1 caption retranslation behavior unchanged.
            print("translate_caption_mode_1")
            transed_caption["trans_content"] = await self._request_llm_for_retrans_error_parts(self.prompts["retrans_error_parts_system_prompt"],
                                                                                         part=transed_caption,
                                                                                         error_message=error_message,
                                                                                         fail_part=placeholder,
                                                                                         type="cap",
                                                                                         session=session)
            
        elif self.trans_mode == 2:
            if not self.term_dict:
                transed_caption["trans_content"] = await self._request_llm_for_trans(self.prompts["caption_system_prompt"],
                                                        caption["content"], 
                                                        fail_part=placeholder,
                                                        type="cap",
                                                        session=session
                                                        )
            else:
                transed_caption["trans_content"] = await self._request_llm_for_trans_with_terms(self.prompts["caption_system_prompt_with_dict"],
                                                                                          caption["content"],
                                                                                          fail_part=placeholder,
                                                                                          type="cap",
                                                                                          session=session)
            try:
                if self.update_term == True:
                    src_text = self._extract_text_from_tex(transed_caption["content"])
                    tgt_text = self._extract_text_from_tex(transed_caption["trans_content"])
                    term_text = await self._request_llm_for_extract_terms(pm.extract_terminology_system_prompt,
                                                            src_text,
                                                            tgt_text,
                                                            session=session
                                                            )

                    # self._updated_term_dict(term_text)
                    self._updated_term_dict_v2(term_text)
            except Exception as e:
                return transed_caption

        api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("cap", placeholder))
        if (
            self._is_payload_invariant_reason(api_fallback_reason)
            and self._is_source_preserved_translation(caption["content"], transed_caption.get("trans_content", ""))
        ):
            rescued_caption = await self._rescue_plain_text_by_paragraph(
                text=caption["content"],
                identifier=placeholder,
                part_type="cap",
                session=session,
                error_message="Previous caption attempt violated protected-token invariants.",
                prompt_key="caption_system_prompt",
                prompt_key_with_terms="caption_system_prompt_with_dict",
            )
            if rescued_caption is not None:
                transed_caption["trans_content"] = rescued_caption
                self._clear_api_fallback("cap", placeholder)
                api_fallback_reason = None

        self._update_caption_metadata(
            transed_caption,
            status=self._resolve_api_fallback_status(api_fallback_reason),
            fallback_reason=api_fallback_reason,
        )

        return transed_caption

    async def _request_env_translation(
        self,
        *,
        env: Dict[str, Any],
        text: str,
        placeholder: str,
        session: aiohttp.ClientSession,
        error_message: Optional[str] = None,
    ) -> str:
        prompt_suffix = ""
        if error_message:
            prompt_suffix += f"\n[Error Correction Requirement]\n{error_message}"

        if self.trans_mode == 1:
            retry_part = {
                "content": text,
                "trans_content": env.get("trans_content", text),
            }
            return await self._request_llm_for_retrans_error_parts(
                self.prompts["retrans_error_parts_system_prompt"],
                part=retry_part,
                error_message=error_message or "",
                fail_part=placeholder,
                type="env",
                session=session,
            )

        if self.trans_mode in (0, 3):
            return await self._request_llm_for_trans(
                self.prompts["env_system_prompt"] + prompt_suffix,
                text,
                fail_part=placeholder,
                type="env",
                session=session,
            )

        if self.trans_mode == 2:
            if self.term_dict:
                return await self._request_llm_for_trans_with_terms(
                    self.prompts["env_system_prompt_with_dict"] + prompt_suffix,
                    text,
                    fail_part=placeholder,
                    type="env",
                    session=session,
                )
            return await self._request_llm_for_trans(
                self.prompts["env_system_prompt"] + prompt_suffix,
                text,
                fail_part=placeholder,
                type="env",
                session=session,
            )

        return text

    async def _translate_eqnarray_env(
        self,
        env: Dict[str, Any],
        session: aiohttp.ClientSession,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        transed_env = env.copy()
        placeholder = env["placeholder"]
        content = env.get("content", "")
        self._update_env_metadata(
            transed_env,
            status=self.STATUS_TRANSLATED,
            fallback_subtype=self.FALLBACK_SUBTYPE_NONE,
            row_fallback_count=0,
        )

        masked_content, comment_map = mask_eqnarray_comments_strict(content)
        match = re.match(
            r'(?s)\A(?P<head>\s*\\begin\{eqnarray\*?\})(?P<body>.*?)(?P<tail>\\end\{eqnarray\*?\}\s*)\Z',
            masked_content,
        )
        if not match:
            transed_env["trans_content"] = await self._request_env_translation(
                env=env,
                text=content,
                placeholder=placeholder,
                session=session,
                error_message=error_message,
            )
            api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
            self._update_env_metadata(
                transed_env,
                status=self._resolve_api_fallback_status(api_fallback_reason),
                fallback_reason=api_fallback_reason,
                fallback_subtype=self.FALLBACK_SUBTYPE_OTHER_ENV if api_fallback_reason else self.FALLBACK_SUBTYPE_NONE,
                row_fallback_count=0,
            )
            return transed_env

        head = match.group("head")
        body = match.group("body")
        tail = match.group("tail")
        rows, separators = split_eqnarray_rows_strict(body)
        row_kinds = [classify_eqnarray_row_kind(row) for row in rows]
        text_row_indices = [idx for idx, kind in enumerate(row_kinds) if kind == "text"]

        if not text_row_indices:
            rebuilt = rebuild_eqnarray_rows_strict(rows, separators)
            restored = restore_eqnarray_comments_strict(f"{head}{rebuilt}{tail}", comment_map)
            transed_env["trans_content"] = restored
            self._update_env_metadata(
                transed_env,
                status=self.STATUS_MATH_PRESERVED,
                fallback_subtype=self.FALLBACK_SUBTYPE_NONE,
                row_fallback_count=0,
            )
            return transed_env

        translated_rows = list(rows)
        row_fallback_count = 0

        for row_idx in text_row_indices:
            source_row = rows[row_idx]
            row_key = self._env_row_retry_key(placeholder, row_idx)
            token = f"<EQROW_{row_idx}>"
            payload = f"{token} {source_row}"
            expected_tokens = [token]
            translated_row_core: Optional[str] = None
            mismatch_error: Optional[str] = None

            for attempt in range(2):
                retry_hint = (
                    "Keep immutable EQROW placeholder tokens unchanged with exact count and order."
                    if attempt == 1 else None
                )
                merged_error = "\n".join(
                    part for part in [error_message, retry_hint] if part
                ) or None
                candidate = await self._request_env_translation(
                    env=env,
                    text=payload,
                    placeholder=placeholder,
                    session=session,
                    error_message=merged_error,
                )
                mismatch_error = validate_immutable_placeholder_sequence(
                    candidate,
                    expected_tokens,
                    "EQROW",
                )
                if mismatch_error:
                    if row_key in self._c1_retried_parts:
                        self.c1_retry_enforced_once = True
                        break
                    self._c1_retried_parts.add(row_key)
                    continue

                token_index = candidate.find(token)
                if token_index < 0:
                    mismatch_error = "eqrow_placeholder_sequence_mismatch: token not found after validation"
                    if row_key in self._c1_retried_parts:
                        self.c1_retry_enforced_once = True
                        break
                    self._c1_retried_parts.add(row_key)
                    continue

                row_translation = (candidate[:token_index] + candidate[token_index + len(token):]).strip()
                if row_translation:
                    translated_row_core = row_translation
                else:
                    translated_row_core = source_row.strip()
                break

            if translated_row_core is None:
                row_fallback_count += 1
                translated_rows[row_idx] = source_row
                logger.warning(
                    "Eqnarray row fallback applied for %s row=%d (%s)",
                    placeholder,
                    row_idx,
                    mismatch_error or "unknown_row_error",
                )
                continue

            leading_ws = re.match(r"^\s*", source_row).group(0)
            trailing_ws = re.search(r"\s*$", source_row).group(0)
            translated_rows[row_idx] = f"{leading_ws}{translated_row_core.strip()}{trailing_ws}"

        rebuilt_body = rebuild_eqnarray_rows_strict(translated_rows, separators)
        rebuilt_env = f"{head}{rebuilt_body}{tail}"
        restored_env = restore_eqnarray_comments_strict(rebuilt_env, comment_map)
        transed_env["trans_content"] = restored_env

        api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
        if api_fallback_reason:
            self._update_env_metadata(
                transed_env,
                status=self._resolve_api_fallback_status(api_fallback_reason),
                fallback_reason=api_fallback_reason,
                fallback_subtype=self.FALLBACK_SUBTYPE_MATH_ENV,
                row_fallback_count=row_fallback_count,
            )
            return transed_env

        self._update_env_metadata(
            transed_env,
            status=self.STATUS_TRANSLATED,
            fallback_subtype=self.FALLBACK_SUBTYPE_MATH_ENV if row_fallback_count > 0 else self.FALLBACK_SUBTYPE_NONE,
            row_fallback_count=row_fallback_count,
        )
        return transed_env

    async def _translate_list_env(
        self,
        env: Dict[str, Any],
        session: aiohttp.ClientSession,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        transed_env = env.copy()
        placeholder = env["placeholder"]
        anchored_text, item_map, expected_tokens = anchor_list_items_in_env_body(env.get("content", ""))
        if not expected_tokens:
            translated_content = await self._request_env_translation(
                env=env,
                text=env.get("content", ""),
                placeholder=placeholder,
                session=session,
                error_message=error_message,
            )
            if self._has_unrestored_env_artifacts(translated_content):
                transed_env["trans_content"] = env.get("content", "")
                self._update_env_metadata(
                    transed_env,
                    status=self.STATUS_FALLBACK_SOURCE_API_FAILURE,
                    fallback_reason="list_env_restore_preserved_source",
                    fallback_subtype=self.FALLBACK_SUBTYPE_LIST_ENV,
                    row_fallback_count=0,
                )
                return transed_env
            transed_env["trans_content"] = translated_content
            api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
            self._update_env_metadata(
                transed_env,
                status=self._resolve_api_fallback_status(api_fallback_reason),
                fallback_reason=api_fallback_reason,
                fallback_subtype=self.FALLBACK_SUBTYPE_LIST_ENV if api_fallback_reason else self.FALLBACK_SUBTYPE_NONE,
                row_fallback_count=0,
            )
            return transed_env

        list_retry_key = self._part_retry_key("env", f"{placeholder}:list")
        last_mismatch: Optional[str] = None
        last_candidate: Optional[str] = None
        for attempt in range(2):
            strict_hint = (
                "Do not reorder/remove ITEM placeholders. Preserve ITEM token count and sequence exactly."
                if attempt == 1 else None
            )
            merged_error = "\n".join(part for part in [error_message, strict_hint] if part) or None
            candidate = await self._request_env_translation(
                env=env,
                text=anchored_text,
                placeholder=placeholder,
                session=session,
                error_message=merged_error,
            )
            last_candidate = candidate
            if self._has_unrestored_env_artifacts(candidate):
                transed_env["trans_content"] = env.get("content", "")
                self._update_env_metadata(
                    transed_env,
                    status=self.STATUS_FALLBACK_SOURCE_API_FAILURE,
                    fallback_reason="list_env_restore_preserved_source",
                    fallback_subtype=self.FALLBACK_SUBTYPE_LIST_ENV,
                    row_fallback_count=0,
                )
                return transed_env
            mismatch = validate_immutable_placeholder_sequence(candidate, expected_tokens, "ITEM")
            if not mismatch:
                restored = restore_list_items_in_env_body(candidate, item_map)
                transed_env["trans_content"] = restored
                api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
                self._update_env_metadata(
                    transed_env,
                    status=self._resolve_api_fallback_status(api_fallback_reason),
                    fallback_reason=api_fallback_reason,
                    fallback_subtype=self.FALLBACK_SUBTYPE_LIST_ENV if api_fallback_reason else self.FALLBACK_SUBTYPE_NONE,
                    row_fallback_count=0,
                )
                return transed_env
            last_mismatch = mismatch
            if list_retry_key in self._c1_retried_parts:
                self.c1_retry_enforced_once = True
                break
            self._c1_retried_parts.add(list_retry_key)

        transed_env["trans_content"] = last_candidate or env.get("content", "")
        fallback_error = {
            "part": "env",
            "num_or_ph": placeholder,
            "error_type": ERROR_TYPE_C1,
            "math_error": last_mismatch or "item_anchor_sequence_mismatch: unknown",
        }
        self._apply_compile_first_fallback(
            transed_env,
            fallback_error,
            recheck_report=fallback_error,
        )
        self._update_env_metadata(
            transed_env,
            fallback_subtype=self.FALLBACK_SUBTYPE_LIST_ENV,
            row_fallback_count=0,
        )
        return transed_env

    async def _translate_env(self, env: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        """
        Translates an environment block (env) based on whether translation is needed.
        """
        transed_env = env.copy()
        placeholder = env["placeholder"]
        env_name = self._normalize_env_name(str(env.get("env_name", "")))
        need_trans = bool(env.get("need_trans", True))

        self._update_env_metadata(
            transed_env,
            status=self.STATUS_TRANSLATED,
            fallback_subtype=self.FALLBACK_SUBTYPE_NONE,
            row_fallback_count=0,
        )

        if not need_trans:
            transed_env["trans_content"] = env.get("content", "")
            return transed_env

        if env_name in {"eqnarray", "eqnarray*"}:
            transed_env = await self._translate_eqnarray_env(env, session, error_message=error_message)
        elif env_name in {"enumerate", "enumerate*", "itemize", "itemize*"}:
            transed_env = await self._translate_list_env(env, session, error_message=error_message)
        elif self._is_generic_text_env(env_name):
            wrapper = self._split_env_wrapper(env.get("content", ""), env_name)
            if wrapper is None:
                source_text = env.get("content", "")
                translated_content = await self._request_env_translation(
                    env=env,
                    text=source_text,
                    placeholder=placeholder,
                    session=session,
                    error_message=error_message,
                )
                if self._has_unrestored_env_artifacts(translated_content):
                    retried_content = await self._retry_env_translation_on_restore_artifacts(
                        env=env,
                        text=source_text,
                        placeholder=placeholder,
                        session=session,
                        error_message=error_message,
                    )
                    if retried_content is not None:
                        translated_content = retried_content
                api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
                payload_invariant_passthrough = self._is_payload_invariant_reason(api_fallback_reason)
                needs_plain_text_recovery = (
                    self._has_unrestored_env_artifacts(translated_content)
                    or bool(api_fallback_reason)
                    or self._is_source_preserved_translation(source_text, translated_content)
                )
                if needs_plain_text_recovery:
                    recovered_content = await self._recover_generic_text_env_body_as_plain_text(
                        env=env,
                        text=source_text,
                        placeholder=placeholder,
                        session=session,
                        error_message=error_message,
                    )
                    if recovered_content is not None:
                        translated_content = recovered_content
                        self._clear_api_fallback("env", placeholder)
                    else:
                        rescued_content = await self._rescue_generic_text_env_by_paragraph(
                            text=source_text,
                            placeholder=placeholder,
                            session=session,
                            error_message=error_message,
                        )
                        if rescued_content is not None:
                            translated_content = rescued_content
                            self._clear_api_fallback("env", placeholder)
                source_preserved_after_recovery = self._is_source_preserved_translation(
                    source_text,
                    translated_content,
                )
                if self._has_unrestored_env_artifacts(translated_content) or source_preserved_after_recovery:
                    transed_env["trans_content"] = source_text
                    self._update_env_metadata(
                        transed_env,
                        status=(
                            self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH
                            if payload_invariant_passthrough
                            else self.STATUS_FALLBACK_SOURCE_API_FAILURE
                        ),
                        fallback_reason=(
                            api_fallback_reason
                            if payload_invariant_passthrough and api_fallback_reason
                            else (
                                "env_plain_text_recovery_preserved_source"
                                if source_preserved_after_recovery
                                else "env_wrapper_restore_preserved_source"
                            )
                        ),
                        fallback_subtype=self.FALLBACK_SUBTYPE_OTHER_ENV,
                        row_fallback_count=0,
                    )
                    return transed_env
                transed_env["trans_content"] = translated_content
                api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
                self._update_env_metadata(
                    transed_env,
                    status=self._resolve_api_fallback_status(api_fallback_reason),
                    fallback_reason=api_fallback_reason,
                    fallback_subtype=self.FALLBACK_SUBTYPE_OTHER_ENV if api_fallback_reason else self.FALLBACK_SUBTYPE_NONE,
                    row_fallback_count=0,
                )
            else:
                env_head, env_body, env_tail = wrapper
                translated_body = await self._request_env_translation(
                    env=env,
                    text=env_body,
                    placeholder=placeholder,
                    session=session,
                    error_message=error_message,
                )
                if self._has_unrestored_env_artifacts(translated_body):
                    retried_body = await self._retry_env_translation_on_restore_artifacts(
                        env=env,
                        text=env_body,
                        placeholder=placeholder,
                        session=session,
                        error_message=error_message,
                    )
                    if retried_body is not None:
                        translated_body = retried_body
                api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
                payload_invariant_passthrough = self._is_payload_invariant_reason(api_fallback_reason)
                needs_plain_text_recovery = (
                    self._has_unrestored_env_artifacts(translated_body)
                    or bool(api_fallback_reason)
                    or self._is_source_preserved_translation(env_body, translated_body)
                )
                if needs_plain_text_recovery:
                    recovered_body = await self._recover_generic_text_env_body_as_plain_text(
                        env=env,
                        text=env_body,
                        placeholder=placeholder,
                        session=session,
                        error_message=error_message,
                    )
                    if recovered_body is not None:
                        translated_body = recovered_body
                        self._clear_api_fallback("env", placeholder)
                    else:
                        rescued_body = await self._rescue_generic_text_env_by_paragraph(
                            text=env_body,
                            placeholder=placeholder,
                            session=session,
                            error_message=error_message,
                        )
                        if rescued_body is not None:
                            translated_body = rescued_body
                            self._clear_api_fallback("env", placeholder)
                source_preserved_after_recovery = self._is_source_preserved_translation(
                    env_body,
                    translated_body,
                )
                if self._has_unrestored_env_artifacts(translated_body) or source_preserved_after_recovery:
                    translated_body = env_body
                    self._update_env_metadata(
                        transed_env,
                        status=(
                            self.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH
                            if payload_invariant_passthrough
                            else self.STATUS_FALLBACK_SOURCE_API_FAILURE
                        ),
                        fallback_reason=(
                            api_fallback_reason
                            if payload_invariant_passthrough and api_fallback_reason
                            else (
                                "env_plain_text_recovery_preserved_source"
                                if source_preserved_after_recovery
                                else "env_wrapper_restore_preserved_source"
                            )
                        ),
                        fallback_subtype=self.FALLBACK_SUBTYPE_OTHER_ENV,
                        row_fallback_count=0,
                    )
                transed_env["trans_content"] = f"{env_head}{translated_body}{env_tail}"
                if transed_env.get("translation_status") != self.STATUS_FALLBACK_SOURCE_API_FAILURE:
                    api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
                    self._update_env_metadata(
                        transed_env,
                        status=self._resolve_api_fallback_status(api_fallback_reason),
                        fallback_reason=api_fallback_reason,
                        fallback_subtype=self.FALLBACK_SUBTYPE_OTHER_ENV if api_fallback_reason else self.FALLBACK_SUBTYPE_NONE,
                        row_fallback_count=0,
                    )
        else:
            transed_env["trans_content"] = await self._request_env_translation(
                env=env,
                text=env.get("content", ""),
                placeholder=placeholder,
                session=session,
                error_message=error_message,
            )
            api_fallback_reason = self._api_fallback_parts.get(self._part_retry_key("env", placeholder))
            self._update_env_metadata(
                transed_env,
                status=self._resolve_api_fallback_status(api_fallback_reason),
                fallback_reason=api_fallback_reason,
                fallback_subtype=self.FALLBACK_SUBTYPE_OTHER_ENV if api_fallback_reason else self.FALLBACK_SUBTYPE_NONE,
                row_fallback_count=0,
            )

        if self.trans_mode == 2 and need_trans:
            try:
                if self.update_term:
                    src_text = self._extract_text_from_tex(transed_env["content"])
                    tgt_text = self._extract_text_from_tex(transed_env.get("trans_content") or transed_env["content"])
                    text = await self._request_llm_for_extract_terms(
                        pm.extract_terminology_system_prompt,
                        src_text,
                        tgt_text,
                        session=session,
                    )
                    self._updated_term_dict_v2(text)
            except Exception:
                return transed_env

        return transed_env

    async def _request_llm_for_trans(self,
                                     system_prompt: str,
                                     text: str,
                                     fail_part: str,
                                     type: str,
                                     session: aiohttp.ClientSession,
                                     previous_context: Optional[str] = None) -> str:
        # Inject Reference Context Template if available
        if previous_context and "REFERENCE_CONTEXT_TEMPLATE" in self.prompts:
            template = self.prompts["REFERENCE_CONTEXT_TEMPLATE"]
            system_prompt += template.format(context=previous_context)
        try:
            return await self._call_llm_with_freeze(
                system_prompt=system_prompt,
                user_text=text,
                fail_part=fail_part,
                part_type=type,
                session=session,
                fallback_text=text,
                include_glossary=False,
            )
        except PipelineInvariantViolation as inv:
            logger.error(
                "LLM payload invariant violation for %s (%s): %s",
                fail_part,
                inv.error_code,
                inv,
            )
            self._register_llm_part_failure(type, str(fail_part))
            self._mark_api_fallback(type, str(fail_part), f"invariant_{inv.error_code.lower()}")
            return text


    async def _request_llm_for_trans_with_terms(self,
                                          system_prompt: str,
                                          text: str,
                                          fail_part: str,
                                          type: str,
                                          session: aiohttp.ClientSession,
                                          previous_context: Optional[str] = None) -> str:
        # Inject Reference Context Template if available
        if previous_context and "REFERENCE_CONTEXT_TEMPLATE" in self.prompts:
            template = self.prompts["REFERENCE_CONTEXT_TEMPLATE"]
            system_prompt += template.format(context=previous_context)
        try:
            return await self._call_llm_with_freeze(
                system_prompt=system_prompt,
                user_text=text,
                fail_part=fail_part,
                part_type=type,
                session=session,
                fallback_text=text,
                include_glossary=True,
                user_prefix="[Current LaTeX Paragraph]:\n",
            )
        except PipelineInvariantViolation as inv:
            logger.error(
                "LLM payload invariant violation (with terms) for %s (%s): %s",
                fail_part,
                inv.error_code,
                inv,
            )
            self._register_llm_part_failure(type, str(fail_part))
            self._mark_api_fallback(type, str(fail_part), f"invariant_{inv.error_code.lower()}")
            return text


    async def _request_llm_for_retrans_error_parts(self,
                                                   system_prompt: str,
                                                   part: Dict[str, Any],
                                                   error_message: str,
                                                   fail_part: str,
                                                   type: str,
                                                   session: aiohttp.ClientSession) -> str:
        safe_error_message = self._sanitize_retrans_error_message(error_message or "")
        raw_user_prompt = (
            f"[Original]:\n{part.get('content', '')}\n"
            f"[Translation]:\n{part.get('trans_content', '')}\n"
            f"[Error]:\n{safe_error_message}"
        )
        fallback_text = part.get("trans_content") or part.get("content", "")
        try:
            return await self._call_llm_with_freeze(
                system_prompt=system_prompt,
                user_text=raw_user_prompt,
                fail_part=fail_part,
                part_type=type,
                session=session,
                fallback_text=fallback_text,
                include_glossary=True,
            )
        except PipelineInvariantViolation as inv:
            logger.error(
                "Retrans payload invariant violation for %s (%s): %s",
                fail_part,
                inv.error_code,
                inv,
            )
            self._register_llm_part_failure(type, str(fail_part))
            self._mark_api_fallback(type, str(fail_part), f"invariant_{inv.error_code.lower()}")
            return fallback_text

    async def _request_llm_for_extract_terms(self, system_prompt, src, tgt,
                                       session: aiohttp.ClientSession) -> str:

        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<en source>\n{src}\n<zh translation>\n{tgt}"
                }
            ],
            "temperature": 0.7,
            # "max_length": 100000,
            # "max_tokens": 50
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        _timeout = build_llm_client_timeout(self.config, default=self.request_timeout_seconds)
        for attempt in range(1, 4):
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 10 * attempt))
                            logger.warning(f"Rate limited (429) during term extraction, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if isinstance(e, aiohttp.ClientResponseError) and e.status in (400, 401, 403, 404):
                    logger.error(f"鉂?Fatal API error {e.status} during term extraction: {getattr(e, 'message', str(e))}. Aborting retries.")
                    return "N/A"

                wait = 5 * (2 ** (attempt - 1))  # 5s, 10s, 20s
                if attempt < 3:
                    logger.warning(f"Term extraction attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Failed to extract terms after 3 attempts, set N/A.")
                    return "N/A"

    async def _request_llm_for_summary(self, system_prompt: str, text: str, session: aiohttp.ClientSession) -> str:
        """
        Requests the LLM to summarize the given text.
        """
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<Text to summarize>:\n{text}\n<Summary>:\n"
                }
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        _timeout = build_llm_client_timeout(self.config, default=self.request_timeout_seconds)
        for attempt in range(1, 4):
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 10 * attempt))
                            logger.warning(f"Rate limited (429) during summarization, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait = 5 * (2 ** (attempt - 1))
                if attempt < 3:
                    logger.warning(f"Summary attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Failed to summarize text after 3 attempts, set N/A.")
                    return "N/A"

    async def _request_llm_for_refine_summary(self, system_prompt: str, text: str, sum: str, session: aiohttp.ClientSession) -> str:
        """
        Requests the LLM to refine the given summary.
        """
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<prev_summary>:\n{sum}\n<new_section>:\n{text}\n<refined_summary>:\n"
                }
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        _timeout = build_llm_client_timeout(self.config, default=self.request_timeout_seconds)
        for attempt in range(1, 4):
            try:
                async with global_llm_semaphore:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=_timeout) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 10 * attempt))
                            logger.warning(f"Rate limited (429) during refine summary, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait = 5 * (2 ** (attempt - 1))
                if attempt < 3:
                    logger.warning(f"Refine summary attempt {attempt}/3 failed: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.warning("Failed to refine summary after 3 attempts, set N/A.")
                    return "N/A"

    def _updated_term_dict(self, text: str) -> None:
        """
        Updates the term dictionary with new terms.
        """
        pattern = r'"([^"]+)"\s*-\s*"([^"]+)"'
        matches = re.findall(pattern, text)

        seen_lower = {k.lower() for k in self.term_dict}
        
        for en, zh in matches:
            en_lower = en.lower()
            if en_lower not in seen_lower:
                self.term_dict[en] = zh  
                seen_lower.add(en_lower)

        self.save_file(Path(self.output_dir, "term_dict.json"), "json", self.term_dict)

    def _updated_term_dict_v2(self, text: str) -> None:

        new_term_dict = {}
        lines = text.split('\n')[1:]
        for line in lines:
            line = line.strip()
            if not line:
                continue  

            match = re.match(r'^"(.+?)"\s*-\s*"(.+?)"$', line)
            if match:
                english = match.group(1)
                chinese = match.group(2)
                new_term_dict[english] = chinese

        for en, zh in new_term_dict.items():
            if en not in self.term_dict:
                self.term_dict[en] = zh

    def _process_latex_to_eva(self, latex_code):
        latex_code = replace_href(latex_code)
        latex_code = replace_includegraphics(latex_code)
        return latex_code

    def _extract_text_from_tex(self, tex):
        # convert = CustomLatexNodes2Text()
        # text = convert.latex_to_text(tex)
        tex = self._process_latex_to_eva(tex)
        text = LatexNodes2Text().latex_to_text(tex)
        text = delete_ph(text)
        return text
    
    def _merge_with_prev_sections(self, sections: list[dict], idx: int) -> str:
        """
        Merge content of current section with previous two sections (if valid).
        Ignore sections whose 'section' field is "-1" or "0".

        Parameters:
            sections (list of dict): A list of sections, each with keys "section" and "content".
            idx (int): The index of the current section in the list.

        Returns:
            str: The merged content string.
        """
        if not (0 <= idx < len(sections)):
            raise IndexError("Index out of range.")

        merged_content = []
        merged_trans_content = []

        # Check second previous section
        # if idx >= 2:
        #     sec = sections[idx - 2]
        #     if sec["section"] not in {"-1", "0"}:
        #         try:
        #             content = self._extract_text_from_tex(sec["content"])
        #             transed_content = self._extract_text_from_tex(sec["trans_content"])
        #             merged_content.append(content)
        #             merged_trans_content.append(transed_content)
        #         except Exception as e:
        #             pass
                

        # Check first previous section
        if idx >= 1:
            sec = sections[idx - 1]
            if sec["section"] not in {"-1", "0"}:
                try:
                    content = self._extract_text_from_tex(sec["content"])
                    transed_content = self._extract_text_from_tex(sec["trans_content"])
                    merged_content.append(content)
                    merged_trans_content.append(transed_content)
                except Exception as e:
                    pass

        # Always include current section
        try:
            content = self._extract_text_from_tex(sections[idx]["content"])
            transed_content = self._extract_text_from_tex(sections[idx]["trans_content"])
            merged_content.append(content)
            merged_trans_content.append(transed_content)
        except Exception as e:
            pass

        return "\n".join(merged_content)

    def build_term_dict(self):
        if self.user_term:
            df = pd.read_csv(self.user_term, header=None, names=['English Term', 'Chinese Translation'])
            self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
        else:
            arxiv_id = os.path.basename(self.project_dir)
            # Check if category is not None and has the arxiv_id
            if self.category and self.category.get(arxiv_id):
                term_dict_loaded = False
                for category in self.category[arxiv_id]:
                    file_path = os.path.join('terms', f'{category}.csv')
                    try:
                        df = pd.read_csv(file_path, header=None, names=['English Term', 'Chinese Translation'])
                        self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                        term_dict_loaded = True

                    except FileNotFoundError:
                        continue

                if not term_dict_loaded:
                    try:
                        df = pd.read_csv('terms/default.csv', header=None,
                                         names=['English Term', 'Chinese Translation'])
                        self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                    except FileNotFoundError as e:
                        print(f"Error: Default terminology file not found: {e}")
            else:
                try:
                    df = pd.read_csv('terms/default.csv', header=None,
                                     names=['English Term', 'Chinese Translation'])
                    self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                except FileNotFoundError as e:
                    print(f"Error: Default terminology file not found: {e}")

    def add_placeholder(self):

        # Add placeholders from caption, env, input, and newcommand to the vocabulary
        caption_path = os.path.join(self.output_dir, "captions_map.json")
        input_path = os.path.join(self.output_dir, "inputs_map.json")
        env_path = os.path.join(self.output_dir, "envs_map.json")
        command_path = os.path.join(self.output_dir, "newcommands_map.json")

        placeholder_list = []

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "begin" in item:
                placeholder_list.append(item["begin"])
            if "end" in item:
                placeholder_list.append(item["end"])

        with open(env_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])

        with open(caption_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])

        with open(command_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])


        for item in placeholder_list:
            self.term_dict[item] = item

    def _save_terminology_table(self) -> None:
        """
        Save terminology table to CSV file in output directory.
        """
        import csv
        
        if not self.terminology_table:
            logger.warning("Terminology table is empty, skipping save")
            return
        
        # 鍘婚噸
        unique_terms = list(dict.fromkeys(self.terminology_table))
        
        term_file = Path(self.output_dir) / "terminology_table.csv"
        try:
            with open(term_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Source Term', 'Translation'])
                writer.writerows(unique_terms)
            logger.info(f"Terminology table saved to {term_file} with {len(unique_terms)} unique terms")
        except Exception as e:
            logger.error(f"Failed to save terminology table: {e}")
    
    async def _extract_terminology_from_translation(
        self, 
        src_text: str, 
        tgt_text: str, 
        session: aiohttp.ClientSession
    ) -> List[Tuple[str, str]]:
        """
        Extract terminology pairs from source and target text.
        Returns list of (source_term, target_term) tuples.
        """
        if not self.generate_terminology:
            return []
        
        try:
            # 浣跨敤鐜版湁鐨勬湳璇彁鍙栭€昏緫
            term_text = await self._request_llm_for_extract_terms(
                self.prompts["extract_terminology_system_prompt"],
                src_text,
                tgt_text,
                session=session
            )
            
            # 瑙ｆ瀽杩斿洖鐨勬湳璇枃鏈负鏈瀵瑰垪琛?
            terms = self._parse_terminology_text(term_text)
            return terms
        except Exception as e:
            logger.warning(f"Failed to extract terminology: {e}")
            return []
    
    def _parse_terminology_text(self, term_text: str) -> List[Tuple[str, str]]:
        """
        Parse terminology text from LLM response into list of tuples.
        Expects format like: "term1: translation1\nterm2: translation2"
        """
        terms = []
        if not term_text or term_text == "N/A":
            return terms
        
        lines = term_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 灏濊瘯澶氱鍒嗛殧绗?
            for sep in [':', '：', '|', '-', '->']:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        src = parts[0].strip()
                        tgt = parts[1].strip()
                        if src and tgt:
                            terms.append((src, tgt))
                        break
        return terms

    def _log_protection_actions(
        self,
        mapping: Dict[str, str],
        fail_part: str,
        *,
        hard_freeze_entries: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Task 12.5: Persist protection log entries to data/protection_log/<task_id>.json.

        Only writes when *mapping* is non-empty.  Entries are appended to an
        existing JSON array so the file accumulates across all translation calls.
        """
        if (not mapping and not hard_freeze_entries) or not self.output_dir:
            return

        try:
            output_dir = Path(self.output_dir)
            if not output_dir.exists():
                return
            # Convention: output_dir is <data_root>/<task_id>/output  (or similar).
            task_id = output_dir.parent.name or output_dir.name

            log_dir = output_dir.parent.parent / "protection_log"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{task_id}.json"

            entries: list = []
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as fh:
                        entries = json.load(fh)
                except (json.JSONDecodeError, OSError):
                    entries = []

            for placeholder, original in mapping.items():
                entries.append({
                    "fail_part": fail_part,
                    "placeholder": placeholder,
                    "original_command": original,
                    "type": "mask_mapping",
                })

            for item in hard_freeze_entries or []:
                entries.append(
                    {
                        "fail_part": fail_part,
                        "type": "hard_freeze",
                        "token": item.get("token"),
                        "original": item.get("original"),
                        "kind": item.get("kind"),
                        "ordinal": item.get("ordinal"),
                        "request_nonce": item.get("request_nonce"),
                        "digest": item.get("digest"),
                    }
                )

            with open(log_file, "w", encoding="utf-8") as fh:
                json.dump(entries, fh, ensure_ascii=False, indent=2)

            logger.debug(
                "_log_protection_actions: wrote %d entries to %s",
                len(mapping),
                log_file,
            )
        except Exception as exc:
            logger.warning("_log_protection_actions failed: %s", exc)

