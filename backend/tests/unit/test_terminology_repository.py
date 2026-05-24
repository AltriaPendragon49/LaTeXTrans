import sqlite3
from pathlib import Path

import pytest

from backend.app.core.config import get_settings
from backend.app.repositories.terminology_repository import TerminologyRepository


def _create_sqlite_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table if not exists terminology_terms (
                id                  varchar(64)  not null primary key,
                source_term         varchar(512) not null,
                target_term         varchar(512) not null,
                source_lang         varchar(16)  not null default 'en',
                target_lang         varchar(16)  not null default 'zh',
                domain              varchar(128)          default null,
                source_type         varchar(32)  not null default 'auto_extracted',
                status              varchar(32)  not null default 'pending_review',
                owner_user_id       varchar(64)          default null,
                created_by_user_id  varchar(64)          default null,
                reviewed_by_user_id varchar(64)          default null,
                reviewed_at         datetime             default null,
                rejection_reason    varchar(1024)        default null,
                extracted_from_task_id varchar(64)       default null,
                provenance          text                 default null,
                embedding_model     varchar(128)         default null,
                embedding_status    varchar(32)  not null default 'none',
                vector_collection   varchar(128)         default null,
                vector_term_id      varchar(128)         default null,
                source_length       integer              default null,
                created_at          datetime     not null,
                updated_at          datetime     not null
            );
            create table if not exists terminology_match_log (
                id                  varchar(64)  not null primary key,
                task_id             varchar(64)  not null,
                term_id             varchar(64)  not null,
                chunk_index         int          not null default 0,
                retrieval_source    varchar(32)  not null default 'bm25',
                was_injected        tinyint      not null default 0,
                rerank_score        float                default null,
                created_at          datetime     not null
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TerminologyRepository:
    database_path = tmp_path / "terminology.db"
    _create_sqlite_schema(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    return TerminologyRepository()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestCrud:
    def test_insert_and_get_term(self, repo: TerminologyRepository) -> None:
        payload = {
            "source_term": "attention mechanism",
            "target_term": "注意力机制",
            "domain": "deep_learning",
            "source_lang": "en",
            "target_lang": "zh",
            "source_type": "system",
            "status": "approved",
        }
        inserted = repo.insert_term(payload)
        assert inserted["source_term"] == "attention mechanism"
        assert inserted["target_term"] == "注意力机制"
        assert inserted["domain"] == "deep_learning"
        assert inserted["status"] == "approved"
        assert inserted["id"] is not None

        fetched = repo.get_term(inserted["id"])
        assert fetched is not None
        assert fetched["source_term"] == "attention mechanism"

    def test_get_term_returns_none_for_missing(self, repo: TerminologyRepository) -> None:
        assert repo.get_term("nonexistent-id") is None

    def test_update_term(self, repo: TerminologyRepository) -> None:
        inserted = repo.insert_term({"source_term": "transformer", "target_term": "变压器"})
        updated = repo.update_term(inserted["id"], {"target_term": "Transformer模型", "domain": "deep_learning"})
        assert updated is True

        fetched = repo.get_term(inserted["id"])
        assert fetched is not None
        assert fetched["target_term"] == "Transformer模型"
        assert fetched["domain"] == "deep_learning"

    def test_update_term_returns_false_for_nonexistent(self, repo: TerminologyRepository) -> None:
        assert repo.update_term("no-such-id", {"target_term": "x"}) is False

    def test_delete_term(self, repo: TerminologyRepository) -> None:
        inserted = repo.insert_term({"source_term": "to_delete", "target_term": "待删除"})
        deleted = repo.delete_term(inserted["id"])
        assert deleted is True
        assert repo.get_term(inserted["id"]) is None

    def test_delete_term_returns_false_for_nonexistent(self, repo: TerminologyRepository) -> None:
        assert repo.delete_term("no-such-id") is False

    def test_update_deleted_term(self, repo: TerminologyRepository) -> None:
        inserted = repo.insert_term({"source_term": "temp", "target_term": "临时"})
        repo.delete_term(inserted["id"])
        # Updating a deleted (nonexistent) term should return False
        assert repo.update_term(inserted["id"], {"target_term": "已删除"}) is False

    def test_get_term_with_empty_id(self, repo: TerminologyRepository) -> None:
        assert repo.get_term("") is None


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

class TestReviewWorkflow:
    def test_approve_term(self, repo: TerminologyRepository) -> None:
        inserted = repo.insert_term({"source_term": "batch norm", "target_term": "批归一化"})
        assert inserted["status"] == "pending_review"

        approved = repo.approve_term(inserted["id"], "reviewer-1")
        assert approved is True

        fetched = repo.get_term(inserted["id"])
        assert fetched is not None
        assert fetched["status"] == "approved"
        assert fetched["reviewed_by_user_id"] == "reviewer-1"
        assert fetched["embedding_status"] == "pending"

    def test_reject_term(self, repo: TerminologyRepository) -> None:
        inserted = repo.insert_term({"source_term": "bad term", "target_term": "错误术语"})
        rejected = repo.reject_term(inserted["id"], "reviewer-1", reason="incorrect translation")
        assert rejected is True

        fetched = repo.get_term(inserted["id"])
        assert fetched is not None
        assert fetched["status"] == "rejected"
        assert fetched["rejection_reason"] == "incorrect translation"
        assert fetched["embedding_status"] == "none"

    def test_reject_term_without_reason(self, repo: TerminologyRepository) -> None:
        inserted = repo.insert_term({"source_term": "vague", "target_term": "模糊"})
        repo.reject_term(inserted["id"], "reviewer-1")
        fetched = repo.get_term(inserted["id"])
        assert fetched is not None
        assert fetched["status"] == "rejected"
        assert fetched["rejection_reason"] is None

    def test_double_reject_is_idempotent(self, repo: TerminologyRepository) -> None:
        inserted = repo.insert_term({"source_term": "double", "target_term": "双重"})
        repo.reject_term(inserted["id"], "reviewer-1", reason="first")
        repo.reject_term(inserted["id"], "reviewer-2", reason="second")
        fetched = repo.get_term(inserted["id"])
        assert fetched is not None
        assert fetched["status"] == "rejected"
        # The second rejection updates the reviewer and reason
        assert fetched["reviewed_by_user_id"] == "reviewer-2"
        assert fetched["rejection_reason"] == "second"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_approved_terms_by_domain(self, repo: TerminologyRepository) -> None:
        repo.insert_term({"source_term": "CNN", "target_term": "卷积神经网络", "domain": "cv", "status": "approved"})
        repo.insert_term({"source_term": "RNN", "target_term": "循环神经网络", "domain": "deep_learning", "status": "approved"})
        repo.insert_term({"source_term": "LSTM", "target_term": "长短期记忆", "domain": "deep_learning", "status": "pending_review"})

        results = repo.search_approved_terms(domain="deep_learning")
        assert len(results) == 1
        assert results[0]["source_term"] == "RNN"

    def test_search_approved_terms_by_query(self, repo: TerminologyRepository) -> None:
        repo.insert_term({"source_term": "batch normalization", "target_term": "批归一化", "status": "approved"})
        repo.insert_term({"source_term": "layer normalization", "target_term": "层归一化", "status": "approved"})
        repo.insert_term({"source_term": "dropout", "target_term": "丢弃法", "status": "approved"})

        results = repo.search_approved_terms(query="normalization")
        assert len(results) == 2

    def test_search_approved_terms_filters_pending(self, repo: TerminologyRepository) -> None:
        repo.insert_term({"source_term": "attention", "target_term": "注意力", "status": "pending_review"})
        results = repo.search_approved_terms()
        assert len(results) == 0

    def test_get_all_approved_terms(self, repo: TerminologyRepository) -> None:
        repo.insert_term({"source_term": "term_a", "target_term": "术语A", "status": "approved"})
        repo.insert_term({"source_term": "term_b", "target_term": "术语B", "status": "approved"})
        repo.insert_term({"source_term": "term_c", "target_term": "术语C", "status": "pending_review"})

        all_approved = repo.get_all_approved_terms()
        assert len(all_approved) == 2

    def test_search_terms_with_filters(self, repo: TerminologyRepository) -> None:
        repo.insert_term({"source_term": "GPU", "target_term": "图形处理器", "domain": "hardware", "status": "approved"})
        repo.insert_term({"source_term": "TPU", "target_term": "张量处理器", "domain": "hardware", "status": "pending_review"})
        repo.insert_term({"source_term": "CPU", "target_term": "中央处理器", "domain": "hardware", "status": "approved"})

        results, total = repo.search_terms(status="approved", domain="hardware")
        assert total == 2
        assert len(results) == 2

    def test_search_terms_pagination(self, repo: TerminologyRepository) -> None:
        for i in range(5):
            repo.insert_term({"source_term": f"term_{i}", "target_term": f"术语{i}", "status": "approved"})

        page1, total = repo.search_terms(page=1, page_size=2)
        assert total == 5
        assert len(page1) == 2

        page2, total = repo.search_terms(page=2, page_size=2)
        assert total == 5
        assert len(page2) == 2


# ---------------------------------------------------------------------------
# Owner scoping
# ---------------------------------------------------------------------------

class TestOwnerScoping:
    def test_get_terms_by_owner(self, repo: TerminologyRepository) -> None:
        repo.insert_term({"source_term": "my_term", "target_term": "我的术语", "owner_user_id": "user-1"})
        repo.insert_term({"source_term": "other_term", "target_term": "其他术语", "owner_user_id": "user-2"})

        owned, total = repo.get_terms_by_owner("user-1")
        assert total == 1
        assert len(owned) == 1
        assert owned[0]["source_term"] == "my_term"

    def test_get_terms_by_owner_with_status_filter(self, repo: TerminologyRepository) -> None:
        repo.insert_term({"source_term": "approved_term", "target_term": "已批准", "owner_user_id": "user-1", "status": "approved"})
        repo.insert_term({"source_term": "pending_term", "target_term": "待审核", "owner_user_id": "user-1", "status": "pending_review"})

        owned, total = repo.get_terms_by_owner("user-1", status="approved")
        assert total == 1
        assert owned[0]["source_term"] == "approved_term"


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------

class TestBatch:
    def test_insert_terms_batch(self, repo: TerminologyRepository) -> None:
        terms = [
            {"source_term": "batch_1", "target_term": "批量1", "domain": "test"},
            {"source_term": "batch_2", "target_term": "批量2", "domain": "test"},
        ]
        ids = repo.insert_terms_batch(terms)
        assert len(ids) == 2

        fetched = repo.get_term(ids[0])
        assert fetched is not None
        assert fetched["source_term"] == "batch_1"

    def test_insert_terms_batch_empty(self, repo: TerminologyRepository) -> None:
        ids = repo.insert_terms_batch([])
        assert ids == []


# ---------------------------------------------------------------------------
# Match logs
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Embedding status 更新 (set_embedding_status)
# ---------------------------------------------------------------------------

class TestEmbeddingStatus:
    """set_embedding_status 状态更新测试。"""

    def test_set_embedding_status_completed_with_all_fields(self, repo: TerminologyRepository) -> None:
        """更新 embedding_status 为 completed，同时设置 model/collection/vector_term_id。"""
        inserted = repo.insert_term({"source_term": "word2vec", "target_term": "词向量"})
        assert repo.set_embedding_status(
            inserted["id"],
            "completed",
            model="sentence-transformers/all-MiniLM-L6-v2",
            collection="terminology_terms",
            vector_term_id="vec-001",
        ) is True

        fetched = repo.get_term(inserted["id"])
        assert fetched["embedding_status"] == "completed"
        assert fetched["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert fetched["vector_collection"] == "terminology_terms"
        assert fetched["vector_term_id"] == "vec-001"

    def test_set_embedding_status_in_progress(self, repo: TerminologyRepository) -> None:
        """更新为 in_progress 状态。"""
        inserted = repo.insert_term({"source_term": "GloVe", "target_term": "全局向量"})
        assert repo.set_embedding_status(inserted["id"], "in_progress") is True

        fetched = repo.get_term(inserted["id"])
        assert fetched["embedding_status"] == "in_progress"
        # 未传入可选字段，不被覆盖
        assert fetched["embedding_model"] is None
        assert fetched["vector_collection"] is None

    def test_set_embedding_status_error(self, repo: TerminologyRepository) -> None:
        """错误状态可以正确记录。"""
        inserted = repo.insert_term({"source_term": "BERT", "target_term": "BERT模型"})
        assert repo.set_embedding_status(inserted["id"], "error") is True

        fetched = repo.get_term(inserted["id"])
        assert fetched["embedding_status"] == "error"

    def test_set_embedding_status_partial_update(self, repo: TerminologyRepository) -> None:
        """仅传入部分可选字段。"""
        inserted = repo.insert_term({"source_term": "ELMo", "target_term": "ELMo模型"})
        assert repo.set_embedding_status(
            inserted["id"], "completed", model="custom-model"
        ) is True

        fetched = repo.get_term(inserted["id"])
        assert fetched["embedding_status"] == "completed"
        assert fetched["embedding_model"] == "custom-model"
        assert fetched["vector_collection"] is None  # 未传入

    def test_set_embedding_status_nonexistent(self, repo: TerminologyRepository) -> None:
        """更新不存在术语的 embedding 状态返回 False。"""
        assert repo.set_embedding_status("no-such-id", "completed") is False

    def test_set_embedding_status_transitions(self, repo: TerminologyRepository) -> None:
        """embedding 状态可多次更新（none -> pending -> in_progress -> completed）。"""
        inserted = repo.insert_term({"source_term": "stateful", "target_term": "有状态"})
        assert inserted["embedding_status"] == "none"

        # 批准触发 pending 状态
        repo.approve_term(inserted["id"], "reviewer-1")
        assert repo.get_term(inserted["id"])["embedding_status"] == "pending"

        # 开始处理
        repo.set_embedding_status(inserted["id"], "in_progress")
        assert repo.get_term(inserted["id"])["embedding_status"] == "in_progress"

        # 完成
        repo.set_embedding_status(inserted["id"], "completed", model="all-MiniLM-L6-v2")
        assert repo.get_term(inserted["id"])["embedding_status"] == "completed"

        # 出错也可以覆盖
        repo.set_embedding_status(inserted["id"], "error")
        assert repo.get_term(inserted["id"])["embedding_status"] == "error"


class TestMatchLogs:
    def test_insert_and_get_match_logs(self, repo: TerminologyRepository) -> None:
        term = repo.insert_term({"source_term": "attention", "target_term": "注意力", "status": "approved"})

        log_id = repo.insert_match_log({
            "task_id": "task-1",
            "term_id": term["id"],
            "chunk_index": 0,
            "retrieval_source": "bm25",
            "was_injected": True,
            "rerank_score": 0.95,
        })
        assert log_id is not None

        logs = repo.get_match_logs_for_task("task-1")
        assert len(logs) == 1
        assert logs[0]["term_id"] == term["id"]
        assert logs[0]["was_injected"] == 1
        assert logs[0]["source_term"] == "attention"  # from join

    def test_get_match_logs_empty_for_unknown_task(self, repo: TerminologyRepository) -> None:
        assert repo.get_match_logs_for_task("nonexistent-task") == []
