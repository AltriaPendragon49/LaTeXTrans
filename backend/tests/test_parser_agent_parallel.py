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


class TestEnvironmentFiltering:
    """Tests for SKIP_LLM_JUDGMENT_ENVS filtering logic."""

    def test_skip_llm_judgment_envs_list_exists(self):
        """Test that SKIP_LLM_JUDGMENT_ENVS is defined."""
        from backend.app.services.agents.parser_agent import SKIP_LLM_JUDGMENT_ENVS
        
        assert isinstance(SKIP_LLM_JUDGMENT_ENVS, list)
        assert len(SKIP_LLM_JUDGMENT_ENVS) > 0
        # Check expected env types are included
        assert 'abstract' in SKIP_LLM_JUDGMENT_ENVS
        assert 'theorem' in SKIP_LLM_JUDGMENT_ENVS
        assert 'proof' in SKIP_LLM_JUDGMENT_ENVS
        assert 'itemize' in SKIP_LLM_JUDGMENT_ENVS

    def test_skip_llm_judgment_envs_covers_common_types(self):
        """Test that common environment types are covered."""
        from backend.app.services.agents.parser_agent import SKIP_LLM_JUDGMENT_ENVS
        
        expected_types = [
            'abstract', 'itemize', 'enumerate', 'description',
            'theorem', 'lemma', 'proposition', 'corollary', 'remark', 'proof',
            'definition', 'example', 'exercise', 'problem', 'solution', 'note',
            'quotation', 'quote', 'verse'
        ]
        
        for env_type in expected_types:
            assert env_type in SKIP_LLM_JUDGMENT_ENVS, f"{env_type} should be in SKIP_LLM_JUDGMENT_ENVS"

    def test_filtering_logic_skips_known_env_types(self):
        """Test that known environment types are skipped from LLM judgment."""
        from backend.app.services.agents.parser_agent import SKIP_LLM_JUDGMENT_ENVS
        
        test_envs = [
            {"env_name": "theorem", "need_trans": True, "content": "This is a long theorem content"},
            {"env_name": "proof", "need_trans": True, "content": "This is a proof with content"},
            {"env_name": "custom_env", "need_trans": True, "content": "This needs LLM judgment"},
        ]
        
        env_need_trans = []
        for env in test_envs:
            if not env["need_trans"]:
                continue
            if env["env_name"] in SKIP_LLM_JUDGMENT_ENVS:
                continue
            content = env.get("content", "")
            if len(content.strip()) <= 20:
                continue
            env_need_trans.append(env)
        
        # Only 'custom_env' should need LLM judgment
        assert len(env_need_trans) == 1
        assert env_need_trans[0]["env_name"] == "custom_env"

    def test_filtering_logic_skips_short_content(self):
        """Test that short content environments are skipped."""
        from backend.app.services.agents.parser_agent import SKIP_LLM_JUDGMENT_ENVS
        
        test_envs = [
            {"env_name": "custom1", "need_trans": True, "content": "short"},  # 5 chars
            {"env_name": "custom2", "need_trans": True, "content": "exactly twenty chars"},  # 20 chars
            {"env_name": "custom3", "need_trans": True, "content": "This is definitely longer than twenty"},  # > 20
        ]
        
        env_need_trans = []
        for env in test_envs:
            if not env["need_trans"]:
                continue
            if env["env_name"] in SKIP_LLM_JUDGMENT_ENVS:
                continue
            content = env.get("content", "")
            if len(content.strip()) <= 20:
                continue
            env_need_trans.append(env)
        
        # Only custom3 has content > 20 chars
        assert len(env_need_trans) == 1
        assert env_need_trans[0]["env_name"] == "custom3"

