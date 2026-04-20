import asyncio
import json

from backend.app.services.agents import langgraph_orchestrator as orch
from backend.app.services.agents.pipeline_schema import FallbackReport


def test_route_after_validate_uses_ultimate_downgrade_after_repair_budget_exhausted():
    state = {
        "fallback_reports": [{"chunk_scope": "sec-1"}],
        "repair_retry_count": orch.MAX_REPAIR_RETRIES,
    }

    assert orch._route_after_validate(state) == "ultimate_downgrade"


def test_build_pipeline_graph_registers_ultimate_downgrade_node():
    graph = orch.build_pipeline_graph(enable_diagnostics=False)
    compiled = graph.get_graph()

    assert "ultimate_downgrade" in compiled.nodes


def test_node_ultimate_downgrade_rewrites_pending_compile_sections_before_generate(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    sections = [
        {
            "section": "3_chunk_1",
            "content": r"\section{Results}" + "\n\n" + "Original English body with <PLACEHOLDER_CAP_1>.",
            "trans_content": r"\section{Jie Guo}" + "\n\n" + "Current unsafe target text with <PLACEHOLDER_CAP_1>.",
            "translation_status": "structural_fallback_pending_compile",
        }
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "content": r"\begin{itemize}\item Original bullet\end{itemize}",
            "trans_content": r"\begin{itemize}\item Unsafe target bullet\end{itemize}",
            "translation_status": "structural_fallback_pending_compile",
        }
    ]
    (out_dir / "sections_map.json").write_text(
        json.dumps(sections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "envs_map.json").write_text(
        json.dumps(envs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    state = {
        "transed_project_dir": str(out_dir),
        "task_id": "task-ultimate",
        "base_name": "task-ultimate",
        "fallback_reports": [
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="3_chunk_1",
                root_cause="c2",
            ),
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="<PLACEHOLDER_ENV_1>",
                root_cause="c2",
            ),
        ],
        "on_progress": None,
    }

    new_state = asyncio.run(orch.node_ultimate_downgrade(state))

    updated_sections = json.loads((out_dir / "sections_map.json").read_text(encoding="utf-8"))
    updated_envs = json.loads((out_dir / "envs_map.json").read_text(encoding="utf-8"))

    assert updated_sections[0]["translation_status"] == "ultimate_downgrade_applied"
    assert updated_envs[0]["translation_status"] == "ultimate_downgrade_applied"
    assert "<PLACEHOLDER_CAP_1>" in updated_sections[0]["trans_content"]
    assert "Original English body" not in updated_sections[0]["trans_content"]
    assert r"\begin{itemize}" not in updated_envs[0]["trans_content"]
    assert r"\end{itemize}" not in updated_envs[0]["trans_content"]
    assert new_state["fallback_reports"] == []
