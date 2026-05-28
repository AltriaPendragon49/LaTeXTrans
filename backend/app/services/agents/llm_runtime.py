"""LLM 运行时配置工具模块。

负责从配置中提取 LLM 参数、解析超时和并发限制等。
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp

from backend.app.core.config import settings


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """将值安全地转换为 Mapping 类型，无效时返回空字典。"""
    if isinstance(value, Mapping):
        return value
    return {}


def extract_llm_config(config: Any) -> Mapping[str, Any]:
    """从配置中提取 LLM 配置子字典。"""
    mapping = _as_mapping(config)
    llm_config = mapping.get("llm_config")
    if isinstance(llm_config, Mapping):
        return llm_config
    return mapping


def _coerce_positive_int(value: Any, fallback: int) -> int:
    """尝试将值解析为正整数，失败时返回回退值。"""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def resolve_llm_timeout(config: Any = None, *, default: int | None = None) -> int:
    """解析 LLM 请求超时（秒），优先使用配置中的值。"""
    fallback = default if default is not None else settings.llm_timeout
    llm_config = extract_llm_config(config)
    return _coerce_positive_int(llm_config.get("timeout"), fallback)


def resolve_llm_max_concurrent_requests(
    config: Any = None,
    *,
    default: int | None = None,
) -> int:
    """解析 LLM 最大并发请求数，优先使用配置中的值。"""
    fallback = default if default is not None else settings.llm_max_concurrent_requests
    mapping = _as_mapping(config)
    return _coerce_positive_int(mapping.get("llm_max_concurrent_requests"), fallback)


def resolve_task_llm_max_concurrent_requests(
    config: Any = None,
    *,
    default: int | None = None,
    cap: int | None = 10,
) -> int:
    """解析任务级别 LLM 最大并发请求数，支持上限限制。"""
    value = resolve_llm_max_concurrent_requests(config, default=default)
    if cap is None:
        return value
    return min(value, _coerce_positive_int(cap, value))


def build_llm_client_timeout(config: Any = None, *, default: int | None = None) -> aiohttp.ClientTimeout:
    """根据配置构建 aiohttp 客户端超时对象。"""
    return aiohttp.ClientTimeout(total=resolve_llm_timeout(config, default=default))
