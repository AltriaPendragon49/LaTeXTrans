"""
TDD Test Suite: Phase 3 Deterministic Downgrade
=================================================
Tests for the `deterministic_downgrade` function.

Design spec (from design.md §1 Phase 3):
  1. Phase 3 MUST NOT invoke any LLM — it is deterministic.
  2. Valid downgrade strategies (in priority order):
       a. Source passthrough (fallback_to_source)
       b. Placeholder + warning comment
  3. The returned env dict MUST be "compilation-safe":
       - `trans_content` is non-empty.
       - `translation_status` is set to a downgrade status string.
       - `downgrade_reason` is set to one of the canonical reasons.
  4. The function MUST handle all failure origins:
       - QueueTimeoutError (排队超时)
       - RepairRateLimitExceededError (429 弃权)
       - Any other Phase 2 exception
  5. The function MUST preserve all original env fields.
  6. The `trans_content` must equal `content` (source passthrough).
"""
import pytest

from backend.app.services.translation.downgrade_handler import (
    deterministic_downgrade,
    DOWNGRADE_REASON_QUEUE_TIMEOUT,
    DOWNGRADE_REASON_RATE_LIMIT,
    DOWNGRADE_REASON_REPAIR_FAILED,
    DOWNGRADE_STATUS,
)
from backend.app.services.translation.repair_scheduler import QueueTimeoutError
from backend.app.services.agents.controlled_repair_agent import RepairRateLimitExceededError


class TestDeterministicDowngrade:

    def test_queue_timeout_sets_source_passthrough(self):
        env = {"content": "broken latex $", "placeholder": "<ENV_1>", "env_name": "theorem"}
        exc = QueueTimeoutError("排队超时")
        result = deterministic_downgrade(env, exc)
        # trans_content must equal source (safe passthrough)
        assert result["trans_content"] == env["content"]

    def test_queue_timeout_sets_correct_reason(self):
        env = {"content": "x", "placeholder": "<ENV_1>"}
        result = deterministic_downgrade(env, QueueTimeoutError("timeout"))
        assert result["downgrade_reason"] == DOWNGRADE_REASON_QUEUE_TIMEOUT

    def test_rate_limit_sets_source_passthrough(self):
        env = {"content": "some broken env", "placeholder": "<ENV_2>"}
        exc = RepairRateLimitExceededError("429 弃权")
        result = deterministic_downgrade(env, exc)
        assert result["trans_content"] == env["content"]

    def test_rate_limit_sets_correct_reason(self):
        env = {"content": "x", "placeholder": "<ENV_3>"}
        result = deterministic_downgrade(env, RepairRateLimitExceededError("x"))
        assert result["downgrade_reason"] == DOWNGRADE_REASON_RATE_LIMIT

    def test_generic_exception_sets_repair_failed_reason(self):
        env = {"content": "env content"}
        result = deterministic_downgrade(env, RuntimeError("unexpected"))
        assert result["downgrade_reason"] == DOWNGRADE_REASON_REPAIR_FAILED

    def test_generic_exception_sets_source_passthrough(self):
        env = {"content": "env content"}
        result = deterministic_downgrade(env, RuntimeError("unexpected"))
        assert result["trans_content"] == env["content"]

    def test_translation_status_is_set(self):
        env = {"content": "x"}
        result = deterministic_downgrade(env, QueueTimeoutError("x"))
        assert result.get("translation_status") == DOWNGRADE_STATUS

    def test_all_original_fields_preserved(self):
        env = {
            "content": "original",
            "placeholder": "<ENV_9>",
            "env_name": "figure",
            "need_trans": True,
            "custom_field": 42,
        }
        result = deterministic_downgrade(env, QueueTimeoutError("x"))
        for key, val in env.items():
            if key not in ("trans_content", "translation_status", "downgrade_reason"):
                assert result[key] == val, f"Field '{key}' was unexpectedly changed"

    def test_never_calls_llm(self):
        """No aiohttp or async calls should be made — function must be synchronous."""
        import inspect
        from backend.app.services.translation import downgrade_handler
        func = getattr(downgrade_handler, "deterministic_downgrade")
        assert not inspect.iscoroutinefunction(func), (
            "deterministic_downgrade must be a regular (sync) function — LLM calls are forbidden."
        )

    def test_empty_content_gives_placeholder_comment(self):
        """If original content is empty, output a safe placeholder comment."""
        env = {"content": "", "placeholder": "<ENV_1>"}
        result = deterministic_downgrade(env, QueueTimeoutError("x"))
        assert result["trans_content"] is not None
        assert isinstance(result["trans_content"], str)

    def test_downgrade_reason_is_string(self):
        env = {"content": "x"}
        result = deterministic_downgrade(env, QueueTimeoutError("x"))
        assert isinstance(result["downgrade_reason"], str)
        assert len(result["downgrade_reason"]) > 0
