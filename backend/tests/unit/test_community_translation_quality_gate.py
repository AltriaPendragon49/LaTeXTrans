from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.services import paper_service
from backend.app.services.community_translation_quality import (
    evaluate_community_translation_quality,
)
from backend.scripts.audit_community_translation_quality import (
    _configure_stdout_utf8,
    scan_community_papers,
)


def _reason_codes(result) -> set[str]:
    return {str(reason["code"]) for reason in result.reasons}


def test_quality_gate_rejects_fixed_fake_fallback_phrase() -> None:
    result = evaluate_community_translation_quality(
        preview_html="<html><body><p>此处内容已做保守中文降级处理。</p></body></html>",
        task={"task_id": "task-fake"},
    )

    assert result.passed is False
    assert "fake_fallback_phrase" in _reason_codes(result)
    assert result.diagnostics()["passed"] is False


def test_quality_gate_rejects_current_fake_fallback_phrases() -> None:
    for phrase in ("相关内容已转为简要中文表述", "此处内容已做保守中文降级处理"):
        result = evaluate_community_translation_quality(
            preview_html=f"<html><body><p>{phrase}</p></body></html>",
            task={"task_id": "task-fake-current"},
        )

        assert result.passed is False
        assert "fake_fallback_phrase" in _reason_codes(result)


def test_quality_gate_rejects_multiple_source_fallback_sections() -> None:
    result = evaluate_community_translation_quality(
        sections=[
            {
                "section": "2",
                "translation_status": "fallback_source_api_failure",
                "trans_content": "This source paragraph was retained after provider failure.",
            },
            {
                "section": "3",
                "translation_status": "payload_invariant_passthrough",
                "trans_content": "This second source paragraph was also retained.",
            },
        ],
        output_text="这是译文主体。This source paragraph was retained after provider failure.",
    )

    assert result.passed is False
    assert "excessive_source_fallback" in _reason_codes(result)


def test_quality_gate_tolerates_short_isolated_fallback_and_technical_english() -> None:
    result = evaluate_community_translation_quality(
        preview_html="""
        <article>
          <p>本文介绍一种训练方法，并报告主要实验结果。</p>
          <p>公式 $E=mc^2$、引用 [12]、URL https://example.org、BERT、NASA 和 ResNet-50 均可保留。</p>
          <pre>for token in tokens: print(token)</pre>
          <section><h2>References</h2><p>Smith, Alice. Foundation Models. 2024.</p></section>
        </article>
        """,
        sections=[
            {
                "section": "appendix-a",
                "translation_status": "fallback_source_api_failure",
                "trans_content": "Implementation note.",
            }
        ],
    )

    assert result.passed is True
    assert _reason_codes(result) == set()


def test_quality_gate_rejects_large_english_prose_retention() -> None:
    result = evaluate_community_translation_quality(
        preview_html="""
        <article>
          <p>这是译文开头。</p>
          <p>This final output still contains a long English paragraph that should
          be treated as source language retention because it is ordinary prose,
          not a citation, code block, URL, formula, acronym, or proper noun list.</p>
        </article>
        """
    )

    assert result.passed is False
    assert "high_source_language_retention" in _reason_codes(result)


def test_sync_task_assets_blocks_canonical_publish_when_quality_gate_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    diagnostics_path = tmp_path / "community_publish_quality_gate.json"
    updated_payloads: list[dict] = []

    monkeypatch.setattr(
        paper_service.task_manager,
        "get_task",
        lambda _task_id: {
            "task_id": "task-quota",
            "status": "completed",
            "output_path": str(tmp_path),
            "failure_reason_code": "provider_quota_exhausted",
        },
    )
    monkeypatch.setattr(
        paper_service,
        "_resolve_translated_pdf_asset",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("canonical PDF sync must be gated")),
    )
    monkeypatch.setattr(
        paper_service,
        "_resolve_preview_html_asset",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("canonical preview sync must be gated")),
    )

    async def _update_paper(paper_id: str, payload: dict):
        updated_payloads.append(payload)
        return {"id": paper_id, **payload}

    monkeypatch.setattr(paper_service, "_update_paper", _update_paper)

    result = asyncio.run(
        paper_service._sync_task_assets_for_paper(
            paper_id="paper-1",
            task_id="task-quota",
            promote_to_official=True,
            paper={"id": "paper-1"},
        )
    )

    assert result["status"] == "quality_gate_failed"
    assert result["quality_gate"]["passed"] is False
    assert "fatal_provider_failure" in {reason["code"] for reason in result["quality_gate"]["reasons"]}
    assert diagnostics_path.exists()
    assert json.loads(diagnostics_path.read_text(encoding="utf-8"))["passed"] is False
    assert updated_payloads[-1]["trans_status"] == "failed"
    assert "community_status" not in updated_payloads[-1]


def test_scan_community_papers_flags_known_bad_patterns(tmp_path: Path) -> None:
    root = tmp_path / "community_papers"
    for arxiv_id, body in {
        "1712.01815": "此处内容已做保守中文降级处理。",
        "2111.14330": (
            "This final output still contains a long English paragraph that should be "
            "reported because it survived publication as ordinary untranslated prose."
        ),
        "2112.10752": json.dumps(
            [
                {"section": "1", "translation_status": "fallback_source_api_failure"},
                {"section": "2", "translation_status": "fallback_source_api_failure"},
            ],
            ensure_ascii=False,
        ),
    }.items():
        paper_dir = root / arxiv_id
        paper_dir.mkdir(parents=True)
        if arxiv_id == "2112.10752":
            (paper_dir / "sections_map.json").write_text(body, encoding="utf-8")
        else:
            (paper_dir / "preview.html").write_text(body, encoding="utf-8")

    report = scan_community_papers(root)

    flagged = {item["arxiv_id"]: item for item in report["items"] if not item["passed"]}
    assert {"1712.01815", "2111.14330", "2112.10752"}.issubset(flagged)
    assert "fake_fallback_phrase" in {reason["code"] for reason in flagged["1712.01815"]["reasons"]}


def test_audit_cli_configures_stdout_utf8_for_unicode_reports() -> None:
    calls: list[dict] = []

    class _Stdout:
        def reconfigure(self, **kwargs):
            calls.append(kwargs)

    _configure_stdout_utf8(_Stdout())

    assert calls == [{"encoding": "utf-8"}]
