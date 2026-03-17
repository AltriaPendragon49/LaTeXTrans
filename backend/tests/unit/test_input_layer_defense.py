"""
Phase 1 Input-Layer Defense — TDD Tests
=========================================
Tests for:
  1. isolate_inline_math   – replace $...$ and \(...\) with <INLMATH_NN> placeholders
  2. restore_inline_math   – restore placeholders back to original math
  3. preprocess_risky_tokens – pre-escape bare _ outside math blocks to \_

These tests are written BEFORE the implementation (TDD red phase).
"""
import pytest
from backend.app.services.latex.utils import (
    isolate_inline_math,
    restore_inline_math,
    isolate_env_blocks,
    restore_env_blocks,
    preprocess_risky_tokens,
    mask_sensitive_commands,
    unmask_sensitive_commands,
    mask_eqnarray_comments_strict,
    restore_eqnarray_comments_strict,
    split_eqnarray_rows_strict,
    rebuild_eqnarray_rows_strict,
    classify_eqnarray_row_kind,
    anchor_list_items_in_env_body,
    restore_list_items_in_env_body,
    validate_immutable_placeholder_sequence,
)


# ---------------------------------------------------------------------------
# isolate_inline_math
# ---------------------------------------------------------------------------

class TestIsolateInlineMath:

    def test_single_dollar_replaced(self):
        """$x+y$ should become a placeholder."""
        text = r"The value is $x + y$ in the equation."
        result, math_map = isolate_inline_math(text)
        assert "<INLMATH_01>" in result
        assert "$x + y$" not in result
        assert len(math_map) == 1

    def test_multiple_dollars_replaced_in_order(self):
        """Multiple $...$ spans get sequentially numbered placeholders."""
        text = r"Let $a$ and $b$ be real."
        result, math_map = isolate_inline_math(text)
        assert "<INLMATH_01>" in result
        assert "<INLMATH_02>" in result
        assert "$a$" not in result
        assert "$b$" not in result
        assert len(math_map) == 2

    def test_paren_notation_replaced(self):
        r"""Parenthesis-style inline math \(...\) is also replaced."""
        text = r"Formula \(x^2\) is inline."
        result, math_map = isolate_inline_math(text)
        assert "<INLMATH_01>" in result
        assert r"\(x^2\)" not in result
        assert len(math_map) == 1

    def test_display_math_not_replaced(self):
        """Display math $$ ... $$ should NOT be replaced by this function."""
        text = r"Display: $$x = 1$$ stays."
        result, math_map = isolate_inline_math(text)
        assert "$$" in result
        assert len(math_map) == 0

    def test_empty_string(self):
        """Empty input returns empty output with empty map."""
        result, math_map = isolate_inline_math("")
        assert result == ""
        assert math_map == {}

    def test_no_math(self):
        """Text without math remains unchanged."""
        text = "Hello world, no math here."
        result, math_map = isolate_inline_math(text)
        assert result == text
        assert math_map == {}

    def test_mixed_inline_and_paren(self):
        r"""Mix of $...$ and \(...\) are both replaced."""
        text = r"We have $a$ and \(b\) both inline."
        result, math_map = isolate_inline_math(text)
        assert len(math_map) == 2
        # Original notation gone
        assert "$a$" not in result
        assert r"\(b\)" not in result

    def test_multiline_inline_not_replaced(self):
        """$...$ spanning multiple lines is NOT treated as inline math (safety measure)."""
        text = "Here is $first\nsecond$ spanning lines."
        result, math_map = isolate_inline_math(text)
        # Multiline math should remain untouched for safety
        assert "$" in result  # still there
        # map should be empty OR contain the span — implementation can decide;
        # the key requirement is not to break multi-line display math
        # We only assert the text is not corrupted:
        assert "first" in result
        assert "second" in result


# ---------------------------------------------------------------------------
# restore_inline_math
# ---------------------------------------------------------------------------

class TestRestoreInlineMath:

    def test_single_restore(self):
        """A single placeholder is correctly restored."""
        original_math = r"$x + y$"
        math_map = {"<INLMATH_01>": original_math}
        text = "The value is <INLMATH_01> in the equation."
        result = restore_inline_math(text, math_map)
        assert original_math in result
        assert "<INLMATH_01>" not in result

    def test_multiple_restore_order(self):
        """Multiple placeholders are all restored correctly."""
        math_map = {"<INLMATH_01>": "$a$", "<INLMATH_02>": "$b$"}
        text = "Let <INLMATH_01> and <INLMATH_02> be real."
        result = restore_inline_math(text, math_map)
        assert "$a$" in result
        assert "$b$" in result
        assert "<INLMATH_01>" not in result
        assert "<INLMATH_02>" not in result

    def test_empty_map(self):
        """Empty map leaves text unchanged."""
        text = "No placeholders here."
        result = restore_inline_math(text, {})
        assert result == text

    def test_roundtrip(self):
        """isolate then restore returns the original text."""
        text = r"We solve $\alpha + \beta = 0$ for all $x \in \mathbb{R}$."
        isolated, math_map = isolate_inline_math(text)
        restored = restore_inline_math(isolated, math_map)
        assert restored == text


# ---------------------------------------------------------------------------
# isolate_env_blocks / restore_env_blocks
# ---------------------------------------------------------------------------

class TestEnvironmentIsolation:

    def test_level_a_environment_is_fully_frozen(self):
        text = r"Before \begin{theorem}Let x_i be fixed.\end{theorem} After."
        isolated, env_map = isolate_env_blocks(text)
        assert "<ENV_" in isolated
        assert r"\begin{theorem}" not in isolated
        assert r"\end{theorem}" not in isolated
        restored = restore_env_blocks(isolated, env_map)
        assert restored == text

    def test_level_b_environment_freezes_boundaries_only(self):
        text = r"Start \begin{customenv}Inner english text.\end{customenv} End"
        isolated, env_map = isolate_env_blocks(text)
        assert "<ENV_BEGIN_" in isolated
        assert "<ENV_END_" in isolated
        assert "Inner english text." in isolated
        restored = restore_env_blocks(isolated, env_map)
        assert restored == text

    def test_verb_command_is_frozen_as_level_a_literal(self):
        text = r"Use \verb|a_b_c| in sentence."
        isolated, env_map = isolate_env_blocks(text)
        assert r"\verb|a_b_c|" not in isolated
        assert "<ENV_" in isolated
        restored = restore_env_blocks(isolated, env_map)
        assert restored == text

    def test_restore_env_blocks_raises_when_placeholder_missing(self):
        text = r"\begin{theorem}x\end{theorem}"
        isolated, env_map = isolate_env_blocks(text)
        broken = isolated.replace("<ENV_", "<BROKEN_ENV_")
        with pytest.raises(ValueError):
            restore_env_blocks(broken, env_map)


class TestEqnarrayStrictHelpers:

    def test_eqnarray_comment_mask_roundtrip(self):
        text = "a + b % inline comment\nc + d % tail"
        masked, cmap = mask_eqnarray_comments_strict(text)
        assert "% inline comment" not in masked
        assert "% tail" not in masked
        restored = restore_eqnarray_comments_strict(masked, cmap)
        assert restored == text

    def test_eqnarray_split_rebuild_keeps_star_and_optional_suffix(self):
        body = r"x = y \\*[2pt] plain text row \\ z = t"
        rows, seps = split_eqnarray_rows_strict(body)
        assert len(rows) == 3
        assert seps[0] == r"\\*[2pt]"
        assert seps[1] == r"\\"
        rebuilt = rebuild_eqnarray_rows_strict(rows, seps)
        assert rebuilt == body

    def test_eqnarray_split_with_comments_does_not_break_delimiter(self):
        body = "x = y % has \\\\ in comment\n\\\\[2pt] text row \\\\* z = t"
        masked, cmap = mask_eqnarray_comments_strict(body)
        rows, seps = split_eqnarray_rows_strict(masked)
        rebuilt = rebuild_eqnarray_rows_strict(rows, seps)
        restored = restore_eqnarray_comments_strict(rebuilt, cmap)
        assert restored == body

    def test_eqnarray_row_classification(self):
        assert classify_eqnarray_row_kind(r"a & b = c") == "math"
        assert classify_eqnarray_row_kind(r"This is natural language row.") == "text"
        assert classify_eqnarray_row_kind(r"id_1") == "math"


class TestListItemAnchors:

    def test_anchor_list_items_scoped_to_list_env_body(self):
        text = r"\begin{itemize}\item first \item[Key] second\end{itemize}"
        anchored, item_map, tokens = anchor_list_items_in_env_body(text)
        assert len(tokens) == 2
        assert "<ITEM_1>" in anchored
        assert "<ITEM_2>" in anchored
        restored = restore_list_items_in_env_body(anchored, item_map)
        assert restored == text

    def test_validate_immutable_placeholder_sequence_for_item_and_eqrow(self):
        ok_text = "<ITEM_1> x <ITEM_2> y <EQROW_0> z"
        assert validate_immutable_placeholder_sequence(ok_text, ["<ITEM_1>", "<ITEM_2>"], "ITEM") is None
        assert validate_immutable_placeholder_sequence(ok_text, ["<EQROW_0>"], "EQROW") is None
        item_err = validate_immutable_placeholder_sequence("<ITEM_2> <ITEM_1>", ["<ITEM_1>", "<ITEM_2>"], "ITEM")
        eqrow_err = validate_immutable_placeholder_sequence("<EQROW_1>", ["<EQROW_0>"], "EQROW")
        assert "item_anchor_sequence_mismatch" in item_err
        assert "eqrow_placeholder_sequence_mismatch" in eqrow_err


# ---------------------------------------------------------------------------
# preprocess_risky_tokens
# ---------------------------------------------------------------------------

class TestPreprocessRiskyTokens:

    def test_bare_underscore_escaped_in_text(self):
        """A bare _ in plain text is escaped to \_."""
        text = "The variable my_var is used here."
        math_map = {}
        result = preprocess_risky_tokens(text, math_map)
        assert r"my\_var" in result or r"my\\_var" in result

    def test_underscore_inside_math_not_escaped(self):
        """An _ already placed inside a math placeholder region is NOT escaped."""
        # First isolate math so the map tells us what's already safe
        text = r"We use $x_i$ and also text_var outside."
        isolated, math_map = isolate_inline_math(text)
        result = preprocess_risky_tokens(isolated, math_map)
        # The math placeholder should remain intact
        assert "<INLMATH_01>" in result
        # The math content is safely hidden; outside underscore should be escaped
        assert r"text\_var" in result or r"text\\_var" in result

    def test_already_escaped_not_double_escaped(self):
        r"""An already-escaped \_ should NOT become \\\_."""
        text = r"Already escaped \_ should stay."
        math_map = {}
        result = preprocess_risky_tokens(text, math_map)
        # Should not double-escape
        assert r"\\_" not in result or result.count(r"\_") == 1

    def test_empty_string(self):
        result = preprocess_risky_tokens("", {})
        assert result == ""

    def test_no_underscores(self):
        text = "No underscores in this text at all."
        result = preprocess_risky_tokens(text, {})
        assert result == text

    def test_underscore_in_placeholder_name_not_escaped(self):
        """Underscores inside <INLMATH_NN> tags must not be escaped."""
        # After isolation, the text contains <INLMATH_01> which has no _
        # but if there were a placeholder like <PLACEHOLDER_ENV_1>, its _ should be safe.
        text = "See <PLACEHOLDER_ENV_1> for details and my_var here."
        math_map = {}
        result = preprocess_risky_tokens(text, math_map)
        # Placeholder tags must remain intact
        assert "<PLACEHOLDER_ENV_1>" in result
        # text underscore outside placeholders should be escaped
        assert r"my\_var" in result or r"my\\_var" in result

    def test_env_placeholder_underscore_not_escaped(self):
        text = "X <ENV_BEGIN_9> body <ENV_END_9> token_name"
        result = preprocess_risky_tokens(text, {})
        assert "<ENV_BEGIN_9>" in result
        assert "<ENV_END_9>" in result
        assert r"token\_name" in result or r"token\\_name" in result

    def test_item_eqrow_placeholder_underscore_not_escaped(self):
        text = "A <ITEM_1> body <EQROW_2> another_token"
        result = preprocess_risky_tokens(text, {})
        assert "<ITEM_1>" in result
        assert "<EQROW_2>" in result
        assert r"another\_token" in result or r"another\\_token" in result

    def test_mask_sensitive_commands_round_trips_synthetic_placeholders(self):
        text = (
            "See <PLACEHOLDER_ENV_1> and <ENV_BEGIN_2>body<ENV_END_2> "
            "plus <ITEM_3> and <INLMATH_04>."
        )

        masked, mapping = mask_sensitive_commands(text)

        assert "<PROTECTED_CMD_" in masked
        assert "<PLACEHOLDER_ENV_1>" not in masked
        assert "<ENV_BEGIN_2>" not in masked
        assert "<ENV_END_2>" not in masked
        assert "<ITEM_3>" not in masked
        assert "<INLMATH_04>" in masked
        assert unmask_sensitive_commands(masked, mapping) == text

    def test_cross_ref_and_cite_keys_are_not_escaped(self):
        text = (
            r"See \cite{He_2016_CVPR}, \ref{eq:foo_bar}, \label{sec:part_a}, "
            r"\Cref{tab:my_table_key} and plain_token."
        )
        result = preprocess_risky_tokens(text, {})
        assert r"\cite{He_2016_CVPR}" in result
        assert r"\ref{eq:foo_bar}" in result
        assert r"\label{sec:part_a}" in result
        assert r"\Cref{tab:my_table_key}" in result
        assert r"plain\_token" in result or r"plain\\_token" in result
