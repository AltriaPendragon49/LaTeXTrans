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


# ---------------------------------------------------------------------------
# TerminologyService 集成测试 (mock 数据库 + mock pipeline)
# ---------------------------------------------------------------------------


class TestTerminologyServiceGetRagGlossary:
    """测试 TerminologyService.get_rag_glossary 的完整路径与回退逻辑。"""

    def test_returns_empty_when_disabled(self) -> None:
        """RAG 特性关闭时直接返回空结果。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = False
            mock_get_settings.return_value = settings

            service = TerminologyService()
            result = service.get_rag_glossary("attention mechanism")
            assert result == {"terms": [], "glossary_block": "", "match_count": 0}

    def test_full_pipeline_path(self) -> None:
        """pipeline 可用时走完整 RAG 路径。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_get_settings.return_value = settings

            mock_pipeline = MagicMock()
            mock_pipeline.is_ready = True
            mock_pipeline.run_pipeline.return_value = {
                "glossary_block": "<Glossary>\nattention mechanism -> 注意力机制\n</Glossary>",
                "selected_terms": [
                    {"source_term": "attention mechanism", "target_term": "注意力机制"}
                ],
                "total_candidates": 1,
                "retrieval_sources": ["bm25"],
            }

            service = TerminologyService()
            with patch.object(service, "_get_pipeline", return_value=mock_pipeline):
                result = service.get_rag_glossary("attention mechanism")
                assert result["glossary_block"] != ""
                assert result["match_count"] == 1
                assert len(result["terms"]) == 1

    def test_fallback_to_substring_when_pipeline_unavailable(self) -> None:
        """pipeline 不可用时回退到子串匹配。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_get_settings.return_value = settings

            mock_repo = MagicMock()
            mock_repo.get_all_approved_terms.return_value = [
                {"id": "t1", "source_term": "attention mechanism", "target_term": "注意力机制", "source_lang": "en"},
                {"id": "t2", "source_term": "transformer", "target_term": "Transformer模型", "source_lang": "en"},
                {"id": "t3", "source_term": "unrelated term", "target_term": "不相关", "source_lang": "en"},
            ]

            service = TerminologyService(repository=mock_repo)
            # _get_pipeline 返回 None 表示 pipeline 不可用
            with patch.object(service, "_get_pipeline", return_value=None):
                result = service.get_rag_glossary("attention mechanism in transformer")
                # 子串匹配应找到 attention mechanism 和 transformer
                assert result["match_count"] > 0
                matched_terms = [t["source_term"] for t in result["terms"]]
                assert "unrelated term" not in matched_terms

    def test_substring_fallback_respects_top_n(self) -> None:
        """子串匹配回退时返回不超过 top_n 个结果。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_get_settings.return_value = settings

            mock_repo = MagicMock()
            mock_repo.get_all_approved_terms.return_value = [
                {"id": "t1", "source_term": "attention", "target_term": "注意力", "source_lang": "en"},
                {"id": "t2", "source_term": "mechanism", "target_term": "机制", "source_lang": "en"},
                {"id": "t3", "source_term": "transformer", "target_term": "Transformer", "source_lang": "en"},
                {"id": "t4", "source_term": "model", "target_term": "模型", "source_lang": "en"},
            ]

            service = TerminologyService(repository=mock_repo)
            with patch.object(service, "_get_pipeline", return_value=None):
                result = service.get_rag_glossary(
                    "attention mechanism transformer model", top_n=2
                )
                assert result["match_count"] <= 2
                assert len(result["terms"]) <= 2

    def test_handles_pipeline_exception_gracefully(self) -> None:
        """pipeline.run_pipeline 抛出异常时回退到子串匹配。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_get_settings.return_value = settings

            mock_pipeline = MagicMock()
            mock_pipeline.is_ready = True
            mock_pipeline.run_pipeline.side_effect = RuntimeError("search failed")

            mock_repo = MagicMock()
            mock_repo.get_all_approved_terms.return_value = [
                {"id": "t1", "source_term": "attention", "target_term": "注意力", "source_lang": "en"},
            ]

            service = TerminologyService(repository=mock_repo)
            with patch.object(service, "_get_pipeline", return_value=mock_pipeline):
                result = service.get_rag_glossary("attention mechanism")
                # 不应抛异常，应回退到子串匹配
                assert result["match_count"] >= 0


class TestTerminologyServiceSeedOfficialTerms:
    """测试 TerminologyService.seed_official_terms 的幂等性。"""

    def test_skips_when_disabled(self) -> None:
        """RAG 特性关闭时返回 0 且不执行任何插入。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = False
            mock_get_settings.return_value = settings

            service = TerminologyService()
            assert service.seed_official_terms() == 0

    def test_skips_when_system_terms_already_exist(self) -> None:
        """已存在 system 类型术语时跳过（幂等性）。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_get_settings.return_value = settings

            mock_repo = MagicMock()
            # search_terms 返回 (rows, total)，total > 0 表示已存在
            mock_repo.search_terms.return_value = (
                [{"id": "exist-1", "source_term": "attention", "target_term": "注意力"}],
                1,
            )

            service = TerminologyService(repository=mock_repo)
            # 即使 seed 文件不存在，已存在 system term 也应该直接返回 0
            assert service.seed_official_terms() == 0

    def test_handles_repo_error_gracefully(self) -> None:
        """数据库异常时跳过而非抛异常。"""
        from backend.app.services.terminology_service import TerminologyService

        with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
            settings = MagicMock()
            settings.rag_terminology_enabled = True
            mock_get_settings.return_value = settings

            mock_repo = MagicMock()
            mock_repo.search_terms.side_effect = RuntimeError("DB connection lost")

            service = TerminologyService(repository=mock_repo)
            # 不存在的 seed 文件 + DB 异常 -> 返回 0
            assert service.seed_official_terms() == 0

    def test_seed_inserts_new_terms_when_empty_db(self) -> None:
        """空数据库且 seed 文件存在时正常插入。"""
        import json
        import os
        import tempfile

        from backend.app.services.terminology_service import TerminologyService

        # 创建临时 seed file
        seed_data = [
            {
                "source_term": "machine learning",
                "target_term": "机器学习",
                "source_lang": "en",
                "target_lang": "zh",
                "domain": "machine_learning",
            },
            {
                "source_term": "deep learning",
                "target_term": "深度学习",
                "source_lang": "en",
                "target_lang": "zh",
                "domain": "deep_learning",
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(seed_data, f)
            seed_path = f.name

        try:
            with patch("backend.app.services.terminology_service.get_settings") as mock_get_settings:
                settings = MagicMock()
                settings.rag_terminology_enabled = True
                mock_get_settings.return_value = settings

                mock_repo = MagicMock()
                # 第一次 search_terms 返回 0（表示无 system term）
                mock_repo.search_terms.return_value = ([], 0)
                # insert_term 正常插入
                mock_repo.insert_term.side_effect = lambda payload: {
                    **payload,
                    "id": "new-" + payload["source_term"],
                }

                service = TerminologyService(repository=mock_repo)

                # Patch os.path so the seed file is found at our temp location.
                with patch("os.path.join", return_value=seed_path):
                    with patch("os.path.exists", return_value=True):
                        count = service.seed_official_terms()

                assert count == 2
                assert mock_repo.insert_term.call_count == 2
        finally:
            os.unlink(seed_path)


class TestTerminologyServiceApproveTerm:
    """测试 approve_term 触发索引刷新。"""

    def test_approve_term_success(self) -> None:
        """审批操作委托给 repository.approve_term。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_repo.approve_term.return_value = True

        service = TerminologyService(repository=mock_repo)
        assert service.approve_term("term-1", "reviewer-1") is True
        mock_repo.approve_term.assert_called_once_with("term-1", "reviewer-1")

    def test_approve_term_failure(self) -> None:
        """repository 异常时返回 False 而非抛异常。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_repo.approve_term.side_effect = RuntimeError("DB error")

        service = TerminologyService(repository=mock_repo)
        assert service.approve_term("term-1", "reviewer-1") is False

    def test_reject_term_success(self) -> None:
        """拒绝操作委托给 repository.reject_term。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_repo.reject_term.return_value = True

        service = TerminologyService(repository=mock_repo)
        assert service.reject_term("term-1", "reviewer-1", reason="翻译错误") is True
        mock_repo.reject_term.assert_called_once_with("term-1", "reviewer-1", "翻译错误")

    def test_reject_term_failure(self) -> None:
        """repository 异常时返回 False。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_repo.reject_term.side_effect = RuntimeError("DB error")

        service = TerminologyService(repository=mock_repo)
        assert service.reject_term("term-1", "reviewer-1") is False


class TestTerminologyServiceExtractAndStore:
    """测试 extract_and_store 术语自动提取流程。"""

    def test_extract_and_store_with_extraction_result(self) -> None:
        """提取到术语对后批量插入。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_repo.insert_terms_batch.return_value = ["new-1", "new-2"]

        # Mock extractor 返回包含两个术语的结果
        mock_extraction_result = MagicMock()
        mock_extraction_result.extracted_terms = [
            {"source_term": "neural network", "target_term": "神经网络", "domain": "deep_learning"},
            {"source_term": "backpropagation", "target_term": "反向传播", "domain": "deep_learning"},
        ]

        with patch(
            "backend.app.services.terminology_service.run_extraction",
            return_value=mock_extraction_result,
        ):
            service = TerminologyService(repository=mock_repo)
            ids = service.extract_and_store(
                task_id="task-001",
                source_text="neural network uses backpropagation",
                target_text="神经网络使用反向传播",
            )
            assert len(ids) == 2
            assert ids == ["new-1", "new-2"]

    def test_extract_and_store_empty_result(self) -> None:
        """未提取到术语时返回空列表。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_extraction_result = MagicMock()
        mock_extraction_result.extracted_terms = []

        with patch(
            "backend.app.services.terminology_service.run_extraction",
            return_value=mock_extraction_result,
        ):
            service = TerminologyService(repository=mock_repo)
            ids = service.extract_and_store(
                task_id="task-001",
                source_text="hello world",
                target_text="你好世界",
            )
            assert ids == []

    def test_extract_and_store_with_llm_fn(self) -> None:
        """传入自定义 LLM 提取函数。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_repo.insert_terms_batch.return_value = ["llm-1"]

        mock_extraction_result = MagicMock()
        mock_extraction_result.extracted_terms = [
            {"source_term": "LLM term", "target_term": "大模型术语", "domain": ""},
        ]

        llm_fn = MagicMock()

        with patch(
            "backend.app.services.terminology_service.run_extraction",
            return_value=mock_extraction_result,
        ) as mock_run_extraction:
            service = TerminologyService(repository=mock_repo)
            ids = service.extract_and_store(
                task_id="task-002",
                source_text="source",
                target_text="target",
                llm_extract_fn=llm_fn,
                user_id="user-42",
            )
            # run_extraction 被调用时传入了 llm_fn
            mock_run_extraction.assert_called_once_with("source", "target", llm_fn)
            assert len(ids) == 1

    def test_extract_and_store_db_error_graceful(self) -> None:
        """数据库插入异常时返回空列表而非抛异常。"""
        from backend.app.services.terminology_service import TerminologyService

        mock_repo = MagicMock()
        mock_repo.insert_terms_batch.side_effect = RuntimeError("DB insert failed")

        mock_extraction_result = MagicMock()
        mock_extraction_result.extracted_terms = [
            {"source_term": "term", "target_term": "术语", "domain": ""},
        ]

        with patch(
            "backend.app.services.terminology_service.run_extraction",
            return_value=mock_extraction_result,
        ):
            service = TerminologyService(repository=mock_repo)
            ids = service.extract_and_store(
                task_id="task-001",
                source_text="source",
                target_text="target",
            )
            assert ids == []
