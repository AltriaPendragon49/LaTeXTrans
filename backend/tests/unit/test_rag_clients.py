from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.rag.cross_encoder_reranker import CrossEncoderReranker
from backend.app.services.rag.embedding_client import EmbeddingClient, EmbeddingError
from backend.app.services.rag.vector_retriever import VectorRetriever


# ===========================================================================
# EmbeddingClient
# ===========================================================================

class TestEmbeddingClient:
    def test_encode_returns_empty_for_empty_input(self) -> None:
        client = EmbeddingClient()
        assert client.encode([]) == []

    def test_encode_with_mocked_model(self) -> None:
        mock_model = MagicMock()
        mock_model.encode.return_value = [MagicMock()]
        mock_model.encode.return_value[0].tolist.return_value = [0.1, 0.2, 0.3]

        client = EmbeddingClient()
        with patch.object(client, "_load_model", return_value=None):
            client._model = mock_model
            result = client.encode(["test text"])

        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]

    def test_encode_raises_embedding_error_on_failure(self) -> None:
        client = EmbeddingClient()
        with patch.object(client, "_load_model", side_effect=EmbeddingError("model failed")):
            with pytest.raises(EmbeddingError):
                client.encode(["test"])

    def test_model_name_stored(self) -> None:
        client = EmbeddingClient(model_name="custom-model")
        assert client.model_name == "custom-model"


# ===========================================================================
# CrossEncoderReranker
# ===========================================================================

class TestCrossEncoderReranker:
    def test_is_not_available_when_model_not_loaded(self) -> None:
        reranker = CrossEncoderReranker()
        assert reranker.is_available() is False

    def test_rerank_falls_back_when_model_not_loaded(self) -> None:
        reranker = CrossEncoderReranker()
        candidates = [
            {"term_id": "t1", "source_term": "attention", "bm25_score": 0.8},
            {"term_id": "t2", "source_term": "transformer", "bm25_score": 0.5},
        ]
        result = reranker.rerank("neural network", candidates, top_n=2)
        # Fallback: should sort by bm25_score descending
        assert len(result) == 2
        assert result[0]["term_id"] == "t1"

    def test_rerank_empty_query(self) -> None:
        reranker = CrossEncoderReranker()
        candidates = [{"term_id": "t1", "source_term": "attention"}]
        assert reranker.rerank("", candidates, top_n=5) == candidates[:5]

    def test_rerank_empty_candidates(self) -> None:
        reranker = CrossEncoderReranker()
        assert reranker.rerank("query", []) == []

    def test_rerank_fallback_sort_scores(self) -> None:
        reranker = CrossEncoderReranker()
        candidates = [
            {"term_id": "t1", "source_term": "term_a", "vector_score": 0.9},
            {"term_id": "t2", "source_term": "term_b", "bm25_score": 0.95},
        ]
        result = reranker.rerank("query", candidates, top_n=2)
        # t2 has highest effective score (0.95 > 0.9)
        assert result[0]["term_id"] == "t2"

    def test_is_available_true_when_model_loaded(self) -> None:
        reranker = CrossEncoderReranker()
        reranker._model = MagicMock()
        assert reranker.is_available() is True

    def test_rerank_with_mocked_model(self) -> None:
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.3]

        reranker = CrossEncoderReranker()
        reranker._model = mock_model

        candidates = [
            {"term_id": "t1", "source_term": "attention mechanism"},
            {"term_id": "t2", "source_term": "dropout"},
        ]
        result = reranker.rerank("neural network", candidates, top_n=2)

        assert len(result) == 2
        assert result[0]["term_id"] == "t1"  # higher rerank_score
        assert result[0]["rerank_score"] == 0.9
        assert result[1]["rerank_score"] == 0.3

    def test_rerank_skips_empty_source_terms(self) -> None:
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]

        reranker = CrossEncoderReranker()
        reranker._model = mock_model

        candidates = [
            {"term_id": "t1", "source_term": ""},
            {"term_id": "t2", "source_term": "valid term"},
        ]
        result = reranker.rerank("query", candidates, top_n=2)

        # Only the valid source_term is scored; empty source terms are omitted
        assert len(result) == 1
        assert result[0]["term_id"] == "t2"


# ===========================================================================
# VectorRetriever (pymilvus not available)
# ===========================================================================

class TestVectorRetriever:
    def test_health_check_returns_false_when_pymilvus_unavailable(self) -> None:
        retriever = VectorRetriever(uri="http://localhost:19530", collection_name="test")
        assert retriever.health_check() is False

    def test_search_returns_empty_when_not_connected(self) -> None:
        retriever = VectorRetriever(uri="http://localhost:19530", collection_name="test")
        assert retriever.search([0.1, 0.2, 0.3]) == []

    def test_upsert_term_returns_false_when_not_ready(self) -> None:
        retriever = VectorRetriever(uri="http://localhost:19530", collection_name="test")
        assert retriever.upsert_term("t1", [0.1], "src", "tgt") is False

    def test_batch_upsert_nonempty_returns_false_when_not_ready(self) -> None:
        retriever = VectorRetriever(uri="http://localhost:19530", collection_name="test")
        assert retriever.batch_upsert([{"term_id": "t1", "embedding": [0.1], "source_term": "src", "target_term": "tgt"}]) is False

    def test_batch_upsert_empty_returns_false_when_not_ready(self) -> None:
        """batch_upsert checks readiness before checking empty input."""
        retriever = VectorRetriever(uri="http://localhost:19530", collection_name="test")
        assert retriever.batch_upsert([]) is False

    def test_delete_term_returns_false_when_not_ready(self) -> None:
        retriever = VectorRetriever(uri="http://localhost:19530", collection_name="test")
        assert retriever.delete_term("t1") is False

    def test_ensure_collection_returns_false_when_pymilvus_unavailable(self) -> None:
        retriever = VectorRetriever(uri="http://localhost:19530", collection_name="test")
        assert retriever.ensure_collection() is False


# ===========================================================================
# compute_similarity
# ===========================================================================

class TestComputeSimilarity:
    def test_identical_vectors(self) -> None:
        from backend.app.services.rag.embedding_client import compute_similarity
        v = [1.0, 0.0, 0.0]
        assert compute_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        from backend.app.services.rag.embedding_client import compute_similarity
        assert compute_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        from backend.app.services.rag.embedding_client import compute_similarity
        assert compute_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self) -> None:
        from backend.app.services.rag.embedding_client import compute_similarity
        assert compute_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_dimension_mismatch_returns_zero(self) -> None:
        from backend.app.services.rag.embedding_client import compute_similarity
        assert compute_similarity([1.0, 0.0], [1.0]) == 0.0
