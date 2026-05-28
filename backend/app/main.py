"""
FastAPI 主应用程序

最小化 MVP 版本，提供：
- 健康检查端点
- arXiv 下载端点
- 基础 CORS 配置
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import List, Set

from fastapi import FastAPI, Response, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.auth import require_admin_request
from backend.app.core.config import get_settings
from backend.app.db import DatabaseUnavailableError
from backend.app.repositories import CommunityPaperRepository, TranslationTaskRepository
from backend.app.services.task_manager import (
    get_task_manager,
    get_task_queue,
)
from backend.app.services import runtime_pressure
from backend.app.services import task_manager as task_manager_module

if hasattr(task_manager_module, "set_runtime_shutting_down"):
    set_runtime_shutting_down = task_manager_module.set_runtime_shutting_down
else:
    def set_runtime_shutting_down(_flag: bool) -> None:
        """设置运行时关闭标志（兼容性空实现）"""
        return None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 获取全局设置
settings = get_settings()

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="PaperX Backend API"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def frontend_pressure_middleware(request, call_next):
    """前端流量压力感知中间件：当 Web 运行时启用时记录前端请求压力"""
    if runtime_pressure.web_runtime_enabled():
        runtime_pressure.record_frontend_pressure()
    return await call_next(request)

api_router = APIRouter()

# 被中断的任务状态集合
INTERRUPTED_TASK_STATUSES = ["queued", "pending", "processing"]
# 非成功状态的论文状态集合
NON_SUCCESS_PAPER_STATUSES = [
    "not_started",
    "queued",
    "processing",
    "failed",
    "failed_compilation",
    "structure_invalid",
]


def _dedupe_non_empty(values: List[str]) -> List[str]:
    """对非空字符串列表去重，保持原始顺序"""
    seen: Set[str] = set()
    ordered: List[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


async def _seed_rag_terminology():
    """在首次启动时写入官方 RAG 术语数据"""
    try:
        seed_enabled = os.getenv("RAG_TERMINOLOGY_SEED_ON_STARTUP", "true").strip().lower() in {"1", "true", "yes"}
        if not seed_enabled:
            logger.info("[RAGSeed] Seeding disabled (set RAG_TERMINOLOGY_SEED_ON_STARTUP=false to confirm).")
            return

        from backend.app.services.terminology_service import TerminologyService
        service = TerminologyService()
        count = service.seed_official_terms()
        if count > 0:
            logger.info("[RAGSeed] Seeded %d official terminology terms.", count)
        else:
            logger.info("[RAGSeed] No new terms to seed (already present or empty seed file).")
    except Exception:
        logger.warning("[RAGSeed] Failed to seed terminology (non-fatal):", exc_info=True)


def get_translation_task_repository() -> TranslationTaskRepository:
    """获取翻译任务仓库实例"""
    return TranslationTaskRepository()


def get_community_paper_repository() -> CommunityPaperRepository:
    """获取社区论文仓库实例"""
    return CommunityPaperRepository()


async def reset_stale_community_tasks() -> dict:
    """
    清理非成功状态的社区论文记录。

    移除相关的本地产物和论文相关的本地数据库行。
    """
    import asyncio as _asyncio
    import shutil as _shutil

    result = {"reset_papers": 0, "deleted_folders": 0, "errors": []}
    repository = get_community_paper_repository()
    task_manager = get_task_manager()
    purge_enabled = os.getenv("ENABLE_STALE_PAPER_PURGE", "true").strip().lower() in {"1", "true", "yes", "on"}
    if not purge_enabled:
        logger.info("[StaleCleanup] Purge disabled (set ENABLE_STALE_PAPER_PURGE=true to enable).")
        result["purge_disabled"] = True
        return result

    try:
        purgeable_rows = repository.list_purgeable_non_success_papers(NON_SUCCESS_PAPER_STATUSES)
    except DatabaseUnavailableError as exc:
        msg = f"[StaleCleanup] Local community repository unavailable; cleanup skipped: {exc}"
        logger.error(msg)
        result["errors"].append(msg)
        return result
    except Exception as exc:
        msg = f"[StaleCleanup] Failed to query local community repository: {exc}"
        logger.error(msg)
        result["errors"].append(msg)
        return result

    try:
        # 安全守卫：绝不在启动时清除公开已发布的论文。
        # 仅清除草稿/私有/已移除状态且仍处于非成功状态的记录。
        purgeable_rows = [
            row
            for row in purgeable_rows
            if str(row.get("status") or "").strip() == "removed"
            or str(row.get("visibility") or "").strip() not in {"public"}
        ]
        purgeable_ids = [row["id"] for row in purgeable_rows if row.get("id")]
        logger.info("[StaleCleanup] Purgeable non-success papers: %s", purgeable_ids)

        cp_dir = settings.community_papers_dir
        for paper_id in purgeable_ids:
            target = cp_dir / paper_id
            if target.exists():
                try:
                    _shutil.rmtree(target)
                    result["deleted_folders"] += 1
                except Exception as rm_err:
                    msg = f"[StaleCleanup] Failed to delete {target}: {rm_err}"
                    logger.error(msg)
                    result["errors"].append(msg)

        if not purgeable_ids:
            logger.info("[StaleCleanup] Nothing to purge")
            return result

        asset_task_ids = await _asyncio.to_thread(repository.list_asset_task_ids_for_papers, purgeable_ids)
        comment_ids = await _asyncio.to_thread(repository.list_comment_ids_for_papers, purgeable_ids)
        report_ids = await _asyncio.to_thread(
            repository.list_report_ids_for_targets,
            target_type="paper",
            target_ids=purgeable_ids,
        )
        if comment_ids:
            report_ids.extend(
                await _asyncio.to_thread(
                    repository.list_report_ids_for_targets,
                    target_type="comment",
                    target_ids=comment_ids,
                )
            )
        report_ids = _dedupe_non_empty(report_ids)

        if report_ids:
            await _asyncio.to_thread(
                repository.delete_rows_by_ids,
                "moderation_actions",
                id_column="report_id",
                row_ids=report_ids,
            )
            await _asyncio.to_thread(
                repository.delete_rows_by_ids,
                "reports",
                id_column="id",
                row_ids=report_ids,
            )

        for table_name in ["comments", "paper_assets", "paper_likes", "paper_favorites"]:
            await _asyncio.to_thread(repository.delete_rows_for_papers, table_name, purgeable_ids)

        purgeable_task_ids = _dedupe_non_empty(
            [row.get("trans_latest_task_id") for row in purgeable_rows]
            + [row.get("community_selected_task_id") for row in purgeable_rows]
            + asset_task_ids
        )

        for task_id in purgeable_task_ids:
            deletion_result = task_manager.delete_task_full(task_id)
            result.setdefault("deleted_task_artifacts", []).append(
                {
                    "task_id": task_id,
                    "success": deletion_result.get("success", False),
                    "deleted_dirs": deletion_result.get("deleted_dirs", []),
                }
            )
            result.setdefault("task_cleanup_errors", []).extend(deletion_result.get("errors", []))

        if purgeable_task_ids:
            await _asyncio.to_thread(repository.delete_translation_tasks, purgeable_task_ids)

        await _asyncio.to_thread(repository.delete_rows_for_papers, "papers", purgeable_ids)
        result["purged_records"] = len(purgeable_ids)
    except Exception as e:
        msg = f"[StaleCleanup] Unexpected error: {e}"
        logger.error(msg, exc_info=True)
        result["errors"].append(msg)

    logger.info("[StaleCleanup] Done: %s", result)
    return result


async def fail_interrupted_translation_tasks() -> dict:
    """
    重启时将中断的排队/待处理/进行中翻译任务标记为失败。

    同时清理本地任务产物并更新受影响的社区论文状态。
    """
    result = {"failed_tasks": 0, "updated_papers": 0, "cleaned_task_artifacts": 0, "errors": []}
    repository = get_translation_task_repository()
    task_manager = get_task_manager()

    try:
        from backend.app.services.paper_service import mark_paper_translation_failed_by_task

        active_ids = _dedupe_non_empty(repository.list_task_ids_by_status(INTERRUPTED_TASK_STATUSES))
        locally_updated_papers = 0
        now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        handled_task_ids: Set[str] = set()

        if active_ids:
            for task_id in active_ids:
                deletion_result = task_manager.delete_task_full(task_id)
                if deletion_result.get("success"):
                    result["cleaned_task_artifacts"] += 1
                result.setdefault("task_cleanup_errors", []).extend(deletion_result.get("errors", []))

            result["failed_tasks"] = repository.update_tasks(
                active_ids,
                {
                    "status": "failed",
                    "progress": 100,
                    "message": "Task interrupted by backend restart",
                    "error": "Task interrupted by backend restart",
                    "detail_code": "task_interrupted_restart",
                    "completed_at": now,
                },
            )

            for task_id in active_ids:
                handled_task_ids.add(task_id)
                locally_updated_papers += await mark_paper_translation_failed_by_task(task_id)

        try:
            community_repository = get_community_paper_repository()
            stale_rows = await asyncio.to_thread(community_repository.list_inflight_translation_papers)
        except DatabaseUnavailableError:
            stale_rows = []
        except Exception as exc:
            logger.warning("[RestartFailover] Failed to load inflight local papers: %s", exc)
            stale_rows = []

        if stale_rows:
            stale_task_ids = _dedupe_non_empty([row.get("community_selected_task_id") for row in stale_rows])
            terminal_failed_statuses = {"failed", "failed_compilation", "structure_invalid"}
            failed_task_ids = [
                task_id
                for task_id, status in repository.list_task_statuses(stale_task_ids).items()
                if status in terminal_failed_statuses
            ]
            for task_id in failed_task_ids:
                if task_id in handled_task_ids:
                    continue
                handled_task_ids.add(task_id)
                locally_updated_papers += await mark_paper_translation_failed_by_task(task_id)

        result["updated_papers"] = locally_updated_papers
    except Exception as exc:
        msg = f"[RestartFailover] Unexpected error: {exc}"
        logger.error(msg, exc_info=True)
        result["errors"].append(msg)

    logger.info("[RestartFailover] Done: %s", result)
    return result


@app.on_event("startup")
async def startup_event():
    """应用启动事件处理器：初始化任务队列、恢复中断任务、启动后台循环"""
    set_runtime_shutting_down(False)
    runtime_role = str(getattr(settings, "backend_runtime_role", "all") or "all").strip().lower()
    if runtime_role == "worker":
        runtime_pressure.apply_worker_process_priority()
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info(f"CORS origins: {settings.cors_origins}")
    logger.info(f"Backend runtime role: {runtime_role}")
    logger.warning(
        "Task runtime state is still partially in-process memory; "
        "run a single worker in production until full runtime-state externalization is implemented."
    )
    app.state.cleanup_task = None
    app.state.admin_job_poll_task = None
    app.state.public_feed_rebuild_task = None
    app.state.arxiv_metadata_repair_task = None
    app.state.hot_ranking_cron_task = None

    # 初始化任务队列
    import backend.app.services.task_manager as tm_module
    from backend.app.services.task_manager import TaskQueue
    tq = TaskQueue(max_concurrent=settings.max_concurrent_translations)
    await tq.initialize()
    tm_module.task_queue = tq
    logger.info(f"[Startup] TaskQueue initialized (max_concurrent={settings.max_concurrent_translations})")

    if runtime_role in {"all", "worker"}:
        await fail_interrupted_translation_tasks()
        if runtime_role == "all":
            await reset_stale_community_tasks()
        else:
            logger.info(
                "[Startup] Worker role completed interrupted-task reconciliation and skipped stale paper cleanup."
            )

    if runtime_role in {"all", "worker"}:
        from backend.app.services import paper_service

        async def _poll_admin_jobs():
            while True:
                try:
                    await paper_service.resume_pending_admin_curation_jobs()
                    await paper_service.resume_pending_delete_jobs()
                except Exception as exc:
                    logger.warning("[Startup] Failed to poll community admin jobs: %s", exc)
                await asyncio.sleep(max(1.0, float(getattr(settings, "admin_job_poll_interval_seconds", 5.0) or 5.0)))

        app.state.admin_job_poll_task = asyncio.create_task(_poll_admin_jobs())
        logger.info("[Startup] Admin job polling started")

        public_feed_rebuild_interval_seconds = max(
            0.0,
            float(getattr(settings, "community_feed_rebuild_interval_seconds", 300.0) or 0.0),
        )
        if public_feed_rebuild_interval_seconds > 0:
            async def _repair_public_feed_indexes():
                while True:
                    try:
                        await paper_service.rebuild_public_feed_indexes_if_enabled()
                    except Exception as exc:
                        logger.warning("[Startup] Failed to rebuild shared public feed indexes: %s", exc)
                    await asyncio.sleep(public_feed_rebuild_interval_seconds)

            app.state.public_feed_rebuild_task = asyncio.create_task(_repair_public_feed_indexes())
            logger.info(
                "[Startup] Public feed index rebuild loop started (interval=%ss)",
                public_feed_rebuild_interval_seconds,
            )

        arxiv_metadata_repair_interval_seconds = max(
            0.0,
            float(getattr(settings, "community_arxiv_metadata_repair_interval_seconds", 1800.0) or 0.0),
        )
        arxiv_metadata_repair_limit = max(
            1,
            int(getattr(settings, "community_arxiv_metadata_repair_limit", 20) or 20),
        )
        if arxiv_metadata_repair_interval_seconds > 0:
            async def _repair_arxiv_metadata_loop():
                while True:
                    try:
                        await paper_service.repair_published_arxiv_metadata(
                            limit=arxiv_metadata_repair_limit,
                        )
                    except Exception as exc:
                        logger.warning("[Startup] Failed to repair published arXiv metadata: %s", exc)
                    await asyncio.sleep(arxiv_metadata_repair_interval_seconds)

            app.state.arxiv_metadata_repair_task = asyncio.create_task(_repair_arxiv_metadata_loop())
            logger.info(
                "[Startup] arXiv metadata repair loop started (interval=%ss, limit=%s)",
                arxiv_metadata_repair_interval_seconds,
                arxiv_metadata_repair_limit,
            )

        # Hot ranking daily cron
        hot_ranking_cron_enabled = bool(getattr(settings, "hot_ranking_cron_enabled", True))
        if hot_ranking_cron_enabled:
            from backend.app.core import timezone_utils

            async def _hot_ranking_daily_cron():
                """每日热门排行定时任务：刷新排名、自动收录新论文、写入摘要"""
                while True:
                    # 计算距离下一次 CST 触发时间的秒数
                    now_cst = timezone_utils.get_cst_now()
                    hour = int(getattr(settings, "hot_ranking_cron_hour", 3) or 3)
                    minute = int(getattr(settings, "hot_ranking_cron_minute", 7) or 7)

                    # 下一次 CST 触发时间
                    next_trigger = now_cst.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_trigger <= now_cst:
                        from datetime import timedelta

                        next_trigger += timedelta(days=1)

                    wait_seconds = (next_trigger - now_cst).total_seconds()
                    # 最多等待 24 小时，最少 60 秒
                    wait_seconds = max(60.0, min(wait_seconds, 86400.0))

                    logger.info(
                        "[Startup] Hot ranking daily cron: next run at %s CST (in %.0f seconds)",
                        next_trigger.strftime("%Y-%m-%d %H:%M:%S"),
                        wait_seconds,
                    )
                    await asyncio.sleep(wait_seconds)
                    try:
                        await paper_service.run_hot_ranking_daily_cron()
                    except Exception as exc:
                        logger.warning("[Startup] Hot ranking daily cron failed: %s", exc)

            app.state.hot_ranking_cron_task = asyncio.create_task(_hot_ranking_daily_cron())
            logger.info("[Startup] Hot ranking daily cron started")

    if runtime_role != "all":
        # 为所有运行时角色写入 RAG 术语数据
        await _seed_rag_terminology()
        return

    # 孤立任务清理在启动时运行一次，之后定期运行
    from backend.app.services.task_manager import task_manager as _tm
    from pathlib import Path as _Path
    import shutil as _shutil
    import time as _time

    cleanup_interval = 30 * 60  # 30 minutes

    async def _run_cleanup():
        """
        状态无关的孤立任务清理。

        扫描 data/outputs 和 data/terms 目录中超过 guest_task_ttl_hours 的目录。
        在本地翻译任务持久化存储中找不到的 task_id 视为孤立任务并删除。
        如果本地翻译任务存储不可达，则跳过整个删除过程以防止意外数据丢失。
        """
        import asyncio as _asyncio2
        try:
            outputs_dir = _Path(settings.outputs_dir)
            terms_dir   = _Path(settings.data_dir) / "terms"
            ttl_seconds = settings.guest_task_ttl_hours * 3600
            now = _time.time()

            # 1. 从两个扫描目录中收集超过 TTL 的目录
            old_task_ids: set = set()
            for scan_dir in [outputs_dir, terms_dir]:
                if not scan_dir.exists():
                    continue
                for entry in scan_dir.iterdir():
                    if not entry.is_dir():
                        continue
                    try:
                        age = now - entry.stat().st_mtime
                        if age >= ttl_seconds:
                            old_task_ids.add(entry.name)
                    except OSError:
                        pass

            if not old_task_ids:
                logger.debug("[OrphanedCleanup] No old directories found, skipping.")
                return

            # 2. 批量查询本地持久化存储，找出哪些 task_id 仍在数据库中
            repository = get_translation_task_repository()
            try:
                db_task_ids = set(
                    await _asyncio2.to_thread(
                        repository.list_existing_task_ids,
                        list(old_task_ids),
                    )
                )
            except Exception as db_err:
                logger.warning(
                    f"[OrphanedCleanup] Local translation-task query failed ({db_err}) - "
                    "skipping deletion to prevent accidental data loss."
                )
                return


            # 3. 删除数据库中不存在的 task_id 对应的目录（孤立任务）
            orphaned = old_task_ids - db_task_ids
            if not orphaned:
                logger.debug("[OrphanedCleanup] No orphaned tasks found.")
                return

            logger.info(f"[OrphanedCleanup] Found {len(orphaned)} orphaned task(s) to delete.")
            for task_id in orphaned:
                for base_dir in [outputs_dir, terms_dir]:
                    target = base_dir / task_id
                    if target.exists():
                        try:
                            _shutil.rmtree(target)
                            logger.info(f"[OrphanedCleanup] Deleted: {target}")
                        except Exception as rm_err:
                            logger.error(f"[OrphanedCleanup] Failed to delete {target}: {rm_err}")
                # 同时从内存缓存中驱逐（如果存在）
                _tm._tasks.pop(task_id, None)

        except Exception as e:
            logger.error(f"[OrphanedCleanup] Unexpected error during cleanup: {e}", exc_info=True)

    async def cleanup_loop():
        """孤立任务清理循环：启动时立即运行一次，之后定期执行"""
        # --- 启动时立即运行一次 ---
        logger.info("[OrphanedCleanup] Running initial cleanup on startup...")
        await _run_cleanup()

        # --- 之后定期运行 ---
        while True:
            await asyncio.sleep(cleanup_interval)
            logger.info("[OrphanedCleanup] Running scheduled cleanup...")
            await _run_cleanup()

            # 同时刷新过期的内存驻留游客任务（补充清理）
            try:
                from backend.app.services.task_manager import guest_tracker
                expired_ids = guest_tracker.get_expired_task_ids()
                for task_id in expired_ids:
                    _tm._tasks.pop(task_id, None)
                    guest_tracker.remove(task_id)
                if expired_ids:
                    logger.info(f"[GuestCleanup] Evicted {len(expired_ids)} in-memory guest task(s)")
            except Exception as e:
                logger.error(f"[GuestCleanup] Error flushing in-memory tasks: {e}", exc_info=True)

    app.state.cleanup_task = asyncio.create_task(cleanup_loop())
    logger.info("[Startup] Orphaned-task cleanup started (runs on startup + every 30 min)")

    # Seed RAG terminology for "all" runtime role
    await _seed_rag_terminology()




@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件处理器：取消所有后台任务，优雅退出"""
    set_runtime_shutting_down(True)
    public_feed_rebuild_task = getattr(app.state, 'public_feed_rebuild_task', None)
    if public_feed_rebuild_task:
        public_feed_rebuild_task.cancel()
        try:
            await public_feed_rebuild_task
        except asyncio.CancelledError:
            pass
    arxiv_metadata_repair_task = getattr(app.state, 'arxiv_metadata_repair_task', None)
    if arxiv_metadata_repair_task:
        arxiv_metadata_repair_task.cancel()
        try:
            await arxiv_metadata_repair_task
        except asyncio.CancelledError:
            pass
    admin_job_poll_task = getattr(app.state, 'admin_job_poll_task', None)
    if admin_job_poll_task:
        admin_job_poll_task.cancel()
        try:
            await admin_job_poll_task
        except asyncio.CancelledError:
            pass
    cleanup_task = getattr(app.state, 'cleanup_task', None)
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    hot_ranking_cron_task = getattr(app.state, "hot_ranking_cron_task", None)
    if hot_ranking_cron_task:
        hot_ranking_cron_task.cancel()
        try:
            await hot_ranking_cron_task
        except asyncio.CancelledError:
            pass
    logger.info(f"Shutting down {settings.app_name}")


@api_router.post("/admin/cleanup", tags=["admin"])
async def admin_cleanup_stale_tasks(_admin: dict = Depends(require_admin_request)):
    """
    手动触发过期任务清理和重启故障转移协调。
    """
    failover_result = await fail_interrupted_translation_tasks()
    cleanup_result = await reset_stale_community_tasks()
    errors = list(cleanup_result.get("errors", [])) + list(failover_result.get("errors", []))
    return {"ok": not errors, **cleanup_result, **failover_result, "errors": errors}


@api_router.get("/health")
async def health_check():
    """
    健康检查端点

    返回：
        应用状态信息
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "llm_model": settings.llm_model
    }


@api_router.get("/")
async def root():
    """
    根路径端点

    返回：
        欢迎信息和 API 入口说明
    """
    return {
        "message": "PaperX Backend API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/api/health"
    }


@api_router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    处理 favicon.ico 请求，防止日志中出现 404 错误
    """
    return Response(content="", media_type="image/x-icon")


# 导入并注册 API 路由
from backend.app.api.routes import auth, arxiv, upload, task, translate, download, history, papers, community_agent, pdf_direct
from backend.app.api.routes import settings as settings_routes
from backend.app.api.routes import terminology

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(arxiv.router, tags=["arxiv"])
api_router.include_router(translate.router, tags=["translate"])
api_router.include_router(task.router, tags=["task"])
api_router.include_router(download.router, tags=["download"])
api_router.include_router(settings_routes.router, tags=["settings"])
api_router.include_router(history.router, tags=["history"])
api_router.include_router(papers.router, tags=["papers"])
api_router.include_router(community_agent.router, tags=["community-agent"])
api_router.include_router(terminology.router, tags=["terminology"])
api_router.include_router(pdf_direct.router, tags=["pdf-direct"])
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )

