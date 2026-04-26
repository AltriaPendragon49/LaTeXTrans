"""
compilation_diagnostic_node.py
Phase 4b — CompilationDiagnosticNode（Gate 4b-3）

设计约束（来自 OpenSpec langgraph-agent-evolution Step 4）：
  - 独立于 ControlledRepairAgent，严禁引入字符级修补
  - 只输出结构化诊断建议（DiagnosticReport），不写回任何 .tex 文件
  - 所有 suggestions.action_type 必须在白名单枚举内
  - 每次 LLM 调用完整原始响应存入 raw_llm_response 供审计
  - 默认禁用（由 orchestrator 的 feature flag 控制是否激活本节点）
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

import aiohttp
from pydantic import BaseModel, field_validator, model_validator
from .llm_runtime import build_llm_client_timeout, resolve_llm_timeout
from .llm_token_pool import post_chat_completion_with_pool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 白名单动作集（只允许下列操作类型作为建议动作，任何其他值将被 schema 拒绝）
# ---------------------------------------------------------------------------
WHITELISTED_ACTION_TYPES = frozenset({
    "comment_package",     # 注释掉某个宏包
    "add_usepackage",      # 建议补充宏包
    "fix_preamble",        # 建议修正 preamble 块
    "manual_review",       # 建议人工介入
})

# 诊断 LLM 的系统提示（严格只做分析，绝不提供修改后内容）
_DIAGNOSTIC_SYSTEM_PROMPT = (
    "You are a LaTeX compilation error analyst. "
    "Your ONLY task is to analyze the provided compilation error log and output a "
    "structured JSON diagnostic report. "
    "\n\n"
    "ABSOLUTE PROHIBITIONS — violating these rules is a critical failure:\n"
    "1. You MUST NOT output any modified LaTeX source code.\n"
    "2. You MUST NOT perform any character-level patching or text rewriting.\n"
    "3. You MUST NOT translate any text.\n"
    "4. You MUST NOT suggest actions outside the whitelist: "
    "[comment_package, add_usepackage, fix_preamble, manual_review].\n"
    "\n"
    "Output ONLY valid JSON with the following structure:\n"
    "{\n"
    '  "root_cause_category": "<package_conflict|syntax_error|env_mismatch|unknown>",\n'
    '  "confidence": <0.0-1.0>,\n'
    '  "is_actionable": <true|false>,\n'
    '  "suggestions": [\n'
    '    {\n'
    '      "action_type": "<comment_package|add_usepackage|fix_preamble|manual_review>",\n'
    '      "target": "<package_name_or_filename>",\n'
    '      "reason": "<brief structural reason>"'
    '    }\n'
    '  ]\n'
    "}"
)


# ---------------------------------------------------------------------------
# Pydantic Schema
# ---------------------------------------------------------------------------


class DiagnosticSuggestion(BaseModel):
    """单条诊断建议（所有字段不可变，action_type 白名单严格校验）。"""
    action_type: Literal[
        "comment_package",
        "add_usepackage",
        "fix_preamble",
        "manual_review",
    ]
    target: str
    reason: str
    is_whitelisted: bool = True
    reversible: bool = True  # 所有建议固定为可回滚

    @model_validator(mode="after")
    def enforce_reversible_and_whitelisted(self) -> "DiagnosticSuggestion":
        # 白名单内的 action_type 永远是可回滚且已白名单化的
        assert self.action_type in WHITELISTED_ACTION_TYPES, (
            f"action_type '{self.action_type}' 不在白名单内"
        )
        return self


class DiagnosticReport(BaseModel):
    """编译诊断报告（Gate 4b-3 结构化输出）。"""
    task_id: str
    error_count: int
    root_cause_category: Literal[
        "package_conflict",
        "syntax_error",
        "env_mismatch",
        "unknown",
    ]
    suggestions: List[DiagnosticSuggestion]
    confidence: float
    is_actionable: bool
    raw_llm_response: str  # 审计：存储 LLM 原始响应

    @field_validator("suggestions")
    @classmethod
    def cap_suggestions(cls, v: list) -> list:
        """最多允许 3 条建议，防止过度干预。"""
        if len(v) > 3:
            return v[:3]
        return v

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ---------------------------------------------------------------------------
# CompilationDiagnosticNode
# ---------------------------------------------------------------------------


class CompilationDiagnosticNode:
    """
    Phase 4b 编译失败诊断节点（Gate 4b-3）。

    设计原则：
      - 输入：error_summary（字符串）+ error_count（整数）
      - 输出：DiagnosticReport（仅包含结构化建议，绝不含修改后的 LaTeX）
      - 副作用：ZERO — 此节点绝不读写任何 .tex 文件

    使用方式：
        node = CompilationDiagnosticNode(config=config, task_id=task_id)
        report = await node.execute(error_summary=..., error_count=...)
    """

    def __init__(self, config: Dict[str, Any], task_id: str = "") -> None:
        llm_cfg = config.get("llm_config", {}) or {}
        self._config = config
        self._api_key: str = llm_cfg.get("api_key", "")
        self._base_url: str = llm_cfg.get("base_url", "")
        self._model: str = llm_cfg.get("model", "gpt-4o")
        self._timeout_seconds: int = resolve_llm_timeout(config, default=120)
        self._task_id: str = task_id

    def _build_user_message(self, error_summary: str, error_count: int) -> str:
        return (
            f"Compilation error count: {error_count}\n\n"
            f"Error log:\n{error_summary[:4000]}"  # 截断防 token 爆炸
        )

    def _build_payload(self, error_summary: str, error_count: int) -> Dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _DIAGNOSTIC_SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_message(error_summary, error_count)},
            ],
            "temperature": 0.0,
            "max_new_tokens": 1024,
        }

    def _uses_system_pool(self) -> bool:
        llm_config = self._config.get("llm_config", {})
        if str(llm_config.get("pool_mode") or "").strip() == "system_managed" and llm_config.get("pool_members"):
            return True
        return bool(str(llm_config.get("base_url") or "").strip() and str(llm_config.get("api_key") or "").strip())

    def _parse_llm_response(
        self,
        raw: str,
        task_id: str,
        error_count: int,
    ) -> DiagnosticReport:
        """解析 LLM JSON 输出，失败时降级为 unknown / not actionable。"""
        try:
            data = json.loads(raw)
            suggestions_raw = data.get("suggestions", [])[:3]
            suggestions = []
            for s in suggestions_raw:
                try:
                    suggestions.append(DiagnosticSuggestion(
                        action_type=s.get("action_type", "manual_review"),
                        target=s.get("target", "unknown"),
                        reason=s.get("reason", ""),
                    ))
                except Exception:
                    # 非白名单动作直接跳过
                    pass

            return DiagnosticReport(
                task_id=task_id,
                error_count=error_count,
                root_cause_category=data.get("root_cause_category", "unknown"),
                suggestions=suggestions,
                confidence=float(data.get("confidence", 0.5)),
                is_actionable=bool(data.get("is_actionable", False)),
                raw_llm_response=raw,
            )
        except Exception as e:
            logger.warning("CompilationDiagnosticNode: LLM response parse failed: %s", e)
            return DiagnosticReport(
                task_id=task_id,
                error_count=error_count,
                root_cause_category="unknown",
                suggestions=[],
                confidence=0.0,
                is_actionable=False,
                raw_llm_response=raw,
            )

    async def execute(
        self,
        error_summary: str,
        error_count: int = 0,
    ) -> DiagnosticReport:
        """
        向 LLM 发起一次诊断调用（无 retry），返回 DiagnosticReport。

        如果 LLM 调用失败，返回 root_cause_category="unknown"，is_actionable=False。
        绝对不会修改任何文件。
        """
        payload = self._build_payload(error_summary, error_count)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        timeout = build_llm_client_timeout(self._config, default=self._timeout_seconds)

        raw = ""
        try:
            async with aiohttp.ClientSession() as session:
                if self._uses_system_pool():
                    result = await post_chat_completion_with_pool(
                        session=session,
                        llm_config=self._config.get("llm_config", {}),
                        payload=payload,
                        timeout=timeout,
                    )
                    raw = result["choices"][0]["message"]["content"].strip()
                    return self._parse_llm_response(raw, self._task_id, error_count)
                async with session.post(
                    self._base_url, json=payload, headers=headers, timeout=timeout
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    raw = result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(
                "CompilationDiagnosticNode: LLM call failed (task_id=%s): %s",
                self._task_id, e,
            )
            return DiagnosticReport(
                task_id=self._task_id,
                error_count=error_count,
                root_cause_category="unknown",
                suggestions=[],
                confidence=0.0,
                is_actionable=False,
                raw_llm_response=f"LLM call failed: {e}",
            )

        return self._parse_llm_response(raw, self._task_id, error_count)
