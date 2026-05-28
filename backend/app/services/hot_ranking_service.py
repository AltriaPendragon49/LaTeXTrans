"""热门排序服务 - 编排每日热门排序流水线

步骤:
  1. run_ranking_cycle  - 通过排序引擎对候选论文进行排序并写入产物
  2. filter_existing_papers - 查询数据库过滤已存在的论文
  3. auto_intake         - 通过管理策展自动收录排名靠前的候选
  4. generate_daily_summary - 写入每日收录摘要
  5. run_full_cycle      - 依次执行以上所有步骤
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import get_settings
from backend.app.services.ranking.engine import rank_candidates
from backend.app.services.ranking.schemas import (
    DailyIntakeSummary,
    RankedCandidate,
    RankResult,
    ScoreBreakdown,
    SourceEvidence,
)
from backend.app.services.ranking.artifact_writer import (
    utc_now_iso,
    write_daily_intake_artifacts,
    write_window_artifacts,
)
from backend.app.core.timezone_utils import get_cst_now

logger = logging.getLogger(__name__)

# ── 演示/合成数据生成器 ──────────────────────────────────────────────

_DEMO_ARXIV_IDS = [
    "2501.12345",
    "2502.23456",
    "2503.34567",
    "2504.45678",
    "2505.56789",
    "2501.09876",
    "2502.98765",
    "2503.87654",
    "2504.76543",
    "2505.65432",
    "2401.11111",
    "2402.22222",
    "2403.33333",
    "2404.44444",
    "2405.55555",
    "2406.66666",
    "2407.77777",
    "2408.88888",
    "2409.99999",
    "2410.00000",
    "2311.13579",
    "2312.24680",
    "2301.11223",
    "2302.33445",
    "2303.55667",
]


def _pub_date_from_arxiv_id(arxiv_id: str) -> str:
    """从 arXiv ID 推断 ISO 格式的发布日期，如 2501.12345 -> 2025-01-15T00:00:00Z"""
    parts = arxiv_id.split(".")
    if len(parts) >= 2 and len(parts[0]) == 4:
        yy = int(parts[0][:2])
        mm = int(parts[0][2:])
        year = 2000 + yy
        if 1 <= mm <= 12:
            return f"{year:04d}-{mm:02d}-15T00:00:00Z"
    return "2025-01-15T00:00:00Z"


def _generate_demo_candidates(window: str = "30d") -> list[dict]:
    """生成合成候选数据供排序引擎使用

    当源数据适配器不可用时的回退方案。
    发布日期分布在最近几天，确保能通过窗口过滤。
    """
    from random import Random

    rng = Random(42)
    now = datetime.now(timezone.utc)
    candidates: list[dict] = []
    for idx, arxiv_id in enumerate(_DEMO_ARXIV_IDS):
        # 将候选分散到最近 60 天，确保每个窗口都有数据
        days_ago = rng.uniform(0, 60)
        pub_dt = now - timedelta(days=days_ago)
        pub_date = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_attention = rng.uniform(0, 500)
        raw_authority = rng.uniform(0, 300)
        raw_implementation = rng.uniform(0, 200)
        raw_local = rng.uniform(0, 100)

        candidates.append({
            "arxiv_id": arxiv_id,
            "title": f"Demo Paper {idx + 1}: Advances in Machine Learning",
            "authors": ["Author A", "Author B"],
            "categories": ["cs.LG", "cs.AI"],
            "publication_date": pub_date,
            "raw_attention": raw_attention,
            "raw_authority": raw_authority,
            "raw_implementation": raw_implementation,
            "raw_local": raw_local,
        })
    return candidates


# ── 服务类 ───────────────────────────────────────────────────────────


class HotRankingService:
    """编排热门排序流水线：排序 -> 过滤 -> 收录 -> 摘要"""

    def __init__(self, settings=None):
        """初始化热门排序服务

        参数:
            settings: 配置对象（可选，默认使用全局配置）
        """
        self.settings = settings or get_settings()
        self._intaken_in_run: set[str] = set()  # 内存中去重，防止同一次运行重复收录

    # ── 辅助方法 ────────────────────────────────────────────────────

    def _get_arxiv_id_dir(self) -> Path:
        """获取热门排序产物的基础输出目录"""
        raw = getattr(self.settings, "hot_ranking_arxiv_id_dir", "") or ""
        if raw:
            return Path(raw)
        # 默认: backend/arxiv_id/hot_ranked
        return Path(__file__).resolve().parent.parent.parent / "arxiv_id" / "hot_ranked"

    def _exported_at(self) -> str:
        """返回当前 UTC 时间戳的 ISO 字符串"""
        return utc_now_iso()

    # ── 步骤 1: 排序 ────────────────────────────────────────────────

    async def run_ranking_cycle(self, window: str | None = None) -> RankResult:
        """运行排序引擎并写入窗口产物

        1. 尝试通过源适配器获取真实候选（失败则回退到演示数据）
        2. 调用 engine.rank_candidates()
        3. 写入窗口产物
        4. 返回 RankResult
        """
        active_window = window or getattr(self.settings, "hot_ranking_auto_intake_default_window", "3d") or "3d"
        exported_at = self._exported_at()
        raw_candidates: list[dict] = []

        # --- 尝试使用真实源适配器 ---
        try:
            from backend.app.services.ranking.source_adapters import collect_candidates_from_sources

            # 从 alphaXiv 热门流和所有源适配器收集真实候选
            source_candidates = await collect_candidates_from_sources(
                limit=200,
                timeout=120,
                retries=3,
            )
            if source_candidates:
                raw_candidates = source_candidates
                logger.info(
                    "Hot ranking: collected %d candidates from live source adapters",
                    len(raw_candidates),
                )
        except Exception as exc:
            logger.warning(
                "Hot ranking: source adapters failed, falling back to demo data: %s", exc
            )

        # --- 回退到演示数据 ---
        if not raw_candidates:
            logger.info("Hot ranking: using demo/synthetic candidate data")
            raw_candidates = _generate_demo_candidates(window=active_window)

        # --- 排序 ---
        ranked = rank_candidates(raw_candidates, window=active_window)

        # --- 写入产物 ---
        base_dir = self._get_arxiv_id_dir()
        try:
            paths = write_window_artifacts(ranked, window=active_window, base_dir=base_dir, exported_at=exported_at)
            logger.info(
                "Hot ranking: wrote %d candidates to %s and %s",
                len(ranked),
                paths["json"],
                paths["md"],
            )
        except Exception as exc:
            logger.error("Hot ranking: failed to write window artifacts: %s", exc)

        return RankResult(
            window=active_window,
            candidates=ranked,
            exported_at=exported_at,
            total_count=len(ranked),
        )

    # ── 步骤 2: 过滤已存在论文 ─────────────────────────────────────

    async def filter_existing_papers(
        self, candidates: list[RankedCandidate]
    ) -> tuple[list[RankedCandidate], list[dict]]:
        """查询数据库过滤已存在的论文

        对每个候选检查:
        - get_paper_by_arxiv_id() -> 若找到，论文已存在
        - list_curation_jobs_for_arxiv_id() -> 若活跃任务存在，跳过

        返回: (新候选列表, 已跳过信息列表)

        注意: 使用 try/except 处理数据库访问。若数据库不可用，记录警告
        并将所有候选标记为新候选，跳过列表为空。
        """
        new_candidates: list[RankedCandidate] = []
        skipped_info: list[dict] = []

        try:
            from backend.app.services.paper_service import get_community_paper_repository

            repository = get_community_paper_repository()
        except Exception as exc:
            logger.warning(
                "Hot ranking: cannot access paper repository, skipping DB filter: %s", exc
            )
            return list(candidates), []

        for candidate in candidates:
            try:
                # 检查论文是否已存在于数据库
                paper_row = await asyncio.to_thread(
                    repository.get_paper_by_arxiv_id, candidate.arxiv_id
                )
                if paper_row is not None:
                    skipped_info.append({
                        "arxiv_id": candidate.arxiv_id,
                        "reason": "already_in_library",
                        "paper_id": paper_row.get("id", ""),
                    })
                    continue

                # 检查是否存在活跃的策展任务
                curation_jobs = await asyncio.to_thread(
                    repository.list_curation_jobs_for_arxiv_id, candidate.arxiv_id
                )
                active_statuses = {"queued", "processing", "translating", "publishing", "pending"}
                has_active_job = any(
                    job.get("status", "").lower() in active_statuses
                    for job in (curation_jobs or [])
                )
                if has_active_job:
                    skipped_info.append({
                        "arxiv_id": candidate.arxiv_id,
                        "reason": "active_curation_job_exists",
                    })
                    continue

                new_candidates.append(candidate)

            except Exception as exc:
                logger.warning(
                    "Hot ranking: DB check failed for %s, treating as new: %s",
                    candidate.arxiv_id,
                    exc,
                )
                new_candidates.append(candidate)

        logger.info(
            "Hot ranking: %d new, %d skipped (already existing)",
            len(new_candidates),
            len(skipped_info),
        )
        return new_candidates, skipped_info

    # ── 步骤 3-4: 自动收录 ──────────────────────────────────────────

    async def auto_intake(
        self, candidates: list[RankedCandidate]
    ) -> dict[str, Any]:
        """通过管理策展自动收录排名靠前的候选

        1. 按配置中的 min_score 过滤
        2. 取配置中的 top_n 条
        3. 通过现有管理策展批量路径提交符合条件的 arXiv ID
        4. 返回收录结果字典

        使用延迟导入以避免循环依赖。
        """
        min_score = float(getattr(self.settings, "hot_ranking_auto_intake_min_score", 50.0) or 50.0)
        top_n = int(getattr(self.settings, "hot_ranking_auto_intake_top_n", 20) or 20)

        intaken: list[dict] = []
        skipped: list[dict] = []
        errors: list[dict] = []

        # 过滤与排序
        eligible = [c for c in candidates if c.hot_score >= min_score]
        eligible.sort(key=lambda c: -c.hot_score)
        eligible = eligible[:top_n]

        if not eligible:
            logger.info("Hot ranking auto_intake: no candidates above threshold %.1f", min_score)
            return {"intaken": [], "skipped": [], "errors": []}

        system_user_id = str(getattr(self.settings, "hot_ranking_system_user_id", "") or "").strip()
        if not system_user_id:
            logger.error("Hot ranking auto_intake: HOT_RANKING_SYSTEM_USER_ID is not configured")
            return {
                "intaken": [],
                "skipped": [],
                "errors": [{"arxiv_id": "N/A", "error": "HOT_RANKING_SYSTEM_USER_ID is not configured"}],
            }

        # 延迟导入（避免循环依赖）
        try:
            from backend.app.services.paper_service import (
                _schedule_curation_job,
                submit_admin_arxiv_curation_batch,
            )
        except ImportError as exc:
            logger.error(
                "Hot ranking: cannot import paper_service functions for auto_intake: %s", exc
            )
            return {
                "intaken": [],
                "skipped": [],
                "errors": [{"arxiv_id": "N/A", "error": f"ImportError: {exc}"}],
            }

        selected_candidates: list[RankedCandidate] = []
        for candidate in eligible:
            if candidate.arxiv_id in self._intaken_in_run:
                skipped.append({
                    "arxiv_id": candidate.arxiv_id,
                    "reason": "already_intaken_in_this_run",
                })
                continue
            self._intaken_in_run.add(candidate.arxiv_id)
            selected_candidates.append(candidate)

        if not selected_candidates:
            return {"intaken": [], "skipped": skipped, "errors": []}

        candidate_by_id = {candidate.arxiv_id: candidate for candidate in selected_candidates}
        try:
            batch = await submit_admin_arxiv_curation_batch(
                arxiv_ids=[candidate.arxiv_id for candidate in selected_candidates],
                current_user={"id": system_user_id},
                source_language="en",
                target_language="zh",
                schedule_jobs=False,
            )
        except Exception as exc:
            logger.error("Hot ranking auto_intake: curation batch submission failed: %s", exc, exc_info=True)
            return {
                "intaken": [],
                "skipped": skipped,
                "errors": [
                    {"arxiv_id": candidate.arxiv_id, "error": str(exc)}
                    for candidate in selected_candidates
                ],
            }

        for item in batch.get("items", []) or []:
            try:
                arxiv_id = str(item.get("arxiv_id") or "").strip()
                candidate = candidate_by_id.get(arxiv_id)
                if candidate is None:
                    continue

                logger.info(
                    "Hot ranking auto_intake: %s job_id=%s paper_id=%s",
                    candidate.arxiv_id,
                    item.get("job_id"),
                    item.get("paper_id"),
                )

                try:
                    from backend.app.services.paper_service import get_community_paper_repository

                    repository = get_community_paper_repository()
                    await asyncio.to_thread(
                        repository.update_curation_job,
                        str(item.get("job_id") or ""),
                        {
                            "source_family": "hot_ranking",
                            "hot_score": candidate.hot_score,
                            "score_breakdown": {
                                "attention": candidate.score_breakdown.attention,
                                "authority": candidate.score_breakdown.authority,
                                "implementation": candidate.score_breakdown.implementation,
                                "local": candidate.score_breakdown.local,
                            },
                        },
                    )
                    _schedule_curation_job(str(item.get("job_id") or ""))
                except Exception as exc:
                    logger.warning(
                        "Hot ranking auto_intake: failed to attach score metadata or schedule job %s: %s",
                        item.get("job_id"),
                        exc,
                    )

                intaken.append({
                    "arxiv_id": candidate.arxiv_id,
                    "paper_id": item.get("paper_id") or "",
                    "job_id": item.get("job_id") or "",
                    "title": candidate.title or "",
                    "hot_score": candidate.hot_score,
                    "score_breakdown": {
                        "attention": candidate.score_breakdown.attention,
                        "authority": candidate.score_breakdown.authority,
                        "implementation": candidate.score_breakdown.implementation,
                        "local": candidate.score_breakdown.local,
                    },
                    "selected_reason": candidate.selected_reason,
                    "reused": False,
                    "imported": True,
                })

            except Exception as exc:
                logger.error(
                    "Hot ranking auto_intake: failed for %s: %s",
                    candidate.arxiv_id,
                    exc,
                    exc_info=True,
                )
                errors.append({
                    "arxiv_id": candidate.arxiv_id,
                    "error": str(exc),
                })

        logger.info(
            "Hot ranking auto_intake: intaken=%d, skipped=%d, errors=%d",
            len(intaken),
            len(skipped),
            len(errors),
        )
        return {"intaken": intaken, "skipped": skipped, "errors": errors}

    # ── 步骤 5: 生成每日摘要 ────────────────────────────────────────

    async def generate_daily_summary(
        self,
        rank_result: RankResult,
        intake_result: dict,
    ) -> DailyIntakeSummary:
        """生成每日收录摘要

        构建 DailyIntakeSummary 数据类，通过 write_daily_intake_artifacts 写入产物。
        返回摘要对象。
        """
        now_cst = get_cst_now()
        date_str = now_cst.strftime("%Y-%m-%d")
        exported_at = self._exported_at()

        intaken_papers = intake_result.get("intaken", []) if intake_result else []
        skipped_papers = intake_result.get("skipped", []) if intake_result else []

        total_candidates = len(rank_result.candidates)
        intaken_count = len(intaken_papers)
        below_threshold = sum(
            1 for c in rank_result.candidates
            if c.hot_score < float(getattr(self.settings, "hot_ranking_auto_intake_min_score", 50.0) or 50.0)
        )

        # 统计已存在的论文
        existing_count = total_candidates - intaken_count - below_threshold
        # 同时计入因已存在而被跳过的论文
        already_existing = len([s for s in skipped_papers if s.get("reason") == "already_in_library"])
        existing_count = max(existing_count, already_existing)

        summary = DailyIntakeSummary(
            date=date_str,
            window=rank_result.window,
            triggered_at=exported_at,
            total_candidates=total_candidates,
            existing_count=existing_count,
            below_threshold_count=below_threshold,
            intaken_count=intaken_count,
            intaken_papers=intaken_papers,
            skipped_papers=skipped_papers,
            quality_gate_failures_from_prior_runs=[],
        )

        # 写入产物
        base_dir = self._get_arxiv_id_dir()
        try:
            paths = write_daily_intake_artifacts(summary, base_dir)
            logger.info(
                "Hot ranking: wrote daily intake summary to %s and %s",
                paths["json"],
                paths["md"],
            )
        except Exception as exc:
            logger.error("Hot ranking: failed to write daily intake artifacts: %s", exc)

        return summary

    # ── 完整周期 ────────────────────────────────────────────────────

    async def run_full_cycle(self) -> dict[str, Any]:
        """运行完整的每日排序周期：排序 -> 过滤 -> 收录 -> 摘要

        返回包含用于日志/报告的摘要信息的字典。
        即使某个步骤失败，也始终会写入产物。
        """
        window = (
            getattr(self.settings, "hot_ranking_auto_intake_default_window", "3d")
            or "3d"
        )
        logger.info("Hot ranking daily cycle started for window=%s", window)

        # 步骤 1: 排序
        try:
            rank_result = await self.run_ranking_cycle(window=window)
        except Exception as exc:
            logger.error("Hot ranking: rank cycle failed: %s", exc, exc_info=True)
            return {"status": "error", "step": "rank", "window": window, "error": str(exc)}

        # 步骤 2: 过滤
        try:
            new_candidates, skipped = await self.filter_existing_papers(rank_result.candidates)
        except Exception as exc:
            logger.error("Hot ranking: filter step failed: %s", exc, exc_info=True)
            new_candidates = rank_result.candidates
            skipped = []

        # 步骤 3-4: 收录
        auto_intake_enabled = bool(
            getattr(self.settings, "hot_ranking_auto_intake_enabled", True)
        )
        intake_result: dict = {}
        if auto_intake_enabled and new_candidates:
            try:
                intake_result = await self.auto_intake(new_candidates)
            except Exception as exc:
                logger.error("Hot ranking: auto_intake failed: %s", exc, exc_info=True)
                intake_result = {"intaken": [], "skipped": [], "errors": [{"error": str(exc)}]}

        # 步骤 5: 摘要
        try:
            summary = await self.generate_daily_summary(rank_result, intake_result)
        except Exception as exc:
            logger.error("Hot ranking: summary generation failed: %s", exc, exc_info=True)
            return {
                "status": "partial",
                "window": window,
                "ranked": len(rank_result.candidates),
                "intaken": 0,
                "error": str(exc),
            }

        return {
            "status": "completed",
            "window": window,
            "ranked": len(rank_result.candidates),
            "new_candidates": len(new_candidates),
            "skipped_existing": len(skipped),
            "intaken": summary.intaken_count,
            "date": summary.date,
        }
