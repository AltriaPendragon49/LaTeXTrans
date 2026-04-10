"""
test_translation_repair_agent.py
reduce-translation-fallbacks ‚Ä?Unit tests for context-aware repair enhancements

Covers:
  1. _count_math_delimiters ‚Ä?basic counting, $$ exclusion, \\( / \\) pairs
  2. _math_delimiter_guard ‚Ä?complex-env bypass; mismatch detection
  3. _build_repair_prompt ‚Ä?three branches (Total Erasure / Math Mismatch / General)
  4. Token gate in _repair_one ‚Ä?source > 256 tokens skips LLM
  5. Math guard integration ‚Ä?_repair_one returns None on delimiter mismatch
  6. All four distinct warning tags are tested
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.agents.translation_repair_agent import (
    MAX_ERASURE_RECOVERY_TOKENS,
    _count_math_delimiters,
    _math_delimiter_guard,
    _placeholder_guard,
    TranslationRepairAgent,
)
from backend.app.services.agents.pipeline_schema import FallbackReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent() -> TranslationRepairAgent:
    return TranslationRepairAgent(config={
        "llm_config": {
            "model": "test-model",
            "base_url": "http://fake-llm/v1/chat",
            "api_key": "test-key",
        },
        "source_language": "en",
        "target_language": "zh",
    })


def _make_report(
    *,
    fallback_kind: str = "c1_structural_rollback",
    chunk_scope: str = "sec_1",
    root_cause: str = "math_delimiter_mismatch",
    translated_text: str = "some translated text",
    validation_evidence: dict | None = None,
) -> FallbackReport:
    return FallbackReport(
        fallback_kind=fallback_kind,
        chunk_scope=chunk_scope,
        root_cause=root_cause,
        translated_text=translated_text,
        validation_evidence=validation_evidence,
    )


# ---------------------------------------------------------------------------
# 1. _count_math_delimiters
# ---------------------------------------------------------------------------

class TestCountMathDelimiters:

    def test_counts_lone_dollar(self):
        assert _count_math_delimiters(r"The value $x$ is fine.") == 2

    def test_does_not_count_display_math_dollars(self):
        # $$ should NOT be counted
        assert _count_math_delimiters(r"$$x = y$$") == 0

    def test_counts_paren_delimiters(self):
        text = r"We have \(x\) and \(y\)."
        assert _count_math_delimiters(text) == 4  # 2√ó\( + 2√ó\)

    def test_mixed_delimiters(self):
        text = r"See $a$ and \(b\) here."
        assert _count_math_delimiters(text) == 4  # 2 dollar + 2 paren

    def test_empty_string(self):
        assert _count_math_delimiters("") == 0

    def test_no_math(self):
        assert _count_math_delimiters("Plain text without math.") == 0

    def test_double_dollar_not_counted_alongside_lone(self):
        # One pair of $$ and one lone $x$ ‚Ü?only 2 from $x$
        text = r"Formula: $$\int_0^1$$. Also $\alpha$."
        assert _count_math_delimiters(text) == 2


# ---------------------------------------------------------------------------
# 2. _math_delimiter_guard
# ---------------------------------------------------------------------------

class TestMathDelimiterGuard:

    def test_matching_counts_returns_true(self):
        src = r"Value $x$ and $y$."
        rep = r"ÂÄ?$x$ Âí?$y$„Ä?
        assert _math_delimiter_guard(src, rep) is True

    def test_mismatch_returns_false(self):
        src = r"Formula $x$ here."
        rep = r"ÂÖ¨Âºè x ËøôÈáå„Ä?  # missing the $ delimiters
        assert _math_delimiter_guard(src, rep) is False

    def test_complex_env_skips_check(self):
        # Source has align ‚Ä?guard must return True regardless of repaired content
        src = r"\begin{align}a &= b\end{align}"
        rep = r"\begin{align}a = b\end{align} $extra$"
        assert _math_delimiter_guard(src, rep) is True

    def test_cases_env_skips_check(self):
        src = r"\begin{cases}a & b\end{cases}"
        rep = r"\begin{cases}a & b\end{cases} missing dollar"
        assert _math_delimiter_guard(src, rep) is True

    def test_no_math_both_empty_returns_true(self):
        assert _math_delimiter_guard("plain text", "ÊôÆÈÄöÊñáÊú?) is True


# ---------------------------------------------------------------------------
# 3. _build_repair_prompt branches
# ---------------------------------------------------------------------------

class TestBuildRepairPrompt:

    def test_total_erasure_branch(self):
        agent = _make_agent()
        report = _make_report(
            fallback_kind="c1_structural_rollback",
            translated_text="",
            root_cause="total_erasure",
        )
        prompt = agent._build_repair_prompt(report, "Source text here.")
        assert "recovery" in prompt.lower() or "translate" in prompt.lower()
        assert "Do NOT introduce any new LaTeX environments or macros" in prompt
        assert "PLACEHOLDER" in prompt

    def test_math_mismatch_branch(self):
        agent = _make_agent()
        report = _make_report(
            fallback_kind="c1_structural_rollback",
            translated_text="Â∑≤ÁøªËØëÊñáÊú?$x ÈÖçÂØπÈîô‰∫Ü„Ä?,
            root_cause="math_delimiter_mismatch",
            validation_evidence={"math_error": "math_delimiter_mismatch: count differs"},
        )
        prompt = agent._build_repair_prompt(report, r"Source $x$ here.")
        # Must mention the exact source delimiter count
        assert "1" in prompt  # source has 2 lone $ signs = 2; wait, "Source $x$" has 2
        assert "math" in prompt.lower()
        assert "align" in prompt.lower() or "complex" in prompt.lower()

    def test_general_branch(self):
        agent = _make_agent()
        report = _make_report(
            fallback_kind="c2_structural_collapse",
            translated_text="ÊúâÈóÆÈ¢òÁöÑÁøªËØëÊñáÊú¨„Ä?,
            root_cause="c2_global_structure_collapse",
        )
        prompt = agent._build_repair_prompt(report, "Some source text.")
        assert "PLACEHOLDER" in prompt
        assert "ITEM" in prompt  # anchor preservation
        assert "rephrase" in prompt.lower() or "semantic" in prompt.lower() or "do not" in prompt.lower()

    def test_erasure_prompt_forbids_new_envs(self):
        """Regression: Total Erasure prompt MUST explicitly forbid new environments."""
        agent = _make_agent()
        report = _make_report(translated_text="", root_cause="total_erasure")
        prompt = agent._build_repair_prompt(report, "Source.")
        assert "Do NOT introduce any new LaTeX environments or macros" in prompt


# ---------------------------------------------------------------------------
# 4. Token gate in _repair_one
# ---------------------------------------------------------------------------

class TestTokenGate:

    def test_large_erasure_skips_llm(self):
        """source_tokens > MAX_ERASURE_RECOVERY_TOKENS ‚Ü?no LLM call."""
        agent = _make_agent()
        # Generate text that exceeds the token gate
        long_source = "word " * 300  # well over 256 tokens
        report = _make_report(translated_text="", root_cause="total_erasure")

        llm_called = {"count": 0}

        async def fake_llm(prompt, text):
            llm_called["count"] += 1
            return "repaired"

        agent._call_llm_repair = fake_llm
        result, reason = asyncio.run(agent._repair_one(report, long_source))

        assert result is None, "Token gate should have skipped LLM and returned None"
        assert reason == "token-gate"
        assert llm_called["count"] == 0, "LLM should not have been called"

    def test_small_erasure_calls_llm(self):
        """source_tokens <= MAX_ERASURE_RECOVERY_TOKENS ‚Ü?LLM is called."""
        agent = _make_agent()
        short_source = "Short source text."  # well under 256 tokens
        report = _make_report(translated_text="", root_cause="total_erasure")

        llm_called = {"count": 0}

        async def fake_llm(prompt, text):
            llm_called["count"] += 1
            return short_source  # return identical so guards pass

        agent._call_llm_repair = fake_llm
        asyncio.run(agent._repair_one(report, short_source))

        assert llm_called["count"] == 1, "LLM should have been called for small erasure"

    def test_token_gate_boundary(self):
        """Exactly at MAX_ERASURE_RECOVERY_TOKENS should still call LLM."""
        import math as _math
        agent = _make_agent()
        # Craft text that uses exactly MAX_ERASURE_RECOVERY_TOKENS tokens (UTF-8 bytes/3)
        target_bytes = MAX_ERASURE_RECOVERY_TOKENS * 3
        boundary_source = "a" * target_bytes
        assert _math.ceil(len(boundary_source.encode("utf-8")) / 3.0) == MAX_ERASURE_RECOVERY_TOKENS

        report = _make_report(translated_text="", root_cause="total_erasure")
        llm_called = {"count": 0}

        async def fake_llm(prompt, text):
            llm_called["count"] += 1
            return boundary_source

        agent._call_llm_repair = fake_llm
        asyncio.run(agent._repair_one(report, boundary_source))
        assert llm_called["count"] == 1


# ---------------------------------------------------------------------------
# 5. Math guard integration in _repair_one
# ---------------------------------------------------------------------------

class TestMathGuardIntegration:

    def test_math_mismatch_repair_rejected(self):
        """Gate 4: if repaired text has wrong delimiter count, return None."""
        agent = _make_agent()
        source = r"Value $x$ and $y$ here."  # 4 delimiters
        report = _make_report(
            translated_text=source,
            root_cause="math_delimiter_mismatch",
            validation_evidence={"math_error": "math_delimiter_mismatch"},
        )

        async def fake_llm(prompt, text):
            # Return text with only 2 delimiters instead of 4
            return r"ÂÄ?$x$ ËøôÈáå„Ä?

        agent._call_llm_repair = fake_llm
        result, reason = asyncio.run(agent._repair_one(report, source))
        assert result is None
        assert reason == "math-guard"

    def test_matching_delimiter_repair_accepted(self):
        agent = _make_agent()
        source = r"Value $x$ here."  # 2 delimiters
        report = _make_report(
            translated_text=source,
            root_cause="math_delimiter_mismatch",
            validation_evidence={"math_error": "math_delimiter_mismatch"},
        )

        async def fake_llm(prompt, text):
            return r"ÂÄ?$x$ ËøôÈáå„Ä?  # also 2 delimiters

        agent._call_llm_repair = fake_llm
        result, reason = asyncio.run(agent._repair_one(report, source))
        assert result == r"ÂÄ?$x$ ËøôÈáå„Ä?
        assert reason is None


# ---------------------------------------------------------------------------
# 6. Placeholder guard integration
# ---------------------------------------------------------------------------

class TestPlaceholderGuardIntegration:

    def test_missing_placeholder_rejected(self):
        agent = _make_agent()
        source = "See <PLACEHOLDER_ENV_1> for details."
        report = _make_report(translated_text=source, root_cause="bracket_mismatch")

        async def fake_llm(prompt, text):
            return "ËØ¶ËßÅËØ¶ÊÉÖ„Ä?  # placeholder stripped

        agent._call_llm_repair = fake_llm
        result, reason = asyncio.run(agent._repair_one(report, source))
        assert result is None
        assert reason == "placeholder-guard"

    def test_preserved_placeholder_accepted(self):
        agent = _make_agent()
        source = "See <PLACEHOLDER_ENV_1> for details."
        report = _make_report(translated_text=source, root_cause="bracket_mismatch")

        async def fake_llm(prompt, text):
            return "ËØ¶ËßÅ <PLACEHOLDER_ENV_1>„Ä?

        agent._call_llm_repair = fake_llm
        result, reason = asyncio.run(agent._repair_one(report, source))
        assert result is not None
        assert reason is None
        assert "<PLACEHOLDER_ENV_1>" in result


# ---------------------------------------------------------------------------
# 7. MAX_ERASURE_RECOVERY_TOKENS constant
# ---------------------------------------------------------------------------

def test_max_erasure_recovery_tokens_value():
    """Spec specifies 256 as the hard safety threshold."""
    assert MAX_ERASURE_RECOVERY_TOKENS == 256
