"""
TDD Test Suite: Selective Math / Citation Node Translation (Phase 2)
====================================================================
Tests for `translate_safe_nodes` function in selective_node_translator.py.

Spec invariants (from refine-downgrade-and-translation proposal):
  1. Only whitelisted nodes (\\text{}, \\caption{}, \\section{}, etc.) are translated.
  2. Non-whitelisted nodes (\\frac{}, \\cite{}, etc.) MUST remain completely untouched.
  3. Any failure (exception) from translator_fn MUST result in original source text returned.
  4. Structural mismatch (unbalanced braces) in translated output MUST trigger rollback to source.
  5. NO repair queuing: the function is pure and has zero side effects on failure.
  6. Citation key structure MUST be completely untouched.

Design boundary (from spec): If a node is undecidable or triggers any risk,
retaining the original source text is an intentional, safety-first design choice.
"""
import asyncio
import pytest

_selective_mod = pytest.importorskip("backend.app.services.translation.selective_node_translator")
translate_safe_nodes = _selective_mod.translate_safe_nodes
SAFE_NODE_WHITELIST = _selective_mod.SAFE_NODE_WHITELIST


async def simple_translator(text: str) -> str:
    """A mock translator that simulates successful translation."""
    return text.replace("Hello", "你好").replace("World", "世界").replace("Introduction", "介绍")


async def failing_translator(text: str) -> str:
    """A mock translator that always raises an exception."""
    raise RuntimeError("LLM connection failed")


async def structural_break_translator(text: str) -> str:
    """A mock translator that returns text with unbalanced braces �?triggers rollback."""
    return "broken { { text"


class TestSafeNodeWhitelist:

    def test_whitelist_contains_text_cmd(self):
        assert r"\text" in SAFE_NODE_WHITELIST

    def test_whitelist_contains_caption_cmd(self):
        assert r"\caption" in SAFE_NODE_WHITELIST

    def test_whitelist_contains_section_cmds(self):
        assert r"\section" in SAFE_NODE_WHITELIST
        assert r"\subsection" in SAFE_NODE_WHITELIST
        assert r"\subsubsection" in SAFE_NODE_WHITELIST


class TestTranslateSafeNodes:

    def test_text_node_inner_translated(self):
        """\\text{Hello World} should become \\text{你好 世界}."""
        source = r"\text{Hello World}"
        result = asyncio.run(translate_safe_nodes(source, simple_translator))
        assert "你好" in result or "世界" in result, f"Expected translation in: {result}"
        assert result.startswith(r"\text{"), f"\\text wrapper should be preserved: {result}"
        assert result.endswith("}"), f"closing brace should be preserved: {result}"

    def test_non_whitelisted_node_untouched(self):
        """\\frac{a}{b} must pass through completely unchanged."""
        source = r"\frac{a}{b}"
        result = asyncio.run(translate_safe_nodes(source, simple_translator))
        assert result == source, f"Non-whitelisted node must not be modified: {result}"

    def test_cite_structure_untouched(self):
        """\\cite{key2024} must come out exactly the same �?citation key must not change."""
        source = r"\cite{key2024}"
        result = asyncio.run(translate_safe_nodes(source, simple_translator))
        assert result == source, f"Citation must not be modified: {result}"

    def test_failure_rollback_to_source(self):
        """Any exception from translator_fn must return original source text."""
        source = r"\text{Introduction}"
        result = asyncio.run(translate_safe_nodes(source, failing_translator))
        assert result == source, (
            f"On translator_fn failure, must rollback to original source. Got: {result}"
        )

    def test_no_repair_queued_on_failure(self):
        """translate_safe_nodes must have no side effects on failure �?pure function."""
        # The function must complete normally (no exception propagating out)
        source = r"\text{Introduction}"
        try:
            result = asyncio.run(translate_safe_nodes(source, failing_translator))
            assert result == source
        except Exception as e:
            pytest.fail(f"translate_safe_nodes must not propagate translator exceptions: {e}")

    def test_structural_mismatch_rollback(self):
        """If translated result has unbalanced braces, rollback to source."""
        source = r"\text{Introduction}"
        result = asyncio.run(translate_safe_nodes(source, structural_break_translator))
        assert result == source, (
            f"Unbalanced braces in translation must trigger rollback. Got: {result}"
        )

    def test_section_node_translated(self):
        """\\section{Introduction} should translate the inner text."""
        source = r"\section{Introduction}"
        result = asyncio.run(translate_safe_nodes(source, simple_translator))
        assert "介绍" in result, f"Section content should be translated: {result}"
        assert r"\section{" in result, f"\\section wrapper must be preserved: {result}"

    def test_mixed_content_only_whitelisted_translated(self):
        """In mixed content, only whitelisted nodes should be translated."""
        source = r"$f(x) = \frac{1}{2} \text{Hello}$"
        result = asyncio.run(translate_safe_nodes(source, simple_translator))
        # frac must be unchanged
        assert r"\frac{1}{2}" in result, f"\\frac must not be touched: {result}"
        # text content may be translated
        # The outer equation structure must remain intact
        assert result.startswith("$"), f"Dollar sign must be preserved: {result}"
        assert result.endswith("$"), f"Closing dollar sign must be preserved: {result}"

    def test_function_is_async(self):
        """translate_safe_nodes must be an async function."""
        import inspect
        assert inspect.iscoroutinefunction(translate_safe_nodes), (
            "translate_safe_nodes must be an async function"
        )

    def test_empty_source_returns_empty(self):
        """Empty source text should return empty string."""
        result = asyncio.run(translate_safe_nodes("", simple_translator))
        assert result == ""
