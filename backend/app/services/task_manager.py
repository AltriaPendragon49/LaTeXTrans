"""任务管理服务

基于内存的线程安全任务状态追踪。管理任务状态、进度更新和状态查询。

支持双层存储：
- 内存缓存用于所有任务（访客 + 已认证用户）
- 本地持久化存储仅用于已认证用户
"""

import uuid
import asyncio
import threading
import queue
import time
import logging
import shutil
import json
import re
import os
import platform
import signal
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union, List
from backend.app.core.config import TaskStatus, CompilationStage, get_settings
from backend.app.repositories import AuthRepository, TranslationTaskRepository
from backend.app.core.timezone_utils import get_cst_now, get_cst_now_iso
from backend.app.services.runtime_pressure import backfill_start_blocked_by_frontend_pressure
from backend.app.services.task_detail import (
    infer_task_detail,
    normalize_detail_params,
    normalize_stage,
)

logger = logging.getLogger(__name__)

_runtime_shutting_down = False
_runtime_state_lock = threading.Lock()
_TERMINAL_TASK_STATUSES = frozenset(
    {
        TaskStatus.COMPLETED.value,
        TaskStatus.COMPLETED_WITH_WARNINGS.value,
        TaskStatus.FAILED.value,
        TaskStatus.FAILED_COMPILATION.value,
        TaskStatus.STRUCTURE_INVALID.value,
    }
)


def get_translation_task_repository() -> TranslationTaskRepository:
    """获取翻译任务仓库实例"""
    return TranslationTaskRepository()


def get_auth_repository() -> AuthRepository:
    """获取认证仓库实例"""
    return AuthRepository()


def _delete_local_cache_path(path: Path) -> None:
    """递归删除本地缓存路径（文件或目录）"""
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
        return
    path.unlink()


def _is_within_cleanup_roots(candidate: Path, allowed_roots: List[Path]) -> bool:
    """安全护栏：仅允许在已知运行时根目录下执行缓存清理"""
    try:
        resolved_candidate = candidate.resolve(strict=False)
    except Exception:
        return False

    for root in allowed_roots:
        try:
            resolved_root = root.resolve(strict=False)
        except Exception:
            continue
        if resolved_candidate == resolved_root or resolved_candidate.is_relative_to(resolved_root):
            return True
    return False


def clear_cached_runtime_artifacts(task_id: str, retained_paths: List[Path]) -> List[str]:
    """清理任务的运行时缓存产物（在持久化完成后安全删除本地缓存）"""
    settings = get_settings()
    allowed_roots = []
    for attr_name in ("outputs_dir", "uploads_dir", "storage_temp_dir"):
        raw_root = getattr(settings, attr_name, None)
        if raw_root is None:
            continue
        allowed_roots.append(Path(raw_root))
    cleared_paths: List[str] = []
    for candidate in retained_paths:
        if not isinstance(candidate, Path):
            candidate = Path(candidate)
        if not candidate.exists():
            continue
        if not _is_within_cleanup_roots(candidate, allowed_roots):
            logger.warning(
                "[TaskManager] Skipped unsafe cache cleanup outside allowed roots for task %s: %s",
                task_id,
                candidate,
            )
            continue
        try:
            _delete_local_cache_path(candidate)
        except Exception as exc:
            logger.warning(
                "[TaskManager] Failed to clear cached artifact for task %s (%s): %s",
                task_id,
                candidate,
                exc,
            )
            continue
        cleared_paths.append(str(candidate))
    if cleared_paths:
        logger.info(
            "[TaskManager] Cleared local cache artifacts for task %s after durable persistence: %s",
            task_id,
            cleared_paths,
        )
    return cleared_paths


def _kill_process_tree(pid: int) -> None:
    """递归终止整个进程树（Windows 用 taskkill，Linux 用 SIGTERM）"""
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=10,
            )
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception as exc:
        logger.warning("[TaskManager] Failed to kill process tree for PID %s: %s", pid, exc)
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass



def set_runtime_shutting_down(value: bool) -> None:
    """设置全局运行时关闭标志，用于任务执行守卫"""
    global _runtime_shutting_down
    with _runtime_state_lock:
        _runtime_shutting_down = bool(value)


def is_runtime_shutting_down() -> bool:
    """判断后端运行时是否正在关闭"""
    with _runtime_state_lock:
        return _runtime_shutting_down


def _is_terminal_task_status(status: Optional[str]) -> bool:
    """判断是否为终态状态（已完成/失败等）"""
    return str(status or "").strip() in _TERMINAL_TASK_STATUSES


def _serialize_task_timestamp(value: Any) -> Optional[str]:
    """序列化任务时间戳为 ISO 格式字符串"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _should_refresh_cached_task_from_storage(task: Dict[str, Any]) -> bool:
    """判断是否需要从持久化存储中刷新缓存的任务（仅 Web 节点对非终态认证用户任务）"""
    runtime_role = str(getattr(get_settings(), "backend_runtime_role", "all") or "all").strip().lower()
    if runtime_role != "web":
        return False
    if not str(task.get("user_id") or "").strip():
        return False
    return not _is_terminal_task_status(task.get("status"))


def _merge_runtime_fields_into_recovered_task(
    cached_task: Dict[str, Any],
    recovered_task: Dict[str, Any],
) -> Dict[str, Any]:
    """当 Web 节点从存储刷新任务时，保留内存中的运行时状态字段"""
    merged_task = dict(recovered_task)

    merged_task["attempt_id"] = max(
        int(recovered_task.get("attempt_id") or 0),
        int(cached_task.get("attempt_id") or 0),
    )

    for field_name in (
        "_last_flush_time",
        "compile_pid",
        "compile_engine",
        "compile_started_at",
    ):
        if field_name in cached_task:
            merged_task[field_name] = cached_task.get(field_name)

    if cached_task.get("failure_intercepted"):
        merged_task["failure_intercepted"] = True

    if cached_task.get("failed_output_path"):
        merged_task["failed_output_path"] = cached_task.get("failed_output_path")

    if cached_task.get("evidence_chain_broken"):
        merged_task["evidence_chain_broken"] = True

    if merged_task.get("advanced_config") is None and cached_task.get("advanced_config") is not None:
        merged_task["advanced_config"] = cached_task.get("advanced_config")

    if merged_task.get("latex_validation") is None and cached_task.get("latex_validation") is not None:
        merged_task["latex_validation"] = cached_task.get("latex_validation")

    return merged_task


# ── 运行时状态解耦：刷新节流配置 ───────────────────────────────────

#: 时间节流刷新（非语义性）的最小间隔秒数。
#: 语义性转换（status / stage 变化）总是立即刷新。
FLUSH_INTERVAL: float = 5.0

#: 构成语义性转换的字段集合，变更时必须立即触发持久化刷新。
_SEMANTIC_FLUSH_FIELDS = frozenset({"status", "stage"})


class PersistentStateFlusher:
    """非阻塞、线程安全的持久化状态刷新器，支持合并（coalescing）。

    Worker 调用 ``enqueue`` 提交 ``(task_id, db_updates)`` 对。
    后台守护线程排空待处理字典并写入本地持久化存储，
    确保调用线程永远不会被网络 I/O 阻塞。

    合并策略（每个 task_id 最后写入胜出）
    -------------------------------------------
    刷新器使用 ``_pending`` 字典而非 FIFO 队列：
    ``task_id -> 合并后的 db_updates``。
    如果同一 task_id 在 worker 唤醒前被多次入队，
    更新将逐字段合并（后入队的字段值胜出）。
    这消除了重试/错误风暴下的冗余持久化写入。

    线程安全约定
    -------------
    * ``_pending`` 和 ``_drain_events`` 由 ``_lock`` 保护。
    * ``_has_work`` (``threading.Event``) 用于唤醒——从任何线程设置都是安全的。
    * ``enqueue`` 永不阻塞。
    """

    def __init__(self, writer):
        """初始化刷新器

        参数:
            writer: 可调用对象 ``(task_id: str, updates: dict) -> None``，
                    执行实际的本地持久化写入。
                    从 TaskManager 注入，以便测试可以 monkeypatch ``TaskManager._persist_task_update``。
        """
        self._writer = writer
        self._lock = threading.Lock()
        self._pending: dict = {}          # task_id -> 合并后的 db_updates
        self._drain_events: list = []     # 等待空闲的 threading.Event 列表
        self._has_work = threading.Event()
        self._stop = False
        self._thread = threading.Thread(
            target=self._run,
            name="persistent-state-flusher",
            daemon=True,
        )
        self._thread.start()

    def enqueue(self, task_id: str, db_updates: dict) -> None:
        """将 ``db_updates`` 合并到 ``task_id`` 的待处理字典中并唤醒刷新线程。

        始终立即返回（非阻塞）。
        字段级最后写入胜出：后入队的字段覆盖先入队的同名字段。
        """
        with self._lock:
            if task_id in self._pending:
                self._pending[task_id].update(db_updates)
            else:
                self._pending[task_id] = dict(db_updates)
        self._has_work.set()

    def drain(self, timeout: float = 2.0) -> None:
        """阻塞直到所有当前待处理项已被刷新。

        仅供测试使用。
        """
        done = threading.Event()
        with self._lock:
            if not self._pending:
                return  # 无待处理项，已空闲
            self._drain_events.append(done)
        self._has_work.set()
        done.wait(timeout=timeout)

    def _run(self) -> None:
        """后台工作线程 -- 等待 _has_work 唤醒，排空待处理字典，执行写入"""
        while not self._stop:
            self._has_work.wait()
            self._has_work.clear()

            # 原子性地快照并清空
            with self._lock:
                snapshot = dict(self._pending)
                self._pending.clear()
                drain_events = list(self._drain_events)
                self._drain_events.clear()

            for task_id, updates in snapshot.items():
                try:
                    self._writer(task_id, updates)
                except Exception as exc:  # pragma: no cover
                    logger.error(
                        "[PersistentStateFlusher] Failed to flush task %s: %s",
                        task_id, exc, exc_info=True,
                    )

            # 通知所有 drain() 等待者
            for event in drain_events:
                event.set()

    def shutdown(self) -> None:  # pragma: no cover
        """请求优雅关闭"""
        self._stop = True
        self._has_work.set()


def _is_duplicate_task_insert_error(exc: Exception) -> bool:
    """判断异常是否为任务重复插入错误"""
    message = str(exc).lower()
    return (
        "duplicate key value violates unique constraint" in message
        and "translation_tasks_task_id_key" in message
    )


class TaskManager:
    """线程安全的内存任务管理器，用于追踪翻译任务"""

    def __init__(self):
        """初始化任务管理器，创建后台刷新器"""
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._cancelled_tasks: set = set()  # 追踪已取消的任务
        self._lock = threading.Lock()
        # 后台刷新器排空合并后的本地持久化更新。
        # 传入 lambda 以便测试可以在构造后 monkeypatch `self._persist_task_update`，
        # 刷新器会使用修补后的版本。
        self._flusher = PersistentStateFlusher(writer=lambda tid, upd: self._persist_task_update(tid, upd))

    def create_task(
        self,
        source_type: str = "upload",
        advanced_config: Optional[Dict[str, Any]] = None,
        arxiv_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source_language: str = "en",
        target_language: str = "zh",
        persist_to_db: bool = False
    ) -> str:
        """创建新任务并返回其 ID

        参数:
            source_type: "upload"、"arxiv" 或 "folder_upload"
            advanced_config: 可选的高级配置快照
            arxiv_id: arXiv 论文 ID（如适用）
            user_id: 已认证用户的用户 ID（启用持久化）
            source_language: 源语言代码
            target_language: 目标语言代码
            persist_to_db: 是否立即持久化到数据库（默认: False）

        返回:
            格式为 ``{prefix}-MMDD-HHmm-{full_uuid}`` 的任务 ID，
            其中 prefix 是清洗后的 arxiv_id，或本地上传时为 "upload"
        """
        now = get_cst_now()
        prefix = (
            re.sub(r"[^A-Za-z0-9.\-]", "_", str(arxiv_id))
            if arxiv_id
            else "upload"
        )
        task_id = f"{prefix}-{now.strftime('%m%d')}-{now.strftime('%H%M')}-{uuid.uuid4()}"

        # 1. 创建内存缓存（所有任务）
        with self._lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "progress": 0,
                "stage": CompilationStage.IDLE.value,
                "message": "Task created",
                "detail_code": "task_waiting",
                "detail_params": None,
                "error": None,
                "warnings": None,
                "failure_reason_code": None,
                "failure_class": None,
                "guard_phase": None,
                "replay_bundle_ref": None,
                "evidence_chain_broken": False,
                "source_available": False,
                "guardian_intercepted": False,
                "created_at": get_cst_now_iso(),
                "completed_at": None,
                "source_type": source_type,
                "source_path": None,
                "output_path": None,
                "advanced_config": advanced_config,
                "latex_validation": None,
                "arxiv_id": arxiv_id,
                "user_id": user_id,
                "source_language": source_language,
                "target_language": target_language,
                "config_hash": None,
                "failure_intercepted": False,
                "failed_output_path": None,
                "compile_pid": None,
                "compile_engine": None,
                "compile_started_at": None,
                # 运行时刷新追踪；绝不暴露给 API 或持久化存储。
                "_last_flush_time": time.monotonic(),
            }

        # 2. 注册访客任务以进行 TTL 追踪
        if not user_id:
            guest_tracker.register(task_id)

        # 3. 持久化到本地存储（仅在 persist_to_db=True 且用户已认证时）
        if persist_to_db and user_id:
            self._persist_task_create(task_id, user_id, source_type, arxiv_id,
                                      source_language, target_language, advanced_config)

        return task_id

    def begin_task_attempt(self, task_id: str) -> int:
        """开始新的执行尝试并清除过期的终态标记"""
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(task_id)
            task = self._tasks[task_id]
            next_attempt_id = int(task.get("attempt_id") or 0) + 1
            task["attempt_id"] = next_attempt_id
            task["completed_at"] = None
            task["failure_intercepted"] = False
            task["failed_output_path"] = None
            return next_attempt_id

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        detail_code: Optional[str] = None,
        detail_params: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        warnings: Optional[str] = None,
        failure_reason_code: Optional[str] = None,
        failure_class: Optional[str] = None,
        guard_phase: Optional[str] = None,
        replay_bundle_ref: Optional[str] = None,
        evidence_chain_broken: Optional[bool] = None,
        source_available: Optional[bool] = None,
        source_path: Optional[str] = None,
        output_path: Optional[str] = None,
        advanced_config: Optional[Dict[str, Any]] = None,
        latex_validation: Optional[Dict[str, Any]] = None,
        arxiv_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        config_hash: Optional[str] = None,
        compile_pid: Optional[int] = None,
        compile_engine: Optional[str] = None,
        compile_started_at: Optional[str] = None,
        expected_attempt_id: Optional[int] = None,
    ) -> bool:
        """更新任务字段

        参数:
            task_id: 任务 ID
            status: 新状态（可选）
            progress: 进度百分比 0-100（可选）
            stage: 当前阶段（可选）
            message: 状态消息（可选）
            error: 错误消息（可选）
            warnings: 警告消息（可选）
            source_available: 源文件是否可用（可选）
            source_path: 源文件路径（可选）
            output_path: 输出文件路径（可选）
            advanced_config: 高级配置快照（可选）
            latex_validation: LaTeX 验证结果（可选）
            arxiv_id: arXiv 论文 ID（可选）
            user_id: 用户 ID，提供后同步到本地持久化存储（可选）

        返回:
            任务存在且已更新返回 True，否则返回 False
        """
        # 收集用于本地持久化同步的更新
        db_updates = {}
        task_snapshot: Optional[Dict[str, Any]] = None

        with self._lock:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]

            # 捕获变更前的旧语义字段
            _old_status = task.get("status")
            _old_stage = task.get("stage")
            current_attempt_id = int(task.get("attempt_id") or 0)

            if (
                expected_attempt_id is not None
                and int(expected_attempt_id) != current_attempt_id
            ):
                logger.info(
                    "[TaskManager] Ignoring stale update for task %s: expected attempt %s, current attempt %s",
                    task_id,
                    expected_attempt_id,
                    current_attempt_id,
                )
                return False

            if (
                status is not None
                and expected_attempt_id is not None
                and _is_terminal_task_status(_old_status)
                and not _is_terminal_task_status(status)
            ):
                logger.info(
                    "[TaskManager] Ignoring terminal-regressing update for task %s in attempt %s: %s -> %s",
                    task_id,
                    current_attempt_id,
                    _old_status,
                    status,
                )
                return False

            if status is not None:
                task["status"] = status
                db_updates["status"] = status
                # 自动设置完成时间戳
                if _is_terminal_task_status(status):
                    task["completed_at"] = get_cst_now_iso()
                    db_updates["completed_at"] = task["completed_at"]
                elif task.get("completed_at") is not None:
                    task["completed_at"] = None
                    db_updates["completed_at"] = None

            if progress is not None:
                task["progress"] = max(0, min(100, progress))
                db_updates["progress"] = task["progress"]

            if stage is not None:
                normalized_stage = normalize_stage(stage)
                task["stage"] = normalized_stage
                db_updates["stage"] = normalized_stage

            if message is not None:
                task["message"] = message
                db_updates["message"] = message

            if error is not None:
                task["error"] = error
                db_updates["error"] = error

            if warnings is not None:
                task["warnings"] = warnings

            if failure_reason_code is not None:
                task["failure_reason_code"] = failure_reason_code

            if failure_class is not None:
                task["failure_class"] = failure_class

            if guard_phase is not None:
                task["guard_phase"] = guard_phase

            if replay_bundle_ref is not None:
                task["replay_bundle_ref"] = replay_bundle_ref

            if evidence_chain_broken is not None:
                task["evidence_chain_broken"] = bool(evidence_chain_broken)

            if source_available is not None:
                task["source_available"] = source_available

            if source_path is not None:
                task["source_path"] = source_path
                db_updates["source_path"] = source_path

            if output_path is not None:
                task["output_path"] = output_path
                db_updates["output_path"] = output_path

            if advanced_config is not None:
                task["advanced_config"] = advanced_config
                # 提取相关字段用于数据库
                if isinstance(advanced_config, dict):
                    db_updates["translation_mode"] = advanced_config.get("translation_mode", "full")
                    db_updates["compile_strategy"] = advanced_config.get("compile_strategy", "auto")
                    db_updates["translation_model"] = advanced_config.get("translation_model")
                    db_updates["generate_glossary"] = advanced_config.get("generate_terminology_table", True)
                    db_updates["use_author_api"] = advanced_config.get("use_author_api", True)
                    db_updates["custom_base_url"] = advanced_config.get("custom_base_url")
                    db_updates["custom_api_key_encrypted"] = advanced_config.get("custom_api_key_encrypted")
                    # 将格式化配置持久化为 JSONB
                    fmt = advanced_config.get("formatting")
                    if fmt is not None:
                        # 如需，将 Pydantic 模型转换为字典
                        if hasattr(fmt, "model_dump"):
                            fmt = fmt.model_dump(exclude_none=True)
                        elif hasattr(fmt, "dict"):
                            fmt = fmt.dict(exclude_none=True)
                        db_updates["formatting"] = fmt if fmt else None

            if latex_validation is not None:
                task["latex_validation"] = latex_validation

            if arxiv_id is not None:
                task["arxiv_id"] = arxiv_id
                db_updates["arxiv_id"] = arxiv_id

            if source_language is not None:
                task["source_language"] = source_language
                db_updates["source_language"] = source_language

            if target_language is not None:
                task["target_language"] = target_language
                db_updates["target_language"] = target_language

            if config_hash is not None:
                task["config_hash"] = config_hash
                db_updates["config_hash"] = config_hash

            # 运行时编译元数据（从不持久化）。
            if compile_pid is not None:
                task["compile_pid"] = compile_pid or None
            if compile_engine is not None:
                task["compile_engine"] = compile_engine
            if compile_started_at is not None:
                task["compile_started_at"] = compile_started_at

            should_refresh_detail = any(
                value is not None
                for value in (
                    status,
                    progress,
                    stage,
                    message,
                    warnings,
                    detail_code,
                    detail_params,
                )
            )
            if should_refresh_detail:
                resolved_detail_code = detail_code
                resolved_detail_params = normalize_detail_params(detail_params)

                if resolved_detail_code is None:
                    resolved_detail_code, resolved_detail_params = infer_task_detail(
                        status=task.get("status"),
                        stage=task.get("stage"),
                        message=task.get("message"),
                        progress=task.get("progress"),
                        warnings=task.get("warnings"),
                    )
                    resolved_detail_params = normalize_detail_params(resolved_detail_params)

                task["detail_code"] = resolved_detail_code
                task["detail_params"] = resolved_detail_params
                db_updates["detail_code"] = resolved_detail_code
                db_updates["detail_params"] = resolved_detail_params

            # 如果未提供 user_id，从任务中获取
            if user_id is None:
                user_id = task.get("user_id")
            task_snapshot = task.copy()

        # ── 节流的持久化刷新 ─────────────────────────────────────────
        # 仅已认证用户的任务有持久化记录需要更新。
        if user_id and db_updates:
            # 语义性转换指 VALUE 实际发生了变化，而非键仅存在于 db_updates 中。
            status_changed = ("status" in db_updates and db_updates["status"] != _old_status)
            stage_changed = ("stage" in db_updates and db_updates["stage"] != _old_stage)
            is_semantic = status_changed or stage_changed

            if is_semantic:
                # 语义性转换（status / stage 值发生变化）-> 立即刷新
                logger.debug(
                    "[FLUSH] task=%s SEMANTIC flush: status %s->%s, stage %s->%s",
                    task_id, _old_status, db_updates.get("status"), _old_stage, db_updates.get("stage"),
                )
                self._flusher.enqueue(task_id, db_updates)
                with self._lock:
                    if task_id in self._tasks:
                        self._tasks[task_id]["_last_flush_time"] = time.monotonic()
            else:
                # 仅值变化（progress / message）-> 时间节流刷新
                with self._lock:
                    last = self._tasks.get(task_id, {}).get("_last_flush_time", 0.0)
                elapsed = time.monotonic() - last
                if elapsed >= FLUSH_INTERVAL:
                    logger.debug(
                        "[FLUSH] task=%s THROTTLED flush after %.1fs, keys=%s",
                        task_id, elapsed, list(db_updates.keys()),
                    )
                    self._flusher.enqueue(task_id, db_updates)
                    with self._lock:
                        if task_id in self._tasks:
                            self._tasks[task_id]["_last_flush_time"] = time.monotonic()

        failed_statuses = {
            TaskStatus.FAILED.value,
            TaskStatus.FAILED_COMPILATION.value,
            TaskStatus.STRUCTURE_INVALID.value,
        }
        if status in failed_statuses and task_snapshot is not None:
            self._intercept_failed_task(
                task_id=task_id,
                status_message=message,
                status_error=error,
            )

        # ── 终态时发送邮件通知 ──────────────────────────────────────
        # 即发即忘：错误仅记录日志，绝不抛给调用者。
        final_statuses = {
            TaskStatus.COMPLETED.value,
            TaskStatus.COMPLETED_WITH_WARNINGS.value,
            TaskStatus.FAILED.value,
            TaskStatus.FAILED_COMPILATION.value,
            TaskStatus.STRUCTURE_INVALID.value,
        }
        if status in final_statuses:
            self._maybe_send_email_notification(task_id, status, user_id)

        return True

    def set_compile_runtime(
        self,
        task_id: str,
        *,
        pid: Optional[int],
        engine: Optional[str],
        started_at: Optional[str],
    ) -> bool:
        """更新内存中任务的编译运行时元数据"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            task = self._tasks[task_id]
            task["compile_pid"] = pid
            task["compile_engine"] = engine
            task["compile_started_at"] = started_at
            return True

    def _should_skip_failure_quarantine(
        self,
        task_id: str,
        task_snapshot: Dict[str, Any],
        status_message: Optional[str],
        status_error: Optional[str],
        is_cancelled: bool,
    ) -> bool:
        """判断失败任务是否应跳过隔离（已拦截/已取消则跳过）"""
        if task_snapshot.get("failure_intercepted"):
            return True

        if is_cancelled:
            return True

        text_candidates = [
            status_message,
            status_error,
            task_snapshot.get("message"),
            task_snapshot.get("error"),
        ]
        for text in text_candidates:
            if not text:
                continue
            lowered = str(text).lower()
            if "cancelled" in lowered or "canceled" in lowered or "取消" in str(text):
                return True

        return False

    def _quarantine_failed_output(self, task_id: str, task_snapshot: Dict[str, Any]) -> Optional[str]:
        """将失败任务的输出移动到 data/failed_tasks 隔离目录

        返回目标路径（若已移动或已在 failed_tasks 内），否则返回 None。
        """
        settings = get_settings()
        source_path = task_snapshot.get("output_path")
        source_dir = Path(source_path) if source_path else settings.outputs_dir / task_id

        if not source_dir.exists() or not source_dir.is_dir():
            logger.info(
                f"[TaskManager] No output directory to quarantine for failed task {task_id}: {source_dir}"
            )
            return None

        failed_root = Path(settings.failed_tasks_dir)
        failed_root.mkdir(parents=True, exist_ok=True)

        try:
            source_resolved = source_dir.resolve()
            failed_root_resolved = failed_root.resolve()
            if source_resolved == failed_root_resolved or failed_root_resolved in source_resolved.parents:
                logger.info(f"[TaskManager] Failed output already quarantined for task {task_id}: {source_dir}")
                return str(source_dir)
        except Exception:
            # 路径解析失败不应阻塞隔离逻辑。
            pass

        dest_dir = failed_root / task_id
        if dest_dir.exists():
            suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            dest_dir = failed_root / f"{task_id}_{suffix}"

        shutil.move(str(source_dir), str(dest_dir))
        logger.info(f"[TaskManager] Quarantined failed output for task {task_id}: {dest_dir}")
        return str(dest_dir)

    @staticmethod
    def _rewrite_scoped_absolute_path(value: Any, old_root: Path, new_root: Path) -> Any:
        """将指定根目录范围内的绝对路径重写到新根目录下"""
        if not isinstance(value, str):
            return value
        candidate = value.strip()
        if not candidate:
            return value

        is_abs = os.path.isabs(candidate) or bool(re.match(r"^[A-Za-z]:[\\/]", candidate)) or candidate.startswith("\\\\")
        if not is_abs:
            return value

        old_norm = os.path.normcase(os.path.normpath(str(old_root)))
        val_norm = os.path.normcase(os.path.normpath(candidate))
        if val_norm == old_norm:
            return str(new_root)

        prefix = old_norm + os.sep
        if not val_norm.startswith(prefix):
            return value

        rel = os.path.relpath(candidate, str(old_root))
        return str((new_root / rel).resolve())

    def _write_task_log_event(
        self,
        task_log_path: Path,
        *,
        event: str,
        payload: Optional[Dict[str, Any]] = None,
        dedupe_key: Optional[Dict[str, Any]] = None,
    ) -> None:
        """向任务日志文件追加事件条目，支持去重"""
        entries: List[Dict[str, Any]] = []
        if task_log_path.exists():
            try:
                loaded = json.loads(task_log_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    entries = loaded
            except Exception:
                entries = []

        if dedupe_key:
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("event") != event:
                    continue
                if all(entry.get(k) == v for k, v in dedupe_key.items()):
                    return

        row: Dict[str, Any] = {
            "timestamp": get_cst_now_iso(),
            "event": event,
        }
        if payload:
            row.update(payload)
        entries.append(row)
        task_log_path.parent.mkdir(parents=True, exist_ok=True)
        task_log_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def _rewrite_replay_evidence_after_quarantine(
        self,
        *,
        task_id: str,
        task_snapshot: Dict[str, Any],
        old_task_root: Path,
        new_task_root: Path,
    ) -> Dict[str, Any]:
        """隔离后重写 replay 证据文件中的绝对路径引用"""
        old_root = old_task_root.resolve()
        new_root = new_task_root.resolve()

        replay_refs: set[str] = set()
        task_log_paths = sorted(new_root.rglob("task_log.json"))

        for task_log_path in task_log_paths:
            changed = False
            entries: List[Dict[str, Any]] = []
            try:
                loaded = json.loads(task_log_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    entries = loaded
            except Exception as exc:
                logger.warning("[TaskManager] Failed loading task log for replay rewrite (%s): %s", task_log_path, exc)
                continue

            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                ref_value = entry.get("replay_bundle_ref")
                rewritten_ref = self._rewrite_scoped_absolute_path(ref_value, old_root, new_root)
                if rewritten_ref != ref_value:
                    entry["replay_bundle_ref"] = rewritten_ref
                    changed = True
                if isinstance(entry.get("replay_bundle_ref"), str):
                    replay_refs.add(entry["replay_bundle_ref"])

            if changed:
                task_log_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

        replay_bundle_ref = task_snapshot.get("replay_bundle_ref")
        rewritten_task_ref = self._rewrite_scoped_absolute_path(replay_bundle_ref, old_root, new_root)
        if isinstance(rewritten_task_ref, str):
            replay_refs.add(rewritten_task_ref)

        bundle_paths: set[Path] = set()
        for ref in replay_refs:
            try:
                p = Path(ref)
                if p.exists() and p.is_file():
                    bundle_paths.add(p)
            except Exception:
                continue
        for bundled in new_root.rglob("replay_bundle.json"):
            if bundled.is_file():
                bundle_paths.add(bundled)

        missing_paths: List[str] = []
        main_tex_paths: List[Path] = []

        for bundle_path in sorted(bundle_paths):
            changed_bundle = False
            try:
                payload = json.loads(bundle_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("[TaskManager] Failed loading replay bundle for rewrite (%s): %s", bundle_path, exc)
                continue
            if not isinstance(payload, dict):
                continue

            for key, value in list(payload.items()):
                if not isinstance(value, str):
                    continue
                if key == "main_tex_path" or key.endswith("_path") or key.endswith("_ref"):
                    rewritten = self._rewrite_scoped_absolute_path(value, old_root, new_root)
                    if rewritten != value:
                        payload[key] = rewritten
                        changed_bundle = True

            main_tex = payload.get("main_tex_path")
            if isinstance(main_tex, str):
                main_path = Path(main_tex)
                if not main_path.is_absolute():
                    main_path = (bundle_path.parent / main_tex).resolve()
                main_tex_paths.append(main_path)

            if changed_bundle:
                bundle_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if isinstance(rewritten_task_ref, str):
            ref_path = Path(rewritten_task_ref)
            if not ref_path.exists():
                missing_paths.append(str(ref_path))

        for main_path in main_tex_paths:
            if not main_path.exists():
                missing_paths.append(str(main_path))

        evidence_chain_broken = bool(missing_paths)
        if evidence_chain_broken:
            warning_payload = {
                "evidence_chain_broken": True,
                "task_id": task_id,
                "missing_paths": sorted(set(missing_paths)),
            }
            if task_log_paths:
                warning_log = task_log_paths[0]
            else:
                warning_log = new_root / "task_log.json"
            self._write_task_log_event(
                warning_log,
                event="evidence_chain_warning",
                payload=warning_payload,
                dedupe_key={"task_id": task_id, "missing_paths": warning_payload["missing_paths"]},
            )

        return {
            "replay_bundle_ref": rewritten_task_ref if isinstance(rewritten_task_ref, str) else None,
            "evidence_chain_broken": evidence_chain_broken,
            "missing_paths": sorted(set(missing_paths)),
        }

    def _intercept_failed_task(
        self,
        task_id: str,
        status_message: Optional[str],
        status_error: Optional[str],
    ) -> None:
        """处理失败任务的隔离和数据库清理，不中断任务流"""
        with self._lock:
            current_task = self._tasks.get(task_id)
            if current_task is None:
                return

            is_cancelled = task_id in self._cancelled_tasks
            latest_snapshot = current_task.copy()
            if self._should_skip_failure_quarantine(
                task_id=task_id,
                task_snapshot=latest_snapshot,
                status_message=status_message,
                status_error=status_error,
                is_cancelled=is_cancelled,
            ):
                return

            # 立即标记以实现跨重复失败更新的幂等性。
            current_task["failure_intercepted"] = True
            current_task.setdefault("failed_output_path", None)
            current_task.setdefault("evidence_chain_broken", False)

        settings = get_settings()
        source_task_root = Path(latest_snapshot.get("output_path") or settings.outputs_dir / task_id)

        quarantined_output_path: Optional[str] = None
        replay_rewrite_result: Optional[Dict[str, Any]] = None
        try:
            quarantined_output_path = self._quarantine_failed_output(task_id, latest_snapshot)
        except Exception as e:
            logger.error(f"[TaskManager] Failed output quarantine for task {task_id}: {e}", exc_info=True)

        if quarantined_output_path:
            try:
                replay_rewrite_result = self._rewrite_replay_evidence_after_quarantine(
                    task_id=task_id,
                    task_snapshot=latest_snapshot,
                    old_task_root=source_task_root,
                    new_task_root=Path(quarantined_output_path),
                )
            except Exception as exc:
                logger.error(f"[TaskManager] Failed replay evidence rewrite for task {task_id}: {exc}", exc_info=True)

        # 注意: 我们有意不从本地持久化中删除失败任务。
        # 持久化的任务行是终态的权威来源。删除记录会导致历史页面
        # 永久显示过时的 "等待中" 状态。
        # (fix-task-status-sync: Task 1)

        if quarantined_output_path:
            with self._lock:
                current_task = self._tasks.get(task_id)
                if current_task is not None:
                    current_task["failed_output_path"] = quarantined_output_path
                    current_task["output_path"] = quarantined_output_path
                    if replay_rewrite_result and replay_rewrite_result.get("replay_bundle_ref"):
                        current_task["replay_bundle_ref"] = replay_rewrite_result["replay_bundle_ref"]
                    if replay_rewrite_result is not None:
                        current_task["evidence_chain_broken"] = bool(
                            replay_rewrite_result.get("evidence_chain_broken", False)
                        )

    def _maybe_send_email_notification(
        self, task_id: str, status: str, user_id: Optional[str]
    ):
        """如果任务开启了邮件通知且用户已认证，查找用户邮箱并发送通知

        同步调用（从 update_task 调用），但所有失败都会被吞掉，
        绝不中断主任务流。
        """
        try:
            # 获取完整任务快照（此时已持锁）
            with self._lock:
                task_snap = self._tasks.get(task_id, {}).copy()

            adv = task_snap.get("advanced_config") or {}
            if not adv.get("email_notification"):
                return  # 用户未开启邮件通知

            uid = user_id or task_snap.get("user_id")
            if not uid:
                return  # 访客用户无邮箱地址

            try:
                user_row = get_auth_repository().get_user_by_id(str(uid))
                to_email = str(user_row.get("email") or "").strip() if user_row else None
            except Exception as e:
                logger.warning(
                    f"[EmailService] Failed to fetch email for user {uid} from local auth repository: {e}"
                )
                return

            if not to_email:
                logger.warning(
                    f"[EmailService] No email found for user {uid}, skipping notification."
                )
                return

            # 发送邮件（非阻塞，EmailService 内部会吞掉错误）
            from backend.app.services.email_service import get_email_service
            get_email_service().send_task_completed_email(
                to_email=to_email,
                task_id=task_id,
                status=status,
            )

        except Exception as e:
            logger.error(
                f"[EmailService] Unexpected error while sending notification "
                f"for task {task_id}: {e}",
                exc_info=True,
            )


    def persist_task_if_needed(self, task_id: str) -> bool:
        """如果任务尚未持久化到数据库，则首次持久化

        用于延迟任务创建：上传/下载时只创建内存任务，翻译时才持久化。

        参数:
            task_id: 任务 ID

        返回:
            已持久化（或之前已持久化）返回 True，失败返回 False
        """
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"[TaskManager] Cannot persist non-existent task: {task_id}")
            return False

        user_id = task.get("user_id")
        if not user_id:
            # 访客任务，无需持久化
            return True

        # 调用持久化方法（自动处理已存在的情况）
        try:
            persisted = self._persist_task_create(
                task_id=task_id,
                user_id=user_id,
                source_type=task.get("source_type", "upload"),
                arxiv_id=task.get("arxiv_id"),
                source_language=task.get("source_language", "en"),
                target_language=task.get("target_language", "zh"),
                advanced_config=task.get("advanced_config"),
                config_hash=task.get("config_hash"),
            )
            if persisted:
                logger.info(f"[TaskManager] Persisted task {task_id} to database")
            return persisted
        except Exception as e:
            logger.error(f"[TaskManager] Failed to persist task {task_id}: {e}")
            return False

    async def persist_task_with_retry(
        self,
        task_id: str,
        retries: int = 2,
        delay: float = 5.0
    ) -> bool:
        """带自动重试的异步版本 persist_task_if_needed

        所有重试耗尽时：
        - 访客任务可能被注册到 guest_tracker 以进行 TTL 清理
        - 已认证任务保持仅本地模式，标记 persist_failed=True，
          前端可据此展示降级的持久化状态

        参数:
            task_id: 待持久化的任务 ID
            retries: 首次失败后的重试次数（默认: 2）
            delay: 重试间隔秒数（默认: 5.0）

        返回:
            持久化成功返回 True，所有尝试失败返回 False
        """
        for attempt in range(retries + 1):
            success = self.persist_task_if_needed(task_id)
            if success:
                logger.info(
                    f"[TaskManager] persist_task_with_retry: task {task_id} "
                    f"persisted on attempt {attempt + 1}"
                )
                return True
            if attempt < retries:
                logger.warning(
                    f"[TaskManager] persist_task_with_retry: attempt {attempt + 1} "
                    f"failed for task {task_id}, retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        # 所有尝试耗尽 -> 优雅降级
        logger.error(
            f"[TaskManager] persist_task_with_retry: all {retries + 1} attempts "
            f"failed for task {task_id}. Registering as temporary task for auto-cleanup."
        )
        # 注册到 guest_tracker，以便定期清理稍后删除文件
        task_user_id = None
        with self._lock:
            if task_id in self._tasks:
                task_user_id = self._tasks[task_id].get("user_id")

        if not task_user_id:
            guest_tracker.register(task_id)
        # 设置内存标志，供前端检测并警告用户
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["persist_failed"] = True
        return False


    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取任务

        首先检查内存缓存，然后尝试从以下位置恢复:
        1. 本地持久化存储（已认证用户的任务）
        2. 本地文件系统（访客任务或数据库不可用时）

        参数:
            task_id: 任务 ID

        返回:
            任务字典，未找到时返回 None
        """

        cached_task: Optional[Dict[str, Any]] = None
        with self._lock:
            if task_id in self._tasks:
                cached_task = self._tasks.get(task_id, None).copy()

        if cached_task is not None and not _should_refresh_cached_task_from_storage(cached_task):
            return cached_task

        if cached_task is not None:
            refreshed_task = self._recover_from_persistent_store(task_id)
            if refreshed_task:
                refreshed_task = _merge_runtime_fields_into_recovered_task(
                    cached_task,
                    refreshed_task,
                )
                with self._lock:
                    self._tasks[task_id] = refreshed_task
                logger.info(f"[TaskManager] Refreshed cached task {task_id} from persistent storage")
                return refreshed_task.copy()
            return cached_task

        # 任务不在内存中，尝试从持久化存储恢复
        recovered_task = self._recover_task_from_storage(task_id)
        if recovered_task:
            # 缓存已恢复的任务
            with self._lock:
                self._tasks[task_id] = recovered_task
            logger.info(f"[TaskManager] Recovered task {task_id} from persistent storage")
            return recovered_task.copy()

        return None

    def task_exists(self, task_id: str) -> bool:
        """检查任务是否存在"""
        with self._lock:
            return task_id in self._tasks

    def delete_task(self, task_id: str) -> bool:
        """仅从内存缓存中删除任务

        参数:
            task_id: 任务 ID

        返回:
            任务已删除返回 True，未找到返回 False
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                # 同时从取消集合中移除
                self._cancelled_tasks.discard(task_id)
                return True
            return False

    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否已被取消

        参数:
            task_id: 任务 ID

        返回:
            已取消返回 True，否则返回 False
        """
        with self._lock:
            return task_id in self._cancelled_tasks

    def cancel_task(
        self,
        task_id: str,
        *,
        terminal_reason: Optional[str] = None,
        timeout_reason: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """取消任务：强制中断正在运行的 asyncio.Task（如有），
        然后将内存记录标记为失败。

        参数:
            task_id: 任务 ID

        返回:
            任务存在且已标记为取消返回 True
        """
        task_exists = False
        task_snapshot: Optional[Dict[str, Any]] = None
        with self._lock:
            if task_id in self._tasks:
                self._cancelled_tasks.add(task_id)
                task_snapshot = dict(self._tasks[task_id])
                if timeout_reason is not None:
                    self._tasks[task_id]["timeout_reason"] = timeout_reason
                task_exists = True

        if not task_exists:
            return False

        compile_pid = task_snapshot.get("compile_pid") if task_snapshot else None

        try:
            if task_queue is not None:
                task_queue.cancel_execution(task_id)
        except Exception as exc:
            logger.warning(
                f"[TaskManager] cancel_task: cancel_execution raised for {task_id}: {exc}"
            )

        if compile_pid:
            try:
                _kill_process_tree(int(compile_pid))
            except Exception as exc:
                logger.warning("[TaskManager] Failed to terminate compile process for %s: %s", task_id, exc)

        resolved_terminal_reason = str(terminal_reason or "").strip() or "task_cancelled"
        resolved_message = (
            str(message).strip()
            if message is not None and str(message).strip()
            else (
                "Task execution timed out"
                if resolved_terminal_reason == "task_execution_timeout"
                else "Task admission timed out"
                if resolved_terminal_reason == "task_admission_timeout"
                else "Task cancelled by user"
            )
        )
        resolved_error = error if error is not None else resolved_message
        self.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            progress=100,
            stage="done",
            message=resolved_message,
            error=resolved_error,
            detail_code=resolved_terminal_reason,
            failure_reason_code=resolved_terminal_reason,
            user_id=(task_snapshot or {}).get("user_id"),
        )

        refreshed_task = self.get_task(task_id) or {}
        persisted_updates = {
            "status": refreshed_task.get("status") or TaskStatus.FAILED.value,
            "progress": refreshed_task.get("progress") if refreshed_task.get("progress") is not None else 100,
            "stage": refreshed_task.get("stage") or "done",
            "message": refreshed_task.get("message") or resolved_message,
            "error": refreshed_task.get("error") or resolved_error,
            "detail_code": refreshed_task.get("detail_code") or resolved_terminal_reason,
            "completed_at": refreshed_task.get("completed_at") or get_cst_now_iso(),
        }
        if (task_snapshot or {}).get("user_id"):
            self._persist_task_update(task_id, persisted_updates)

        return True

    def delete_task_full(self, task_id: str) -> Dict[str, Any]:
        """完全删除任务：内存缓存 + 本地文件系统

        将删除:
        - data/uploads/{task_id}/
        - data/outputs/{task_id}/
        - data/terms/{task_id}/
        - data/outputs/protection_log/{task_id}.json
        - 内存缓存
        - 取消标志

        注意: 持久化行删除应由 API 层处理。

        参数:
            task_id: 任务 ID

        返回:
            包含删除结果的字典:
            {
                "success": bool,
                "deleted_dirs": [已删除目录列表],
                "errors": [错误消息列表]
            }
        """
        import shutil
        from pathlib import Path
        from backend.app.core.config import get_settings

        settings = get_settings()
        deleted_dirs = []
        errors = []

        # 定义需要删除的目录
        # 注意: uploads/ 现在跨任务共享（基于 arxiv_id），不删除
        dirs_to_delete = [
            settings.outputs_dir / task_id,
            Path(settings.outputs_dir).parent / "terms" / task_id,  # data/terms/{task_id}
        ]

        # 逐一删除目录
        for dir_path in dirs_to_delete:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    deleted_dirs.append(str(dir_path))
                    logger.info(f"[TaskManager] Deleted directory: {dir_path}")
                except Exception as e:
                    error_msg = f"Failed to delete {dir_path}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"[TaskManager] {error_msg}")

        # 删除 task_configs/{task_id}.json（运行时配置快照）
        # 这些文件会静默累积而不被清理 -> 在此删除。
        try:
            task_config_file = Path(settings.task_configs_dir) / f"{task_id}.json"
            if task_config_file.exists():
                task_config_file.unlink()
                deleted_dirs.append(str(task_config_file))
                logger.info(f"[TaskManager] Deleted task config: {task_config_file}")
        except AttributeError:
            # settings.task_configs_dir 不可用（旧版配置），优雅跳过
            logger.debug(f"[TaskManager] task_configs_dir not configured, skipping config cleanup for {task_id}")
        except Exception as e:
            error_msg = f"Failed to delete task config for {task_id}: {str(e)}"
            errors.append(error_msg)
            logger.warning(f"[TaskManager] {error_msg}")

        # 删除 outputs/protection_log/{task_id}.json
        try:
            protection_log_file = Path(settings.outputs_dir) / "protection_log" / f"{task_id}.json"
            if protection_log_file.exists():
                protection_log_file.unlink()
                deleted_dirs.append(str(protection_log_file))
                logger.info(f"[TaskManager] Deleted protection log: {protection_log_file}")
        except Exception as e:
            error_msg = f"Failed to delete protection log for {task_id}: {str(e)}"
            errors.append(error_msg)
            logger.warning(f"[TaskManager] {error_msg}")

        # 从内存缓存和取消集合中删除
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
            self._cancelled_tasks.discard(task_id)

        success = len(errors) == 0
        return {
            "success": success,
            "deleted_dirs": deleted_dirs,
            "errors": errors
        }

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务（调试用）"""
        with self._lock:
            return {k: v.copy() for k, v in self._tasks.items()}

    def create_progress_callback(self, task_id: str, *, attempt_id: Optional[int] = None) -> Callable:
        """为指定任务创建进度回调函数

        参数:
            task_id: 任务 ID

        返回:
            签名为 on_progress(percentage, message) 的回调函数
        """
        def on_progress(percentage: int, message: str = ""):
            """进度回调"""
            # percentage == -1 表示 "仅更新消息，保持当前进度"
            if percentage == -1:
                # 在不持锁的情况下读取当前进度（update_task 会获取锁）
                current_progress = 0
                current_stage = CompilationStage.TRANSLATING.value
                with self._lock:
                    task = self._tasks.get(task_id)
                    if task:
                        current_progress = task.get("progress", 0)
                        current_stage = task.get("stage", CompilationStage.TRANSLATING.value)
                    else:
                        return  # 任务未找到，跳过
                # 在不持锁的情况下调用 update_task
                self.update_task(
                    task_id=task_id,
                    status=TaskStatus.PROCESSING.value,
                    progress=current_progress,
                    stage=current_stage,
                    message=message,
                    expected_attempt_id=attempt_id
                )
                return

            # 从进度百分比推断阶段
            if percentage < 10:
                stage = CompilationStage.PARSING.value
            elif percentage < 70:
                stage = CompilationStage.TRANSLATING.value
            elif percentage < 100:
                stage = CompilationStage.COMPILING.value
            else:
                stage = CompilationStage.DONE.value

            self.update_task(
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                progress=percentage,
                stage=stage,
                message=message,
                expected_attempt_id=attempt_id
            )

        return on_progress

    def _persist_task_create(
        self,
        task_id: str,
        user_id: str,
        source_type: str,
        arxiv_id: Optional[str],
        source_language: str,
        target_language: str,
        advanced_config: Optional[Dict[str, Any]],
        config_hash: Optional[str] = None,
    ) -> bool:
        """将任务创建持久化到本地翻译任务存储

        参数:
            task_id: 任务 ID
            user_id: 用户 ID
            source_type: "upload" 或 "arxiv"
            arxiv_id: arXiv 论文 ID（如适用）
            source_language: 源语言代码
            target_language: 目标语言代码
            advanced_config: 高级配置快照
        """
        try:
            repository = get_translation_task_repository()
            db_record = {
                "task_id": task_id,
                "user_id": user_id,
                "source_type": source_type,
                "arxiv_id": arxiv_id,
                "source_language": source_language,
                "target_language": target_language,
                "status": TaskStatus.PENDING.value,
                "progress": 0,
                "stage": CompilationStage.IDLE.value,
                "detail_code": "task_waiting",
                "message": "Task created",
                "created_at": get_cst_now_iso(),
                "completed_at": None,
                "translation_mode": "full",
                "compile_strategy": "auto",
                "translation_model": None,
                "generate_glossary": True,
                "use_author_api": True,
                "email_notification": False,
            }
            if config_hash:
                db_record["config_hash"] = config_hash

            if advanced_config and isinstance(advanced_config, dict):
                db_record["translation_mode"] = advanced_config.get("translation_mode", "full")
                db_record["compile_strategy"] = advanced_config.get("compile_strategy", "auto")
                db_record["translation_model"] = advanced_config.get("translation_model")
                db_record["generate_glossary"] = advanced_config.get("generate_terminology_table", True)
                db_record["use_author_api"] = advanced_config.get("use_author_api", True)
                db_record["email_notification"] = advanced_config.get("email_notification", False)
                fmt = advanced_config.get("formatting")
                if fmt is not None:
                    if hasattr(fmt, "model_dump"):
                        fmt = fmt.model_dump(exclude_none=True)
                    elif hasattr(fmt, "dict"):
                        fmt = fmt.dict(exclude_none=True)
                    db_record["formatting"] = fmt if fmt else None

            task_snapshot = self.get_task(task_id) or {}
            for key in ("source_path", "output_path", "status", "progress", "stage", "message", "error", "completed_at"):
                if task_snapshot.get(key) is not None:
                    db_record[key] = task_snapshot.get(key)

            repository.upsert_task(task_id, db_record)
            logger.info(f"[TaskManager] Persisted task {task_id} to local translation storage for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"[TaskManager] Failed to persist task {task_id} to local translation storage: {e}", exc_info=True)
            return False

    def _persist_task_update(self, task_id: str, updates: Dict[str, Any]):
        """将任务更新持久化到本地翻译任务存储

        参数:
            task_id: 任务 ID
            updates: 待更新字段的字典
        """
        try:
            repository = get_translation_task_repository()
            if repository.update_task(task_id, updates):
                logger.debug(f"[TaskManager] Synced task {task_id} to local translation storage: {list(updates.keys())}")
        except Exception as e:
            logger.error(f"[TaskManager] Failed to sync task {task_id} to local translation storage: {e}")

    def _recover_task_from_storage(self, task_id: str) -> Optional[Dict[str, Any]]:
        """尝试从持久化存储或本地文件系统恢复任务

        参数:
            task_id: 待恢复的任务 ID

        返回:
            任务字典（如找到），否则 None
        """
        # 首先尝试本地数据库
        task = self._recover_from_persistent_store(task_id)
        if task:
            return task

        # 回退到本地文件系统
        task = self._recover_from_filesystem(task_id)
        if task:
            return task

        return None

    def _recover_from_persistent_store(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从本地翻译任务存储恢复任务

        参数:
            task_id: 任务 ID

        返回:
            任务字典（如找到），否则 None
        """
        try:
            repository = get_translation_task_repository()
            db_task = repository.get_task(task_id)
            if not db_task:
                return None

            if (
                db_task.get("completed_at")
                and not _is_terminal_task_status(db_task.get("status"))
            ):
                reconciliation_message = (
                    "Recovered inconsistent task state: non-terminal status with completed_at already set"
                )
                repository.update_task(
                    task_id,
                    {
                        "status": TaskStatus.FAILED.value,
                        "progress": 100,
                        "message": reconciliation_message,
                        "error": db_task.get("error") or reconciliation_message,
                        "detail_code": "task_state_reconciled",
                    },
                )
                db_task = dict(db_task)
                db_task["status"] = TaskStatus.FAILED.value
                db_task["progress"] = 100
                db_task["message"] = reconciliation_message
                db_task["error"] = db_task.get("error") or reconciliation_message
                db_task["detail_code"] = "task_state_reconciled"

            task = {
                "task_id": db_task.get("task_id"),
                "status": db_task.get("status", "completed"),
                "progress": db_task.get("progress", 100),
                "stage": db_task.get("stage", "done"),
                "message": db_task.get("message", "Task completed"),
                "detail_code": db_task.get("detail_code"),
                "detail_params": db_task.get("detail_params"),
                "error": db_task.get("error"),
                "warnings": None,
                "source_available": True,
                "created_at": _serialize_task_timestamp(
                    db_task.get("created_at", datetime.now(timezone.utc).isoformat())
                ),
                "completed_at": _serialize_task_timestamp(db_task.get("completed_at")),
                "source_type": db_task.get("source_type", "arxiv"),
                "source_path": db_task.get("source_path"),
                "output_path": db_task.get("output_path"),
                "advanced_config": {
                    "translation_mode": db_task.get("translation_mode", "full"),
                    "compile_strategy": db_task.get("compile_strategy", "auto"),
                    "translation_model": db_task.get("translation_model"),
                    "generate_terminology_table": db_task.get("generate_glossary", True),
                    "use_author_api": db_task.get("use_author_api", True),
                    "email_notification": db_task.get("email_notification", False),
                },
                "latex_validation": None,
                "arxiv_id": db_task.get("arxiv_id"),
                "user_id": db_task.get("user_id"),
                "source_language": db_task.get("source_language", "en"),
                "target_language": db_task.get("target_language", "zh"),
                "attempt_id": 0,
            }

            formatting = db_task.get("formatting")
            if formatting is not None:
                task["advanced_config"]["formatting"] = formatting

            if not task["output_path"] or not task["source_path"]:
                self._infer_paths_from_filesystem(task)

            logger.debug(f"[TaskManager] Recovered task {task_id} from local translation storage")
            return task
        except Exception as e:
            logger.warning(f"[TaskManager] Failed to recover task {task_id} from local translation storage: {e}")

        return None

    def _recover_from_filesystem(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从本地文件系统恢复任务

        参数:
            task_id: 任务 ID

        返回:
            任务字典（如找到），否则 None
        """
        from pathlib import Path
        from backend.app.core.config import get_settings

        try:
            settings = get_settings()
            output_base = Path(settings.outputs_dir)

            # 检查此任务的输出目录是否存在
            task_output_dir = output_base / task_id
            if task_output_dir.exists() and task_output_dir.is_dir():
                # 任务输出存在，从文件系统构建任务信息
                task = {
                    "task_id": task_id,
                    "status": TaskStatus.COMPLETED.value,  # 如果输出存在，假设已完成
                    "progress": 100,
                    "stage": CompilationStage.DONE.value,
                    "message": "Task recovered from filesystem",
                    "detail_code": "compile_complete",
                    "detail_params": None,
                    "error": None,
                    "warnings": None,
                    "source_available": True,
                    "created_at": datetime.fromtimestamp(task_output_dir.stat().st_ctime).isoformat(),
                    "completed_at": datetime.fromtimestamp(task_output_dir.stat().st_mtime).isoformat(),
                    "source_type": "unknown",
                    "source_path": None,  # 将在下面推断
                    "output_path": str(task_output_dir),
                    "advanced_config": None,
                    "latex_validation": None,
                    "arxiv_id": None,
                    "user_id": None,
                    "source_language": "en",
                    "target_language": "zh"
                }

                # 尝试找到源路径
                source_base = Path(settings.uploads_dir)
                task_source_dir = source_base / task_id
                if task_source_dir.exists():
                    task["source_path"] = str(task_source_dir)

                # 尝试从目录内容推断 arxiv_id
                self._infer_arxiv_id(task, task_output_dir)

                logger.debug(f"[TaskManager] Recovered task {task_id} from filesystem")
                return task

        except Exception as e:
            logger.warning(
                "[TaskManager] Failed to recover task %s from filesystem "
                "(outputs_dir=%r, uploads_dir=%r): %s",
                task_id,
                getattr(settings, "outputs_dir", None) if "settings" in locals() else None,
                getattr(settings, "uploads_dir", None) if "settings" in locals() else None,
                e,
                exc_info=True,
            )

        return None

    def _infer_paths_from_filesystem(self, task: Dict[str, Any]):
        """从文件系统推断 source_path 和 output_path（如未设置）

        参数:
            task: 待更新的任务字典
        """
        from pathlib import Path
        from backend.app.core.config import get_settings

        try:
            settings = get_settings()
            task_id = task["task_id"]

            if not task.get("output_path"):
                output_dir = Path(settings.outputs_dir) / task_id
                if output_dir.exists():
                    task["output_path"] = str(output_dir)

            if not task.get("source_path"):
                source_dir = Path(settings.uploads_dir) / task_id
                if source_dir.exists():
                    task["source_path"] = str(source_dir)

        except Exception as e:
            logger.warning(
                "[TaskManager] Failed to infer filesystem paths for task %s "
                "(outputs_dir=%r, uploads_dir=%r): %s",
                task.get("task_id"),
                getattr(settings, "outputs_dir", None) if "settings" in locals() else None,
                getattr(settings, "uploads_dir", None) if "settings" in locals() else None,
                e,
                exc_info=True,
            )

    def _infer_arxiv_id(self, task: Dict[str, Any], directory: Any):
        """尝试从目录内容推断 arxiv_id

        参数:
            task: 待更新的任务字典
            directory: 待搜索的目录
        """
        import re
        arxiv_pattern = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')

        try:
            # 检查目录名
            match = arxiv_pattern.search(directory.name)
            if match:
                task["arxiv_id"] = match.group(1)
                task["source_type"] = "arxiv"
                return

            # 检查文件名
            for file_path in directory.iterdir():
                match = arxiv_pattern.search(file_path.name)
                if match:
                    task["arxiv_id"] = match.group(1)
                    task["source_type"] = "arxiv"
                    return

        except Exception:
            pass


# 全局任务管理器实例
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    return task_manager


class GuestTaskTracker:
    """以 TTL 追踪访客（未认证）任务 ID，用于自动清理。

    线程安全的内存追踪器。
    """

    def __init__(self):
        """初始化访客任务追踪器"""
        self._guest_tasks: Dict[str, datetime] = {}  # task_id -> 过期时间
        self._lock = threading.Lock()

    def register(self, task_id: str, ttl_hours: Optional[int] = None):
        """注册带 TTL 的访客任务

        参数:
            task_id: 待注册的任务 ID
            ttl_hours: TTL 小时数（默认取自 settings.guest_task_ttl_hours）
        """
        from backend.app.core.config import get_settings
        if ttl_hours is None:
            ttl_hours = get_settings().guest_task_ttl_hours
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        with self._lock:
            self._guest_tasks[task_id] = expires_at
        logger.debug(f"[GuestTracker] Registered guest task {task_id}, expires at {expires_at}")

    def get_expired_task_ids(self) -> List[str]:
        """返回已过期的访客任务 ID 列表"""
        now = datetime.now(timezone.utc)
        with self._lock:
            return [tid for tid, exp in self._guest_tasks.items() if exp <= now]

    def remove(self, task_id: str):
        """从追踪器中移除访客任务"""
        with self._lock:
            self._guest_tasks.pop(task_id, None)

    def get_all(self) -> Dict[str, datetime]:
        """返回所有已追踪访客任务的副本"""
        with self._lock:
            return dict(self._guest_tasks)


class TaskQueue:
    """基于 asyncio 的按令牌哈希隔离的任务队列，支持每用户配额。

    架构: 令牌隔离多桶模型
    --------------------------
    每个唯一的 ``token_hash`` 拥有自己的:
      - ``asyncio.Queue`` -- FIFO 通道，对其他令牌不可见
      - ``asyncio.Semaphore`` -- 并发上限 = ``max_concurrent``
      - 后台 ``_worker`` 协程 -- 延迟创建，永不退出

    Worker 生命周期: 首次入队时延迟创建，之后永久存在。
    这消除了空闲 worker 退出时产生的入队与生成竞态。

    必须通过 ``initialize()`` 在异步上下文中初始化。
    """

    def __init__(self, max_concurrent: int = 3):
        """初始化任务队列

        参数:
            max_concurrent: 每个令牌桶的最大并发数
        """
        self._max_concurrent = max_concurrent
        self._cancel_retry_limit = 2
        # 按令牌哈希分桶（延迟填充）
        self._queues: Dict[str, Dict[str, asyncio.Queue]] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._bucket_capacity: Dict[str, int] = {}
        self._bucket_events: Dict[str, asyncio.Event] = {}
        self._workers: Dict[str, asyncio.Task] = {}
        # 跨桶共享状态
        self._active_tasks: Dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        self._active_task_lanes: Dict[str, str] = {}      # task_id -> interactive|backfill
        self._skipped: set = set()                         # 出队时需要丢弃的 task_ids
        self._explicitly_cancelled: set = set()           # 控制流显式取消的 task_ids
        self._user_task_count: Dict[str, int] = {}        # user_id -> 活跃任务计数
        self._init_lock: Optional[asyncio.Lock] = None    # 在 initialize() 中创建

    async def initialize(self):
        """初始化共享锁（必须在异步上下文中调用）"""
        self._init_lock = asyncio.Lock()
        logger.info(f"[TaskQueue] Initialized with max_concurrent={self._max_concurrent}")

    # ── 内部: 延迟桶创建 ────────────────────────────────────────────

    def _normalize_bucket_capacity(self, llm_capacity: Optional[int] = None) -> int:
        """规范化桶容量"""
        if llm_capacity is None:
            return max(int(self._max_concurrent or 1), 1)
        return max(min(int(llm_capacity or 1), int(self._max_concurrent or 1)), 1)

    def _set_bucket_capacity(self, token_hash: str, capacity: int) -> None:
        """设置桶容量（仅在首次设置时生效，避免覆盖）"""
        current = self._bucket_capacity.get(token_hash)
        if current == capacity:
            return
        if current is not None:
            logger.info(
                "[TaskQueue] Keeping existing bucket capacity for token=%s at %s; requested %s",
                token_hash[:8],
                current,
                capacity,
            )
            return
        self._bucket_capacity[token_hash] = capacity

    async def _ensure_bucket(self, token_hash: str, llm_capacity: Optional[int] = None) -> None:
        """延迟创建 token_hash 对应的队列、信号量和 worker。

        如果桶已存在则无操作。受 _init_lock 保护。
        """
        normalized_capacity = self._normalize_bucket_capacity(llm_capacity)
        if token_hash in self._queues:
            self._set_bucket_capacity(token_hash, normalized_capacity)
            worker = self._workers.get(token_hash)
            if worker is None or worker.done():
                self._workers[token_hash] = asyncio.create_task(self._worker(token_hash))
                logger.warning(
                    f"[TaskQueue] Respawned worker for token_hash={token_hash[:8]}..."
                )
            return
        async with self._init_lock:
            # 持锁后二次检查
            if token_hash in self._queues:
                self._set_bucket_capacity(token_hash, normalized_capacity)
                worker = self._workers.get(token_hash)
                if worker is None or worker.done():
                    self._workers[token_hash] = asyncio.create_task(self._worker(token_hash))
                    logger.warning(
                        f"[TaskQueue] Respawned worker for token_hash={token_hash[:8]}..."
                    )
                return
            self._queues[token_hash] = {
                "interactive": asyncio.Queue(),
                "backfill": asyncio.Queue(),
            }
            self._bucket_capacity[token_hash] = normalized_capacity
            self._semaphores[token_hash] = asyncio.Semaphore(normalized_capacity)
            self._bucket_events[token_hash] = asyncio.Event()
            worker = asyncio.create_task(self._worker(token_hash))
            self._workers[token_hash] = worker
            logger.info(
                f"[TaskQueue] Created bucket for token_hash={token_hash[:8]}... "
                f"(max_concurrent={normalized_capacity})"
            )

    # ── 公开 API ─────────────────────────────────────────────────────

    async def enqueue(
        self,
        task_id: str,
        coro_factory,
        user_id: Optional[str] = None,
        token_hash: str = "default",
        lane: str = "interactive",
        llm_capacity: Optional[int] = None,
    ):
        """将翻译任务入队到 token_hash 对应的桶中

        参数:
            task_id: 任务 ID
            coro_factory: 无参数异步可调用对象，执行翻译任务
            user_id: 可选用户 ID，用于每用户配额追踪
            token_hash: LLM API Key 的 MD5 十六进制摘要，确定路由桶
            lane: 调度通道，``interactive`` 或 ``backfill``
        """
        normalized_lane = "backfill" if str(lane or "").strip().lower() == "backfill" else "interactive"

        # 更新任务状态为 QUEUED
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.QUEUED.value,
            message="Task queued, waiting for available slot",
            detail_code="task_queued",
            user_id=user_id,
        )

        # 增加用户配额计数
        if user_id:
            async with self._init_lock:
                self._user_task_count[user_id] = (
                    self._user_task_count.get(user_id, 0) + 1
                )

        # 确保桶存在（延迟创建）
        await self._ensure_bucket(token_hash, llm_capacity=llm_capacity)

        await self._queues[token_hash][normalized_lane].put((task_id, coro_factory, user_id, normalized_lane))
        self._bucket_events[token_hash].set()

        bucket_size = sum(queue.qsize() for queue in self._queues[token_hash].values())
        logger.info(
            f"[TaskQueue] Enqueued task {task_id} "
            f"(token={token_hash[:8]}..., lane={normalized_lane}, user={user_id}, "
            f"bucket_size={bucket_size}, llm_capacity={self._bucket_capacity.get(token_hash)})"
        )

    def cancel_execution(self, task_id: str) -> bool:
        """强制取消 task_id 的执行

        - 如果任务当前正在运行：调用 ``asyncio.Task.cancel()``
        - 如果任务已入队但尚未运行：将其加入 ``_skipped``，
          worker 在下次出队时丢弃。

        返回:
            任务已找到（运行中或排队中）返回 True，否则返回 False
        """
        self._explicitly_cancelled.add(task_id)

        running_task = self._active_tasks.get(task_id)
        if running_task is not None and not running_task.done():
            running_task.cancel()
            logger.info(f"[TaskQueue] cancel_execution: cancelled running task {task_id}")
            return True

        # 未运行 - 标记为已跳过，worker 出队时丢弃
        self._skipped.add(task_id)
        logger.info(
            f"[TaskQueue] cancel_execution: task {task_id} not yet running, "
            f"added to _skipped"
        )
        return True

    def get_user_active_count(self, user_id: str) -> int:
        """获取用户的活跃（排队 + 运行中）任务数"""
        return self._user_task_count.get(user_id, 0)

    def get_status(self) -> Dict[str, Any]:
        """返回所有令牌桶的聚合队列状态"""
        active_count = len(self._active_tasks)
        queue_size = sum(
            lane_queue.qsize()
            for bucket in self._queues.values()
            for lane_queue in bucket.values()
        )
        interactive_active = sum(1 for lane in self._active_task_lanes.values() if lane == "interactive")
        backfill_active = sum(1 for lane in self._active_task_lanes.values() if lane == "backfill")
        interactive_waiting = sum(bucket["interactive"].qsize() for bucket in self._queues.values())
        backfill_waiting = sum(bucket["backfill"].qsize() for bucket in self._queues.values())
        return {
            "active_count": active_count,
            "queue_size": queue_size,
            "max_concurrent": self._max_concurrent,
            "total_pending": active_count + queue_size,
            "bucket_count": len(self._queues),
            "interactive_active": interactive_active,
            "interactive_waiting": interactive_waiting,
            "backfill_active": backfill_active,
            "backfill_waiting": backfill_waiting,
            "borrowed_slots": backfill_active,
        }

    # ── 内部: 每个令牌的 worker（永久存活）──────────────────────────

    async def _worker(self, token_hash: str):
        """token_hash 桶的后台 worker

        生命周期不变: 应用运行期间绝不退出。
        ``while True`` 循环确保 worker 在队列为空时仍然存在 --
        消除入队与生成竞态条件。
        """
        logger.info(f"[TaskQueue] Worker started for token_hash={token_hash[:8]}...")
        while True:
            try:
                bucket = self._queues[token_hash]
                bucket_event = self._bucket_events[token_hash]
                while bucket["interactive"].empty() and bucket["backfill"].empty():
                    bucket_event.clear()
                    if bucket["interactive"].empty() and bucket["backfill"].empty():
                        await bucket_event.wait()
                # 先预留槽位，再选择下一个通道项
                await self._semaphores[token_hash].acquire()
                if not bucket["interactive"].empty():
                    selected_queue = bucket["interactive"]
                elif not bucket["backfill"].empty():
                    if backfill_start_blocked_by_frontend_pressure():
                        self._semaphores[token_hash].release()
                        bucket_event.clear()
                        try:
                            await asyncio.wait_for(bucket_event.wait(), timeout=0.25)
                        except asyncio.TimeoutError:
                            pass
                        continue
                    selected_queue = bucket["backfill"]
                else:
                    self._semaphores[token_hash].release()
                    continue

                task_id, coro_factory, user_id, lane = await selected_queue.get()
                logger.info(
                    f"[TaskQueue] Worker({token_hash[:8]}...) picked up task {task_id} from lane={lane}"
                )

                # --- 跳过检查（仅针对仅排队取消） ---
                if task_id in self._skipped:
                    self._skipped.discard(task_id)
                    self._explicitly_cancelled.discard(task_id)
                    selected_queue.task_done()
                    logger.info(
                        f"[TaskQueue] Task {task_id} was in _skipped, discarding."
                    )
                    # 减少被跳过任务的用户配额
                    if user_id:
                        async with self._init_lock:
                            count = self._user_task_count.get(user_id, 1)
                            if count <= 1:
                                self._user_task_count.pop(user_id, None)
                            else:
                                self._user_task_count[user_id] = count - 1
                    self._semaphores[token_hash].release()
                    continue


                # --- 第二次跳过检查 ---
                # 处理竞态: cancel_execution() 在 worker 等待信号量时被调用
                # （任务已出队但尚未运行，因此在第一次检查后进入了 _skipped）。
                if task_id in self._skipped:
                    self._skipped.discard(task_id)
                    self._explicitly_cancelled.discard(task_id)
                    self._semaphores[token_hash].release()
                    selected_queue.task_done()
                    logger.info(
                        f"[TaskQueue] Task {task_id} skipped after semaphore acquire "
                        f"(cancelled while waiting for slot)."
                    )
                    if user_id:
                        async with self._init_lock:
                            count = self._user_task_count.get(user_id, 1)
                            if count <= 1:
                                self._user_task_count.pop(user_id, None)
                            else:
                                self._user_task_count[user_id] = count - 1
                    continue
                async def _run_with_cancel_retry(
                    current_task_id=task_id,
                    current_coro_factory=coro_factory,
                    current_user_id=user_id,
                ):
                    retry_count = 0
                    while True:
                        try:
                            await current_coro_factory()
                            return
                        except asyncio.CancelledError:
                            user_cancelled = task_manager.is_cancelled(current_task_id)
                            explicitly_cancelled = current_task_id in self._explicitly_cancelled
                            runtime_stopping = is_runtime_shutting_down()
                            if user_cancelled or explicitly_cancelled or runtime_stopping:
                                raise
                            if retry_count >= self._cancel_retry_limit:
                                logger.warning(
                                    "[TaskQueue] Task %s hit cancel-retry limit (%s), giving up.",
                                    current_task_id,
                                    self._cancel_retry_limit,
                                )
                                raise
                            retry_count += 1
                            logger.warning(
                                "[TaskQueue] Task %s cancelled unexpectedly; retrying (%s/%s).",
                                current_task_id,
                                retry_count,
                                self._cancel_retry_limit,
                            )
                            task_manager.update_task(
                                task_id=current_task_id,
                                status=TaskStatus.QUEUED.value,
                                message=(
                                    f"Task interrupted unexpectedly, retrying "
                                    f"({retry_count}/{self._cancel_retry_limit})"
                                ),
                                detail_code="task_retry_after_cancel",
                                user_id=current_user_id,
                            )
                            await asyncio.sleep(min(1.5 * retry_count, 5.0))

                running_task = asyncio.create_task(_run_with_cancel_retry())
                self._active_tasks[task_id] = running_task
                self._active_task_lanes[task_id] = lane

                def _on_task_done(done_task: asyncio.Task, tid: str, uid: Optional[str], th: str) -> None:
                    async def _cleanup() -> None:
                        try:
                            try:
                                exc = done_task.exception()
                            except asyncio.CancelledError:
                                logger.info(
                                    f"[TaskQueue] Task {tid} was cancelled "
                                    f"(CancelledError), releasing slot."
                                )
                            else:
                                if exc is not None:
                                    logger.error(
                                        f"[TaskQueue] Task {tid} raised exception: {exc}",
                                        exc_info=True,
                                    )
                                    current_task = task_manager.get_task(tid) or {}
                                    if not _is_terminal_task_status(current_task.get("status")):
                                        task_manager.update_task(
                                            task_id=tid,
                                            status=TaskStatus.FAILED.value,
                                            progress=100,
                                            message=f"Task crashed unexpectedly: {exc}",
                                            error=str(exc),
                                            detail_code="task_runtime_exception",
                                            user_id=uid,
                                        )
                                        try:
                                            from backend.app.services import paper_service

                                            await paper_service.mark_paper_translation_failed_by_task(tid)
                                        except Exception:
                                            logger.warning(
                                                "[TaskQueue] Failed to sync paper status after unexpected task exception for %s",
                                                tid,
                                                exc_info=True,
                                            )
                        finally:
                            self._semaphores[th].release()
                            if uid:
                                async with self._init_lock:
                                    count = self._user_task_count.get(uid, 1)
                                    if count <= 1:
                                        self._user_task_count.pop(uid, None)
                                    else:
                                        self._user_task_count[uid] = count - 1
                            self._active_tasks.pop(tid, None)
                            self._active_task_lanes.pop(tid, None)
                            self._explicitly_cancelled.discard(tid)
                            logger.info(
                                f"[TaskQueue] Task {tid} finished, "
                                f"semaphore slot released for token={th[:8]}..."
                            )

                    asyncio.create_task(_cleanup())

                running_task.add_done_callback(
                    lambda done_task, tid=task_id, uid=user_id, th=token_hash: _on_task_done(done_task, tid, uid, th)
                )
                selected_queue.task_done()


            except asyncio.CancelledError:
                if not is_runtime_shutting_down():
                    current_worker = asyncio.current_task()
                    replacement_worker = asyncio.create_task(self._worker(token_hash))
                    if self._workers.get(token_hash) is current_worker:
                        self._workers[token_hash] = replacement_worker
                    logger.warning(
                        f"[TaskQueue] Worker({token_hash[:8]}...) got unexpected cancellation; respawned."
                    )
                    return
                # Worker 本身被取消（例如进程关闭） -> 干净退出
                logger.info(
                    f"[TaskQueue] Worker for token_hash={token_hash[:8]}... cancelled"
                )
                break
            except Exception as e:
                logger.error(
                    f"[TaskQueue] Worker({token_hash[:8]}...) error: {e}",
                    exc_info=True,
                )


# 全局实例
guest_tracker = GuestTaskTracker()
task_queue: Optional[TaskQueue] = None  # 在 main.py 启动时初始化


def get_guest_tracker() -> GuestTaskTracker:
    """获取全局访客任务追踪器实例"""
    return guest_tracker


def get_task_queue() -> Optional[TaskQueue]:
    """获取全局任务队列实例"""
    return task_queue
