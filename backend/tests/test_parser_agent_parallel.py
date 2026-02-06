"""
Tests for ParserAgent parallel LLM call optimization.

Tests the async _request_llm_for_judge_async and _judge_envs_parallel methods.
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.services.agents.parser_agent import ParserAgent

# Configure pytest-asyncio mode
pytestmark = pytest.mark.asyncio(loop_scope="function")


class TestParserAgentAsyncJudge:
    """Tests for async environment judgment methods."""

    @pytest.fixture
    def parser_agent(self):
        """Create a ParserAgent with test config."""
        config = {
            "source_language": "en",
            "target_language": "ch",
            "llm_config": {
                "model": "test-model",
                "base_url": "https://api.test.com/v1/chat/completions",
                "api_key": "test-key"
            }
        }
        return ParserAgent(
            config=config,
            project_dir="/test/project",
            output_dir="/test/output"
        )

    @pytest.fixture
    def mock_envs(self):
        """Create mock environment data."""
        return [
            {"placeholder": "ENV_1", "content": "test content 1", "env_name": "theorem", "need_trans": True},
            {"placeholder": "ENV_2", "content": "test content 2", "env_name": "lemma", "need_trans": True},
            {"placeholder": "ENV_3", "content": "test content 3", "env_name": "proof", "need_trans": True},
        ]

    @pytest.mark.asyncio
    async def test_request_llm_for_judge_async_returns_true(self, parser_agent):
        """Test async LLM judge returns True when response is 'true'."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "True"}}]
        })
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        
        semaphore = asyncio.Semaphore(5)
        
        result = await parser_agent._request_llm_for_judge_async(
            "test prompt", "test text", mock_session, semaphore
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_request_llm_for_judge_async_returns_false(self, parser_agent):
        """Test async LLM judge returns False when response is 'false'."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "false"}}]
        })
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        
        semaphore = asyncio.Semaphore(5)
        
        result = await parser_agent._request_llm_for_judge_async(
            "test prompt", "test text", mock_session, semaphore
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_request_llm_for_judge_async_defaults_to_true_on_error(self, parser_agent):
        """Test async LLM judge defaults to True on error."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Connection error"))
        
        semaphore = asyncio.Semaphore(5)
        
        result = await parser_agent._request_llm_for_judge_async(
            "test prompt", "test text", mock_session, semaphore
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_judge_envs_parallel_processes_all_envs(self, parser_agent, mock_envs):
        """Test parallel judgment processes all environments."""
        class MockLatexParser:
            def __init__(self, envs):
                self.envs_json = envs

        latex_parser = MockLatexParser(mock_envs.copy())
        placeholder_to_index = {env["placeholder"]: i for i, env in enumerate(mock_envs)}
        
        with patch.object(parser_agent, '_request_llm_for_judge_async', 
                         new_callable=AsyncMock) as mock_judge:
            # Return False for first env, True for others
            mock_judge.side_effect = [False, True, True]
            
            await parser_agent._judge_envs_parallel(
                mock_envs, latex_parser, placeholder_to_index
            )
            
            # Verify all envs were processed (3 calls)
            assert mock_judge.call_count == 3
            
            # Verify results applied correctly
            assert latex_parser.envs_json[0]["need_trans"] is False
            assert latex_parser.envs_json[1]["need_trans"] is True
            assert latex_parser.envs_json[2]["need_trans"] is True

    @pytest.mark.asyncio
    async def test_judge_envs_parallel_handles_exceptions_gracefully(self, parser_agent, mock_envs):
        """Test parallel judgment handles exceptions without crashing."""
        class MockLatexParser:
            def __init__(self, envs):
                self.envs_json = envs

        latex_parser = MockLatexParser(mock_envs.copy())
        placeholder_to_index = {env["placeholder"]: i for i, env in enumerate(mock_envs)}
        
        with patch.object(parser_agent, '_request_llm_for_judge_async', 
                         new_callable=AsyncMock) as mock_judge:
            # First call raises exception, others succeed
            mock_judge.side_effect = [Exception("Test error"), True, False]
            
            # Should not raise
            await parser_agent._judge_envs_parallel(
                mock_envs, latex_parser, placeholder_to_index
            )
            
            # Verify remaining envs were processed
            assert latex_parser.envs_json[1]["need_trans"] is True
            assert latex_parser.envs_json[2]["need_trans"] is False

    @pytest.mark.asyncio
    async def test_parallel_execution_completes_all_envs(self, parser_agent, mock_envs):
        """Test that parallel execution processes all environments efficiently."""
        # Create more environments to test parallel execution
        large_mock_envs = [
            {"placeholder": f"ENV_{i}", "content": f"content {i}", "env_name": "theorem", "need_trans": True}
            for i in range(10)
        ]
        
        class MockLatexParser:
            def __init__(self, envs):
                self.envs_json = envs.copy()

        latex_parser = MockLatexParser(large_mock_envs)
        placeholder_to_index = {env["placeholder"]: i for i, env in enumerate(large_mock_envs)}
        
        call_count = 0
        
        async def counting_judge(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return True
        
        with patch.object(parser_agent, '_request_llm_for_judge_async', 
                         side_effect=counting_judge):
            await parser_agent._judge_envs_parallel(
                large_mock_envs, latex_parser, placeholder_to_index
            )
        
        # Verify all 10 environments were processed
        assert call_count == 10
        
        # Verify all results were applied
        for env in latex_parser.envs_json:
            assert env["need_trans"] is True
