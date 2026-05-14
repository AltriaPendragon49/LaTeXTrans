from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.app.services.rag.bm25_retriever import Bm25Retriever
from backend.app.services.rag.cross_encoder_reranker import CrossEncoderReranker
from backend.app.services.rag.embedding_client import EmbeddingClient
from backend.app.services.rag.pipeline import RagTerminologyPipeline
from backend.app.services.rag.vector_retriever import VectorRetriever


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_TERMS = [
    {"id": "t1", "source_term": "attention mechanism", "target_term": "注意力机制", "bm25_score": 0.0},
    {"id": "t2", "source_term": "transformer", "target_term": "Transformer模型", "bm25_score": 0.0},
    {"id": "t3", "source_term": "batch normalization", "target_term": "批归一化", "bm25_score": 0.0},
    {"id": "t4", "source_term": "convolutional neural network", "target_term": "卷积神经网络", "bm25_score": 0.0},
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bm25() -> Bm25Retriever:
    retriever = Bm25Retriever()
    retriever.build_index(SAMPLE_TERMS)
    return retriever


@pytest.fixture
def pipeline(bm25: Bm25Retriever) -> RagTerminologyPipeline:
    return RagTerminologyPipeline(
        bm25_retriever=bm25,
        vector_retriever=None,
        reranker=None,
        embedding_client=None,
    )


# ---------------------------------------------------------------------------
# _merge_candidates
# ---------------------------------------------------------------------------

class TestMergeCandidates:
    def test_deduplicates_by_term_id(self) -> None:
        bm25_results = [
            {"term_id": "t1", "source_term": "attention", "bm25_score": 0.8, "retrieval_source": "bm25"},
            {"term_id": "t2", "source_term": "transformer", "bm25_score": 0.5, "retrieval_source": "bm25"},
        ]
        vector_results = [
            {"term_id": "t1", "source_term": "attention", "vector_score": 0.9, "retrieval_source": "vector"},
        ]

        merged = RagTerminologyPipeline._merge_candidates(bm25_results, vector_results)
        assert len(merged) == 2
        # t1 should have the vector_score since it's higher
        t1 = [m for m in merged if m["term_id"] == "t1"][0]
        assert t1["vector_score"] == 0.9

    def test_keeps_higher_score_for_duplicate(self) -> None:
        lower = [{"term_id": "t1", "source_term": "attention", "bm25_score": 0.3, "retrieval_source": "bm25"}]
        higher = [{"term_id": "t1", "source_term": "attention", "bm25_score": 0.9, "retrieval_source": "bm25"}]

        merged = RagTerminologyPipeline._merge_candidates(lower, higher)
        assert len(merged) == 1
        assert merged[0]["bm25_score"] == 0.9

    def test_empty_lists(self) -> None:
        merged = RagTerminologyPipeline._merge_candidates([], [])
        assert merged == []

    def test_skips_items_without_term_id(self) -> None:
        with_id = [{"term_id": "t1", "source_term": "valid", "bm25_score": 0.5}]
        no_id = [{"no_id": True, "source_term": "invalid", "bm25_score": 0.8}]

        merged = RagTerminologyPipeline._merge_candidates(with_id, no_id)
        assert len(merged) == 1
        assert merged[0]["term_id"] == "t1"


# ---------------------------------------------------------------------------
# _score_merge_sort
# ---------------------------------------------------------------------------

class TestScoreMergeSort:
    def test_sorts_by_effective_score(self) -> None:
        candidates = [
            {"term_id": "t1", "bm25_score": 0.3},
            {"term_id": "t2", "bm25_score": 0.9},
            {"term_id": "t3", "bm25_score": 0.6},
        ]
        sorted_candidates = RagTerminologyPipeline._score_merge_sort(candidates)
        assert sorted_candidates[0]["term_id"] == "t2"
        assert sorted_candidates[1]["term_id"] == "t3"
        assert sorted_candidates[2]["term_id"] == "t1"

    def test_prefers_highest_score_type(self) -> None:
        candidates = [
            {"term_id": "t1", "bm25_score": 0.5, "vector_score": 0.9},
            {"term_id": "t2", "rerank_score": 0.8},
        ]
        sorted_candidates = RagTerminologyPipeline._score_merge_sort(candidates)
        # t1 has effective score 0.9, t2 has 0.8
        assert sorted_candidates[0]["term_id"] == "t1"

    def test_empty_list(self) -> None:
        assert RagTerminologyPipeline._score_merge_sort([]) == []


# ---------------------------------------------------------------------------
# _transform_query
# ---------------------------------------------------------------------------

class TestTransformQuery:
    def test_strips_latex_commands(self) -> None:
        query = RagTerminologyPipeline._transform_query(
            r"\textbf{attention} mechanism is \textit{important}"
        )
        assert "textbf" not in query
        assert "textit" not in query
        assert "attention" in query

    def test_returns_empty_for_empty_input(self) -> None:
        assert RagTerminologyPipeline._transform_query("") == ""
        assert RagTerminologyPipeline._transform_query("   ") == ""

    def test_strips_braces(self) -> None:
        query = RagTerminologyPipeline._transform_query(r"hello {world}")
        assert "{" not in query
        assert "}" not in query
        assert query.strip() != ""

    def test_preserves_plain_text(self) -> None:
        query = RagTerminologyPipeline._transform_query(
            "The attention mechanism is a key component of the transformer architecture."
        )
        assert "attention mechanism" in query.lower()


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def test_returns_glossary_block_with_bm25_only(self, pipeline: RagTerminologyPipeline) -> None:
        result = pipeline.run_pipeline(
            "The attention mechanism in the transformer architecture",
            source_lang="en",
            target_lang="zh",
            top_n=5,
        )
        assert result["glossary_block"] != ""
        assert "<Glossary>" in result["glossary_block"]
        assert "</Glossary>" in result["glossary_block"]
        assert len(result["selected_terms"]) > 0
        assert result["total_candidates"] > 0
        assert "bm25" in result["retrieval_sources"]

    def test_returns_empty_for_empty_chunk(self, pipeline: RagTerminologyPipeline) -> None:
        result = pipeline.run_pipeline("")
        assert result["glossary_block"] == ""
        assert result["selected_terms"] == []
        assert result["total_candidates"] == 0

    def test_returns_empty_for_whitespace_chunk(self, pipeline: RagTerminologyPipeline) -> None:
        result = pipeline.run_pipeline("   ")
        assert result["glossary_block"] == ""

    def test_respects_top_n(self, pipeline: RagTerminologyPipeline) -> None:
        result = pipeline.run_pipeline("neural network transformer attention", top_n=2)
        assert len(result["selected_terms"]) <= 2

    def test_pipeline_is_ready_when_bm25_ready(self, pipeline: RagTerminologyPipeline) -> None:
        assert pipeline.is_ready is True

    def test_pipeline_not_ready_without_bm25(self) -> None:
        empty_bm25 = Bm25Retriever()
        p = RagTerminologyPipeline(
            bm25_retriever=empty_bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
        )
        assert p.is_ready is False


# ---------------------------------------------------------------------------
# Fallback behavior
# ---------------------------------------------------------------------------

class TestFallback:
    def test_vector_search_fallback_when_no_vector_retriever(self, bm25: Bm25Retriever) -> None:
        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
        )
        result = pipeline.run_pipeline("attention mechanism")
        assert "bm25" in result["retrieval_sources"]
        assert "vector" not in result["retrieval_sources"]

    def test_reranker_fallback_when_not_available(self, bm25: Bm25Retriever) -> None:
        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=None,
            reranker=CrossEncoderReranker(),  # model not loaded
            embedding_client=None,
        )
        result = pipeline.run_pipeline("attention mechanism", top_n=5)
        assert result["glossary_block"] != ""
        assert "reranker" not in result["retrieval_sources"]

    def test_vector_search_fallback_on_error(self, bm25: Bm25Retriever) -> None:
        mock_vector = MagicMock(spec=VectorRetriever)
        mock_vector.search.side_effect = Exception("connection refused")

        mock_embedding = MagicMock(spec=EmbeddingClient)
        mock_embedding.encode.return_value = [[0.1, 0.2]]

        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=mock_vector,
            reranker=None,
            embedding_client=mock_embedding,
        )
        # Should not raise - vector failure is non-fatal
        result = pipeline.run_pipeline("attention mechanism")
        assert result["glossary_block"] != ""

    def test_bm25_fallback_on_empty_index(self) -> None:
        empty_bm25 = Bm25Retriever()
        empty_bm25.build_index([])

        pipeline = RagTerminologyPipeline(
            bm25_retriever=empty_bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
        )
        result = pipeline.run_pipeline("attention mechanism")
        assert result["glossary_block"] == ""

    def test_repository_search_merges_with_bm25(self, bm25: Bm25Retriever) -> None:
        mock_repo = MagicMock()
        mock_repo.search_approved_terms.return_value = [
            {"id": "t99", "source_term": "custom term", "target_term": "自定义术语", "source_length": 11},
        ]

        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
            terminology_repository=mock_repo,
        )
        result = pipeline.run_pipeline("custom term", top_n=10)
        assert "repository" in result["retrieval_sources"]
        assert result["total_candidates"] > 0


# ---------------------------------------------------------------------------
# refresh_indexes
# ---------------------------------------------------------------------------

class TestRefreshIndexes:
    def test_refresh_updates_bm25(self, pipeline: RagTerminologyPipeline) -> None:
        new_terms = [
            {"id": "t100", "source_term": "new term", "target_term": "新术语"},
        ]
        pipeline.refresh_indexes(new_terms)
        # Should now only find the new term
        result = pipeline.run_pipeline("new term")
        assert result["total_candidates"] > 0
        assert result["selected_terms"][0]["source_term"] == "new term"
