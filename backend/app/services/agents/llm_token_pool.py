"""LLM 令牌池 —— 多成员调度、故障转移和速率限制管理模块。

提供多 LLM 提供者成员的智能调度、基于 HTTP 状态码的故障转移、
速率限制（429）和瞬态错误（503/5xx）的重试逻辑。
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

import aiohttp

logger = logging.getLogger(__name__)

# 可重试的 HTTP 状态码
_RETRYABLE_STATUS_CODES = frozenset({429, 503})
# 503 故障转移阈值
_STATUS_503_FAILOVER_THRESHOLD = 3
# 503 冷却时间（秒）
_STATUS_503_COOLDOWN_SECONDS = 8
# 所有成员不可用时 503 重试等待时间（秒）
_ALL_MEMBERS_UNAVAILABLE_503_RETRY_SECONDS = 2
# 默认成员并发数
_DEFAULT_MEMBER_CONCURRENCY = 1


class ProviderErrorKind(str, Enum):
    """LLM 提供者错误分类枚举。"""
    RETRYABLE_RATE_LIMIT = "retryable_rate_limit"    # 可重试：速率限制
    RETRYABLE_TRANSIENT = "retryable_transient"      # 可重试：瞬态错误
    COOLDOWN = "cooldown"                            # 需要冷却
    FATAL = "fatal"                                  # 致命错误，不可重试


@dataclass(frozen=True)
class ProviderErrorClassification:
    """提供者错误分类结果。"""
    kind: ProviderErrorKind
    retryable: bool
    cooldown: bool = False
    reason: str = ""


class ProviderFatalError(RuntimeError):
    """LLM 提供者致命错误异常。"""

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        member_id: Optional[str] = None,
        classification: Optional[ProviderErrorClassification] = None,
    ) -> None:
        self.status_code = status_code
        self.member_id = member_id
        self.classification = classification or classify_provider_error(status_code, message)
        super().__init__(f"Fatal LLM provider error {status_code}: {message}")


@dataclass(frozen=True)
class LlmTaskLease:
    """LLM 任务租约，绑定任务到特定的池成员。"""
    task_id: str
    member_id: str
    base_url: str
    masked_api_key: str
    lease_id: str


@dataclass
class _SchedulerMember:
    """调度器内部成员表示。"""
    member_id: str
    base_url: str
    api_key: str
    account_id: str = ""
    quota_scope: str = "shared"
    concurrency: int = _DEFAULT_MEMBER_CONCURRENCY
    reserve: bool = False

    @property
    def quota_key(self) -> str:
        """基于配额范围计算配额键。"""
        if self.quota_scope in {"independent", "account", "per_account"} and self.account_id:
            return f"account:{self.account_id}"
        if self.quota_scope in {"independent", "member"}:
            return f"member:{self.member_id}"
        return f"base:{self.base_url}"


def _mask_api_key(api_key: str) -> str:
    """遮蔽 API 密钥，仅显示前4位和后4位。"""
    normalized = str(api_key or "").strip()
    if len(normalized) <= 8:
        return "***"
    return f"{normalized[:4]}...{normalized[-4:]}"


def classify_provider_error(status_code: int, body: str = "") -> ProviderErrorClassification:
    """根据 HTTP 状态码和响应体分类提供者错误。"""
    text = str(body or "").lower()
    fatal_markers = (
        "invalid api key",
        "incorrect api key",
        "authentication",
        "unauthorized",
        "forbidden",
        "permission denied",
        "quota exhausted",
        "insufficient quota",
        "quota_exceeded",
        "billing hard limit",
        "model not available",
        "model unavailable",
        "unsupported model",
        "model_not_found",
    )
    if status_code in {401, 403}:
        return ProviderErrorClassification(ProviderErrorKind.FATAL, retryable=False, reason="auth")
    if any(marker in text for marker in fatal_markers):
        return ProviderErrorClassification(ProviderErrorKind.FATAL, retryable=False, reason="provider_denial")
    if status_code == 429:
        return ProviderErrorClassification(
            ProviderErrorKind.RETRYABLE_RATE_LIMIT,
            retryable=True,
            cooldown=True,
            reason="rate_limit",
        )
    if status_code == 503:
        return ProviderErrorClassification(
            ProviderErrorKind.RETRYABLE_TRANSIENT,
            retryable=True,
            cooldown=True,
            reason="transient_503",
        )
    if 500 <= status_code <= 599:
        return ProviderErrorClassification(
            ProviderErrorKind.RETRYABLE_TRANSIENT,
            retryable=True,
            cooldown=True,
            reason="transient_5xx",
        )
    if status_code >= 400:
        return ProviderErrorClassification(ProviderErrorKind.FATAL, retryable=False, reason="client_error")
    return ProviderErrorClassification(ProviderErrorKind.RETRYABLE_TRANSIENT, retryable=False, reason="not_error")


class LlmMemberScheduler:
    """LLM 成员调度器，管理任务租约和成员并发控制。"""

    def __init__(
        self,
        *,
        members: Iterable[Mapping[str, Any]],
        reserve_count: int = 0,
        default_member_concurrency: int = _DEFAULT_MEMBER_CONCURRENCY,
        pool_concurrency: Optional[int] = None,
    ) -> None:
        """初始化调度器。

        Args:
            members: 成员配置列表
            reserve_count: 保留成员数量
            default_member_concurrency: 默认成员并发数
            pool_concurrency: 池级别并发限制
        """
        self.reserve_count = max(int(reserve_count or 0), 0)
        self.default_member_concurrency = max(int(default_member_concurrency or _DEFAULT_MEMBER_CONCURRENCY), 1)
        self._members: dict[str, _SchedulerMember] = {}
        self._member_order: list[str] = []
        self._member_semaphores: dict[str, asyncio.Semaphore] = {}
        self._task_leases: dict[str, LlmTaskLease] = {}
        self._lease_sequence = 0
        self._condition = asyncio.Condition()
        self._pool_semaphore = asyncio.Semaphore(max(int(pool_concurrency), 1)) if pool_concurrency else None
        self.update_members(members)

    def update_members(self, members: Iterable[Mapping[str, Any]]) -> None:
        """更新或刷新调度器的成员列表。"""
        normalized_members: dict[str, _SchedulerMember] = {}
        member_order: list[str] = []
        for index, member in enumerate(members):
            member_id = str(member.get("member_id") or f"member-{index}").strip()
            base_url = str(member.get("base_url") or "").strip()
            api_key = str(member.get("api_key") or "").strip()
            if not member_id or not base_url or not api_key:
                continue
            concurrency = int(
                member.get("concurrency")
                or member.get("max_concurrent_requests")
                or member.get("member_concurrency")
                or self.default_member_concurrency
            )
            normalized_members[member_id] = _SchedulerMember(
                member_id=member_id,
                base_url=base_url,
                api_key=api_key,
                account_id=str(member.get("account_id") or "").strip(),
                quota_scope=str(member.get("quota_scope") or "shared").strip().lower(),
                concurrency=max(concurrency, 1),
                reserve=bool(member.get("reserve") or False),
            )
            member_order.append(member_id)

        self._members = normalized_members
        self._member_order = member_order
        for member_id, member in normalized_members.items():
            existing = self._member_semaphores.get(member_id)
            if existing is None or getattr(existing, "_value", 0) > member.concurrency:
                self._member_semaphores[member_id] = asyncio.Semaphore(member.concurrency)
        for member_id in list(self._member_semaphores):
            if member_id not in normalized_members:
                self._member_semaphores.pop(member_id, None)

    def _healthy_member_ids(self) -> list[str]:
        """返回当前健康成员的 ID 列表。"""
        return list(self._member_order)

    def community_task_capacity(self) -> int:
        """计算社区任务容量（独立配额单元数减去保留数）。"""
        healthy = [self._members[member_id] for member_id in self._healthy_member_ids()]
        if not healthy:
            return 0
        independent_units = {member.quota_key for member in healthy}
        return max(1, len(independent_units) - self.reserve_count)

    def reserve_member_ids(self) -> set[str]:
        """计算应在负载下保留的成员 ID 集合。"""
        capacity = self.community_task_capacity()
        leased = {lease.member_id for lease in self._task_leases.values()}
        healthy = set(self._healthy_member_ids())
        reserve = healthy - leased
        if len(reserve) <= self.reserve_count:
            return reserve
        ordered_reserve = [member_id for member_id in self._member_order if member_id in reserve]
        return set(ordered_reserve[-self.reserve_count:])

    async def acquire_task_lease(self, task_id: str) -> LlmTaskLease:
        """为任务获取池成员租约，必要时等待。"""
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("task_id is required for LLM task lease")
        async with self._condition:
            existing = self._task_leases.get(normalized_task_id)
            if existing is not None:
                return existing
            while True:
                capacity = self.community_task_capacity()
                if capacity <= 0:
                    await self._condition.wait()
                    continue
                if len(self._task_leases) < capacity:
                    member = self._choose_unleased_member()
                    if member is not None:
                        self._lease_sequence += 1
                        lease = LlmTaskLease(
                            task_id=normalized_task_id,
                            member_id=member.member_id,
                            base_url=member.base_url,
                            masked_api_key=_mask_api_key(member.api_key),
                            lease_id=f"{normalized_task_id}:{member.member_id}:{self._lease_sequence}",
                        )
                        self._task_leases[normalized_task_id] = lease
                        return lease
                await self._condition.wait()

    async def release_task_lease(self, task_id: str) -> None:
        """释放任务租约并通知等待者。"""
        async with self._condition:
            self._task_leases.pop(str(task_id or "").strip(), None)
            self._condition.notify_all()

    def _choose_unleased_member(self) -> Optional[_SchedulerMember]:
        """按顺序选择尚未租出的成员。"""
        leased = {lease.member_id for lease in self._task_leases.values()}
        for member_id in self._member_order:
            if member_id not in leased:
                return self._members[member_id]
        return None

    @asynccontextmanager
    async def request_permission(self, member_id: str, *, task_id: Optional[str] = None):
        """异步上下文管理器：获取成员级别的请求许可（通过信号量）。"""
        member = self._members.get(member_id)
        if member is None:
            raise KeyError(f"Unknown LLM member {member_id}")
        member_semaphore = self._member_semaphores.setdefault(member_id, asyncio.Semaphore(member.concurrency))
        if self._pool_semaphore is not None:
            async with self._pool_semaphore:
                async with member_semaphore:
                    yield
        else:
            async with member_semaphore:
                yield


class _SchedulerRegistry:
    """调度器注册表，线程安全地管理命名调度器实例。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._schedulers: dict[str, LlmMemberScheduler] = {}

    def ensure_scheduler(
        self,
        pool_id: str,
        members: Iterable[Mapping[str, Any]],
        *,
        reserve_count: int = 0,
        default_member_concurrency: int = _DEFAULT_MEMBER_CONCURRENCY,
        pool_concurrency: Optional[int] = None,
    ) -> LlmMemberScheduler:
        """获取或创建指定池 ID 的调度器。"""
        with self._lock:
            scheduler = self._schedulers.get(pool_id)
            if scheduler is None:
                scheduler = LlmMemberScheduler(
                    members=members,
                    reserve_count=reserve_count,
                    default_member_concurrency=default_member_concurrency,
                    pool_concurrency=pool_concurrency,
                )
                self._schedulers[pool_id] = scheduler
            else:
                scheduler.reserve_count = max(int(reserve_count or 0), 0)
                scheduler.default_member_concurrency = max(int(default_member_concurrency or 1), 1)
                scheduler.update_members(members)
            return scheduler


def build_pool_members_from_groups(groups: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """从组配置列表中构建展平的池成员列表。"""
    members: list[dict[str, Any]] = []
    for group_index, group in enumerate(groups):
        base_url = str(group.get("base_url") or "").strip()
        group_id = str(group.get("group_id") or f"group-{group_index}")
        group_concurrency = group.get("concurrency") or group.get("member_concurrency")
        group_quota_scope = group.get("quota_scope")
        group_account_id = group.get("account_id")
        explicit_members = group.get("members")
        if isinstance(explicit_members, list):
            for member_index, member in enumerate(explicit_members):
                if not isinstance(member, Mapping):
                    continue
                member_base_url = str(member.get("base_url") or base_url).strip()
                api_key = str(member.get("api_key") or "").strip()
                if not member_base_url or not api_key:
                    continue
                members.append(
                    {
                        "member_id": str(member.get("member_id") or f"{group_id}-member-{member_index}"),
                        "base_url": member_base_url,
                        "api_key": api_key,
                        "account_id": str(member.get("account_id") or group_account_id or ""),
                        "quota_scope": str(member.get("quota_scope") or group_quota_scope or "shared"),
                        "concurrency": int(member.get("concurrency") or group_concurrency or _DEFAULT_MEMBER_CONCURRENCY),
                        "reserve": bool(member.get("reserve") or False),
                    }
                )
            continue
        if not base_url:
            continue
        api_keys = group.get("api_keys") or []
        for key_index, api_key in enumerate(api_keys):
            normalized_key = str(api_key or "").strip()
            if not normalized_key:
                continue
            members.append(
                {
                    "member_id": f"{group_id}-member-{key_index}",
                    "base_url": base_url,
                    "api_key": normalized_key,
                    "account_id": str(group_account_id or ""),
                    "quota_scope": str(group_quota_scope or "shared"),
                    "concurrency": int(group_concurrency or _DEFAULT_MEMBER_CONCURRENCY),
                }
            )
    return members


def compute_pool_routing_key(members: Iterable[Mapping[str, Any]]) -> str:
    """根据成员配置计算确定性的池路由键。"""
    normalized = []
    for member in members:
        normalized.append(
            (
                str(member.get("member_id") or "").strip(),
                str(member.get("base_url") or "").strip(),
                str(member.get("api_key") or "").strip(),
                str(member.get("account_id") or "").strip(),
                str(member.get("quota_scope") or "").strip(),
            )
        )
    digest = hashlib.md5(repr(sorted(normalized)).encode("utf-8")).hexdigest()
    return f"system-pool:{digest}"


@dataclass
class _MemberState:
    """池注册表中成员的运行时状态。"""
    member_id: str
    base_url: str
    api_key: str
    reserve: bool = False
    cooldown_until: float = 0.0
    consecutive_429: int = 0
    consecutive_503: int = 0
    last_used_at: float = 0.0
    fatal: bool = False


class _PoolRegistry:
    """池注册表，管理池成员的运行时状态（选择、故障跟踪、冷却）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pools: dict[str, dict[str, _MemberState]] = {}

    def ensure_pool(self, pool_id: str, members: Iterable[Mapping[str, Any]]) -> dict[str, _MemberState]:
        """确保指定池 ID 的成员状态存在并同步。"""
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
                        reserve=bool(member.get("reserve") or False),
                        last_used_at=now,
                    )
                else:
                    existing.base_url = base_url
                    existing.api_key = api_key
                    existing.reserve = bool(member.get("reserve") or False)
            stale = [member_id for member_id in state if member_id not in seen]
            for member_id in stale:
                state.pop(member_id, None)
            return dict(state)

    def choose_member(
        self,
        pool_id: str,
        *,
        exclude: Optional[set[str]] = None,
        preferred_base_urls: Optional[Iterable[str]] = None,
    ) -> Optional[_MemberState]:
        """从池中选择最佳成员，支持排除和首选 base_url 偏好。"""
        now = time.monotonic()
        with self._lock:
            state = self._pools.get(pool_id, {})
            healthy = [
                member
                for member in state.values()
                if member.member_id not in (exclude or set()) and member.cooldown_until <= now and not member.fatal
            ]
            if not healthy:
                return None
            primary = [member for member in healthy if not member.reserve]
            candidates = primary or healthy
            normalized_preferences = [
                str(base_url or "").strip()
                for base_url in (preferred_base_urls or [])
                if str(base_url or "").strip()
            ]
            if normalized_preferences:
                preferred_rank = {base_url: index for index, base_url in enumerate(normalized_preferences)}
                preferred_members = [
                    member
                    for member in candidates
                    if member.base_url in preferred_rank
                ]
                if preferred_members:
                    return min(
                        preferred_members,
                        key=lambda item: (preferred_rank[item.base_url], item.last_used_at, item.member_id),
                    )
            return min(candidates, key=lambda item: (item.last_used_at, item.member_id))

    def mark_attempt(self, pool_id: str, member_id: str) -> None:
        """标记成员的使用时间。"""
        with self._lock:
            member = self._pools.get(pool_id, {}).get(member_id)
            if member is not None:
                member.last_used_at = time.monotonic()

    def record_success(self, pool_id: str, member_id: str) -> None:
        """记录成功的请求，重置故障计数器。"""
        with self._lock:
            member = self._pools.get(pool_id, {}).get(member_id)
            if member is None:
                return
            member.consecutive_429 = 0
            member.consecutive_503 = 0
            member.cooldown_until = 0.0
            member.fatal = False
            member.last_used_at = time.monotonic()

    def record_fatal(self, pool_id: str, member_id: str) -> None:
        """将成员标记为致命故障状态。"""
        with self._lock:
            member = self._pools.get(pool_id, {}).get(member_id)
            if member is None:
                return
            member.fatal = True
            member.last_used_at = time.monotonic()

    def record_status(self, pool_id: str, member_id: str, status: int, *, retry_after_seconds: int = 0) -> tuple[int, bool]:
        """记录 HTTP 状态码结果，更新故障计数器和冷却状态。"""
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
                    member.cooldown_until = max(member.cooldown_until, now + _STATUS_503_COOLDOWN_SECONDS)
                return member.consecutive_503, member.consecutive_503 >= _STATUS_503_FAILOVER_THRESHOLD
            member.consecutive_429 = 0
            member.consecutive_503 = 0
            member.cooldown_until = 0.0
            return 0, False


# 全局单例注册表
_POOL_REGISTRY = _PoolRegistry()
_SCHEDULER_REGISTRY = _SchedulerRegistry()


def _parse_retry_after_seconds(headers: Optional[Mapping[str, str]]) -> int:
    """从响应头中解析 Retry-After 秒数。"""
    raw = str((headers or {}).get("Retry-After") or "").strip()
    if raw.isdigit():
        return max(int(raw), 0)
    return 1


def _log_pool_request_success(
    *,
    pool_id: str,
    member_id: str,
    base_url: str,
    status_code: int,
) -> None:
    """记录池请求成功的结构化日志。"""
    logger.info(
        "LLM pool request served by member %s",
        member_id,
        extra={
            "llm_pool_event": "request_success",
            "llm_pool_id": pool_id,
            "llm_pool_member_id": member_id,
            "llm_pool_base_url": base_url,
            "llm_pool_status_code": status_code,
        },
    )


def _log_pool_failover(
    *,
    pool_id: str,
    current: _MemberState,
    alternative: _MemberState,
    status_code: int,
    reason: str,
) -> None:
    """记录池故障转移事件的结构化日志。"""
    logger.warning(
        "LLM pool failover from member %s to %s after HTTP %s",
        current.member_id,
        alternative.member_id,
        status_code,
        extra={
            "llm_pool_event": "failover",
            "llm_pool_id": pool_id,
            "llm_pool_member_id": current.member_id,
            "llm_pool_base_url": current.base_url,
            "llm_pool_next_member_id": alternative.member_id,
            "llm_pool_next_base_url": alternative.base_url,
            "llm_pool_status_code": status_code,
            "llm_pool_failover_reason": reason,
        },
    )


def _log_pool_exhausted_retry(
    *,
    pool_id: str,
    member_id: str,
    base_url: str,
    status_code: int,
    wait_seconds: int,
) -> None:
    """记录池资源耗尽后重试的结构化日志。"""
    logger.warning(
        "LLM pool all members unavailable after HTTP %s; retrying member %s in %ss",
        status_code,
        member_id,
        wait_seconds,
        extra={
            "llm_pool_event": "all_members_unavailable_retry",
            "llm_pool_id": pool_id,
            "llm_pool_member_id": member_id,
            "llm_pool_base_url": base_url,
            "llm_pool_status_code": status_code,
            "llm_pool_retry_wait_seconds": wait_seconds,
        },
    )


async def _perform_member_request(
    *,
    session: aiohttp.ClientSession,
    base_url: str,
    api_key: str,
    member_id: str,
    payload: Dict[str, Any],
    timeout: aiohttp.ClientTimeout,
    scheduler_lease_id: Optional[str] = None,
) -> tuple[int, Mapping[str, str], Optional[Dict[str, Any]], str]:
    """对指定的池成员执行实际的 HTTP POST 请求。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-LLM-Pool-Member": member_id,
    }
    if scheduler_lease_id:
        headers["X-LLM-Scheduler-Lease"] = scheduler_lease_id
    async with session.post(
        base_url,
        json=payload,
        headers=headers,
        timeout=timeout,
    ) as response:
        if response.status >= 400:
            response_text = ""
            text_getter = getattr(response, "text", None)
            if callable(text_getter):
                try:
                    response_text = await text_getter()
                except Exception:
                    response_text = ""
            return response.status, getattr(response, "headers", {}) or {}, None, response_text
        response.raise_for_status()
        return response.status, getattr(response, "headers", {}) or {}, await response.json(), ""


def _single_member_from_config(llm_config: Mapping[str, Any]) -> dict[str, Any]:
    """从配置中构建单成员表示（非池模式）。"""
    base_url = str(llm_config.get("base_url") or "").strip()
    api_key = str(llm_config.get("api_key") or "").strip()
    member_id_source = f"{base_url}:{api_key}"
    member_id = "single-" + hashlib.md5(member_id_source.encode("utf-8")).hexdigest()[:12]
    return {
        "member_id": member_id,
        "base_url": base_url,
        "api_key": api_key,
        "account_id": str(llm_config.get("account_id") or "").strip(),
        "quota_scope": str(llm_config.get("quota_scope") or "shared").strip(),
        "concurrency": int(llm_config.get("concurrency") or llm_config.get("member_concurrency") or 1),
    }


def _scheduler_defaults(llm_config: Mapping[str, Any]) -> tuple[int, int, Optional[int]]:
    """从配置中提取调度器默认参数。"""
    reserve_count = int(llm_config.get("reserve_count") or llm_config.get("llm_reserve_count") or 0)
    default_member_concurrency = int(
        llm_config.get("default_member_concurrency")
        or llm_config.get("member_concurrency")
        or _DEFAULT_MEMBER_CONCURRENCY
    )
    pool_concurrency_raw = llm_config.get("pool_concurrency") or llm_config.get("shared_pool_concurrency")
    pool_concurrency = int(pool_concurrency_raw) if pool_concurrency_raw else None
    return reserve_count, max(default_member_concurrency, 1), pool_concurrency


async def post_chat_completion_with_pool(
    *,
    session: aiohttp.ClientSession,
    llm_config: Mapping[str, Any],
    payload: Dict[str, Any],
    timeout: aiohttp.ClientTimeout,
    on_retry_message: Optional[Callable[[str], None]] = None,
    preferred_base_urls_getter: Optional[Callable[[], Iterable[str]]] = None,
    on_retryable_status: Optional[Callable[[str, str, int], None]] = None,
) -> Dict[str, Any]:
    """通过 LLM 池（或单成员模式）发送聊天补全请求，支持自动故障转移和重试。

    这是与 LLM 提供者交互的主要入口点。支持两种模式：
    1. 单成员模式（pool_mode != "system_managed" 或无池成员）
    2. 系统托管池模式（pool_mode == "system_managed" 且有池成员）

    在池模式下，自动处理：
    - 基于 HTTP 状态码的故障转移（429、503、5xx）
    - 速率限制退避
    - 首选 base_url 亲和性路由

    Args:
        session: aiohttp 客户端会话
        llm_config: LLM 配置，包含池成员和参数
        payload: 要发送的聊天补全请求载荷
        timeout: HTTP 请求超时
        on_retry_message: 可选的进度消息回调
        preferred_base_urls_getter: 可选的返回首选 base_url 列表的回调
        on_retryable_status: 可选的收到可重试状态码时的回调

    Returns:
        LLM API 响应 JSON 字典
    """
    members = list(llm_config.get("pool_members") or [])
    if llm_config.get("pool_mode") != "system_managed" or not members:
        # 单成员模式
        single_member = _single_member_from_config(llm_config)
        pool_id = str(llm_config.get("pool_routing_key") or compute_pool_routing_key([single_member]))
        reserve_count, default_member_concurrency, pool_concurrency = _scheduler_defaults(llm_config)
        scheduler = _SCHEDULER_REGISTRY.ensure_scheduler(
            pool_id,
            [single_member],
            reserve_count=reserve_count,
            default_member_concurrency=default_member_concurrency,
            pool_concurrency=pool_concurrency,
        )
        lease_id = f"{pool_id}:{single_member['member_id']}"
        async with scheduler.request_permission(single_member["member_id"]):
            status_code, headers, result, response_body = await _perform_member_request(
                session=session,
                base_url=single_member["base_url"],
                api_key=single_member["api_key"],
                member_id=single_member["member_id"],
                payload=payload,
                timeout=timeout,
                scheduler_lease_id=lease_id,
            )
        if status_code >= 400:
            classification = classify_provider_error(status_code, response_body)
            if classification.kind is ProviderErrorKind.FATAL:
                raise ProviderFatalError(
                    status_code=status_code,
                    message=response_body or f"HTTP {status_code}",
                    member_id=single_member["member_id"],
                    classification=classification,
                )
            response = aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=status_code,
                message=response_body or f"HTTP {status_code}",
                headers=headers,
            )
            raise response
        _log_pool_request_success(
            pool_id=pool_id,
            member_id=single_member["member_id"],
            base_url=single_member["base_url"],
            status_code=status_code,
        )
        return result or {}

    # 系统托管池模式
    pool_id = str(llm_config.get("pool_routing_key") or compute_pool_routing_key(members))
    reserve_count, default_member_concurrency, pool_concurrency = _scheduler_defaults(llm_config)
    scheduler = _SCHEDULER_REGISTRY.ensure_scheduler(
        pool_id,
        members,
        reserve_count=reserve_count,
        default_member_concurrency=default_member_concurrency,
        pool_concurrency=pool_concurrency,
    )
    _POOL_REGISTRY.ensure_pool(pool_id, members)
    current = _POOL_REGISTRY.choose_member(
        pool_id,
        preferred_base_urls=(preferred_base_urls_getter() if preferred_base_urls_getter is not None else ()),
    ) or next(iter(_POOL_REGISTRY.ensure_pool(pool_id, members).values()))

    while True:
        _POOL_REGISTRY.mark_attempt(pool_id, current.member_id)
        async with scheduler.request_permission(current.member_id):
            status_code, headers, result, response_body = await _perform_member_request(
                session=session,
                base_url=current.base_url,
                api_key=current.api_key,
                member_id=current.member_id,
                payload=payload,
                timeout=timeout,
                scheduler_lease_id=f"{pool_id}:{current.member_id}",
            )

        classification = classify_provider_error(status_code, response_body) if status_code >= 400 else None
        if classification is not None and classification.kind is ProviderErrorKind.FATAL:
            _POOL_REGISTRY.record_fatal(pool_id, current.member_id)
            raise ProviderFatalError(
                status_code=status_code,
                message=response_body or f"HTTP {status_code}",
                member_id=current.member_id,
                classification=classification,
            )

        if classification is not None and classification.kind in {
            ProviderErrorKind.RETRYABLE_RATE_LIMIT,
            ProviderErrorKind.RETRYABLE_TRANSIENT,
        }:
            if on_retryable_status is not None:
                on_retryable_status(current.member_id, current.base_url, status_code)
            retry_after_seconds = _parse_retry_after_seconds(headers)
            streak, may_failover = _POOL_REGISTRY.record_status(
                pool_id,
                current.member_id,
                status_code,
                retry_after_seconds=retry_after_seconds,
            )
            preferred_base_urls = preferred_base_urls_getter() if preferred_base_urls_getter is not None else ()
            alternative = _POOL_REGISTRY.choose_member(
                pool_id,
                exclude={current.member_id},
                preferred_base_urls=preferred_base_urls,
            )
            preferred_alternative_available = (
                status_code == 503
                and alternative is not None
                and any(
                    str(base_url or "").strip() == alternative.base_url and current.base_url != alternative.base_url
                    for base_url in (preferred_base_urls or ())
                )
            )
            if may_failover and alternative is not None:
                _log_pool_failover(
                    pool_id=pool_id,
                    current=current,
                    alternative=alternative,
                    status_code=status_code,
                    reason="status_threshold",
                )
                if on_retry_message is not None:
                    on_retry_message(
                        f"LLM pool member {current.member_id} returned {status_code}; fail over to {alternative.member_id}"
                    )
                current = alternative
                continue
            if preferred_alternative_available:
                _log_pool_failover(
                    pool_id=pool_id,
                    current=current,
                    alternative=alternative,
                    status_code=status_code,
                    reason="preferred_base",
                )
                if on_retry_message is not None:
                    on_retry_message(
                        f"LLM pool member {current.member_id} returned {status_code}; prefer base fail over to {alternative.member_id}"
                    )
                current = alternative
                continue
            if alternative is not None and status_code == 429:
                _log_pool_failover(
                    pool_id=pool_id,
                    current=current,
                    alternative=alternative,
                    status_code=status_code,
                    reason="rate_limit",
                )
                if on_retry_message is not None:
                    on_retry_message(
                        f"LLM pool member {current.member_id} hit 429; fail over to {alternative.member_id}"
                    )
                current = alternative
                continue

            wait_seconds = retry_after_seconds if status_code == 429 else _ALL_MEMBERS_UNAVAILABLE_503_RETRY_SECONDS
            _log_pool_exhausted_retry(
                pool_id=pool_id,
                member_id=current.member_id,
                base_url=current.base_url,
                status_code=status_code,
                wait_seconds=wait_seconds,
            )
            if on_retry_message is not None:
                on_retry_message(
                    f"LLM pool all members unavailable on {status_code}; retry current member {current.member_id} in {wait_seconds}s"
                )
            await asyncio.sleep(wait_seconds)
            continue

        _POOL_REGISTRY.record_success(pool_id, current.member_id)
        _log_pool_request_success(
            pool_id=pool_id,
            member_id=current.member_id,
            base_url=current.base_url,
            status_code=status_code,
        )
        return result or {}
