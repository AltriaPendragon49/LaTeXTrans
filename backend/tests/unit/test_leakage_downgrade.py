import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.app.services.agents.translator_agent import TranslatorAgent
import asyncio

class TestTranslatorAgentLeakageDowngrade(unittest.TestCase):
    def setUp(self):
        # Initialize an agent with dummy configuration
        self.agent = TranslatorAgent(
            config={
                "llm_config": {
                    "model": "gpt-4o",
                    "base_url": "http://dummy",
                    "api_key": "dummy"
                }
            },
            project_dir="dummy",
            output_dir="dummy",
            trans_mode=0
        )
        self.agent.prompts = {
            "section_system_prompt": "Base section prompt.",
            "REFERENCE_CONTEXT_TEMPLATE": "\n<REFERENCE_CONTEXT>\n{context}\n</REFERENCE_CONTEXT>\nDO NOT TRANSLATE IT."
        }

    @staticmethod
    def _make_response(content: str):
        response = AsyncMock()
        response.status = 200
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {"content": content}}]
        }
        return response
        
    @patch('aiohttp.ClientSession')
    def test_translate_section_success_no_leakage(self, mock_session_cls):
        section = {
            "section": "1_chunk_2",
            "content": "A test sentence.",
            "previous_context": "Previous text context."
        }
        
        # Setup mock session and response
        mock_response = self._make_response("A translated test sentence.")
        
        # The 'async with' context manager returns the response
        mock_session = MagicMock()
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_response
        mock_session.post.return_value = cm
        
        result = asyncio.run(self.agent._translate_section(section, mock_session))
        
        self.assertEqual(result["trans_content"], "A translated test sentence.")
        
        # Verify the prompt passed in payload included the context block
        self.assertEqual(mock_session.post.call_count, 1)
        payload = mock_session.post.call_args[1]['json']
        system_prompt = payload['messages'][0]['content']
        
        self.assertIn("Base section prompt.", system_prompt)
        self.assertIn("<REFERENCE_CONTEXT>", system_prompt)
        self.assertIn("Previous text context.", system_prompt)

    @patch('aiohttp.ClientSession')
    def test_translate_section_leakage_retry_success(self, mock_session_cls):
        section = {
            "section": "1_chunk_2",
            "content": "A test sentence.",
            "previous_context": "Previous text context."
        }
        
        mock_session = MagicMock()
        
        # First response leaks, second doesn't
        resp1 = self._make_response("I leaked some <REFERENCE_CONTEXT> here.")
        
        resp2 = self._make_response("A translated test sentence.")
        
        # Return resp1 then resp2 sequentially
        cm1 = AsyncMock()
        cm1.__aenter__.return_value = resp1
        cm2 = AsyncMock()
        cm2.__aenter__.return_value = resp2
        mock_session.post.side_effect = [cm1, cm2]
        
        result = asyncio.run(self.agent._translate_section(section, mock_session))
        
        self.assertEqual(result["trans_content"], "A translated test sentence.")
        self.assertEqual(mock_session.post.call_count, 2)
        
        # Both requests should have included the context block
        payload1 = mock_session.post.call_args_list[0][1]['json']
        payload2 = mock_session.post.call_args_list[1][1]['json']
        
        self.assertIn("<REFERENCE_CONTEXT>", payload1['messages'][0]['content'])
        self.assertIn("<REFERENCE_CONTEXT>", payload2['messages'][0]['content'])

    @patch('aiohttp.ClientSession')
    def test_translate_section_leakage_downgrade(self, mock_session_cls):
        section = {
            "section": "1_chunk_2",
            "content": "A test sentence.",
            "previous_context": "Previous text context."
        }
        
        mock_session = MagicMock()
        
        resp_leak = self._make_response("I stubbornly leaked <REFERENCE_CONTEXT>.")
        
        resp_clean = self._make_response("A translated test sentence without context.")
        
        cm_leak = AsyncMock()
        cm_leak.__aenter__.return_value = resp_leak
        cm_clean = AsyncMock()
        cm_clean.__aenter__.return_value = resp_clean
        
        mock_session.post.side_effect = [cm_leak, cm_leak, cm_clean]
        
        result = asyncio.run(self.agent._translate_section(section, mock_session))
        
        self.assertEqual(result["trans_content"], "A translated test sentence without context.")
        self.assertEqual(mock_session.post.call_count, 3)
        
        payload1 = mock_session.post.call_args_list[0][1]['json']
        payload2 = mock_session.post.call_args_list[1][1]['json']
        payload3 = mock_session.post.call_args_list[2][1]['json']
        
        self.assertIn("<REFERENCE_CONTEXT>", payload1['messages'][0]['content'])
        self.assertIn("<REFERENCE_CONTEXT>", payload2['messages'][0]['content'])
        
        # Third (downgrade) request should lack the context completely
        self.assertNotIn("<REFERENCE_CONTEXT>", payload3['messages'][0]['content'])
        self.assertNotIn("Previous text context.", payload3['messages'][0]['content'])

if __name__ == '__main__':
    unittest.main()
