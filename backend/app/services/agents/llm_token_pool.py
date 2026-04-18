from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

import aiohttp

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({429, 503})
_STATUS_503_FAILOVER_THRESHOLD = 2


def build_pool_members_from_groups(groups: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    members: list[dict[str, str]] = []
    for group_index, group in enumerate(groups):
        base_url = str(group.get("base_url") or "").strip()
        if not base_url:
            continue
        api_keys = group.get("api_keys") or []
        group_id = str(group.get("group_id") or f"group-{group_index}")
        for key_index, api_key in enumerate(api_keys):
            normalized_key = str(api_key or "").strip()
            if not normalized_key:
                continue
            members.append(
                {
                    "member_id": f"{group_id}-member-{key_index}",
                    "base_url": base_url,
                    "api_key": normalized_key,
                }
            )
    return members


def compute_pool_routing_key(members: Iterable[Mapping[str, Any]]) -> str:
    normalized = []
    for member in members:
        normalized.append(
            (
                str(member.get("member_id") or "").strip(),
                str(member.get("base_url") or "").strip(),
                str(member.get("api_key") or "").strip(),
            )
        )
    digest = hashlib.md5(repr(sorted(normalized)).encode("utf-8")).hexdigest()
    return f"system-pool:{digest}"


@dataclass
class _MemberState:
    member_id: str
    base_url: str
    api_key: str
    cooldown_until: float = 0.0
    consecutive_429: int = 0
    consecutive_503: int = 0
    last_used_at: float = 0.0


class _PoolRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pools: dict[str, dict[str, _MemberState]] = {}

    def ensure_pool(self, pool_id: str, members: Iterable[Mapping[str, Any]]) -> dict[str, _MemberState]:
        now = time.monotonic()
        with self._lock:
            state = self._pools.setdefault(pool_id, {})
            seen: set[str] = set()
            for member in members:
                member_id = str(member.get("member_id") or "").strip()
                base_url = str(member.get("base_url") or "").strip()
                api_key = str(member.get("api_key") or "").strip()
                if not member_id or not base_url or not api_key:
                    continue
                seen.add(member_id)
                existing = state.get(member_id)
                if existing is None:
                    state[member_id] = _MemberState(
                        member_id=member_id,
                        base_url=base_url,
                        api_key=api_key,
                        last_used_at=now,
                    )
                else:
                    existing.base_url = base_url
                    existing.api_key = api_key
            stale = [member_id for member_id in state if member_id not in seen]
            for member_id in stale:
                state.pop(member_id, None)
            return dict(state)

    def choose_member(self, pool_id: str, *, exclude: Optional[set[str]] = None) -> Optional[_MemberState]:
        now = time.monotonic()
        with self._lock:
            state = self._pools.get(pool_id, {})
            healthy = [
                member
                for member in state.values()
                if member.member_id not in (exclude or set()) and member.cooldown_until <= now
            ]
            if not healthy:
                return None
            return min(healthy, key=lambda item: (item.last_used_at, item.member_id))

    def mark_attempt(self, pool_id: str, member_id: str) -> None:
        with self._lock:
            member = self._pools.get(pool_id, {}).get(member_id)
            if member is not None:
                member.last_used_at = time.monotonic()

    def record_success(self, pool_id: str, member_id: str) -> None:
        with self._lock:
            member = self._pools.get(pool_id, {}).get(member_id)
            if member is None:
                return
            member.consecutive_429 = 0
            member.consecutive_503 = 0
            member.cooldown_until = 0.0
            member.last_used_at = time.monotonic()

    def record_status(self, pool_id: str, member_id: str, status: int, *, retry_after_seconds: int = 0) -> tuple[int, bool]:
        now = time.monotonic()
        with self._lock:
            member = self._pools.get(pool_id, {}).get(member_id)
            if member is None:
                return 0, False
            member.last_used_at = now
            if status == 429:
                member.consecutive_429 += 1
                member.consecutive_503 = 0
                member.cooldown_until = max(member.cooldown_until, now + max(retry_after_seconds, 0))
                return member.consecutive_429, True
            if status == 503:
                member.consecutive_503 += 1
                member.consecutive_429 = 0
                if member.consecutive_503 >= _STATUS_503_FAILOVER_THRESHOLD:
                    member.cooldown_until = max(member.cooldown_until, now + 1)
                return member.consecutive_503, member.consecutive_503 >= _STATUS_503_FAILOVER_THRESHOLD
            member.consecutive_429 = 0
            member.consecutive_503 = 0
            member.cooldown_until = 0.0
            return 0, False


_POOL_REGISTRY = _PoolRegistry()


def _parse_retry_after_seconds(headers: Optional[Mapping[str, str]]) -> int:
    raw = str((headers or {}).get("Retry-After") or "").strip()
    if raw.isdigit():
        return max(int(raw), 0)
    return 1


async def _perform_member_request(
    *,
    session: aiohttp.ClientSession,
    base_url: str,
    api_key: str,
    member_id: str,
    payload: Dict[str, Any],
    timeout: aiohttp.ClientTimeout,
) -> tuple[int, Mapping[str, str], Optional[Dict[str, Any]]]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-LLM-Pool-Member": member_id,
    }
    async with session.post(
        base_url,
        json=payload,
        headers=headers,
        timeout=timeout,
    ) as response:
        if response.status in _RETRYABLE_STATUS_CODES:
            return response.status, getattr(response, "headers", {}) or {}, None
        response.raise_for_status()
        return response.status, getattr(response, "headers", {}) or {}, await response.json()


async def post_chat_completion_with_pool(
    *,
    session: aiohttp.ClientSession,
    llm_config: Mapping[str, Any],
    payload: Dict[str, Any],
    timeout: aiohttp.ClientTimeout,
    on_retry_message: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    members = list(llm_config.get("pool_members") or [])
    if llm_config.get("pool_mode") != "system_managed" or not members:
        headers = {
            "Authorization": f"Bearer {str(llm_config.get('api_key') or '').strip()}",
            "Content-Type": "application/json",
        }
        async with session.post(
            str(llm_config.get("base_url") or "").strip(),
            json=payload,
            headers=headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            return await response.json()

    pool_id = str(llm_config.get("pool_routing_key") or compute_pool_routing_key(members))
    _POOL_REGISTRY.ensure_pool(pool_id, members)
    current = _POOL_REGISTRY.choose_member(pool_id) or next(iter(_POOL_REGISTRY.ensure_pool(pool_id, members).values()))

    while True:
        _POOL_REGISTRY.mark_attempt(pool_id, current.member_id)
        status_code, headers, result = await _perform_member_request(
            session=session,
            base_url=current.base_url,
            api_key=current.api_key,
            member_id=current.member_id,
            payload=payload,
            timeout=timeout,
        )

        if status_code in _RETRYABLE_STATUS_CODES:
            retry_after_seconds = _parse_retry_after_seconds(headers)
            streak, may_failover = _POOL_REGISTRY.record_status(
                pool_id,
                current.member_id,
                status_code,
                retry_after_seconds=retry_after_seconds,
            )
            alternative = _POOL_REGISTRY.choose_member(pool_id, exclude={current.member_id})
            if may_failover and alternative is not None:
                if on_retry_message is not None:
                    on_retry_message(
                        f"LLM pool member {current.member_id} returned {status_code}; fail over to {alternative.member_id}"
                    )
                current = alternative
                continue
            if alternative is not None and status_code == 429:
                if on_retry_message is not None:
                    on_retry_message(
                        f"LLM pool member {current.member_id} hit 429; fail over to {alternative.member_id}"
                    )
                current = alternative
                continue

            wait_seconds = retry_after_seconds if status_code == 429 else 1
            if on_retry_message is not None:
                on_retry_message(
                    f"LLM pool all members unavailable on {status_code}; retry current member {current.member_id} in {wait_seconds}s"
                )
            await asyncio.sleep(wait_seconds)
            continue

        _POOL_REGISTRY.record_success(pool_id, current.member_id)
        return result or {}
