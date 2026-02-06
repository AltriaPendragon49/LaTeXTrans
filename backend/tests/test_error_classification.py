"""
Tests for error classification and structural fix functionality.

Tests the classify_error function and structural fix methods.
"""

import pytest
from backend.app.services.agents.validator_agent import (
    classify_error, ERROR_TYPE_A, ERROR_TYPE_B, ERROR_TYPE_C
)
from backend.app.services.agents.translator_agent import TranslatorAgent


class TestErrorClassification:
    """Tests for classify_error function."""

    def test_classify_type_a_resource_not_found(self):
        """Type A: Resource/config missing errors."""
        error = {
            "command_error": "terms/default.csv not found",
            "part": "sec",
            "num_or_ph": "1"
        }
        assert classify_error(error) == ERROR_TYPE_A

    def test_classify_type_a_file_not_found(self):
        """Type A: File not found errors."""
        error = {
            "command_error": "Required file Not Found in project directory",
            "part": "env",
            "num_or_ph": "ENV_1"
        }
        assert classify_error(error) == ERROR_TYPE_A

    def test_classify_type_c_command_count_mismatch(self):
        """Type C: Structural consistency error with expected/found pattern."""
        error = {
            "command_error": "LaTeX command error:\\n'\\mathbb' — expected 3, found 2",
            "part": "sec",
            "num_or_ph": "2"
        }
        assert classify_error(error) == ERROR_TYPE_C

    def test_classify_type_c_missing_placeholders(self):
        """Type C: Missing placeholders (structural issue)."""
        error = {
            "ph_error": "Missing placeholders: <PLACEHOLDER_ENV_1>, <PLACEHOLDER_CAP_2>",
            "part": "sec",
            "num_or_ph": "3"
        }
        assert classify_error(error) == ERROR_TYPE_C

    def test_classify_type_b_bracket_error(self):
        """Type B: Bracket errors are recoverable."""
        error = {
            "bracket_error": "Unmatched opening bracket '{' at position 45",
            "part": "cap",
            "num_or_ph": "CAP_1"
        }
        assert classify_error(error) == ERROR_TYPE_B

    def test_classify_type_b_extra_placeholders(self):
        """Type B: Extra placeholders (not missing) are recoverable."""
        error = {
            "ph_error": "Extra placeholders: <PLACEHOLDER_ENV_99>",
            "part": "env",
            "num_or_ph": "ENV_5"
        }
        assert classify_error(error) == ERROR_TYPE_B

    def test_classify_type_b_default(self):
        """Type B: Default classification for unrecognized errors."""
        error = {
            "command_error": "Some unknown error format",
            "part": "sec",
            "num_or_ph": "1"
        }
        assert classify_error(error) == ERROR_TYPE_B


class TestStructuralFix:
    """Tests for TranslatorAgent structural fix methods."""

    @pytest.fixture
    def translator_agent(self):
        """Create a TranslatorAgent with minimal config."""
        config = {
            "source_language": "en",
            "target_language": "ch",
            "llm_config": {
                "model": "test-model",
                "base_url": "https://api.test.com/v1/chat/completions",
                "api_key": "test-key"
            }
        }
        return TranslatorAgent(config=config)

    def test_fix_missing_placeholders_restores_missing(self, translator_agent):
        """Test that missing placeholders are restored."""
        original = "Text <PLACEHOLDER_ENV_1> more text <PLACEHOLDER_CAP_2>"
        translated = "翻译后的文本，其他文本"
        
        fixed = translator_agent._fix_missing_placeholders(original, translated)
        
        assert "<PLACEHOLDER_ENV_1>" in fixed
        assert "<PLACEHOLDER_CAP_2>" in fixed

    def test_fix_missing_placeholders_preserves_existing(self, translator_agent):
        """Test that existing placeholders are preserved."""
        original = "Text <PLACEHOLDER_ENV_1>"
        translated = "翻译文本 <PLACEHOLDER_ENV_1>"
        
        fixed = translator_agent._fix_missing_placeholders(original, translated)
        
        # Should have exactly one occurrence
        assert fixed.count("<PLACEHOLDER_ENV_1>") == 1

    def test_apply_structural_fix_with_no_translation(self, translator_agent):
        """Test fallback when no translation exists."""
        part = {"content": "Original content", "trans_content": ""}
        error = {"command_error": "expected 2, found 0"}
        
        result = translator_agent._apply_structural_fix(part, error)
        
        assert result is True
        assert part["trans_content"] == "Original content"

    def test_apply_structural_fix_preserves_translation(self, translator_agent):
        """Test that existing translation is preserved on partial fix."""
        part = {
            "content": "Text <PLACEHOLDER_ENV_1>",
            "trans_content": "翻译文本"
        }
        error = {"ph_error": "Missing placeholders: <PLACEHOLDER_ENV_1>"}
        
        result = translator_agent._apply_structural_fix(part, error)
        
        assert result is True
        assert "翻译文本" in part["trans_content"]
        assert "<PLACEHOLDER_ENV_1>" in part["trans_content"]

    def test_find_part_by_error_finds_section(self, translator_agent):
        """Test finding section by error report."""
        secs = [{"section": "1", "content": "sec1"}, {"section": "2", "content": "sec2"}]
        caps = []
        envs = []
        error = {"part": "sec", "num_or_ph": "2"}
        
        part = translator_agent._find_part_by_error(error, secs, caps, envs)
        
        assert part is not None
        assert part["section"] == "2"

    def test_find_part_by_error_finds_env(self, translator_agent):
        """Test finding environment by error report."""
        secs = []
        caps = []
        envs = [{"placeholder": "ENV_1", "content": "env1"}, {"placeholder": "ENV_2", "content": "env2"}]
        error = {"part": "env", "num_or_ph": "ENV_1"}
        
        part = translator_agent._find_part_by_error(error, secs, caps, envs)
        
        assert part is not None
        assert part["placeholder"] == "ENV_1"

    def test_find_part_by_error_returns_none_for_missing(self, translator_agent):
        """Test None returned for non-existent part."""
        secs = [{"section": "1", "content": "sec1"}]
        caps = []
        envs = []
        error = {"part": "sec", "num_or_ph": "99"}
        
        part = translator_agent._find_part_by_error(error, secs, caps, envs)
        
        assert part is None
