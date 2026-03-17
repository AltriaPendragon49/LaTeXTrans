"""
Phase 2 validation/retry routing tests.
"""

from backend.app.services.agents.validator_agent import (
    ERROR_TYPE_A,
    ERROR_TYPE_B,
    ERROR_TYPE_C,
    ERROR_TYPE_C1,
    ERROR_TYPE_C2,
    classify_error,
)


class TestClassifyErrorBackwardCompat:

    def test_type_a_still_returned_for_not_found(self):
        assert classify_error({"command_error": "file not found: abc.tex"}) == ERROR_TYPE_A

    def test_type_b_returned_for_bracket_only(self):
        assert classify_error({"bracket_error": "Extra closing bracket ']' at position 5"}) == ERROR_TYPE_B

    def test_empty_error_returns_b(self):
        assert classify_error({}) == ERROR_TYPE_B


class TestClassifyErrorC1:

    def test_single_missing_placeholder_is_c1(self):
        error = {"ph_error": "Missing placeholders: <PLACEHOLDER_ENV_1> translation error or is missing!"}
        assert classify_error(error) == ERROR_TYPE_C1

    def test_isolated_math_delimiter_mismatch_is_c1(self):
        error = {"math_error": "math_delimiter_mismatch: original has 2 inline $, translation has 1"}
        assert classify_error(error) == ERROR_TYPE_C1

    def test_protected_cmd_residual_is_c1(self):
        error = {
            "math_error": "protected_cmd_residual: translation contains unreplaced PROTECTED_CMD placeholder"
        }
        assert classify_error(error) == ERROR_TYPE_C1

    def test_single_count_mismatch_no_global_is_c1(self):
        error = {"command_error": "LaTeX command translation error: '\\section' - expected 1, found 0"}
        assert classify_error(error) == ERROR_TYPE_C1


class TestClassifyErrorC2:

    def test_multiple_missing_placeholders_is_c2(self):
        error = {
            "ph_error": (
                "Missing placeholders: <PLACEHOLDER_ENV_1>, <PLACEHOLDER_ENV_2> "
                "translation error or is missing!"
            )
        }
        assert classify_error(error) == ERROR_TYPE_C2

    def test_global_ph_error_is_c2(self):
        error = {
            "global_ph_error": "global_placeholder_stack_mismatch: unmatched begin tag <PLACEHOLDER_input_begin>"
        }
        assert classify_error(error) == ERROR_TYPE_C2

    def test_global_ph_error_with_math_error_is_c2(self):
        error = {
            "math_error": "math_delimiter_mismatch: bare math token",
            "global_ph_error": "global_placeholder_stack_mismatch: unmatched tag",
        }
        assert classify_error(error) == ERROR_TYPE_C2

    def test_many_command_mismatches_is_c2(self):
        error = {
            "command_error": (
                "LaTeX command translation error:\n"
                "'\\section' - expected 1, found 0\n"
                "'\\label' - expected 3, found 1\n"
                "'\\cite' - expected 2, found 0"
            )
        }
        assert classify_error(error) == ERROR_TYPE_C2

    def test_missing_placeholder_plus_global_is_c2(self):
        error = {
            "ph_error": "Missing placeholders: <PLACEHOLDER_ENV_1> translation error",
            "global_ph_error": "global_placeholder_stack_mismatch: unmatched tag",
        }
        assert classify_error(error) == ERROR_TYPE_C2

    def test_env_boundary_mismatch_is_c2(self):
        error = {"math_error": "env_boundary_mismatch: crossed boundary tokens ENV_BEGIN_1 ... ENV_END_2"}
        assert classify_error(error) == ERROR_TYPE_C2

    def test_level_a_env_placeholder_residual_is_c2(self):
        error = {"math_error": "level_a_env_placeholder_residual: unresolved Level-A ENV placeholders"}
        assert classify_error(error) == ERROR_TYPE_C2

    def test_eqrow_placeholder_sequence_mismatch_is_c2(self):
        error = {"math_error": "eqrow_placeholder_sequence_mismatch: expected ['<EQROW_0>'], found []"}
        assert classify_error(error) == ERROR_TYPE_C2

    def test_item_anchor_sequence_mismatch_is_c1(self):
        error = {"math_error": "item_anchor_sequence_mismatch: expected ['<ITEM_1>'], found []"}
        assert classify_error(error) == ERROR_TYPE_C1

    def test_list_env_item_order_mismatch_is_c1(self):
        error = {"math_error": "list_env_item_order_mismatch: item count mismatch (expected 2, found 1)"}
        assert classify_error(error) == ERROR_TYPE_C1


class TestErrorTypeConstants:

    def test_c1_constant_defined(self):
        assert ERROR_TYPE_C1 == "C1"

    def test_c2_constant_defined(self):
        assert ERROR_TYPE_C2 == "C2"

    def test_c_backward_compat(self):
        assert ERROR_TYPE_C == "C"

    def test_c1_and_c2_distinct(self):
        assert ERROR_TYPE_C1 != ERROR_TYPE_C2
        assert ERROR_TYPE_C1 != ERROR_TYPE_C
        assert ERROR_TYPE_C2 != ERROR_TYPE_C
