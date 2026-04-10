"""
TDD Test Suite: detect_structure_invariant (Phase 0)
=====================================================
Tests for the lightweight Phase 0 structure classification function.

Design principles:
  - Phase 0 ONLY classifies: it returns `is_structure_safe` bool.
  - It must never raise, block, or trigger downgrade itself.
  - Safe envs must pass quickly (performance-critical hot path).
"""
import pytest

# SUT â€?will live at: backend/app/services/translation/structure_checker.py
from backend.app.services.translation.structure_checker import (
    detect_structure_invariant,
)


class TestStructureInvariantDetection:
    # --- Safe envs ---

    def test_plain_text_is_safe(self):
        result = detect_structure_invariant({"content": "Hello world."})
        assert result["is_structure_safe"] is True

    def test_properly_escaped_dollar_is_safe(self):
        result = detect_structure_invariant({"content": r"Cost is \$5."})
        assert result["is_structure_safe"] is True

    def test_inline_math_with_delimiters_is_safe(self):
        result = detect_structure_invariant({"content": "The formula $E=mc^2$ is famous."})
        # A balanced $...$ pair is safe
        assert result["is_structure_safe"] is True

    def test_empty_content_is_safe(self):
        result = detect_structure_invariant({"content": ""})
        assert result["is_structure_safe"] is True

    def test_missing_content_key_is_safe(self):
        """Missing key should default to safe, not crash."""
        result = detect_structure_invariant({})
        assert result["is_structure_safe"] is True

    # --- Unsafe envs ---

    def test_bare_dollar_is_unsafe(self):
        """A lone unescaped $ not forming a balanced pair is unsafe."""
        result = detect_structure_invariant({"content": "Price is $5 but cost is $10 extra"})
        # Two balanced dollars â†?safe; single lone dollar â†?unsafe
        # Note: `$5` and `$10` in text mode are bare dollars â€?unsafe in LaTeX
        assert result["is_structure_safe"] is False

    def test_leaked_begin_env_is_unsafe(self):
        """A raw \\begin{...} appearing in translated text is a structure leak."""
        result = detect_structure_invariant({
            "content": r"Some text \begin{equation} leaked here"
        })
        assert result["is_structure_safe"] is False

    def test_leaked_end_env_is_unsafe(self):
        result = detect_structure_invariant({
            "content": r"Text \end{itemize} leaked"
        })
        assert result["is_structure_safe"] is False

    def test_unbalanced_braces_is_unsafe(self):
        result = detect_structure_invariant({
            "content": r"{\bf Bold but not closed"
        })
        assert result["is_structure_safe"] is False

    # --- Output contract ---

    def test_result_always_has_is_structure_safe_key(self):
        for content in ["safe text", "$bare", r"\begin{x}", ""]:
            result = detect_structure_invariant({"content": content})
            assert "is_structure_safe" in result

    def test_result_propagates_original_env_fields(self):
        env = {"content": "safe", "id": "env-42", "extra": True}
        result = detect_structure_invariant(env)
        assert result["id"] == "env-42"
        assert result["extra"] is True

    def test_does_not_raise_on_unexpected_types(self):
        """Phase 0 must never crash â€?just return a safe default."""
        weird_envs = [
            {"content": None},
            {"content": 12345},
            {"content": ["list", "content"]},
        ]
        for e in weird_envs:
            result = detect_structure_invariant(e)
            assert "is_structure_safe" in result
