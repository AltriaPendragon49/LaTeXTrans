import asyncio
import json
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")


def test_validate_prefers_structured_fallback_before_residual_english_failure(
    monkeypatch,
    tmp_path,
):
    from backend.app.services.agents import langgraph_orchestrator as orch

    class _CompletenessValidator:
        def __init__(self, *args, **kwargs):
            self.code_like_filtered_bare_tokens = 0

        def execute(self, *args, **kwargs):
            return [
                {
                    "part": "sec",
                    "num_or_ph": "1",
                    "error_type": "C1",
                    "completeness_error": (
                        "long_english_prose_span: remaining English prose detected. "
                        "Translate the residual English prose."
                    ),
                }
            ]

    class _TranslatorWithCompileFallback:
        structural_fallback_count = 1
        structural_fallback_ratio = 0.1
        structural_fallback_cap = 0.38
        structural_fallback_cap_mode = "soft"
        structural_fallback_parts = ["1"]
        noop_sections = []
        payload_invariant_sections = []
        c1_retry_enforced_once = False
        structural_fallback_warning = None

        def __init__(self):
            self.calls = 0
            self.trans_mode = 0
            self.errors_report = []

        async def execute(self, *args, **kwargs):
            self.calls += 1
            return None

    monkeypatch.setattr(orch, "ValidatorAgent", _CompletenessValidator)

    transed_project_dir = tmp_path / "zh_proj"
    transed_project_dir.mkdir(parents=True, exist_ok=True)
    (transed_project_dir / "sections_map.json").write_text(
        json.dumps(
            [
                {
                    "section": "1",
                    "content": r"\section{Participants}" + "\n\n" + "Original English body.",
                    "trans_content": r"\section{Participants}" + "\n\n" + "Original English body.",
                    "translation_status": "structural_fallback_pending_compile",
                    "fallback_reason": "compile_first_structural_fallback:C1_structural_validation_failed",
                    "translation_retry_count": 1,
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (transed_project_dir / "envs_map.json").write_text("[]", encoding="utf-8")

    translator = _TranslatorWithCompileFallback()
    state = {
        "config": {
            "target_language": "zh",
            "enable_post_compile_target_language_fallback": True,
        },
        "project_dir": str(tmp_path / "proj"),
        "transed_project_dir": str(transed_project_dir),
        "mode": 0,
        "translator_agent": translator,
        "base_name": "proj",
        "task_id": "task-1",
        "on_progress": None,
        "post_compile_fallback_attempted": False,
    }

    result = asyncio.run(orch.node_validate_and_retry(state))

    assert translator.calls == 2
    assert result["residual_english_requires_fallback"] is True
    assert len(result["compile_fallback_reports"]) == 1

    logs = json.loads((transed_project_dir / "task_log.json").read_text(encoding="utf-8"))
    assert any(entry["event"] == "validation_blocked_residual_english_prose" for entry in logs)


def test_route_after_validate_prefers_post_compile_target_language_fallback_for_residual_english():
    from backend.app.services.agents import langgraph_orchestrator as orch
    from backend.app.services.agents.pipeline_schema import FallbackReport

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "residual_english_requires_fallback": True,
        "compile_fallback_reports": [
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="1",
                root_cause="c2",
            )
        ],
        "post_compile_fallback_attempted": False,
        "fallback_reports": [],
        "repair_retry_count": 0,
    }

    assert orch._route_after_validate(state) == "post_compile_target_language_fallback"
