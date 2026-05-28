"""BM25 关键词检索器 - 基于内存的文本检索"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── 默认分词器 ───────────────────────────────────────────────────────

_WORD_SPLIT_RE = re.compile(r"[^\w]+")


def _default_tokenize(text: str) -> list[str]:
    """基于空白和常见标点的小写分词"""
    return [t for t in _WORD_SPLIT_RE.split(text.lower()) if t]


# ── 检索器 ───────────────────────────────────────────────────────────


class Bm25Retriever:
    """基于内存的 BM25 关键词检索器，用于已批准术语检索。

    底层使用 ``rank_bm25`` 库（BM25Okapi 变体）。

    参数
    ----------
    tokenizer : callable, 可选
        可调用对象 ``(str) -> list[str]``，用于对索引词和查询进行分词。
        默认使用基于非单词字符的小写分词。
    """

    def __init__(self, tokenizer=None) -> None:
        """初始化 BM25 检索器

        参数:
            tokenizer: 自定义分词器（可选）
        """
        self._tokenizer = tokenizer or _default_tokenize
        self._terms: list[dict] = []
        self._bm25 = None
        self._ready = False

    # ── 索引构建 / 刷新 ──────────────────────────────────────────────

    def build_index(self, terms: list[dict]) -> None:
        """对每个条目的 ``source_term`` 进行分词并构建 BM25 索引。

        参数
        ----------
        terms : list[dict]
            每个字典必须包含 ``id`` 和 ``source_term`` 键。
            其他键（``target_term``, ``language_pair`` 等）将原样保留在内部存储中。
        """
        try:
            from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
        except ImportError as exc:
            logger.warning(
                "rank_bm25 is not installed; BM25 retrieval will be unavailable. "
                "Install with: pip install rank-bm25"
            )
            self._terms = list(terms) if terms else []
            self._bm25 = None
            self._ready = False
            return

        self._terms = list(terms) if terms else []

        if not self._terms:
            self._bm25 = None
            self._ready = True
            logger.info("BM25 index built (empty corpus)")
            return

        tokenized_corpus = [
            self._tokenizer(str(t.get("source_term", ""))) for t in self._terms
        ]
        self._bm25 = BM25Okapi(tokenized_corpus)
        self._ready = True
        logger.info("BM25 index built with %d terms", len(self._terms))

    def refresh(self, terms: list[dict]) -> None:
        """从头重建 BM25 索引。

        等效于用新术语列表调用 :meth:`build_index`。
        """
        self.build_index(terms)

    # ── 检索 ──────────────────────────────────────────────────────────

    def search(self, query: str, top_n: int = 20) -> list[dict]:
        """根据 *query* 对每个索引词评分，返回前 ``top_n`` 个结果。

        参数
        ----------
        query : str
            自由文本查询（如 LaTeX 文本块）。
        top_n : int
            返回的最大候选词数量。

        返回
        -------
        list[dict]
            每个字典格式如下::

                {
                    "term_id": …,
                    "source_term": …,
                    "target_term": …,
                    "bm25_score": float,
                    "retrieval_source": "bm25",
                }

            未就绪或出错时返回空列表。
        """
        if not self._ready or self._bm25 is None or not self._terms:
            return []

        if not query or not query.strip():
            return []

        try:
            tokenized_query = self._tokenizer(query)
            scores = self._bm25.get_scores(tokenized_query)
        except Exception as exc:
            logger.warning("BM25 search failed: %s", exc)
            return []

        candidates = []
        for idx, term in enumerate(self._terms):
            score = float(scores[idx]) if idx < len(scores) else 0.0
            candidates.append(
                {
                    "term_id": term.get("id"),
                    "source_term": str(term.get("source_term", "")),
                    "target_term": str(term.get("target_term", "")),
                    "bm25_score": score,
                    "retrieval_source": "bm25",
                }
            )

        candidates.sort(key=lambda c: c["bm25_score"], reverse=True)
        return candidates[:top_n]

    # ── 属性 ──────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """BM25 索引是否已成功构建"""
        return self._ready
