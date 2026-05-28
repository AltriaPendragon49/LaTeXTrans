"""RAG 术语检索流水线 - 混合检索 + 重排序 + 术语表格式化"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from backend.app.services.rag.bm25_retriever import Bm25Retriever
from backend.app.services.rag.cross_encoder_reranker import CrossEncoderReranker
from backend.app.services.rag.embedding_client import EmbeddingClient
from backend.app.services.rag.glossary_formatter import (
    estimate_token_count,
    format_glossary_block,
    truncate_glossary,
)
from backend.app.services.rag.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)

# ── 流水线 ───────────────────────────────────────────────────────────


class RagTerminologyPipeline:
    """编排三阶段 RAG 术语流水线。

    阶段
    ------
    1. 查询变换（从文本块中提取纯文本关键词）。
    2. 混合检索（BM25 关键词 + 可选 Milvus 向量）。
    3. Cross-Encoder 重排序。
    4. 术语表格式化（用于注入提示）。

    每个阶段都是容错的：失败时记录警告并继续执行，
    确保翻译永远不会被阻塞。
    """

    def __init__(
        self,
        bm25_retriever: Bm25Retriever,
        vector_retriever: Optional[VectorRetriever],
        reranker: Optional[CrossEncoderReranker],
        embedding_client: Optional[EmbeddingClient],
        # TerminologyRepository 可在此注入，但在仓库层实现之前可为 None。
        # 用于可选的 MySQL 精确/前缀查找，补充混合检索。
        terminology_repository: Optional[Any] = None,
    ) -> None:
        """初始化 RAG 术语流水线

        参数:
            bm25_retriever: BM25 关键词检索器
            vector_retriever: 向量检索器（可选）
            reranker: Cross-Encoder 重排序器（可选）
            embedding_client: 嵌入客户端（可选）
            terminology_repository: 术语仓库（可选）
        """
        self._bm25 = bm25_retriever
        self._vector = vector_retriever
        self._reranker = reranker
        self._embedding = embedding_client
        self._repo = terminology_repository

    # ── 主入口点 ─────────────────────────────────────────────────────

    def run_pipeline(
        self,
        chunk_text: str,
        *,
        source_lang: str = "en",
        target_lang: str = "zh",
        top_n: int = 10,
        max_glossary_tokens: int = 512,
    ) -> dict:
        """为单个文本块运行完整的 RAG 术语流水线。

        参数
        ----------
        chunk_text : str
            待翻译的纯文本（或轻度清洗的 LaTeX）文本块。
        source_lang : str
            源语言代码（当前实现未使用，保留供未来语言感知检索）。
        target_lang : str
            目标语言代码（保留）。
        top_n : int
            术语表块中包含的最终术语数量。
        max_glossary_tokens : int
            格式化术语表块的最大 token 预算。

        返回
        -------
        dict
            ``{
                "glossary_block": str,
                "selected_terms": list[dict],
                "total_candidates": int,
                "retrieval_sources": list[str],
            }``

            任何不可恢复的失败时返回空术语表。
        """
        # -- 阶段 1: 查询变换 ------------------------------------------
        query = self._transform_query(chunk_text)
        if not query:
            return self._empty_result()

        retrieval_sources: list[str] = []

        # -- 阶段 2a: BM25 检索 ---------------------------------------
        bm25_candidates = self._safe_bm25_search(query, top_n=top_n * 2)
        if bm25_candidates:
            retrieval_sources.append("bm25")

        # -- 阶段 2b: 向量检索 ----------------------------------------
        vector_candidates: list[dict] = []
        if self._vector is not None and self._embedding is not None:
            vector_candidates = self._safe_vector_search(query, top_n=top_n * 2)
            if vector_candidates:
                retrieval_sources.append("vector")

        # -- 可选: MySQL 精确/前缀查找 ---------------------------------
        repo_candidates: list[dict] = []
        if self._repo is not None:
            try:
                repo_candidates = self._safe_repo_search(
                    query, source_lang, target_lang, top_n=top_n
                )
                if repo_candidates:
                    retrieval_sources.append("repository")
            except Exception:
                logger.warning("Repository search failed; skipping.", exc_info=True)

        # -- 阶段 3: 合并与去重 ----------------------------------------
        merged = self._merge_candidates(bm25_candidates, vector_candidates)
        merged = self._merge_candidates(merged, repo_candidates)

        if not merged:
            return self._empty_result()

        total_candidates = len(merged)

        # -- 阶段 4: Cross-Encoder 重排序 ------------------------------
        if self._reranker is not None and self._reranker.is_available():
            try:
                reranked = self._reranker.rerank(query, merged, top_n=top_n)
                if reranked:
                    retrieval_sources.append("reranker")
            except Exception as exc:
                logger.warning("Reranker failed; using merged scores: %s", exc)
                reranked = self._score_merge_sort(merged)[:top_n]
        else:
            reranked = self._score_merge_sort(merged)[:top_n]

        selected_terms = reranked[:top_n]

        # -- 阶段 5: 格式化术语表 --------------------------------------
        glossary_block = format_glossary_block(selected_terms)

        # 如有需要，应用 token 预算截断。
        if glossary_block and max_glossary_tokens > 0:
            estimated = estimate_token_count(glossary_block)
            if estimated > max_glossary_tokens:
                glossary_block = truncate_glossary(glossary_block, max_glossary_tokens)

        return {
            "glossary_block": glossary_block,
            "selected_terms": selected_terms,
            "total_candidates": total_candidates,
            "retrieval_sources": retrieval_sources,
        }

    # ── 索引维护 ─────────────────────────────────────────────────────

    def refresh_indexes(self, approved_terms: list[dict]) -> None:
        """从新的已批准术语列表重建 BM25 索引。

        参数
        ----------
        approved_terms : list[dict]
            已批准术语字典列表，每个至少包含 ``id`` 和 ``source_term``。
        """
        try:
            self._bm25.refresh(approved_terms)
            logger.info("BM25 index refreshed with %d terms", len(approved_terms))
        except Exception as exc:
            logger.warning("Failed to refresh BM25 index: %s", exc)

    # ── 属性 ─────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """BM25 索引是否已构建并可用于检索"""
        return self._bm25.is_ready

    # ── 内部: 查询变换 ───────────────────────────────────────────────

    @staticmethod
    def _transform_query(chunk_text: str) -> str:
        """从 LaTeX 文本块中提取纯文本查询。

        当前去除最简 LaTeX 结构并原样返回清洗后的文本。
        未来版本可能提取关键词短语或名词块。
        """
        if not chunk_text or not chunk_text.strip():
            return ""

        text = chunk_text.strip()

        # 去除常见 LaTeX 命令和大括号以获得更干净的查询文本。
        text = re.sub(r"\\(?:textbf|textit|emph|textsf|texttt)\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+(?:\{[^}]*\})?", "", text)
        text = re.sub(r"[{}]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    # ── 内部: 安全包装器 ─────────────────────────────────────────────

    def _safe_bm25_search(self, query: str, top_n: int) -> list[dict]:
        """安全的 BM25 搜索（捕获异常）"""
        try:
            return self._bm25.search(query, top_n=top_n)
        except Exception as exc:
            logger.warning("BM25 search error: %s", exc)
            return []

    def _safe_vector_search(self, query: str, top_n: int) -> list[dict]:
        """安全的向量搜索（捕获异常）"""
        try:
            embedding = self._embedding.encode([query])
            if not embedding:
                return []
            return self._vector.search(embedding[0], top_n=top_n)
        except Exception as exc:
            logger.warning("Vector search error: %s", exc)
            return []

    def _safe_repo_search(
        self,
        query: str,
        source_lang: str,
        target_lang: str,
        top_n: int,
    ) -> list[dict]:
        """委托给 TerminologyRepository.exact_search（如果可用）。

        仓库接口预期暴露一个 ``exact_search`` 方法，返回与
        BM25/向量结果相同格式的候选字典列表。
        """
        if not hasattr(self._repo, "search_approved_terms"):
            return []
        return self._repo.search_approved_terms(
            query=query,
            source_lang=source_lang,
            target_lang=target_lang,
        )[:top_n]

    # ── 内部: 合并与排序 ─────────────────────────────────────────────

    @staticmethod
    def _merge_candidates(
        *candidate_lists: list[dict],
    ) -> list[dict]:
        """按 ``term_id`` 去重候选项，保留更高评分。

        评分优先级: ``rerank_score`` > ``vector_score`` > ``bm25_score``。
        当同一术语从多个来源出现时，保留有效评分最高的条目。
        """
        merged: dict[str, dict] = {}

        for candidates in candidate_lists:
            for c in candidates:
                tid = c.get("term_id")
                if tid is None:
                    continue

                if tid in merged:
                    existing = merged[tid]
                    # 选择有效评分更高的候选项。
                    if _effective_score(c) > _effective_score(existing):
                        merged[tid] = c
                else:
                    merged[tid] = c

        return list(merged.values())

    @staticmethod
    def _score_merge_sort(candidates: list[dict]) -> list[dict]:
        """按最佳可用相关性评分排序候选项"""
        candidates.sort(key=_effective_score, reverse=True)
        return candidates

    @staticmethod
    def _empty_result() -> dict:
        """返回空结果字典"""
        return {
            "glossary_block": "",
            "selected_terms": [],
            "total_candidates": 0,
            "retrieval_sources": [],
        }


# ── 模块级辅助函数 ──────────────────────────────────────────────────


def _effective_score(candidate: dict) -> float:
    """返回候选项的最高可用相关性评分"""
    return max(
        float(candidate.get("rerank_score", 0.0) or 0.0),
        float(candidate.get("vector_score", 0.0) or 0.0),
        float(candidate.get("bm25_score", 0.0) or 0.0),
    )
