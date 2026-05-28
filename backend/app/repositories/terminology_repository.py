from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from backend.app.db import db_connection, get_database_dialect

TERMINOLOGY_TERM_COLUMNS = (
    "id",
    "source_term",
    "target_term",
    "source_lang",
    "target_lang",
    "domain",
    "source_type",
    "status",
    "owner_user_id",
    "created_by_user_id",
    "reviewed_by_user_id",
    "reviewed_at",
    "rejection_reason",
    "extracted_from_task_id",
    "provenance",
    "embedding_model",
    "embedding_status",
    "vector_collection",
    "vector_term_id",
    "created_at",
    "updated_at",
)

_JSON_COLUMNS = {"provenance"}
_BOOLEAN_COLUMNS: set[str] = set()


def _utc_now_naive() -> datetime:
    """获取当前UTC时间，去除时区信息和微秒。"""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _placeholder(_index: int) -> str:
    """根据数据库方言返回对应的参数占位符（SQLite: ?，MySQL: %s）。"""
    return "?" if get_database_dialect() == "sqlite" else "%s"


def _placeholders(count: int) -> str:
    """生成指定数量的参数占位符，用逗号分隔。"""
    return ", ".join(_placeholder(index) for index in range(count))


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


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """标准化行数据，解析JSON字段并转换布尔字段。"""
    for col in _JSON_COLUMNS:
        val = row.get(col)
        if isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
        elif val is None:
            row[col] = None
    for col in _BOOLEAN_COLUMNS:
        val = row.get(col)
        if isinstance(val, (int, float)):
            row[col] = bool(val)
        elif isinstance(val, str):
            row[col] = val.lower() in ("1", "true", "yes")
    return row


def _serialize_updates(updates: dict[str, Any]) -> dict[str, Any]:
    """序列化更新载荷，将JSON字段转为字符串，布尔字段转为整数。"""
    serialized = dict(updates)
    for col in _JSON_COLUMNS:
        val = serialized.get(col)
        if val is not None and not isinstance(val, str):
            serialized[col] = json.dumps(val, ensure_ascii=False)
    for col in _BOOLEAN_COLUMNS:
        val = serialized.get(col)
        if isinstance(val, bool):
            serialized[col] = 1 if val else 0
    return serialized


def _new_id() -> str:
    """生成一个新的UUID十六进制字符串作为ID。"""
    return uuid4().hex


class TerminologyRepository:
    """术语数据访问层，负责RAG术语的增删改查、检索和审核工作流。"""

    def _row(self, row: dict[str, Any]) -> dict[str, Any]:
        """标准化单行数据。"""
        return _normalize_row(dict(row))

    def _rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """标准化多行数据。"""
        return [self._row(r) for r in rows]

    # ---- CRUD ----

    def insert_term(self, payload: dict[str, Any]) -> dict[str, Any]:
        """插入一条新的术语记录。"""
        now = _utc_now_naive()
        term_id = payload.get("id") or _new_id()
        record = {
            "id": term_id,
            "source_term": payload["source_term"],
            "target_term": payload["target_term"],
            "source_lang": payload.get("source_lang", "en"),
            "target_lang": payload.get("target_lang", "zh"),
            "domain": payload.get("domain"),
            "source_type": payload.get("source_type", "auto_extracted"),
            "status": payload.get("status", "pending_review"),
            "owner_user_id": payload.get("owner_user_id"),
            "created_by_user_id": payload.get("created_by_user_id"),
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "rejection_reason": None,
            "extracted_from_task_id": payload.get("extracted_from_task_id"),
            "provenance": payload.get("provenance"),
            "embedding_model": None,
            "embedding_status": "none",
            "vector_collection": None,
            "vector_term_id": None,
            "created_at": now,
            "updated_at": now,
        }
        cols = tuple(record.keys())
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"insert into terminology_terms ({', '.join(cols)}) values ({_placeholders(len(cols))})",
                tuple(record.values()),
            )
        return self.get_term(term_id) or record

    def get_term(self, term_id: str) -> Optional[dict[str, Any]]:
        """根据术语ID获取术语记录。"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms where id = {_placeholder(0)}",
                (term_id,),
            )
            row = _fetchone(cursor)
        return self._row(row) if row else None

    def update_term(self, term_id: str, updates: dict[str, Any]) -> bool:
        """更新指定术语记录，返回是否更新成功。"""
        updates["updated_at"] = _utc_now_naive()
        serialized = _serialize_updates(updates)
        set_clause = ", ".join(f"{k} = {_placeholder(i)}" for i, k in enumerate(serialized))
        values = tuple(serialized.values()) + (term_id,)
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"update terminology_terms set {set_clause} where id = {_placeholder(len(serialized))}",
                values,
            )
            return cursor.rowcount > 0

    def delete_term(self, term_id: str) -> bool:
        """删除指定术语记录，返回是否删除成功。"""
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"delete from terminology_terms where id = {_placeholder(0)}",
                (term_id,),
            )
            return cursor.rowcount > 0

    # ---- Search / Retrieval ----

    def search_approved_terms(
        self,
        *,
        source_lang: str = "en",
        target_lang: str = "zh",
        domain: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """搜索已审核通过的术语，支持按语言对、领域和源术语关键词模糊搜索，按术语长度升序排列。"""
        conditions = ["status = 'approved'", f"source_lang = {_placeholder(0)}", f"target_lang = {_placeholder(1)}"]
        params: list[Any] = [source_lang, target_lang]
        if domain:
            conditions.append(f"domain = {_placeholder(len(params))}")
            params.append(domain)
        if query:
            conditions.append(f"source_term like {_placeholder(len(params))}")
            params.append(f"%{query}%")
        where = " and ".join(conditions)
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms where {where} order by length(source_term)",
                tuple(params),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else []

    def get_all_approved_terms(self, *, source_lang: str = "en", domain: Optional[str] = None) -> list[dict[str, Any]]:
        """获取所有已审核通过的术语，支持按源语言和领域过滤。"""
        conditions = [f"status = 'approved'", f"source_lang = {_placeholder(0)}"]
        params: list[Any] = [source_lang]
        if domain:
            conditions.append(f"domain = {_placeholder(len(params))}")
            params.append(domain)
        where = " and ".join(conditions)
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms "
                f"where {where} order by length(source_term)",
                tuple(params),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else []

    def get_approved_system_terms(self, *, source_lang: str = "en", domain: Optional[str] = None) -> list[dict[str, Any]]:
        """获取已审核通过的系统术语（source_type='system'）。"""
        conditions = ["source_type = 'system'", "status = 'approved'", f"source_lang = {_placeholder(0)}"]
        params: list[Any] = [source_lang]
        if domain:
            conditions.append(f"domain = {_placeholder(len(params))}")
            params.append(domain)
        where = " and ".join(conditions)
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms "
                f"where {where} order by length(source_term)",
                tuple(params),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else []

    def get_approved_terms_by_owner(self, owner_user_id: str, *, source_lang: str = "en", domain: Optional[str] = None) -> list[dict[str, Any]]:
        """获取指定用户所有的已审核通过术语。"""
        conditions = [f"owner_user_id = {_placeholder(0)}", "status = 'approved'", f"source_lang = {_placeholder(1)}"]
        params: list[Any] = [owner_user_id, source_lang]
        if domain:
            conditions.append(f"domain = {_placeholder(len(params))}")
            params.append(domain)
        where = " and ".join(conditions)
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms "
                f"where {where} order by length(source_term)",
                tuple(params),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else []

    def find_existing_system_terms(self, source_terms: list[str]) -> set[str]:
        """查找在系统词库中已存在的源术语集合。"""
        if not source_terms:
            return set()
        placeholders_list = ", ".join(_placeholder(i) for i in range(len(source_terms)))
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select source_term from terminology_terms "
                f"where source_type = 'system' and source_term in ({placeholders_list})",
                tuple(source_terms),
            )
            rows = _fetchall(cursor)
        return {r["source_term"] for r in rows} if rows else set()

    def get_terms_by_owner(self, owner_user_id: str, *, page: int = 1, page_size: int = 20,
                           status: Optional[str] = None) -> tuple[list[dict[str, Any]], int]:
        """分页获取指定用户的术语列表，支持按状态过滤。"""
        conditions = [f"owner_user_id = {_placeholder(0)}"]
        params = [owner_user_id]
        if status:
            conditions.append(f"status = {_placeholder(len(params))}")
            params.append(status)
        where = " and ".join(conditions)
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"select count(*) as cnt from terminology_terms where {where}", tuple(params))
            total = cursor.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms "
                f"where {where} order by created_at desc "
                f"limit {_placeholder(len(params))} offset {_placeholder(len(params) + 1)}",
                tuple(params) + (page_size, offset),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else [], total

    # ---- Review Workflow ----

    def list_pending_terms(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        source_lang: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """分页获取待审核的术语列表，支持按源语言和领域过滤。"""
        conditions = ["status = 'pending_review'"]
        params: list[Any] = []
        if source_lang:
            conditions.append(f"source_lang = {_placeholder(len(params))}")
            params.append(source_lang)
        if domain:
            conditions.append(f"domain = {_placeholder(len(params))}")
            params.append(domain)
        where = " and ".join(conditions)
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"select count(*) as cnt from terminology_terms where {where}", tuple(params))
            total = cursor.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms "
                f"where {where} order by created_at desc limit {_placeholder(len(params))} offset {_placeholder(len(params) + 1)}",
                tuple(params) + (page_size, offset),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else [], total

    def approve_term(self, term_id: str, reviewed_by_user_id: str) -> bool:
        """审核通过指定术语，设置审核人和审核时间。"""
        updates = {
            "status": "approved",
            "reviewed_by_user_id": reviewed_by_user_id,
            "reviewed_at": _utc_now_naive(),
            "rejection_reason": None,
            "embedding_status": "pending",
        }
        return self.update_term(term_id, updates)

    def reject_term(self, term_id: str, reviewed_by_user_id: str, reason: Optional[str] = None) -> bool:
        """驳回指定术语，可附带驳回原因。"""
        updates = {
            "status": "rejected",
            "reviewed_by_user_id": reviewed_by_user_id,
            "reviewed_at": _utc_now_naive(),
            "rejection_reason": reason,
            "embedding_status": "none",
        }
        return self.update_term(term_id, updates)

    # ---- Batch operations ----

    def batch_approve_terms(self, term_ids: list[str], reviewed_by_user_id: str) -> int:
        """批量审核通过术语（单条SQL），返回受影响的行数。"""
        if not term_ids:
            return 0
        now = _utc_now_naive()
        placeholders = ", ".join(_placeholder(i) for i in range(len(term_ids)))
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"update terminology_terms set status = 'approved', "
                f"reviewed_by_user_id = {_placeholder(len(term_ids))}, "
                f"reviewed_at = {_placeholder(len(term_ids) + 1)}, "
                f"rejection_reason = NULL, "
                f"embedding_status = 'pending', "
                f"updated_at = {_placeholder(len(term_ids) + 2)} "
                f"where id in ({placeholders})",
                tuple(term_ids) + (reviewed_by_user_id, now, now),
            )
            return cursor.rowcount

    def batch_reject_terms(self, term_ids: list[str], reviewed_by_user_id: str, reason: Optional[str] = None) -> int:
        """批量驳回术语（单条SQL），返回受影响的行数。"""
        if not term_ids:
            return 0
        now = _utc_now_naive()
        placeholders = ", ".join(_placeholder(i) for i in range(len(term_ids)))
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"update terminology_terms set status = 'rejected', "
                f"reviewed_by_user_id = {_placeholder(len(term_ids))}, "
                f"reviewed_at = {_placeholder(len(term_ids) + 1)}, "
                f"rejection_reason = {_placeholder(len(term_ids) + 2)}, "
                f"embedding_status = 'none', "
                f"updated_at = {_placeholder(len(term_ids) + 3)} "
                f"where id in ({placeholders})",
                tuple(term_ids) + (reviewed_by_user_id, now, reason, now),
            )
            return cursor.rowcount

    def batch_delete_terms(self, term_ids: list[str]) -> int:
        """批量删除术语（单条SQL），返回受影响的行数。"""
        if not term_ids:
            return 0
        placeholders = ", ".join(_placeholder(i) for i in range(len(term_ids)))
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"delete from terminology_terms where id in ({placeholders})",
                tuple(term_ids),
            )
            return cursor.rowcount

    def set_embedding_status(self, term_id: str, status: str, *, model: Optional[str] = None,
                             collection: Optional[str] = None, vector_term_id: Optional[str] = None) -> bool:
        """设置术语的向量嵌入状态及相关元信息。"""
        updates: dict[str, Any] = {"embedding_status": status}
        if model:
            updates["embedding_model"] = model
        if collection:
            updates["vector_collection"] = collection
        if vector_term_id:
            updates["vector_term_id"] = vector_term_id
        return self.update_term(term_id, updates)

    # ---- Bulk Operations ----

    def insert_terms_batch(self, terms: list[dict[str, Any]]) -> list[str]:
        """批量插入术语记录，返回新创建的术语ID列表。"""
        ids: list[str] = []
        now = _utc_now_naive()
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            for payload in terms:
                term_id = _new_id()
                record = {
                    "id": term_id,
                    "source_term": payload["source_term"],
                    "target_term": payload["target_term"],
                    "source_lang": payload.get("source_lang", "en"),
                    "target_lang": payload.get("target_lang", "zh"),
                    "domain": payload.get("domain"),
                    "source_type": payload.get("source_type", "imported"),
                    "status": payload.get("status", "pending_review"),
                    "owner_user_id": payload.get("owner_user_id"),
                    "created_by_user_id": payload.get("created_by_user_id"),
                    "reviewed_by_user_id": None,
                    "reviewed_at": None,
                    "rejection_reason": None,
                    "extracted_from_task_id": payload.get("extracted_from_task_id"),
                    "provenance": payload.get("provenance"),
                    "embedding_model": None,
                    "embedding_status": "none",
                    "vector_collection": None,
                    "vector_term_id": None,
                    "created_at": now,
                    "updated_at": now,
                }
                cols = tuple(record.keys())
                cursor.execute(
                    f"insert into terminology_terms ({', '.join(cols)}) values ({_placeholders(len(cols))})",
                    tuple(record.values()),
                )
                ids.append(term_id)
        return ids

    # ---- General-purpose filtered search with pagination ----

    def search_terms(
        self,
        *,
        status: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        domain: Optional[str] = None,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """通用术语搜索方法，支持多条件过滤和SQL级别分页。

        Args:
            status: 按术语状态过滤（如 ``"approved"``、``"pending_review"``）。
            source_lang: 按源语言过滤。
            target_lang: 按目标语言过滤。
            domain: 按领域过滤。
            query: 对 ``source_term`` 进行模糊搜索。
            source_type: 按来源类型过滤（如 ``"system"``、``"imported"``）。
            page: 页码（从1开始）。
            page_size: 每页条目数。

        Returns:
            (list[dict], int): 结果行列表与总行数的元组。
        """
        conditions: list[str] = []
        params: list[Any] = []

        if status:
            conditions.append(f"status = {_placeholder(len(params))}")
            params.append(status)
        if source_lang:
            conditions.append(f"source_lang = {_placeholder(len(params))}")
            params.append(source_lang)
        if target_lang:
            conditions.append(f"target_lang = {_placeholder(len(params))}")
            params.append(target_lang)
        if domain:
            conditions.append(f"domain = {_placeholder(len(params))}")
            params.append(domain)
        if query:
            conditions.append(f"source_term like {_placeholder(len(params))}")
            params.append(f"%{query}%")
        if source_type:
            conditions.append(f"source_type = {_placeholder(len(params))}")
            params.append(source_type)

        where = " and ".join(conditions) if conditions else "1 = 1"

        with db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"select count(*) as cnt from terminology_terms where {where}",
                tuple(params),
            )
            total = cursor.fetchone()["cnt"]

            offset = (page - 1) * page_size
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} "
                f"from terminology_terms where {where} "
                f"order by created_at desc "
                f"limit {_placeholder(len(params))} offset {_placeholder(len(params) + 1)}",
                tuple(params) + (page_size, offset),
            )
            rows = _fetchall(cursor)

        return self._rows(rows) if rows else [], total

    # ---- Match Log ----

    def insert_match_log(self, payload: dict[str, Any]) -> str:
        """插入一条术语匹配日志记录，返回日志ID。"""
        log_id = _new_id()
        now = _utc_now_naive()
        record = {
            "id": log_id,
            "task_id": payload["task_id"],
            "term_id": payload["term_id"],
            "chunk_index": payload.get("chunk_index", 0),
            "retrieval_source": payload.get("retrieval_source", "bm25"),
            "was_injected": payload.get("was_injected", False),
            "rerank_score": payload.get("rerank_score"),
            "created_at": now,
        }
        cols = tuple(record.keys())
        with db_connection(commit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"insert into terminology_match_log ({', '.join(cols)}) values ({_placeholders(len(cols))})",
                tuple(record.values()),
            )
        return log_id

    def get_match_logs_for_task(self, task_id: str) -> list[dict[str, Any]]:
        """获取指定翻译任务的术语匹配日志列表，包含术语原文和译文。"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select ml.*, t.source_term, t.target_term "
                f"from terminology_match_log ml "
                f"left join terminology_terms t on ml.term_id = t.id "
                f"where ml.task_id = {_placeholder(0)} order by ml.chunk_index, ml.created_at",
                (task_id,),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else []
