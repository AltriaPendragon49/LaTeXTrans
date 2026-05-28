"""Milvus 向量检索器 - 基于嵌入向量的近似最近邻搜索"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── 优雅降级: pymilvus 为可选依赖 ────────────────────────────────────

try:
    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        connections,
        utility,
    )
except ImportError:  # pragma: no cover
    Collection = None
    CollectionSchema = None
    DataType = None
    FieldSchema = None
    connections = None
    utility = None
    logger.info("pymilvus is not installed; vector retrieval will be unavailable.")


# ── 常量 ─────────────────────────────────────────────────────────────

_PRIMARY_FIELD = "term_id"
_VECTOR_FIELD = "embedding"
_SOURCE_FIELD = "source_term"
_TARGET_FIELD = "target_term"
_METADATA_FIELD = "metadata"


# ── 检索器 ───────────────────────────────────────────────────────────


class VectorRetriever:
    """基于 Milvus 的向量检索器，用于已批准术语嵌入检索。

    参数
    ----------
    uri : str
        Milvus 服务器 URI（如 ``"http://localhost:19530"``）。
    collection_name : str
        用于术语嵌入的 Milvus 集合名称。
    embedding_dim : int
        嵌入向量维度（默认 384，适用于 all-MiniLM-L6-v2）。
    """

    def __init__(
        self,
        uri: str,
        collection_name: str,
        embedding_dim: int = 384,
    ) -> None:
        """初始化向量检索器

        参数:
            uri: Milvus 服务器 URI
            collection_name: 集合名称
            embedding_dim: 嵌入维度
        """
        self._uri = uri
        self._collection_name = collection_name
        self._embedding_dim = embedding_dim
        self._collection: Optional[Any] = None
        self._connected = False

    # ── 连接与集合生命周期 ───────────────────────────────────────────

    def _connect(self) -> bool:
        """连接到 Milvus 服务器，已连接则跳过"""
        if self._connected:
            return True
        if connections is None:
            logger.warning("pymilvus is not available; skipping Milvus connection.")
            return False

        try:
            connections.connect(alias="default", uri=self._uri)
            self._connected = True
            logger.info("Connected to Milvus at %s", self._uri)
            return True
        except Exception as exc:
            logger.warning("Failed to connect to Milvus: %s", exc)
            return False

    def ensure_collection(self) -> bool:
        """如果集合不存在则创建。

        返回
        -------
        bool
            集合就绪返回 ``True``，失败返回 ``False``。
        """
        if not self._connect():
            return False
        if Collection is None:
            return False

        try:
            if utility.has_collection(self._collection_name):
                self._collection = Collection(self._collection_name)
                logger.info(
                    "Using existing Milvus collection: %s", self._collection_name
                )
                return True
        except Exception as exc:
            logger.warning(
                "Error checking Milvus collection existence: %s", exc
            )
            return False

        try:
            fields = [
                FieldSchema(
                    name=_PRIMARY_FIELD,
                    dtype=DataType.VARCHAR,
                    max_length=128,
                    is_primary=True,
                ),
                FieldSchema(
                    name=_VECTOR_FIELD,
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self._embedding_dim,
                ),
                FieldSchema(
                    name=_SOURCE_FIELD,
                    dtype=DataType.VARCHAR,
                    max_length=512,
                ),
                FieldSchema(
                    name=_TARGET_FIELD,
                    dtype=DataType.VARCHAR,
                    max_length=512,
                ),
                FieldSchema(
                    name=_METADATA_FIELD,
                    dtype=DataType.JSON,
                ),
            ]
            schema = CollectionSchema(
                fields,
                description="Approved terminology embeddings",
            )
            self._collection = Collection(
                name=self._collection_name, schema=schema
            )

            # 在向量字段上创建 IVF_FLAT 索引以支持 ANN 搜索
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }
            self._collection.create_index(
                field_name=_VECTOR_FIELD, index_params=index_params
            )
            logger.info(
                "Created Milvus collection: %s (dim=%d)",
                self._collection_name,
                self._embedding_dim,
            )

            # 将集合加载到内存中以支持搜索
            self._collection.load()
            return True
        except Exception as exc:
            logger.warning("Failed to create Milvus collection: %s", exc)
            return False

    # ── 写入操作 ─────────────────────────────────────────────────────

    def upsert_term(
        self,
        term_id: str,
        embedding: list[float],
        source_term: str,
        target_term: str,
        metadata: dict | None = None,
    ) -> bool:
        """在 Milvus 中插入或更新单个术语嵌入。

        返回
        -------
        bool
            成功返回 ``True``，失败返回 ``False``。
        """
        if not self._ensure_ready():
            return False

        try:
            entities = [
                [term_id],
                [embedding],
                [source_term],
                [target_term],
                [metadata or {}],
            ]
            self._collection.insert(entities)
            self._collection.flush()
            return True
        except Exception as exc:
            logger.warning("Milvus upsert_term failed for %s: %s", term_id, exc)
            return False

    def batch_upsert(self, entries: list[dict]) -> bool:
        """在 Milvus 中批量插入或更新多个术语嵌入。

        每个 *entry* 字典必须包含: ``term_id``, ``embedding``,
        ``source_term``, ``target_term`` 以及可选的 ``metadata``。

        返回
        -------
        bool
            成功返回 ``True``，失败返回 ``False``。
        """
        if not self._ensure_ready():
            return False
        if not entries:
            return True

        try:
            ids = [e["term_id"] for e in entries]
            embeddings = [e["embedding"] for e in entries]
            source_terms = [e.get("source_term", "") for e in entries]
            target_terms = [e.get("target_term", "") for e in entries]
            metadata_list = [e.get("metadata", {}) for e in entries]

            entities = [ids, embeddings, source_terms, target_terms, metadata_list]
            self._collection.insert(entities)
            self._collection.flush()
            logger.info("Milvus batch_upsert: %d terms", len(entries))
            return True
        except Exception as exc:
            logger.warning("Milvus batch_upsert failed: %s", exc)
            return False

    # ── 读取操作 ─────────────────────────────────────────────────────

    def search(
        self,
        embedding: list[float],
        top_n: int = 20,
    ) -> list[dict]:
        """在 Milvus 中搜索最近邻术语。

        参数
        ----------
        embedding : list[float]
            查询向量。
        top_n : int
            返回的结果数量。

        返回
        -------
        list[dict]
            每个条目格式::

                {
                    "term_id": …,
                    "source_term": …,
                    "target_term": …,
                    "vector_score": float,
                    "retrieval_source": "vector",
                }

            失败时返回空列表。
        """
        if not self._ensure_ready():
            return []

        try:
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10},
            }
            results = self._collection.search(
                data=[embedding],
                anns_field=_VECTOR_FIELD,
                param=search_params,
                limit=top_n,
                output_fields=[_PRIMARY_FIELD, _SOURCE_FIELD, _TARGET_FIELD],
            )

            candidates = []
            for hits in results:
                for hit in hits:
                    candidates.append(
                        {
                            "term_id": hit.entity.get(_PRIMARY_FIELD),
                            "source_term": str(
                                hit.entity.get(_SOURCE_FIELD, "")
                            ),
                            "target_term": str(
                                hit.entity.get(_TARGET_FIELD, "")
                            ),
                            "vector_score": float(hit.score),
                            "retrieval_source": "vector",
                        }
                    )
            return candidates
        except Exception as exc:
            logger.warning("Milvus search failed: %s", exc)
            return []

    def delete_term(self, term_id: str) -> bool:
        """按 ``term_id`` 从 Milvus 删除术语。

        返回
        -------
        bool
            成功返回 ``True``，失败返回 ``False``。
        """
        if not self._ensure_ready():
            return False

        try:
            self._collection.delete(f'{_PRIMARY_FIELD} == "{term_id}"')
            self._collection.flush()
            return True
        except Exception as exc:
            logger.warning("Milvus delete_term failed for %s: %s", term_id, exc)
            return False

    # ── 健康检查 ─────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """返回 Milvus 连接和集合是否可用"""
        if not self._connect():
            return False
        if utility is None:
            return False
        try:
            return utility.has_collection(self._collection_name)
        except Exception:
            return False

    # ── 内部辅助方法 ─────────────────────────────────────────────────

    def _ensure_ready(self) -> bool:
        """确保集合已加载，必要时创建"""
        if self._collection is not None:
            return True
        return self.ensure_collection()
