from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp

from backend.app.core.config import settings


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def extract_llm_config(config: Any) -> Mapping[str, Any]:
    mapping = _as_mapping(config)
    llm_config = mapping.get("llm_config")
    if isinstance(llm_config, Mapping):
        return llm_config
    return mapping


def _coerce_positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def resolve_llm_timeout(config: Any = None, *, default: int | None = None) -> int:
    fallback = default if default is not None else settings.llm_timeout
    llm_config = extract_llm_config(config)
    return _coerce_positive_int(llm_config.get("timeout"), fallback)


def resolve_llm_max_concurrent_requests(
    config: Any = None,
    *,
    default: int | None = None,
) -> int:
    fallback = default if default is not None else settings.llm_max_concurrent_requests
    mapping = _as_mapping(config)
    return _coerce_positive_int(mapping.get("llm_max_concurrent_requests"), fallback)


def resolve_task_llm_max_concurrent_requests(
    config: Any = None,
    *,
    default: int | None = None,
    cap: int | None = 10,
) -> int:
    value = resolve_llm_max_concurrent_requests(config, default=default)
    if cap is None:
        return value
    return min(value, _coerce_positive_int(cap, value))


def build_llm_client_timeout(config: Any = None, *, default: int | None = None) -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(total=resolve_llm_timeout(config, default=default))
