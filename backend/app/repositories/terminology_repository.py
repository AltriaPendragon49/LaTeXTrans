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
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _placeholder(_index: int) -> str:
    return "?" if get_database_dialect() == "sqlite" else "%s"


def _placeholders(count: int) -> str:
    return ", ".join(_placeholder(index) for index in range(count))


def _fetchone(cursor) -> Optional[dict[str, Any]]:
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _fetchall(cursor) -> list[dict[str, Any]]:
    rows = cursor.fetchall() or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(dict(row))
        else:
            normalized.append({key: row[key] for key in row.keys()})
    return normalized


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
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
    return uuid4().hex


class TerminologyRepository:
    """Repository for RAG terminology term CRUD, search, and review workflows."""

    def _row(self, row: dict[str, Any]) -> dict[str, Any]:
        return _normalize_row(dict(row))

    def _rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self._row(r) for r in rows]

    # ---- CRUD ----

    def insert_term(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms where id = {_placeholder(0)}",
                (term_id,),
            )
            row = _fetchone(cursor)
        return self._row(row) if row else None

    def update_term(self, term_id: str, updates: dict[str, Any]) -> bool:
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
                f"select {', '.join(TERMINOLOGY_TERM_COLUMNS)} from terminology_terms where {where} order by source_length",
                tuple(params),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else []

    def get_all_approved_terms(self, *, source_lang: str = "en", domain: Optional[str] = None) -> list[dict[str, Any]]:
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
                f"where {where}",
                tuple(params),
            )
            rows = _fetchall(cursor)
        return self._rows(rows) if rows else []

    def get_terms_by_owner(self, owner_user_id: str, *, page: int = 1, page_size: int = 20,
                           status: Optional[str] = None) -> tuple[list[dict[str, Any]], int]:
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
        updates = {
            "status": "approved",
            "reviewed_by_user_id": reviewed_by_user_id,
            "reviewed_at": _utc_now_naive(),
            "rejection_reason": None,
            "embedding_status": "pending",
        }
        return self.update_term(term_id, updates)

    def reject_term(self, term_id: str, reviewed_by_user_id: str, reason: Optional[str] = None) -> bool:
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
        """Approve multiple terms in a single SQL statement. Returns count of affected rows."""
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
        """Reject multiple terms in a single SQL statement. Returns count of affected rows."""
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
        """Delete multiple terms in a single SQL statement. Returns count of affected rows."""
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
                    "status": "pending_review",
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
        """Search terms with flexible filters and SQL-level pagination.

        Parameters
        ----------
        status : str, optional
            Filter by term status (e.g. ``"approved"``, ``"pending_review"``).
        source_lang : str, optional
            Filter by source language.
        target_lang : str, optional
            Filter by target language.
        domain : str, optional
            Filter by domain.
        query : str, optional
            LIKE search on ``source_term``.
        source_type : str, optional
            Filter by source type (e.g. ``"system"``, ``"imported"``).
        source_type : str, optional
            Filter by source type (e.g. ``"system"``, ``"imported"``).
        page : int
            Page number (1-based).
        page_size : int
            Items per page.

        Returns
        -------
        (list[dict], int)
            Tuple of (rows, total_count).
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
