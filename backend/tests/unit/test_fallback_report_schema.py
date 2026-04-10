"""
test_fallback_report_schema.py
eliminate-silent-fallback â€?Phase 1 Unit Tests

Verifies:
  1. FallbackReport schema construction for all three fallback_kind values.
  2. FallbackReport is emitted in translator_agent.fallback_reports during
     forced oversize downgrade (spec: oversize_downgrade FallbackReport).
  3. FallbackReport validates required fields and rejects invalid kinds.
  4. to_dict() produces a JSON-serializable dict.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.services.agents.pipeline_schema import FallbackReport
from backend.app.services.agents.translator_agent import TranslatorAgent


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_agent(tmp_path: Path) -> TranslatorAgent:
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    agent = TranslatorAgent(
        config={
            "llm_config": {
                "model": "gpt-4o",
                "base_url": "http://dummy",
                "api_key": "dummy",
            },
            "model_context_tokens": 1000,
            "prompt_reserve_tokens": 100,
        },
        project_dir=str(tmp_path / "project"),
        output_dir=str(output_dir),
        trans_mode=0,
    )
    return agent


# ---------------------------------------------------------------------------
# FallbackReport schema tests
# ---------------------------------------------------------------------------


class TestFallbackReportSchema:

    def test_oversize_downgrade_construction(self):
        """FallbackReport must be constructible for oversize_downgrade."""
        report = FallbackReport(
            fallback_kind="oversize_downgrade",
            chunk_scope="3_chunk_1",
            root_cause="oversize_no_safe_boundary",
            validation_evidence=None,
            translated_text=None,
        )
        assert report.fallback_kind == "oversize_downgrade"
        assert report.chunk_scope == "3_chunk_1"
        assert report.root_cause == "oversize_no_safe_boundary"
        assert report.validation_evidence is None
        assert report.translated_text is None

    def test_c2_structural_collapse_construction(self):
        """FallbackReport must be constructible for c2_structural_collapse."""
        report = FallbackReport(
            fallback_kind="c2_structural_collapse",
            chunk_scope="2_chunk_3",
            root_cause="c2_global_structure_collapse",
            validation_evidence={"error_type": "C2", "bracket_diff": -2},
            translated_text="broken latex output",
        )
        assert report.fallback_kind == "c2_structural_collapse"
        assert report.validation_evidence["error_type"] == "C2"
        assert report.translated_text == "broken latex output"

    def test_c1_structural_rollback_construction(self):
        """FallbackReport must be constructible for c1_structural_rollback."""
        report = FallbackReport(
            fallback_kind="c1_structural_rollback",
            chunk_scope="<PLACEHOLDER_ENV_5>",
            root_cause="c1_local_structural_mismatch",
            validation_evidence={"error_type": "C1"},
        )
        assert report.fallback_kind == "c1_structural_rollback"

    def test_c1_rollback_with_source_snapshot_construction(self):
        """FallbackReport remains constructible even when legacy extra fields are provided."""
        report = FallbackReport(
            fallback_kind="c1_structural_rollback",
            chunk_scope="1_chunk_2",
            root_cause="api_request_failed_after_3_attempts",
            unit_locator={
                "unit_type": "section",
                "unit_id": "1_chunk_2",
                "chunk_id": 2,
                "doc_path": None,
            },
            source_status_snapshot={
                "translation_status": "fallback_source_api_failure",
                "fallback_reason": "api_request_failed_after_3_attempts",
                "provider": "gpt-4o",
                "attempts": 3,
            },
        )
        dumped = report.to_dict()
        assert report.fallback_kind == "c1_structural_rollback"
        assert report.chunk_scope == "1_chunk_2"
        assert "unit_locator" not in dumped
        assert "source_status_snapshot" not in dumped

    def test_invalid_fallback_kind_raises(self):
        """FallbackReport must reject invalid fallback_kind values."""
        with pytest.raises(Exception):
            FallbackReport(
                fallback_kind="unknown_kind",  # invalid
                chunk_scope="1_chunk_1",
                root_cause="some_cause",
            )

    def test_missing_required_fields_raises(self):
        """FallbackReport must raise when required fields are missing."""
        with pytest.raises(Exception):
            FallbackReport(
                fallback_kind="oversize_downgrade",
                # missing chunk_scope and root_cause
            )

    def test_to_dict_is_json_serializable(self):
        """to_dict() must produce a JSON-serializable dictionary."""
        report = FallbackReport(
            fallback_kind="oversize_downgrade",
            chunk_scope="5_chunk_2",
            root_cause="oversize_no_safe_boundary",
        )
        d = report.to_dict()
        assert isinstance(d, dict)
        # Must be JSON-serializable (no exception)
        serialized = json.dumps(d, ensure_ascii=False)
        assert "oversize_downgrade" in serialized
        assert "5_chunk_2" in serialized

    def test_timestamp_is_auto_set(self):
        """timestamp field must be auto-populated."""
        report = FallbackReport(
            fallback_kind="c2_structural_collapse",
            chunk_scope="1",
            root_cause="c2_global_structure_collapse",
        )
        assert report.timestamp is not None
        assert len(report.timestamp) > 0


# ---------------------------------------------------------------------------
# TranslatorAgent oversize path emits FallbackReport
# ---------------------------------------------------------------------------


class TestTranslatorAgentFallbackReportEmission:

    def test_fallback_reports_initialized_empty(self, tmp_path: Path):
        """TranslatorAgent.fallback_reports must start empty."""
        agent = _build_agent(tmp_path)
        assert hasattr(agent, "fallback_reports")
        assert agent.fallback_reports == []

    def test_oversize_downgrade_emits_fallback_report(self, tmp_path: Path):
        """_record_oversize_downgrade must append a FallbackReport."""
        agent = _build_agent(tmp_path)
        section = {
            "section": "2_chunk_1",
            "content": "A" * 9000,
            "oversize_no_safe_boundary": True,
        }
        metadata = agent._evaluate_oversize_downgrade(section)
        assert metadata is not None, "oversize metadata should be returned"

        agent._record_oversize_downgrade(metadata)

        assert len(agent.fallback_reports) == 1
        report = agent.fallback_reports[0]
        assert isinstance(report, FallbackReport)
        assert report.fallback_kind == "oversize_downgrade"
        assert report.chunk_scope == "2_chunk_1"
        assert report.root_cause == "oversize_no_safe_boundary"

    def test_multiple_oversize_segments_emit_multiple_reports(self, tmp_path: Path):
        """Each oversize segment must emit a separate FallbackReport."""
        agent = _build_agent(tmp_path)
        for i in range(3):
            section = {
                "section": f"{i}_chunk_1",
                "content": "B" * 9000,
                "oversize_no_safe_boundary": True,
            }
            metadata = agent._evaluate_oversize_downgrade(section)
            assert metadata is not None
            agent._record_oversize_downgrade(metadata)

        assert len(agent.fallback_reports) == 3
        kinds = {r.fallback_kind for r in agent.fallback_reports}
        assert kinds == {"oversize_downgrade"}

    def test_non_oversize_section_does_not_emit_report(self, tmp_path: Path):
        """Normal sections must not emit FallbackReport."""
        agent = _build_agent(tmp_path)
        section = {
            "section": "1_chunk_1",
            "content": "Short text",
            "oversize_no_safe_boundary": False,
        }
        metadata = agent._evaluate_oversize_downgrade(section)
        # metadata should be None for non-oversize
        assert metadata is None
        assert agent.fallback_reports == []



