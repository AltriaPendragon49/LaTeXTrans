from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Optional
from uuid import uuid4

from backend.app.db import DatabaseUnavailableError, db_connection, get_database_dialect

PAPER_COLUMNS = (
    "id",
    "created_by",
    "source",
    "arxiv_id",
    "title",
    "authors",
    "categories",
    "abstract_raw",
    "abstract_translated",
    "visibility",
    "status",
    "community_status",
    "trans_status",
    "trans_latest_task_id",
    "trans_latest_asset_pdf_id",
    "community_selected_task_id",
    "community_selected_asset_id",
    "like_count",
    "favorite_count",
    "comment_count",
    "view_count",
    "download_count",
    "hot_score",
    "arxiv_published_at",
    "official_published_at",
    "created_at",
    "updated_at",
)

PAPER_ASSET_COLUMNS = (
    "id",
    "paper_id",
    "task_id",
    "asset_type",
    "storage_backend",
    "file_path",
    "file_name",
    "mime_type",
    "is_latest",
    "created_at",
)

STRUCTURED_INSIGHT_COLUMNS = (
    "paper_id",
    "section_key",
    "content",
    "status",
    "updated_at",
)

SIMILAR_RECOMMENDATION_COLUMNS = (
    "paper_id",
    "position",
    "arxiv_id",
    "title",
    "abstract",
    "arxiv_url",
    "community_paper_id",
    "link_type",
    "updated_at",
)

CURATION_JOB_COLUMNS = (
    "job_id",
    "batch_id",
    "paper_id",
    "published_paper_id",
    "source_type",
    "arxiv_id",
    "original_filename",
    "source_path",
    "task_id",
    "source_language",
    "target_language",
    "status",
    "terminal_task_status",
    "terminal_reason",
    "timeout_reason",
    "error",
    "failed_artifact_path",
    "artifact_storage_backend",
    "source_family",
    "hot_score",
    "score_breakdown",
    "created_by",
    "created_at",
    "updated_at",
)

DELETE_JOB_COLUMNS = (
    "job_id",
    "paper_id",
    "status",
    "attempt_count",
    "last_error",
    "created_by",
    "created_at",
    "updated_at",
)

FAVORITE_FOLDER_COLUMNS = (
    "id",
    "user_id",
    "name",
    "created_at",
    "updated_at",
)


class FavoriteFolderLimitError(ValueError):
    """当用户超出收藏夹数量上限时抛出。"""


class FavoriteFolderNameConflictError(ValueError):
    """当收藏夹名称对同一用户已存在时抛出。"""


class FavoriteFolderNotFoundError(LookupError):
    """当收藏夹不存在或不属于当前用户时抛出。"""

_PAPER_JSON_COLUMNS = {"authors", "categories"}
_DELETE_JOB_INT_COLUMNS = {"attempt_count"}
_PAPER_INT_COLUMNS = {
    "like_count",
    "favorite_count",
    "comment_count",
    "view_count",
    "download_count",
}


def _utc_now_naive() -> datetime:
    """获取当前UTC时间，去除时区信息和微秒。"""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _business_day_utc8() -> str:
    """获取UTC+8时区的当前日期字符串（用于按天统计）。"""
    return datetime.now(timezone(timedelta(hours=8))).date().isoformat()


def _placeholder(_index: int) -> str:
    """根据数据库方言返回对应的参数占位符（SQLite: ?，MySQL: %s）。"""
    return "?" if get_database_dialect() == "sqlite" else "%s"


def _fetchone(cursor) -> Optional[dict[str, Any]]:
    """从游标获取一行数据并转换为字典格式返回。"""
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _fetchall(cursor) -> list[dict[str, Any]]:
    """从游标获取所有行数据并转换为字典列表返回。"""
    rows = cursor.fetchall() or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(dict(row))
        else:
            normalized.append({key: row[key] for key in row.keys()})
    return normalized


def _decode_json_list(value: Any) -> list[Any]:
    """将存储的JSON数据解码为列表格式。"""
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return list(parsed) if isinstance(parsed, list) else []
    return []


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """对字符串列表去重并保持原有顺序。"""
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        normalized = str(raw or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


class CommunityPaperRepository:
    """社区论文数据访问层，管理论文、资产、精选推荐、收藏夹及点赞浏览等操作。"""

    def _normalize_paper_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的论文记录格式，解析JSON字段和整数字段。"""
        if row is None:
            return None

        normalized = dict(row)
        for column in PAPER_COLUMNS:
            value = normalized.get(column)
            if column in _PAPER_JSON_COLUMNS:
                normalized[column] = _decode_json_list(value)
            elif column in _PAPER_INT_COLUMNS and value is not None:
                normalized[column] = int(value)
            else:
                normalized[column] = value
        return normalized

    def _normalize_asset_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的论文资产记录格式。"""
        if row is None:
            return None
        normalized = dict(row)
        normalized["is_latest"] = bool(normalized.get("is_latest"))
        return normalized

    def _serialize_paper_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        """将论文更新载荷序列化为适合数据库存储的格式（JSON列转为字符串）。"""
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in PAPER_COLUMNS:
                continue
            if key in _PAPER_JSON_COLUMNS:
                serialized[key] = json.dumps(list(value or []), ensure_ascii=False)
            elif key in _PAPER_INT_COLUMNS and value is not None:
                serialized[key] = int(value)
            else:
                serialized[key] = value
        return serialized

    def _serialize_asset_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        """将资产更新载荷序列化为适合数据库存储的格式。"""
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in PAPER_ASSET_COLUMNS:
                continue
            if key == "is_latest" and value is not None:
                serialized[key] = bool(value)
            else:
                serialized[key] = value
        return serialized

    def _normalize_structured_insight_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的结构化洞察记录格式。"""
        if row is None:
            return None

        normalized = dict(row)
        for column in STRUCTURED_INSIGHT_COLUMNS:
            normalized[column] = normalized.get(column)
        return normalized

    def _serialize_structured_insight_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        """将结构化洞察更新载荷序列化为适合数据库存储的格式。"""
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in STRUCTURED_INSIGHT_COLUMNS:
                continue
            serialized[key] = value
        return serialized

    def _normalize_similar_recommendation_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的相似推荐记录格式。"""
        if row is None:
            return None

        normalized = dict(row)
        for column in SIMILAR_RECOMMENDATION_COLUMNS:
            value = normalized.get(column)
            if column == "position" and value is not None:
                normalized[column] = int(value)
            else:
                normalized[column] = value
        return normalized

    def _serialize_similar_recommendation_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        """将相似推荐更新载荷序列化为适合数据库存储的格式。"""
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in SIMILAR_RECOMMENDATION_COLUMNS:
                continue
            if key == "position" and value is not None:
                serialized[key] = int(value)
            else:
                serialized[key] = value
        return serialized

    def _normalize_curation_job_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的策划任务记录格式，解析评分字段。"""
        if row is None:
            return None
        normalized = dict(row)
        if normalized.get("hot_score") is not None:
            normalized["hot_score"] = float(normalized["hot_score"])
        if "score_breakdown" in normalized:
            value = normalized.get("score_breakdown")
            if isinstance(value, (bytes, bytearray)):
                value = value.decode("utf-8")
            if isinstance(value, str):
                try:
                    normalized["score_breakdown"] = json.loads(value)
                except json.JSONDecodeError:
                    normalized["score_breakdown"] = {}
        return normalized

    def _serialize_curation_job_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        """将策划任务更新载荷序列化为适合数据库存储的格式。"""
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in CURATION_JOB_COLUMNS:
                continue
            if key == "hot_score" and value is not None:
                serialized[key] = float(value)
            elif key == "score_breakdown" and value is not None:
                serialized[key] = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            else:
                serialized[key] = value
        return serialized

    def _normalize_delete_job_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的删除任务记录格式。"""
        if row is None:
            return None
        normalized = dict(row)
        for column in DELETE_JOB_COLUMNS:
            value = normalized.get(column)
            if column in _DELETE_JOB_INT_COLUMNS and value is not None:
                normalized[column] = int(value)
            else:
                normalized[column] = value
        return normalized

    def _serialize_delete_job_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        """将删除任务更新载荷序列化为适合数据库存储的格式。"""
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in DELETE_JOB_COLUMNS:
                continue
            if key in _DELETE_JOB_INT_COLUMNS and value is not None:
                serialized[key] = int(value)
            else:
                serialized[key] = value
        return serialized

    def _normalize_favorite_folder_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的收藏夹记录格式。"""
        if row is None:
            return None
        normalized = dict(row)
        for column in FAVORITE_FOLDER_COLUMNS:
            normalized[column] = normalized.get(column)
        if normalized.get("paper_count") is not None:
            normalized["paper_count"] = int(normalized["paper_count"])
        return normalized

    def _refresh_like_count(self, cursor, *, paper_id: str) -> int:
        """刷新指定论文的点赞计数，从paper_likes表重新计算并更新。"""
        cursor.execute(
            "select count(*) as total from paper_likes where paper_id = " + _placeholder(0),
            (paper_id,),
        )
        total = int((_fetchone(cursor) or {}).get("total") or 0)
        cursor.execute(
            (
                "update papers set like_count = "
                + _placeholder(0)
                + ", updated_at = "
                + _placeholder(1)
                + " where id = "
                + _placeholder(2)
            ),
            (total, _utc_now_naive().isoformat(), paper_id),
        )
        return total

    def _refresh_favorite_count(self, cursor, *, paper_id: str) -> int:
        """刷新指定论文的收藏计数，从paper_favorites表重新计算并更新。"""
        cursor.execute(
            "select count(*) as total from paper_favorites where paper_id = " + _placeholder(0),
            (paper_id,),
        )
        total = int((_fetchone(cursor) or {}).get("total") or 0)
        cursor.execute(
            (
                "update papers set favorite_count = "
                + _placeholder(0)
                + ", updated_at = "
                + _placeholder(1)
                + " where id = "
                + _placeholder(2)
            ),
            (total, _utc_now_naive().isoformat(), paper_id),
        )
        return total

    def _sync_paper_favorite_marker(self, cursor, *, paper_id: str, user_id: str) -> bool:
        """同步论文的收藏标记：如果用户在任意收藏夹中有此文则标记为已收藏，否则移除标记。"""
        cursor.execute(
            (
                "select 1 from favorite_folder_papers membership "
                "inner join favorite_folders folders on folders.id = membership.folder_id "
                "where folders.user_id = "
                + _placeholder(0)
                + " and membership.paper_id = "
                + _placeholder(1)
                + " limit 1"
            ),
            (user_id, paper_id),
        )
        has_membership = _fetchone(cursor) is not None
        if has_membership:
            cursor.execute(
                (
                    "select 1 from paper_favorites where paper_id = "
                    + _placeholder(0)
                    + " and user_id = "
                    + _placeholder(1)
                    + " limit 1"
                ),
                (paper_id, user_id),
            )
            if _fetchone(cursor) is None:
                cursor.execute(
                    (
                        "insert into paper_favorites (paper_id, user_id, created_at) values ("
                        + _placeholder(0)
                        + ", "
                        + _placeholder(1)
                        + ", "
                        + _placeholder(2)
                        + ")"
                    ),
                    (paper_id, user_id, _utc_now_naive().isoformat()),
                )
        else:
            cursor.execute(
                (
                    "delete from paper_favorites where paper_id = "
                    + _placeholder(0)
                    + " and user_id = "
                    + _placeholder(1)
                ),
                (paper_id, user_id),
            )
        return has_membership

    def get_paper_by_id(self, paper_id: str) -> Optional[dict[str, Any]]:
        """根据论文ID获取论文记录。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + f" from papers where id = {_placeholder(0)} limit 1"
                ),
                (paper_id,),
            )
            return self._normalize_paper_row(_fetchone(cursor))

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[dict[str, Any]]:
        """根据arXiv ID获取论文记录。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + f" from papers where arxiv_id = {_placeholder(0)} limit 1"
                ),
                (arxiv_id,),
            )
            return self._normalize_paper_row(_fetchone(cursor))

    def get_paper_by_title(
        self,
        *,
        title: str,
        source: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """根据论文标题查找论文记录，可选的source参数用于过滤来源。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            params: list[Any] = [title, "removed"]
            sql = (
                "select "
                + ", ".join(PAPER_COLUMNS)
                + f" from papers where title = {_placeholder(0)} and status <> {_placeholder(1)}"
            )
            if source:
                sql += f" and source = {_placeholder(2)}"
                params.append(source)
            sql += " limit 1"
            cursor.execute(sql, tuple(params))
            return self._normalize_paper_row(_fetchone(cursor))

    def list_public_papers(self) -> list[dict[str, Any]]:
        """获取所有公开且未被移除的论文列表。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + " from papers where visibility = "
                    + _placeholder(0)
                    + " and status <> "
                    + _placeholder(1)
                ),
                ("public", "removed"),
            )
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_published_arxiv_papers_needing_metadata_repair(self, *, limit: int) -> list[dict[str, Any]]:
        """获取已发布但元数据不完整需要修复的arXiv论文列表。"""
        normalized_limit = max(1, min(100, int(limit or 20)))
        if get_database_dialect() == "mysql":
            authors_empty_sql = "(authors is null or json_length(authors) = 0)"
            categories_empty_sql = "(categories is null or json_length(categories) = 0)"
        else:
            authors_empty_sql = "trim(coalesce(authors, '')) in ('', '[]', 'null')"
            categories_empty_sql = "trim(coalesce(categories, '')) in ('', '[]', 'null')"
        params: list[Any] = [
            "arxiv",
            "public",
            "published",
            "arXiv:%",
            "curated paper",
            "uploaded paper",
            normalized_limit,
        ]
        sql = (
            "select "
            + ", ".join(PAPER_COLUMNS)
            + " from papers where source = "
            + _placeholder(0)
            + " and visibility = "
            + _placeholder(1)
            + " and status = "
            + _placeholder(2)
            + " and trim(coalesce(arxiv_id, '')) <> ''"
            + " and ("
            + "trim(coalesce(title, '')) = ''"
            + " or title like "
            + _placeholder(3)
            + " or lower(trim(coalesce(title, ''))) in ("
            + _placeholder(4)
            + ", "
            + _placeholder(5)
            + ")"
            + " or "
            + authors_empty_sql
            + " or "
            + categories_empty_sql
            + " or trim(coalesce(abstract_raw, '')) = ''"
            + " or arxiv_published_at is null"
            + ")"
            + " order by coalesce(updated_at, created_at, '') asc"
            + " limit "
            + _placeholder(6)
        )
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, tuple(params))
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def _public_paper_query_parts(
        self,
        *,
        query: Optional[str] = None,
        hot_window: Optional[str] = None,
    ) -> tuple[str, list[Any]]:
        """构建公开论文查询的WHERE子句和参数。"""
        filters = [
            "visibility = " + _placeholder(0),
            "status <> " + _placeholder(1),
        ]
        params: list[Any] = ["public", "removed"]

        normalized_query = str(query or "").strip()
        if normalized_query:
            like_value = f"%{normalized_query.lower()}%"
            query_fields = [
                "lower(coalesce(title, ''))",
                "lower(coalesce(arxiv_id, ''))",
                "lower(coalesce(abstract_raw, ''))",
                "lower(coalesce(abstract_translated, ''))",
                "lower(coalesce(authors, ''))",
                "lower(coalesce(categories, ''))",
            ]
            placeholders = []
            for field in query_fields:
                placeholders.append(f"{field} like {_placeholder(len(params))}")
                params.append(like_value)
            filters.append("(" + " or ".join(placeholders) + ")")

        normalized_window = str(hot_window or "").strip().lower()
        window_days = {"3d": 3, "7d": 7, "30d": 30, "90d": 90}.get(normalized_window)
        if window_days is not None:
            cutoff = datetime.utcnow() - timedelta(days=window_days)
            filters.append(
                "coalesce(arxiv_published_at, official_published_at, created_at) >= "
                + _placeholder(len(params))
            )
            params.append(cutoff.strftime("%Y-%m-%d %H:%M:%S"))

        return " where " + " and ".join(filters), params

    def count_public_papers(
        self,
        *,
        query: Optional[str] = None,
        hot_window: Optional[str] = None,
    ) -> int:
        """统计公开论文总数，支持搜索关键词和热门时间窗口过滤。"""
        where_sql, params = self._public_paper_query_parts(query=query, hot_window=hot_window)
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("select count(*) as total from papers" + where_sql, tuple(params))
            row = _fetchone(cursor) or {}
            return int(row.get("total") or 0)

    def list_public_papers_page(
        self,
        *,
        sort: str,
        query: Optional[str],
        limit: int,
        offset: int,
        hot_window: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """分页获取公开论文列表，支持按最新、热门、浏览量、点赞数排序，以及搜索和热门时间窗口过滤。"""
        normalized_sort = str(sort or "latest").strip().lower()
        where_sql, params = self._public_paper_query_parts(query=query, hot_window=hot_window)
        order_by = (
            " order by coalesce(arxiv_published_at, official_published_at, created_at, '') desc, "
            "coalesce(created_at, '') desc"
        )
        if normalized_sort == "hot":
            order_by = (
                " order by case when community_status = 'official' and trans_status = 'completed' "
                "then coalesce(hot_score, 0) else 0 end desc, "
                "coalesce(view_count, 0) desc, "
                "coalesce(arxiv_published_at, official_published_at, created_at, '') desc, "
                "coalesce(created_at, '') desc"
            )
        elif normalized_sort == "views":
            order_by = (
                " order by coalesce(view_count, 0) desc, "
                "coalesce(arxiv_published_at, official_published_at, created_at, '') desc, "
                "coalesce(created_at, '') desc"
            )
        elif normalized_sort == "likes":
            order_by = (
                " order by coalesce(like_count, 0) desc, "
                "coalesce(arxiv_published_at, official_published_at, created_at, '') desc, "
                "coalesce(created_at, '') desc"
            )

        params.extend([int(limit), int(offset)])
        limit_placeholder = _placeholder(len(params) - 2)
        offset_placeholder = _placeholder(len(params) - 1)
        sql = (
            "select "
            + ", ".join(PAPER_COLUMNS)
            + " from papers"
            + where_sql
            + order_by
            + f" limit {limit_placeholder} offset {offset_placeholder}"
        )

        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, tuple(params))
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def insert_paper(self, payload: dict[str, Any]) -> dict[str, Any]:
        """插入一条新的论文记录。"""
        serialized = self._serialize_paper_updates(payload)
        if "id" not in serialized:
            raise ValueError("paper id is required")
        columns = tuple(column for column in PAPER_COLUMNS if column in serialized)
        placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into papers ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )
        return self.get_paper_by_id(str(serialized["id"])) or dict(payload)

    def update_paper(self, paper_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        """更新指定论文记录。"""
        serialized = self._serialize_paper_updates(updates)
        if not serialized:
            return self.get_paper_by_id(paper_id)

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        values = [serialized[column] for column in serialized.keys()]
        values.append(paper_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update papers set {assignments} "
                    f"where id = {_placeholder(len(values) - 1)}"
                ),
                tuple(values),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_paper_by_id(paper_id)

    def list_latest_assets_for_paper(self, paper_id: str) -> list[dict[str, Any]]:
        """获取指定论文的最新资产列表（标记为is_latest的资产）。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_ASSET_COLUMNS)
                    + " from paper_assets where paper_id = "
                    + _placeholder(0)
                    + " and is_latest = "
                    + _placeholder(1)
                    + " order by created_at desc"
                ),
                (paper_id, True),
            )
            return [
                normalized
                for normalized in (self._normalize_asset_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_latest_assets_for_papers(self, paper_ids: list[str]) -> list[dict[str, Any]]:
        """批量获取多篇论文的最新资产列表。"""
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return []
        with db_connection() as connection:
            cursor = connection.cursor()
            placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_ASSET_COLUMNS)
                    + " from paper_assets where paper_id in ("
                    + placeholders
                    + ") and is_latest = "
                    + _placeholder(len(normalized_ids))
                    + " order by created_at desc"
                ),
                (*normalized_ids, True),
            )
            return [
                normalized
                for normalized in (self._normalize_asset_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def upsert_latest_asset(
        self,
        *,
        paper_id: str,
        task_id: Optional[str],
        asset_type: str,
        file_path: str,
        file_name: str,
        mime_type: str,
        storage_backend: str = "local_disk",
        asset_id: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> dict[str, Any]:
        """创建或更新论文的最新资产（先将旧的is_latest标记为False，再插入或更新新资产）。"""
        normalized_asset_id = str(asset_id or "").strip() or f"{paper_id}:{asset_type}:{task_id or 'none'}"
        normalized_created_at = created_at or _utc_now_naive().isoformat()

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update paper_assets set is_latest = "
                    + _placeholder(0)
                    + " where paper_id = "
                    + _placeholder(1)
                    + " and asset_type = "
                    + _placeholder(2)
                ),
                (False, paper_id, asset_type),
            )

            existing = None
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_ASSET_COLUMNS)
                    + f" from paper_assets where id = {_placeholder(0)} limit 1"
                ),
                (normalized_asset_id,),
            )
            existing = _fetchone(cursor)
            payload = {
                "id": normalized_asset_id,
                "paper_id": paper_id,
                "task_id": task_id,
                "asset_type": asset_type,
                "storage_backend": storage_backend,
                "file_path": file_path,
                "file_name": file_name,
                "mime_type": mime_type,
                "is_latest": True,
                "created_at": normalized_created_at,
            }
            serialized = self._serialize_asset_updates(payload)
            if existing is None:
                columns = tuple(column for column in PAPER_ASSET_COLUMNS if column in serialized)
                placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
                cursor.execute(
                    (
                        "insert into paper_assets ("
                        + ", ".join(columns)
                        + f") values ({placeholders})"
                    ),
                    tuple(serialized[column] for column in columns),
                )
            else:
                assignments = ", ".join(
                    f"{column} = {_placeholder(index)}"
                    for index, column in enumerate(
                        column for column in PAPER_ASSET_COLUMNS if column != "id" and column in serialized
                    )
                )
                update_columns = [column for column in PAPER_ASSET_COLUMNS if column != "id" and column in serialized]
                values = [serialized[column] for column in update_columns]
                values.append(normalized_asset_id)
                cursor.execute(
                    (
                        f"update paper_assets set {assignments} "
                        f"where id = {_placeholder(len(values) - 1)}"
                    ),
                    tuple(values),
                )

        for row in self.list_latest_assets_for_paper(paper_id):
            if str(row.get("asset_type") or "") == asset_type:
                return row
        return payload

    def list_structured_insight_sections(self, paper_id: str) -> list[dict[str, Any]]:
        """获取论文的所有结构化洞察章节。异常时返回空列表。"""
        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    (
                        "select "
                        + ", ".join(STRUCTURED_INSIGHT_COLUMNS)
                        + " from community_structured_insights where paper_id = "
                        + _placeholder(0)
                        + " order by updated_at asc, section_key asc"
                    ),
                    (paper_id,),
                )
                return [
                    normalized
                    for normalized in (
                        self._normalize_structured_insight_row(row) for row in _fetchall(cursor)
                    )
                    if normalized is not None
                ]
        except Exception:
            return []

    def upsert_structured_insight_section(self, payload: dict[str, Any]) -> dict[str, Any]:
        """创建或更新结构化洞察章节（先删后插）。"""
        serialized = self._serialize_structured_insight_updates(payload)
        paper_id = str(serialized.get("paper_id") or "").strip()
        section_key = str(serialized.get("section_key") or "").strip()
        if not paper_id or not section_key:
            raise ValueError("paper_id and section_key are required")

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "delete from community_structured_insights where paper_id = "
                    + _placeholder(0)
                    + " and section_key = "
                    + _placeholder(1)
                ),
                (paper_id, section_key),
            )
            columns = tuple(column for column in STRUCTURED_INSIGHT_COLUMNS if column in serialized)
            placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
            cursor.execute(
                (
                    "insert into community_structured_insights ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )

        rows = self.list_structured_insight_sections(paper_id)
        for row in rows:
            if str(row.get("section_key") or "") == section_key:
                return row
        return payload

    def list_similar_recommendations(self, paper_id: str) -> list[dict[str, Any]]:
        """获取论文的相似推荐列表。异常时返回空列表。"""
        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    (
                        "select "
                        + ", ".join(SIMILAR_RECOMMENDATION_COLUMNS)
                        + " from community_similar_recommendations where paper_id = "
                        + _placeholder(0)
                        + " order by position asc"
                    ),
                    (paper_id,),
                )
                return [
                    normalized
                    for normalized in (
                        self._normalize_similar_recommendation_row(row) for row in _fetchall(cursor)
                    )
                    if normalized is not None
                ]
        except Exception:
            return []

    def replace_similar_recommendations(self, *, paper_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """替换论文的全部相似推荐（先删后批量插入）。"""
        normalized_paper_id = str(paper_id or "").strip()
        if not normalized_paper_id:
            raise ValueError("paper_id is required")

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "delete from community_similar_recommendations where paper_id = " + _placeholder(0),
                (normalized_paper_id,),
            )

            for index, item in enumerate(items):
                payload = {
                    "paper_id": normalized_paper_id,
                    "position": index,
                    "arxiv_id": item.get("arxiv_id"),
                    "title": item.get("title"),
                    "abstract": item.get("abstract"),
                    "arxiv_url": item.get("arxiv_url"),
                    "community_paper_id": item.get("community_paper_id"),
                    "link_type": item.get("link_type"),
                    "updated_at": item.get("updated_at") or _utc_now_naive().isoformat(),
                }
                serialized = self._serialize_similar_recommendation_updates(payload)
                columns = tuple(column for column in SIMILAR_RECOMMENDATION_COLUMNS if column in serialized)
                placeholders = ", ".join(_placeholder(placeholder_index) for placeholder_index in range(len(columns)))
                cursor.execute(
                    (
                        "insert into community_similar_recommendations ("
                        + ", ".join(columns)
                        + f") values ({placeholders})"
                    ),
                    tuple(serialized[column] for column in columns),
                )

        return self.list_similar_recommendations(normalized_paper_id)

    def insert_curation_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        """插入一条新的策划任务记录。"""
        serialized = self._serialize_curation_job_updates(payload)
        job_id = str(serialized.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("job_id is required")

        columns = tuple(column for column in CURATION_JOB_COLUMNS if column in serialized)
        placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into community_curation_jobs ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )
        return self.get_curation_job(job_id) or dict(payload)

    def get_curation_job(self, job_id: str) -> Optional[dict[str, Any]]:
        """根据任务ID获取策划任务记录。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs where job_id = "
                    + _placeholder(0)
                    + " limit 1"
                ),
                (job_id,),
            )
            return self._normalize_curation_job_row(_fetchone(cursor))

    def update_curation_job(self, job_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        """更新指定策划任务记录。"""
        serialized = self._serialize_curation_job_updates(updates)
        if not serialized:
            return self.get_curation_job(job_id)

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        values = [serialized[column] for column in serialized.keys()]
        values.append(job_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update community_curation_jobs set {assignments} "
                    f"where job_id = {_placeholder(len(values) - 1)}"
                ),
                tuple(values),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_curation_job(job_id)

    def list_curation_jobs_for_batch(self, batch_id: str) -> list[dict[str, Any]]:
        """获取指定批次的所有策划任务列表。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs where batch_id = "
                    + _placeholder(0)
                    + " order by created_at asc, job_id asc"
                ),
                (batch_id,),
            )
            return [
                normalized
                for normalized in (self._normalize_curation_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_curation_jobs_for_arxiv_id(self, arxiv_id: str) -> list[dict[str, Any]]:
        """获取指定arXiv ID的所有策划任务列表。"""
        normalized_arxiv_id = str(arxiv_id or "").strip()
        if not normalized_arxiv_id:
            return []
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs where arxiv_id = "
                    + _placeholder(0)
                    + " order by created_at asc, job_id asc"
                ),
                (normalized_arxiv_id,),
            )
            return [
                normalized
                for normalized in (self._normalize_curation_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_pending_curation_jobs(self) -> list[dict[str, Any]]:
        """获取所有待处理的策划任务列表（状态为排队中、处理中、翻译中、发布中）。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs where status in ("
                    + _placeholder(0)
                    + ", "
                    + _placeholder(1)
                    + ", "
                    + _placeholder(2)
                    + ", "
                    + _placeholder(3)
                    + ") order by created_at asc"
                ),
                ("queued", "processing", "translating", "publishing"),
            )
            return [
                normalized
                for normalized in (self._normalize_curation_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_curation_jobs(
        self,
        *,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """条件查询策划任务列表，支持按状态过滤和arXiv ID/批次ID搜索。"""
        conditions: list[str] = []
        params: list[Any] = []

        normalized_status = str(status_filter or "").strip()
        if normalized_status:
            if normalized_status == "processing":
                params.extend(["processing", "translating", "publishing"])
                processing_placeholder = _placeholder(len(params) - 3)
                translating_placeholder = _placeholder(len(params) - 2)
                publishing_placeholder = _placeholder(len(params) - 1)
                conditions.append(
                    "("
                    + f"status = {processing_placeholder} or "
                    + f"status = {translating_placeholder} or "
                    + f"status = {publishing_placeholder}"
                    + ")"
                )
            else:
                params.append(normalized_status)
                conditions.append(f"status = {_placeholder(len(params) - 1)}")

        normalized_search = str(search or "").strip()
        if normalized_search:
            like_value = f"%{normalized_search}%"
            params.append(like_value)
            arxiv_placeholder = _placeholder(len(params) - 1)
            params.append(like_value)
            batch_placeholder = _placeholder(len(params) - 1)
            conditions.append(f"(arxiv_id like {arxiv_placeholder} or batch_id like {batch_placeholder})")

        where_clause = f" where {' and '.join(conditions)}" if conditions else ""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs"
                    + where_clause
                    + " order by created_at desc, job_id desc"
                ),
                tuple(params),
            )
            return [
                normalized
                for normalized in (self._normalize_curation_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def delete_curation_job(self, job_id: str) -> int:
        """删除指定的策划任务记录，返回受影响的行数。"""
        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return 0
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "delete from community_curation_jobs where job_id = " + _placeholder(0),
                (normalized_job_id,),
            )
            return int(cursor.rowcount or 0)

    def insert_delete_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        """插入一条新的删除任务记录。"""
        serialized = self._serialize_delete_job_updates(payload)
        job_id = str(serialized.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("job_id is required")

        columns = tuple(column for column in DELETE_JOB_COLUMNS if column in serialized)
        placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into community_delete_jobs ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )
        return self.get_delete_job(job_id) or dict(payload)

    def get_delete_job(self, job_id: str) -> Optional[dict[str, Any]]:
        """根据任务ID获取删除任务记录。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(DELETE_JOB_COLUMNS)
                    + " from community_delete_jobs where job_id = "
                    + _placeholder(0)
                    + " limit 1"
                ),
                (job_id,),
            )
            return self._normalize_delete_job_row(_fetchone(cursor))

    def get_delete_job_by_paper_id(self, paper_id: str) -> Optional[dict[str, Any]]:
        """根据论文ID获取最新的删除任务记录。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(DELETE_JOB_COLUMNS)
                    + " from community_delete_jobs where paper_id = "
                    + _placeholder(0)
                    + " order by created_at desc limit 1"
                ),
                (paper_id,),
            )
            return self._normalize_delete_job_row(_fetchone(cursor))

    def update_delete_job(self, job_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        """更新指定删除任务记录。"""
        serialized = self._serialize_delete_job_updates(updates)
        if not serialized:
            return self.get_delete_job(job_id)

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        values = [serialized[column] for column in serialized.keys()]
        values.append(job_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update community_delete_jobs set {assignments} "
                    f"where job_id = {_placeholder(len(values) - 1)}"
                ),
                tuple(values),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_delete_job(job_id)

    def list_pending_delete_jobs(self) -> list[dict[str, Any]]:
        """获取所有待处理的删除任务列表（状态为排队中、运行中、重试中）。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(DELETE_JOB_COLUMNS)
                    + " from community_delete_jobs where status in ("
                    + _placeholder(0)
                    + ", "
                    + _placeholder(1)
                    + ", "
                    + _placeholder(2)
                    + ") order by created_at asc"
                ),
                ("queued", "running", "retry"),
            )
            return [
                normalized
                for normalized in (self._normalize_delete_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_favorite_folders(self, *, user_id: str) -> list[dict[str, Any]]:
        """获取用户的全部收藏夹列表，包含每个收藏夹的论文数量。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(f"folders.{column}" for column in FAVORITE_FOLDER_COLUMNS)
                    + ", coalesce(folder_counts.paper_count, 0) as paper_count "
                    + "from favorite_folders folders "
                    + "left join ("
                    + "  select folder_id, count(*) as paper_count "
                    + "  from favorite_folder_papers group by folder_id"
                    + ") folder_counts on folder_counts.folder_id = folders.id "
                    + "where folders.user_id = "
                    + _placeholder(0)
                    + " order by folders.updated_at desc, folders.created_at desc, folders.id desc"
                ),
                (user_id,),
            )
            return [
                normalized
                for normalized in (self._normalize_favorite_folder_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def create_favorite_folder(self, *, user_id: str, name: str) -> dict[str, Any]:
        """为用户创建一个新的收藏夹（上限9个），名称不能重复。"""
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("folder_name_required")
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "select count(*) as total from favorite_folders where user_id = " + _placeholder(0),
                (user_id,),
            )
            if int((_fetchone(cursor) or {}).get("total") or 0) >= 9:
                raise FavoriteFolderLimitError("favorite_folder_limit_reached")
            cursor.execute(
                (
                    "select id from favorite_folders where user_id = "
                    + _placeholder(0)
                    + " and name = "
                    + _placeholder(1)
                    + " limit 1"
                ),
                (user_id, normalized_name),
            )
            if _fetchone(cursor) is not None:
                raise FavoriteFolderNameConflictError("favorite_folder_name_conflict")
            folder_id = f"favorite-folder-{uuid4().hex[:24]}"
            timestamp = _utc_now_naive().isoformat()
            cursor.execute(
                (
                    "insert into favorite_folders (id, user_id, name, created_at, updated_at) values ("
                    + _placeholder(0)
                    + ", "
                    + _placeholder(1)
                    + ", "
                    + _placeholder(2)
                    + ", "
                    + _placeholder(3)
                    + ", "
                    + _placeholder(4)
                    + ")"
                ),
                (folder_id, user_id, normalized_name, timestamp, timestamp),
            )
        return self.get_favorite_folder(folder_id=folder_id, user_id=user_id) or {
            "id": folder_id,
            "user_id": user_id,
            "name": normalized_name,
            "paper_count": 0,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    def get_favorite_folder(self, *, folder_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """获取指定收藏夹详情，验证所有者身份，包含论文数量。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(f"folders.{column}" for column in FAVORITE_FOLDER_COLUMNS)
                    + ", coalesce(folder_counts.paper_count, 0) as paper_count "
                    + "from favorite_folders folders "
                    + "left join ("
                    + "  select folder_id, count(*) as paper_count "
                    + "  from favorite_folder_papers group by folder_id"
                    + ") folder_counts on folder_counts.folder_id = folders.id "
                    + "where folders.id = "
                    + _placeholder(0)
                    + " and folders.user_id = "
                    + _placeholder(1)
                    + " limit 1"
                ),
                (folder_id, user_id),
            )
            return self._normalize_favorite_folder_row(_fetchone(cursor))

    def rename_favorite_folder(self, *, folder_id: str, user_id: str, name: str) -> dict[str, Any]:
        """重命名收藏夹，验证所有者身份且名称不能与其他收藏夹重复。"""
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("folder_name_required")
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id from favorite_folders where id = "
                    + _placeholder(0)
                    + " and user_id = "
                    + _placeholder(1)
                    + " limit 1"
                ),
                (folder_id, user_id),
            )
            if _fetchone(cursor) is None:
                raise FavoriteFolderNotFoundError("favorite_folder_not_found")
            cursor.execute(
                (
                    "select id from favorite_folders where user_id = "
                    + _placeholder(0)
                    + " and name = "
                    + _placeholder(1)
                    + " and id <> "
                    + _placeholder(2)
                    + " limit 1"
                ),
                (user_id, normalized_name, folder_id),
            )
            if _fetchone(cursor) is not None:
                raise FavoriteFolderNameConflictError("favorite_folder_name_conflict")
            cursor.execute(
                (
                    "update favorite_folders set name = "
                    + _placeholder(0)
                    + ", updated_at = "
                    + _placeholder(1)
                    + " where id = "
                    + _placeholder(2)
                    + " and user_id = "
                    + _placeholder(3)
                ),
                (normalized_name, _utc_now_naive().isoformat(), folder_id, user_id),
            )
        folder = self.get_favorite_folder(folder_id=folder_id, user_id=user_id)
        if folder is None:
            raise FavoriteFolderNotFoundError("favorite_folder_not_found")
        return folder

    def delete_favorite_folder(self, *, folder_id: str, user_id: str) -> list[str]:
        """删除收藏夹，返回受影响的论文ID列表（用于重新计算收藏计数）。"""
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select membership.paper_id from favorite_folder_papers membership "
                    "inner join favorite_folders folders on folders.id = membership.folder_id "
                    "where folders.id = "
                    + _placeholder(0)
                    + " and folders.user_id = "
                    + _placeholder(1)
                ),
                (folder_id, user_id),
            )
            affected_paper_ids = _dedupe_preserve_order(
                [str(row.get("paper_id") or "").strip() for row in _fetchall(cursor)]
            )
            cursor.execute(
                (
                    "delete from favorite_folders where id = "
                    + _placeholder(0)
                    + " and user_id = "
                    + _placeholder(1)
                ),
                (folder_id, user_id),
            )
            if int(cursor.rowcount or 0) <= 0:
                raise FavoriteFolderNotFoundError("favorite_folder_not_found")
            for paper_id in affected_paper_ids:
                self._sync_paper_favorite_marker(cursor, paper_id=paper_id, user_id=user_id)
                self._refresh_favorite_count(cursor, paper_id=paper_id)
        return affected_paper_ids

    def list_paper_favorite_folder_ids(self, *, paper_id: str, user_id: str) -> list[str]:
        """获取某篇论文在用户收藏夹中的所有收藏夹ID。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select membership.folder_id from favorite_folder_papers membership "
                    "inner join favorite_folders folders on folders.id = membership.folder_id "
                    "where folders.user_id = "
                    + _placeholder(0)
                    + " and membership.paper_id = "
                    + _placeholder(1)
                    + " order by membership.created_at asc, membership.folder_id asc"
                ),
                (user_id, paper_id),
            )
            return _dedupe_preserve_order(
                [str(row.get("folder_id") or "").strip() for row in _fetchall(cursor)]
            )

    def sync_paper_favorite_folders(
        self,
        *,
        paper_id: str,
        user_id: str,
        folder_ids: list[str],
    ) -> dict[str, Any]:
        """同步论文的收藏夹关联关系，返回更新后的收藏状态。"""
        normalized_folder_ids = _dedupe_preserve_order(list(folder_ids or []))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            if normalized_folder_ids:
                placeholders = ", ".join(_placeholder(index + 1) for index in range(len(normalized_folder_ids)))
                cursor.execute(
                    (
                        "select id from favorite_folders where user_id = "
                        + _placeholder(0)
                        + " and id in ("
                        + placeholders
                        + ")"
                    ),
                    (user_id, *normalized_folder_ids),
                )
                owned_folder_ids = _dedupe_preserve_order(
                    [str(row.get("id") or "").strip() for row in _fetchall(cursor)]
                )
                if set(owned_folder_ids) != set(normalized_folder_ids):
                    raise FavoriteFolderNotFoundError("favorite_folder_not_found")

            cursor.execute(
                (
                    "select membership.folder_id from favorite_folder_papers membership "
                    "inner join favorite_folders folders on folders.id = membership.folder_id "
                    "where folders.user_id = "
                    + _placeholder(0)
                    + " and membership.paper_id = "
                    + _placeholder(1)
                    + " order by membership.created_at asc, membership.folder_id asc"
                ),
                (user_id, paper_id),
            )
            current_folder_ids = _dedupe_preserve_order(
                [str(row.get("folder_id") or "").strip() for row in _fetchall(cursor)]
            )
            current_folder_id_set = set(current_folder_ids)
            target_folder_id_set = set(normalized_folder_ids)
            timestamp = _utc_now_naive().isoformat()

            for folder_id in normalized_folder_ids:
                if folder_id in current_folder_id_set:
                    continue
                cursor.execute(
                    (
                        "insert into favorite_folder_papers (folder_id, paper_id, created_at) values ("
                        + _placeholder(0)
                        + ", "
                        + _placeholder(1)
                        + ", "
                        + _placeholder(2)
                        + ")"
                    ),
                    (folder_id, paper_id, timestamp),
                )

            for folder_id in current_folder_ids:
                if folder_id in target_folder_id_set:
                    continue
                cursor.execute(
                    (
                        "delete from favorite_folder_papers where folder_id = "
                        + _placeholder(0)
                        + " and paper_id = "
                        + _placeholder(1)
                    ),
                    (folder_id, paper_id),
                )

            touched_folder_ids = _dedupe_preserve_order(current_folder_ids + normalized_folder_ids)
            if touched_folder_ids:
                placeholders = ", ".join(_placeholder(index + 1) for index in range(len(touched_folder_ids)))
                cursor.execute(
                    (
                        "update favorite_folders set updated_at = "
                        + _placeholder(0)
                        + " where user_id = "
                        + _placeholder(1)
                        + " and id in ("
                        + placeholders
                        + ")"
                    ),
                    (timestamp, user_id, *touched_folder_ids),
                )

            favorited = self._sync_paper_favorite_marker(cursor, paper_id=paper_id, user_id=user_id)
            favorite_count = self._refresh_favorite_count(cursor, paper_id=paper_id)

        return {
            "paper_id": paper_id,
            "favorited": favorited,
            "favorite_folder_count": len(normalized_folder_ids),
            "favorite_count": favorite_count,
            "selected_folder_ids": normalized_folder_ids,
        }

    def list_favorite_folder_papers(
        self,
        *,
        folder_id: str,
        user_id: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """获取指定收藏夹中的论文列表，返回收藏夹信息和论文列表的元组。"""
        folder = self.get_favorite_folder(folder_id=folder_id, user_id=user_id)
        if folder is None:
            raise FavoriteFolderNotFoundError("favorite_folder_not_found")

        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(f"papers.{column}" for column in PAPER_COLUMNS)
                    + " from favorite_folder_papers membership "
                    + "inner join papers on papers.id = membership.paper_id "
                    + "where membership.folder_id = "
                    + _placeholder(0)
                    + " and papers.visibility = "
                    + _placeholder(1)
                    + " and papers.status <> "
                    + _placeholder(2)
                    + " order by membership.created_at desc, papers.created_at desc"
                ),
                (folder_id, "public", "removed"),
            )
            papers = [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]
        return folder, papers

    def like_paper(self, *, paper_id: str, user_id: str) -> int:
        """用户点赞论文，返回更新后的点赞数。"""
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select 1 from paper_likes where paper_id = "
                    + _placeholder(0)
                    + " and user_id = "
                    + _placeholder(1)
                    + " limit 1"
                ),
                (paper_id, user_id),
            )
            if _fetchone(cursor) is None:
                cursor.execute(
                    (
                        "insert into paper_likes (paper_id, user_id, created_at) values ("
                        + _placeholder(0)
                        + ", "
                        + _placeholder(1)
                        + ", "
                        + _placeholder(2)
                        + ")"
                    ),
                    (paper_id, user_id, _utc_now_naive().isoformat()),
                )
            return self._refresh_like_count(cursor, paper_id=paper_id)

    def unlike_paper(self, *, paper_id: str, user_id: str) -> int:
        """用户取消点赞论文，返回更新后的点赞数。"""
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "delete from paper_likes where paper_id = "
                    + _placeholder(0)
                    + " and user_id = "
                    + _placeholder(1)
                ),
                (paper_id, user_id),
            )
            return self._refresh_like_count(cursor, paper_id=paper_id)

    def record_daily_view(
        self,
        *,
        paper_id: str,
        user_id: str | None = None,
        anon_id: str | None = None,
    ) -> Optional[int]:
        """记录论文的每日浏览次数（同一用户/匿名ID每天仅计一次），返回更新后的浏览数。"""
        principal_type: str | None = None
        principal_key: str | None = None
        if str(user_id or "").strip():
            principal_type = "user"
            principal_key = str(user_id).strip()
        elif str(anon_id or "").strip():
            principal_type = "anon"
            principal_key = sha256(str(anon_id).strip().encode("utf-8")).hexdigest()

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "select view_count from papers where id = " + _placeholder(0) + " limit 1",
                (paper_id,),
            )
            row = _fetchone(cursor)
            if row is None:
                return None

            if principal_type and principal_key:
                business_day = _business_day_utc8()
                cursor.execute(
                    (
                        "select 1 from paper_daily_views where paper_id = "
                        + _placeholder(0)
                        + " and view_date = "
                        + _placeholder(1)
                        + " and principal_type = "
                        + _placeholder(2)
                        + " and principal_key = "
                        + _placeholder(3)
                        + " limit 1"
                    ),
                    (paper_id, business_day, principal_type, principal_key),
                )
                if _fetchone(cursor) is not None:
                    return int(row.get("view_count") or 0)
                cursor.execute(
                    (
                        "insert into paper_daily_views (paper_id, view_date, principal_type, principal_key, created_at) values ("
                        + _placeholder(0)
                        + ", "
                        + _placeholder(1)
                        + ", "
                        + _placeholder(2)
                        + ", "
                        + _placeholder(3)
                        + ", "
                        + _placeholder(4)
                        + ")"
                    ),
                    (paper_id, business_day, principal_type, principal_key, _utc_now_naive().isoformat()),
                )

            cursor.execute(
                (
                    "update papers set view_count = coalesce(view_count, 0) + 1, "
                    "updated_at = "
                    + _placeholder(0)
                    + " where id = "
                    + _placeholder(1)
                ),
                (_utc_now_naive().isoformat(), paper_id),
            )
            cursor.execute(
                "select view_count from papers where id = " + _placeholder(0) + " limit 1",
                (paper_id,),
            )
            row = _fetchone(cursor)
        if row is None:
            return None
        return int(row.get("view_count") or 0)

    def get_viewer_state(self, paper_ids: list[str], *, user_id: str) -> dict[str, dict[str, Any]]:
        """获取用户对一组论文的查看状态（是否已点赞、是否已收藏、收藏夹数量）。"""
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        default_state = {
            paper_id: {"liked": False, "favorited": False, "favorite_folder_count": 0}
            for paper_id in normalized_ids
        }
        if not normalized_ids or not user_id:
            return default_state

        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index + 1) for index in range(len(normalized_ids)))
                cursor.execute(
                    (
                        "select paper_id from paper_likes where user_id = "
                        + _placeholder(0)
                        + " and paper_id in ("
                        + placeholders
                        + ")"
                    ),
                    (user_id, *normalized_ids),
                )
                liked_ids = {
                    str(row.get("paper_id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("paper_id") or "").strip()
                }
                cursor.execute(
                    (
                        "select paper_id from paper_favorites where user_id = "
                        + _placeholder(0)
                        + " and paper_id in ("
                        + placeholders
                        + ")"
                    ),
                    (user_id, *normalized_ids),
                )
                favorited_ids = {
                    str(row.get("paper_id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("paper_id") or "").strip()
                }
                cursor.execute(
                    (
                        "select membership.paper_id, count(*) as folder_count "
                        "from favorite_folder_papers membership "
                        "inner join favorite_folders folders on folders.id = membership.folder_id "
                        "where folders.user_id = "
                        + _placeholder(0)
                        + " and membership.paper_id in ("
                        + placeholders
                        + ") group by membership.paper_id"
                    ),
                    (user_id, *normalized_ids),
                )
                folder_counts = {
                    str(row.get("paper_id") or "").strip(): int(row.get("folder_count") or 0)
                    for row in _fetchall(cursor)
                    if str(row.get("paper_id") or "").strip()
                }
        except Exception:
            return default_state

        for paper_id in normalized_ids:
            default_state[paper_id] = {
                "liked": paper_id in liked_ids,
                "favorited": paper_id in favorited_ids,
                "favorite_folder_count": int(folder_counts.get(paper_id) or 0),
            }
        return default_state

    def increment_view_count(self, paper_id: str) -> Optional[int]:
        """递增论文浏览次数计数器。"""
        return self._increment_counter(paper_id, "view_count")

    def increment_download_count(self, paper_id: str) -> Optional[int]:
        """递增论文下载次数计数器。"""
        return self._increment_counter(paper_id, "download_count")

    def _increment_counter(self, paper_id: str, column: str) -> Optional[int]:
        """递增指定论文的指定计数器字段（view_count或download_count）。"""
        if column not in {"view_count", "download_count"}:
            raise ValueError(f"unsupported counter column: {column}")

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update papers set {column} = coalesce({column}, 0) + 1, "
                    f"updated_at = {_placeholder(0)} where id = {_placeholder(1)}"
                ),
                (_utc_now_naive().isoformat(), paper_id),
            )
            if cursor.rowcount <= 0:
                return None
            cursor.execute(
                f"select {column} from papers where id = {_placeholder(0)} limit 1",
                (paper_id,),
            )
            row = _fetchone(cursor)
        if row is None:
            return None
        value = row.get(column)
        return int(value) if value is not None else 0

    def mark_translation_failed_by_task(self, task_id: str) -> int:
        """将关联到指定翻译任务的论文翻译状态标记为失败。"""
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            return 0

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update papers set trans_status = "
                    + _placeholder(0)
                    + ", updated_at = "
                    + _placeholder(1)
                    + " where community_selected_task_id = "
                    + _placeholder(2)
                    + " and trans_status in ("
                    + _placeholder(3)
                    + ", "
                    + _placeholder(4)
                    + ")"
                ),
                ("failed", _utc_now_naive().isoformat(), normalized_task_id, "queued", "processing"),
            )
            return int(cursor.rowcount or 0)

    def list_inflight_translation_papers(self) -> list[dict[str, Any]]:
        """获取所有正在进行翻译中（排队中/处理中）的论文列表。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + " from papers where trans_status in ("
                    + _placeholder(0)
                    + ", "
                    + _placeholder(1)
                    + ")"
                ),
                ("queued", "processing"),
            )
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_purgeable_non_success_papers(self, statuses: list[str]) -> list[dict[str, Any]]:
        """获取所有处于非成功状态的可清理论文列表。"""
        normalized_statuses = [str(status or "").strip() for status in statuses if str(status or "").strip()]
        if not normalized_statuses:
            return []
        placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_statuses)))
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + " from papers where trans_status in ("
                    + placeholders
                    + ")"
                ),
                tuple(normalized_statuses),
            )
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_asset_task_ids_for_papers(self, paper_ids: list[str]) -> list[str]:
        """获取指定论文关联的所有资产中的翻译任务ID列表。"""
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return []
        placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select task_id from paper_assets where paper_id in ("
                    + placeholders
                    + ")"
                ),
                tuple(normalized_ids),
            )
            return [
                str(row.get("task_id") or "").strip()
                for row in _fetchall(cursor)
                if str(row.get("task_id") or "").strip()
            ]

    def list_comment_ids_for_papers(self, paper_ids: list[str]) -> list[str]:
        """获取指定论文的所有评论ID列表。异常时返回空列表。"""
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return []
        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    (
                        "select id from comments where paper_id in ("
                        + placeholders
                        + ")"
                    ),
                    tuple(normalized_ids),
                )
                return [
                    str(row.get("id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("id") or "").strip()
                ]
        except Exception:
            return []

    def list_report_ids_for_targets(self, *, target_type: str, target_ids: list[str]) -> list[str]:
        """获取指定类型和目标ID的举报记录ID列表。异常时返回空列表。"""
        normalized_ids = [str(target_id or "").strip() for target_id in target_ids if str(target_id or "").strip()]
        if not normalized_ids:
            return []
        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index + 1) for index in range(len(normalized_ids)))
                cursor.execute(
                    (
                        "select id from reports where target_type = "
                        + _placeholder(0)
                        + " and target_id in ("
                        + placeholders
                        + ")"
                    ),
                    (target_type, *normalized_ids),
                )
                return [
                    str(row.get("id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("id") or "").strip()
                ]
        except Exception:
            return []

    def delete_rows_by_ids(self, table_name: str, *, id_column: str, row_ids: list[str]) -> int:
        """按ID列表批量删除指定表中的行。仅支持reports和moderation_actions表。"""
        if table_name not in {"reports", "moderation_actions"}:
            raise ValueError(f"unsupported cleanup table: {table_name}")
        normalized_ids = [str(row_id or "").strip() for row_id in row_ids if str(row_id or "").strip()]
        if not normalized_ids:
            return 0
        try:
            with db_connection(commit=True) as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    f"delete from {table_name} where {id_column} in ({placeholders})",
                    tuple(normalized_ids),
                )
                return int(cursor.rowcount or 0)
        except Exception:
            return 0

    def delete_rows_for_papers(self, table_name: str, paper_ids: list[str]) -> int:
        """按论文ID列表批量删除指定关联表中的行。支持评论、资产、点赞、收藏等表。"""
        if table_name not in {
            "comments",
            "paper_assets",
            "paper_likes",
            "paper_favorites",
            "community_structured_insights",
            "community_similar_recommendations",
            "papers",
        }:
            raise ValueError(f"unsupported cleanup table: {table_name}")
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return 0
        try:
            with db_connection(commit=True) as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    f"delete from {table_name} where paper_id in ({placeholders})"
                    if table_name != "papers"
                    else f"delete from papers where id in ({placeholders})",
                    tuple(normalized_ids),
                )
                return int(cursor.rowcount or 0)
        except Exception:
            return 0

    def delete_translation_tasks(self, task_ids: list[str]) -> int:
        """按任务ID列表批量删除翻译任务记录。异常时返回0。"""
        normalized_ids = [str(task_id or "").strip() for task_id in task_ids if str(task_id or "").strip()]
        if not normalized_ids:
            return 0
        try:
            with db_connection(commit=True) as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    "delete from translation_tasks where task_id in (" + placeholders + ")",
                    tuple(normalized_ids),
                )
                return int(cursor.rowcount or 0)
        except Exception:
            return 0


__all__ = [
    "CommunityPaperRepository",
    "PAPER_COLUMNS",
    "PAPER_ASSET_COLUMNS",
    "SIMILAR_RECOMMENDATION_COLUMNS",
    "DatabaseUnavailableError",
]
