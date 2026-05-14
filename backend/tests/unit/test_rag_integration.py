"""Integration tests for RAG terminology: chaining components end-to-end."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.rag.bm25_retriever import Bm25Retriever
from backend.app.services.rag.glossary_formatter import (
    estimate_token_count,
    format_glossary_block,
    truncate_glossary,
)
from backend.app.services.rag.pipeline import RagTerminologyPipeline
from backend.app.services.rag.translation_hook import (
    build_glossary_from_terms,
    inject_glossary_into_prompt,
)

# ---------------------------------------------------------------------------
# Glossary formatting
# ---------------------------------------------------------------------------


class TestGlossaryFormatter:
    def test_format_glossary_block(self) -> None:
        terms = [
            {"source_term": "attention mechanism", "target_term": "注意力机制"},
            {"source_term": "transformer", "target_term": "Transformer模型"},
        ]
        block = format_glossary_block(terms)
        assert "<Glossary>" in block
        assert "</Glossary>" in block
        assert "attention mechanism -> 注意力机制" in block
        assert "transformer -> Transformer模型" in block

    def test_format_glossary_block_empty(self) -> None:
        assert format_glossary_block([]) == ""

    def test_format_glossary_block_skips_empty_entries(self) -> None:
        terms = [
            {"source_term": "valid", "target_term": "有效"},
            {"source_term": "", "target_term": "空源"},
            {"source_term": "空目标", "target_term": ""},
        ]
        block = format_glossary_block(terms)
        assert "valid -> 有效" in block
        assert "空源" not in block
        assert "空目标" not in block

    def test_estimate_token_count(self) -> None:
        block = format_glossary_block([{"source_term": "test", "target_term": "测试"}])
        assert estimate_token_count(block) >= 1

    def test_estimate_token_count_empty(self) -> None:
        assert estimate_token_count("") == 0

    def test_truncate_glossary(self) -> None:
        terms = [
            {"source_term": f"term_{i}", "target_term": f"术语{i}"}
            for i in range(20)
        ]
        block = format_glossary_block(terms)
        truncated = truncate_glossary(block, max_tokens=20)
        assert truncated != ""
        assert "<Glossary>" in truncated
        assert "</Glossary>" in truncated
        # Truncated block should have fewer term lines
        assert len(truncated.splitlines()) < len(block.splitlines())

    def test_truncate_glossary_empty(self) -> None:
        assert truncate_glossary("", 100) == ""

    def test_truncate_glossary_zero_max_tokens(self) -> None:
        block = format_glossary_block([{"source_term": "test", "target_term": "测试"}])
        assert truncate_glossary(block, 0) == ""

    def test_truncate_glossary_chinese_terms(self) -> None:
        """Chinese terms should be truncated by estimated token count (len//4)."""
        terms = [
            {"source_term": f"attention mechanism {i}", "target_term": f"注意力机制{i}"}
            for i in range(30)
        ]
        block = format_glossary_block(terms)
        truncated = truncate_glossary(block, max_tokens=30)
        assert truncated != ""
        assert "<Glossary>" in truncated
        assert len(truncated.splitlines()) < len(block.splitlines())


# ---------------------------------------------------------------------------
# Prompt injection
# ---------------------------------------------------------------------------


class TestPromptInjection:
    def test_inject_glossary_into_prompt(self) -> None:
        original = "请将以下英文论文翻译为中文。"
        glossary = format_glossary_block([
            {"source_term": "attention", "target_term": "注意力"},
        ])
        augmented = inject_glossary_into_prompt(original, glossary)
        assert augmented.startswith("<Glossary>")
        assert "请将以下英文论文翻译为中文。" in augmented
        assert glossary in augmented

    def test_inject_empty_glossary(self) -> None:
        original = "Translate this text."
        assert inject_glossary_into_prompt(original, "") == original

    def test_inject_whitespace_glossary(self) -> None:
        original = "Translate this text."
        assert inject_glossary_into_prompt(original, "   ") == original


# ---------------------------------------------------------------------------
# build_glossary_from_terms
# ---------------------------------------------------------------------------


class TestBuildGlossaryFromTerms:
    def test_build_from_terms(self) -> None:
        block = build_glossary_from_terms([
            {"source_term": "gradient descent", "target_term": "梯度下降"},
        ])
        assert "gradient descent -> 梯度下降" in block

    def test_build_from_empty_list(self) -> None:
        assert build_glossary_from_terms([]) == ""


# ---------------------------------------------------------------------------
# BM25 → Pipeline → Glossary  end-to-end
# ---------------------------------------------------------------------------


class TestBm25ToGlossaryPipeline:
    def test_full_pipeline_produces_glossary(self) -> None:
        """BM25 → Pipeline → Glossary formatting: all stages produce output."""
        terms = [
            {"id": "t1", "source_term": "attention mechanism", "target_term": "注意力机制"},
            {"id": "t2", "source_term": "transformer architecture", "target_term": "Transformer架构"},
            {"id": "t3", "source_term": "batch normalization", "target_term": "批归一化"},
            {"id": "t4", "source_term": "convolutional neural network", "target_term": "卷积神经网络"},
            {"id": "t5", "source_term": "recurrent neural network", "target_term": "循环神经网络"},
        ]

        bm25 = Bm25Retriever()
        bm25.build_index(terms)

        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
        )

        result = pipeline.run_pipeline(
            "The attention mechanism in the transformer architecture enables "
            "the model to focus on relevant parts of the input sequence.",
            source_lang="en",
            target_lang="zh",
            top_n=3,
        )

        assert result["glossary_block"] != ""
        assert result["total_candidates"] > 0
        assert len(result["selected_terms"]) <= 3
        assert "bm25" in result["retrieval_sources"]

        # All returned terms should have source and target
        for term in result["selected_terms"]:
            assert term.get("source_term")
            assert term.get("target_term")

    def test_pipeline_with_empty_index(self) -> None:
        bm25 = Bm25Retriever()
        bm25.build_index([])

        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
        )

        result = pipeline.run_pipeline("attention mechanism")
        assert result["glossary_block"] == ""

    def test_pipeline_glossary_injection_chain(self) -> None:
        """Chain: BM25 search → format glossary → inject into prompt."""
        bm25 = Bm25Retriever()
        bm25.build_index([
            {"id": "t1", "source_term": "attention mechanism", "target_term": "注意力机制"},
        ])

        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
        )

        result = pipeline.run_pipeline("attention mechanism", top_n=5)

        original_prompt = "请逐段将以下英文论文翻译为中文。"
        augmented_prompt = inject_glossary_into_prompt(original_prompt, result["glossary_block"])

        assert "<Glossary>" in augmented_prompt
        assert "注意力机制" in augmented_prompt
        assert original_prompt in augmented_prompt

    def test_multiple_chunks_consistent_glossary(self) -> None:
        """Pipeline should produce similar glossaries for related chunks."""
        bm25 = Bm25Retriever()
        bm25.build_index([
            {"id": "t1", "source_term": "attention mechanism", "target_term": "注意力机制"},
            {"id": "t2", "source_term": "transformer", "target_term": "Transformer模型"},
            {"id": "t3", "source_term": "embedding", "target_term": "词嵌入"},
            {"id": "t4", "source_term": "dropout", "target_term": "丢弃法"},
        ])

        pipeline = RagTerminologyPipeline(
            bm25_retriever=bm25,
            vector_retriever=None,
            reranker=None,
            embedding_client=None,
        )

        r1 = pipeline.run_pipeline("The attention mechanism in transformers", top_n=2)
        r2 = pipeline.run_pipeline("Attention and embedding layers in the model", top_n=2)

        # Both runs should find relevant terms
        assert r1["total_candidates"] > 0
        assert r2["total_candidates"] > 0

        # Chunks about attention should both include attention-related terms
        r1_terms = {t["source_term"] for t in r1["selected_terms"]}
        r2_terms = {t["source_term"] for t in r2["selected_terms"]}
        assert "attention mechanism" in r1_terms or "attention mechanism" in r2_terms


# ---------------------------------------------------------------------------
# should_run_rag (feature gate)
# ---------------------------------------------------------------------------


class TestShouldRunRag:
    def test_enabled_when_both_levels_true(self) -> None:
        with patch("backend.app.services.rag.translation_hook.get_settings") as mock_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_settings.return_value = settings

            from backend.app.services.rag.translation_hook import should_run_rag
            assert should_run_rag({"enable_rag_terminology": True}) is True

    def test_disabled_when_server_flag_off(self) -> None:
        with patch("backend.app.services.rag.translation_hook.get_settings") as mock_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = False
            mock_settings.return_value = settings

            from backend.app.services.rag.translation_hook import should_run_rag
            assert should_run_rag({"enable_rag_terminology": True}) is False

    def test_disabled_when_user_config_off(self) -> None:
        with patch("backend.app.services.rag.translation_hook.get_settings") as mock_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_settings.return_value = settings

            from backend.app.services.rag.translation_hook import should_run_rag
            assert should_run_rag({"enable_rag_terminology": False}) is False

    def test_disabled_when_user_config_missing(self) -> None:
        with patch("backend.app.services.rag.translation_hook.get_settings") as mock_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_settings.return_value = settings

            from backend.app.services.rag.translation_hook import should_run_rag
            assert should_run_rag({}) is False
