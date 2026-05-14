from __future__ import annotations

import pytest

from backend.app.services.rag.bm25_retriever import Bm25Retriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_term(term_id: str, source_term: str, target_term: str = "") -> dict:
    return {"id": term_id, "source_term": source_term, "target_term": target_term or source_term}


SAMPLE_TERMS = [
    _make_term("t1", "attention mechanism", "注意力机制"),
    _make_term("t2", "transformer", "Transformer模型"),
    _make_term("t3", "batch normalization", "批归一化"),
    _make_term("t4", "dropout", "丢弃法"),
    _make_term("t5", "convolutional neural network", "卷积神经网络"),
    _make_term("t6", "recurrent neural network", "循环神经网络"),
    _make_term("t7", "gradient descent", "梯度下降"),
    _make_term("t8", "backpropagation", "反向传播"),
    _make_term("t9", "embedding", "嵌入"),
    _make_term("t10", "softmax", "Softmax函数"),
]


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

class TestBuildIndex:
    def test_build_index_with_terms(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(SAMPLE_TERMS)
        assert retriever.is_ready is True

    def test_build_index_empty_terms(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index([])
        assert retriever.is_ready is True

    def test_build_index_none_terms(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(None)  # type: ignore[arg-type]
        assert retriever.is_ready is True

    def test_refresh_rebuilds_index(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(SAMPLE_TERMS[:3])
        assert retriever.is_ready is True

        # Refresh with different set
        other = [_make_term("t99", "custom term", "自定义")]
        retriever.refresh(other)
        results = retriever.search("custom")
        assert len(results) == 1
        assert results[0]["term_id"] == "t99"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_returns_relevant_terms(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(SAMPLE_TERMS)
        results = retriever.search("neural network")
        assert len(results) > 0
        # "convolutional neural network" or "recurrent neural network" should score highly
        source_terms = [r["source_term"] for r in results]
        assert any("neural network" in s for s in source_terms)

    def test_search_returns_empty_for_empty_query(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(SAMPLE_TERMS)
        assert retriever.search("") == []
        assert retriever.search("   ") == []

    def test_search_returns_empty_when_not_ready(self) -> None:
        retriever = Bm25Retriever()
        assert retriever.is_ready is False
        assert retriever.search("anything") == []

    def test_search_returns_empty_for_empty_index(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index([])
        results = retriever.search("neural network")
        assert results == []

    def test_search_respects_top_n(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(SAMPLE_TERMS)
        results = retriever.search("network", top_n=3)
        assert len(results) <= 3

    def test_search_result_shape(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(SAMPLE_TERMS[:1])
        results = retriever.search("attention", top_n=5)
        assert len(results) == 1
        entry = results[0]
        assert "term_id" in entry
        assert "source_term" in entry
        assert "target_term" in entry
        assert "bm25_score" in entry
        assert "retrieval_source" in entry
        assert entry["retrieval_source"] == "bm25"
        assert isinstance(entry["bm25_score"], float)

    def test_search_scores_are_descending(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index(SAMPLE_TERMS)
        results = retriever.search("attention mechanism transformer", top_n=10)
        scores = [r["bm25_score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_single_term(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index([_make_term("t1", "singular", "单一")])
        results = retriever.search("singular")
        assert len(results) == 1

    def test_terms_with_special_characters(self) -> None:
        terms = [_make_term("t1", "C++", "C加加"), _make_term("t2", "F#", "F Sharp")]
        retriever = Bm25Retriever()
        retriever.build_index(terms)
        results = retriever.search("C++")
        assert len(results) >= 1

    def test_case_insensitive_matching(self) -> None:
        retriever = Bm25Retriever()
        retriever.build_index([_make_term("t1", "Attention Is All You Need", "注意力机制")])
        results = retriever.search("attention")
        assert len(results) >= 1

    def test_custom_tokenizer(self) -> None:
        def custom_tokenizer(text: str) -> list[str]:
            return text.lower().split()

        retriever = Bm25Retriever(tokenizer=custom_tokenizer)
        retriever.build_index([_make_term("t1", "hello world", "你好世界")])
        results = retriever.search("hello world")
        assert len(results) == 1
