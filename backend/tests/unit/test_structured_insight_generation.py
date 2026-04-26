import asyncio
import json

import pytest
from fastapi import HTTPException

from backend.app.services import paper_service


def _readable_content(section_key: str) -> str:
    return (
        f"{section_key} 模块围绕论文正文生成了一段足够具体、可读、面向读者的中文导读内容，"
        "它不仅说明论文特有的信息，还能满足新的发布可读性门槛，并避免空泛套话与失败占位语。"
    )


def _valid_sections() -> list[dict[str, str]]:
    return [
        {
            "section_key": section_key,
            "content": _readable_content(section_key),
            "status": "ready",
            "updated_at": "2026-04-11T00:00:00Z",
        }
        for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS
    ]


class _AiohttpResponse:
    def __init__(self, *, status: int, payload: dict[str, object]):
        self.status = status
        self._payload = payload
        self.headers: dict[str, str] = {}

    async def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class _AiohttpPostContext:
    def __init__(self, response: _AiohttpResponse):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DirectAiohttpSession:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, *, json: dict[str, object], headers: dict[str, str], timeout: object):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return _AiohttpPostContext(
            _AiohttpResponse(
                status=200,
                payload={"choices": [{"message": {"content": "structured insight output"}}]},
            )
        )


class _BoomAiohttpSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        raise AssertionError("structured insight system-pool path should not call session.post directly")


def test_prepare_structured_insight_sources_routes_relevant_sections_and_falls_back_by_order(monkeypatch, tmp_path):
    output_dir = tmp_path / "task-1" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sections_map.json").write_text(
        json.dumps(
            [
                {
                    "section": "1",
                    "title": "Abstract",
                    "trans_content": "摘要说明了论文要解决的问题、研究动机以及为什么现有做法仍有明显不足。",
                },
                {
                    "section": "2",
                    "title": "Introduction",
                    "trans_content": "引言进一步解释了问题背景、现实重要性，并指出了当前方法在复杂场景中的局限。",
                },
                {
                    "section": "3",
                    "title": "Contributions",
                    "trans_content": "贡献段明确列出方法的新意、本质区别，以及它相对于已有方法的关键突破。",
                },
                {
                    "section": "4",
                    "title": "Method",
                    "trans_content": "方法部分完整说明了整体 pipeline、关键步骤之间如何衔接以及系统如何运行。",
                },
                {
                    "section": "5",
                    "title": "Experiments",
                    "trans_content": "实验部分展示了数据、指标、设置和主要结果，并明确说明结论如何支持方法有效性。",
                },
                {
                    "section": "6",
                    "title": "Conclusion",
                    "trans_content": "结论讨论了局限、潜在扩展方向以及这项工作对后续研究的启发。",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        paper_service,
        "_candidate_output_directories_for_task",
        lambda _task_id: [output_dir],
    )

    sources = paper_service._prepare_structured_insight_sources("task-1")

    assert set(sources) == set(paper_service.STRUCTURED_INSIGHT_SECTION_KEYS)
    assert "问题背景" in sources["problem"] or "现有做法" in sources["problem"]
    assert "整体 pipeline" in sources["solution"]
    assert "关键突破" in sources["innovation"]
    assert "主要结果" in sources["experiment"]
    assert "潜在扩展方向" in sources["future"]
    for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS:
        assert "摘要" in sources[section_key]


def test_prepare_structured_insight_sources_prioritizes_intro_contributions_and_result_sections(monkeypatch, tmp_path):
    output_dir = tmp_path / "task-2" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sections_map.json").write_text(
        json.dumps(
            [
                {
                    "section": "1",
                    "title": "Abstract",
                    "trans_content": "摘要给出论文目标与整体结论。",
                },
                {
                    "section": "2",
                    "title": "Introduction",
                    "trans_content": "引言先解释研究问题。本文贡献如下：第一，提出新的协同框架；第二，显式保持结构约束；第三，增强复杂项目的术语一致性。",
                },
                {
                    "section": "3",
                    "title": "Method",
                    "trans_content": "方法部分介绍整体 pipeline 和关键步骤如何协同。",
                },
                {
                    "section": "4",
                    "title": "Experimental Setup",
                    "trans_content": "实验设置说明数据集、指标和基线模型。",
                },
                {
                    "section": "5",
                    "title": "Results",
                    "trans_content": "结果显示在结构保持指标上提升 3.2 分，在主要对比方法上整体领先，并显著减少编译失败。",
                },
                {
                    "section": "6",
                    "title": "Conclusion",
                    "trans_content": "结论讨论局限与未来方向。",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        paper_service,
        "_candidate_output_directories_for_task",
        lambda _task_id: [output_dir],
    )

    sources = paper_service._prepare_structured_insight_sources("task-2")

    assert "本文贡献如下" in sources["innovation"]
    assert "新的协同框架" in sources["innovation"]
    assert "提升 3.2 分" in sources["experiment"]
    assert "整体领先" in sources["experiment"]


def test_prepare_structured_insight_sources_falls_back_to_preview_asset_when_runtime_sections_are_missing(monkeypatch):
    preview_html = """
    <article class="paper-preview">
      <section>
        <h2>摘要</h2>
        <p>本文聚焦结构化 LaTeX 翻译在复杂论文场景中的关键困难，并说明已有方法在结构保持方面仍有明显不足。</p>
      </section>
      <section>
        <h2>方法</h2>
        <p>我们提出多智能体协同流程，将解析、术语一致性和重建编排到统一 pipeline 中完成。</p>
      </section>
      <section>
        <h2>实验</h2>
        <p>实验结果显示该方法在结构保持与编译成功率上稳定优于对比基线。</p>
      </section>
      <section>
        <h2>结论</h2>
        <p>未来可以继续扩展到更多模板、更多公式密集型场景，并加强术语长期记忆。</p>
      </section>
    </article>
    """

    monkeypatch.setattr(
        paper_service,
        "_candidate_output_directories_for_task",
        lambda _task_id: [],
    )

    class _FakeBackend:
        def read_text(self, *, ref, encoding="utf-8"):
            assert ref.storage_backend == "object_storage"
            assert ref.object_key == "paperx/data/community_papers/paper-1/preview/preview.html"
            assert encoding == "utf-8"
            return preview_html

    monkeypatch.setattr(paper_service, "_get_storage_backend", lambda: _FakeBackend())

    sources = paper_service._prepare_structured_insight_sources(
        "task-1",
        preview_asset={
            "storage_backend": "object_storage",
            "file_path": "paperx/data/community_papers/paper-1/preview/preview.html",
            "mime_type": "text/html",
        },
    )

    assert "结构化 LaTeX 翻译" in sources["problem"]
    assert "多智能体协同流程" in sources["solution"]
    assert "统一 pipeline" in sources["innovation"]
    assert "稳定优于对比基线" in sources["experiment"]
    assert "扩展到更多模板" in sources["future"]


def test_load_structured_insight_runtime_sections_preserves_source_and_translation(monkeypatch, tmp_path):
    output_dir = tmp_path / "task-runtime" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sections_map.json").write_text(
        json.dumps(
            [
                {
                    "section": "1",
                    "title": "Introduction",
                    "content": "Original problem statement with motivation and limitations.",
                    "trans_content": "中文问题描述，说明研究动机与现有方法局限。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        paper_service,
        "_candidate_output_directories_for_task",
        lambda _task_id: [output_dir],
    )

    sections = paper_service._load_structured_insight_runtime_sections("task-runtime")

    assert len(sections) == 1
    assert "Original problem statement" in sections[0]["source_content"]
    assert "中文问题描述" in sections[0]["translated_content"]


def test_normalize_structured_insight_text_falls_back_when_tex_extraction_crashes(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "extract_text_from_tex",
        lambda _text: (_ for _ in ()).throw(IndexError("list index out of range")),
    )

    result = paper_service._normalize_structured_insight_text(
        "Future work discusses limitations and next steps."
    )

    assert result == "Future work discusses limitations and next steps."


def test_validate_structured_insight_sections_rejects_failure_placeholder_content():
    invalid_sections = _valid_sections()
    invalid_sections[0]["content"] = "暂时无法生成"

    with pytest.raises(ValueError, match="problem"):
        paper_service._validate_structured_insight_sections(invalid_sections)


def test_validate_structured_insight_sections_rejects_duplicate_module_content():
    invalid_sections = _valid_sections()
    invalid_sections[1]["content"] = invalid_sections[0]["content"]

    with pytest.raises(ValueError):
        paper_service._validate_structured_insight_sections(invalid_sections)


def test_generate_structured_insight_sections_calls_llm_once_per_module_and_retries_only_failed_module(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_prepare_structured_insight_sources",
        lambda _task_id: {
            section_key: f"标题：Paper\n摘要：这是一段足够长的摘要。\n{section_key} 来源内容足够长，并且都是可靠的中文论文摘录。"
            for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS
        },
    )

    async def _fake_llm_config(_user_id):
        return {
            "base_url": "https://example.invalid/v1/chat/completions",
            "api_key": "test-key",
            "model": "test-model",
            "timeout": 30,
        }

    monkeypatch.setattr(
        paper_service,
        "_build_structured_insight_llm_config",
        _fake_llm_config,
    )

    call_counts: dict[str, int] = {}

    async def _fake_call_structured_insight_llm(*, user_payload, **_kwargs):
        section_key = str(user_payload["section_key"])
        call_counts[section_key] = call_counts.get(section_key, 0) + 1
        if section_key == "future" and call_counts[section_key] == 1:
            return " "
        return _readable_content(section_key)

    monkeypatch.setattr(
        paper_service,
        "_call_structured_insight_llm",
        _fake_call_structured_insight_llm,
    )

    sections = asyncio.run(
        paper_service._generate_structured_insight_sections_from_task(
            task_id="task-1",
            title="Paper title",
            abstract_raw="Abstract",
            created_by="admin-1",
        )
    )

    assert len(sections) == len(paper_service.STRUCTURED_INSIGHT_SECTION_KEYS)
    assert call_counts["future"] == 2
    for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS:
        expected = 2 if section_key == "future" else 1
        assert call_counts[section_key] == expected
    assert next(section for section in sections if section["section_key"] == "future")["content"]


@pytest.mark.asyncio
async def test_structured_insight_llm_uses_pool_helper_for_system_managed_credentials(monkeypatch):
    llm_config = {
        "base_url": "https://relay-a.example/v1/chat/completions",
        "api_key": "k1",
        "model": "test-model",
        "timeout": 30,
        "pool_mode": "system_managed",
        "pool_members": [
            {"member_id": "a1", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k1"},
            {"member_id": "a2", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k2"},
        ],
    }
    called: dict[str, object] = {}

    async def _fake_pool_call(**kwargs):
        called["pool_mode"] = kwargs["llm_config"].get("pool_mode")
        called["payload"] = kwargs["payload"]
        return {"choices": [{"message": {"content": "pooled structured insight"}}]}

    monkeypatch.setattr(paper_service, "post_chat_completion_with_pool", _fake_pool_call, raising=False)
    monkeypatch.setattr(paper_service.aiohttp, "ClientSession", lambda *args, **kwargs: _BoomAiohttpSession())

    result = await paper_service._call_structured_insight_llm(
        llm_config=llm_config,
        system_prompt="Summarize",
        user_payload={"title": "Paper", "section_key": "problem"},
    )

    assert result == "pooled structured insight"
    assert called["pool_mode"] == "system_managed"
    assert isinstance(called["payload"], dict)
    assert called["payload"]["model"] == "test-model"


@pytest.mark.asyncio
async def test_structured_insight_llm_keeps_direct_route_for_custom_credentials(monkeypatch):
    llm_config = {
        "base_url": "https://custom.example/v1/chat/completions",
        "api_key": "user-key",
        "model": "test-model",
        "timeout": 30,
    }
    session = _DirectAiohttpSession()

    async def _unexpected_pool_call(**kwargs):
        raise AssertionError("custom structured insight credentials should not use the system token pool")

    monkeypatch.setattr(paper_service, "post_chat_completion_with_pool", _unexpected_pool_call, raising=False)
    monkeypatch.setattr(paper_service.aiohttp, "ClientSession", lambda *args, **kwargs: session)

    result = await paper_service._call_structured_insight_llm(
        llm_config=llm_config,
        system_prompt="Summarize",
        user_payload={"title": "Paper", "section_key": "problem"},
    )

    assert result == "structured insight output"
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == "https://custom.example/v1/chat/completions"
    assert session.calls[0]["headers"]["Authorization"] == "Bearer user-key"


def test_generate_structured_insight_sections_uses_fallback_content_after_retries(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_prepare_structured_insight_sources",
        lambda _task_id: {
            section_key: f"标题：Paper\n摘要：这是一段足够长的摘要。\n{section_key} 来源内容足够长，并且都是可靠的中文论文摘录。"
            for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS
        },
    )

    async def _fake_llm_config(_user_id):
        return {
            "base_url": "https://example.invalid/v1/chat/completions",
            "api_key": "test-key",
            "model": "test-model",
            "timeout": 30,
        }

    monkeypatch.setattr(
        paper_service,
        "_build_structured_insight_llm_config",
        _fake_llm_config,
    )

    async def _fake_call_structured_insight_llm(*, user_payload, **_kwargs):
        if str(user_payload["section_key"]) == "future":
            raise RuntimeError("provider failed")
        return _readable_content(str(user_payload["section_key"]))

    monkeypatch.setattr(
        paper_service,
        "_call_structured_insight_llm",
        _fake_call_structured_insight_llm,
    )

    sections = asyncio.run(
        paper_service._generate_structured_insight_sections_from_task(
            task_id="task-1",
            title="Paper title",
            abstract_raw="Abstract",
            created_by="admin-1",
        )
    )

    future = next(section for section in sections if section["section_key"] == "future")
    assert "根据论文的中文内容" in future["content"]
    assert "future 来源内容足够长" in future["content"]


def test_generate_structured_insight_sections_sends_paper_specific_boundary_constraints_to_llm(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_prepare_structured_insight_sources",
        lambda _task_id: {
            section_key: f"标题：Paper\n摘要：这是一段足够长的摘要。\n{section_key} 来源内容足够长，并且都是可靠的中文论文摘录。"
            for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS
        },
    )

    async def _fake_llm_config(_user_id):
        return {
            "base_url": "https://example.invalid/v1/chat/completions",
            "api_key": "test-key",
            "model": "test-model",
            "timeout": 30,
        }

    monkeypatch.setattr(
        paper_service,
        "_build_structured_insight_llm_config",
        _fake_llm_config,
    )

    captured_payloads: dict[str, dict[str, str | list[str] | None]] = {}

    async def _fake_call_structured_insight_llm(*, user_payload, **_kwargs):
        captured_payloads[str(user_payload["section_key"])] = user_payload
        return _readable_content(str(user_payload["section_key"]))

    monkeypatch.setattr(
        paper_service,
        "_call_structured_insight_llm",
        _fake_call_structured_insight_llm,
    )

    asyncio.run(
        paper_service._generate_structured_insight_sections_from_task(
            task_id="task-1",
            title="Paper title",
            abstract_raw="Abstract",
            created_by="admin-1",
        )
    )

    problem_payload = captured_payloads["problem"]
    assert "只基于提供的论文内容回答" in str(problem_payload["grounding_requirements"])
    assert "优先使用论文中明确写出的" in str(problem_payload["grounding_requirements"])
    assert "避免用行业常识补全" in str(problem_payload["grounding_requirements"])
    assert "不要详细展开作者方法" in str(problem_payload["avoid"])

    solution_payload = captured_payloads["solution"]
    assert "方法如何工作" in str(solution_payload["section_focus"])
    assert "不要写 CLI、Web、平台" in str(solution_payload["avoid"])
    assert "不要把输出 PDF、源码" in str(solution_payload["avoid"])

    innovation_payload = captured_payloads["innovation"]
    assert "不要使用'首个'、'首次'、'无损'、'质的不同'" in str(innovation_payload["avoid"])
    assert "用可核验的差异解释创新" in str(innovation_payload["must_cover"])

    experiment_payload = captured_payloads["experiment"]
    assert "实验最后证明了什么" in str(experiment_payload["must_cover"])
    assert "优于哪些方法" in str(experiment_payload["must_cover"])

    future_payload = captured_payloads["future"]
    assert "优先依据论文明确提到的局限" in str(future_payload["must_cover"])
    assert "不要扩展出论文未出现的研究建议" in str(future_payload["avoid"])

    for index, section_key in enumerate(paper_service.STRUCTURED_INSIGHT_SECTION_KEYS):
        payload = captured_payloads[section_key]
        assert "避免与其他模块重复" in str(payload["anti_repetition_requirements"])
        previous = payload["previous_module_briefs"]
        assert isinstance(previous, list)
        assert len(previous) == index


def test_generate_structured_insight_sections_adds_numeric_experiment_priority_and_strict_module_bans(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_prepare_structured_insight_sources",
        lambda _task_id: {
            section_key: f"标题：Paper\n摘要：这是一段足够长的摘要。\n{section_key} 来源内容足够长，并且都是可靠的中文论文摘录。"
            for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS
        },
    )

    async def _fake_llm_config(_user_id):
        return {
            "base_url": "https://example.invalid/v1/chat/completions",
            "api_key": "test-key",
            "model": "test-model",
            "timeout": 30,
        }

    monkeypatch.setattr(
        paper_service,
        "_build_structured_insight_llm_config",
        _fake_llm_config,
    )

    captured_payloads: dict[str, dict[str, str | list[str] | None]] = {}

    async def _fake_call_structured_insight_llm(*, user_payload, **_kwargs):
        captured_payloads[str(user_payload["section_key"])] = user_payload
        return _readable_content(str(user_payload["section_key"]))

    monkeypatch.setattr(
        paper_service,
        "_call_structured_insight_llm",
        _fake_call_structured_insight_llm,
    )

    asyncio.run(
        paper_service._generate_structured_insight_sections_from_task(
            task_id="task-3",
            title="Paper title",
            abstract_raw="Abstract",
            created_by="admin-1",
        )
    )

    assert "如果论文中有实验数值、对比结果、提升幅度，请优先写出" in str(
        captured_payloads["experiment"]["must_cover"]
    )
    assert "不要描述系统的使用方式（如CLI、Web平台）" in str(
        captured_payloads["solution"]["avoid"]
    )
    assert "不要写产品功能" in str(captured_payloads["solution"]["avoid"])
    assert "避免使用“首次”“首个”“质的突破”等强判断" in str(
        captured_payloads["innovation"]["avoid"]
    )


def test_generate_structured_insight_sections_keeps_paragraph_first_style_but_allows_dense_experiment_points(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_prepare_structured_insight_sources",
        lambda _task_id: {
            section_key: f"标题：Paper\n摘要：这是一段足够长的摘要。\n{section_key} 来源内容足够长，并且都是可靠的中文论文摘录。"
            for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS
        },
    )

    async def _fake_llm_config(_user_id):
        return {
            "base_url": "https://example.invalid/v1/chat/completions",
            "api_key": "test-key",
            "model": "test-model",
            "timeout": 30,
        }

    monkeypatch.setattr(
        paper_service,
        "_build_structured_insight_llm_config",
        _fake_llm_config,
    )

    captured_payloads: dict[str, dict[str, str | list[str] | None]] = {}

    async def _fake_call_structured_insight_llm(*, system_prompt, user_payload, **_kwargs):
        captured_payloads[str(user_payload["section_key"])] = {
            **user_payload,
            "_system_prompt": system_prompt,
        }
        return _readable_content(str(user_payload["section_key"]))

    monkeypatch.setattr(
        paper_service,
        "_call_structured_insight_llm",
        _fake_call_structured_insight_llm,
    )

    asyncio.run(
        paper_service._generate_structured_insight_sections_from_task(
            task_id="task-4",
            title="Paper title",
            abstract_raw="Abstract",
            created_by="admin-1",
        )
    )

    experiment_payload = captured_payloads["experiment"]
    assert "以段落为主" in str(experiment_payload["density_requirements"])
    assert "至多 2~3 条" in str(experiment_payload["density_requirements"])
    assert "指标、数值、对比结果" in str(experiment_payload["density_requirements"])

    problem_payload = captured_payloads["problem"]
    assert "保持段落式输出" in str(problem_payload["density_requirements"])
    assert "不要改成 bullet 列表" in str(problem_payload["density_requirements"])

    assert "Keep paragraph-first output" in str(experiment_payload["_system_prompt"])
    assert "at most 2-3 short bullet-like lines" in str(experiment_payload["_system_prompt"])


def test_generate_structured_insight_sections_requests_summary_plus_titled_subsections(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_prepare_structured_insight_sources",
        lambda _task_id: {
            section_key: f"标题：Paper\n摘要：这是一段足够长的摘要。\n{section_key} 来源内容足够长，并且都是可靠的中文论文摘录。"
            for section_key in paper_service.STRUCTURED_INSIGHT_SECTION_KEYS
        },
    )

    async def _fake_llm_config(_user_id):
        return {
            "base_url": "https://example.invalid/v1/chat/completions",
            "api_key": "test-key",
            "model": "test-model",
            "timeout": 30,
        }

    monkeypatch.setattr(
        paper_service,
        "_build_structured_insight_llm_config",
        _fake_llm_config,
    )

    captured_payloads: dict[str, dict[str, str | list[str] | None]] = {}

    async def _fake_call_structured_insight_llm(*, system_prompt, user_payload, **_kwargs):
        captured_payloads[str(user_payload["section_key"])] = {
            **user_payload,
            "_system_prompt": system_prompt,
        }
        return _readable_content(str(user_payload["section_key"]))

    monkeypatch.setattr(
        paper_service,
        "_call_structured_insight_llm",
        _fake_call_structured_insight_llm,
    )

    asyncio.run(
        paper_service._generate_structured_insight_sections_from_task(
            task_id="task-5",
            title="Paper title",
            abstract_raw="Abstract",
            created_by="admin-1",
        )
    )

    problem_payload = captured_payloads["problem"]
    assert "一行总结句" in str(problem_payload["structure_requirements"])
    assert "2~4个子结构段" in str(problem_payload["structure_requirements"])
    assert "每个子结构需有简短标题" in str(problem_payload["structure_requirements"])
    assert "不要输出单一长段落" in str(problem_payload["structure_requirements"])

    experiment_payload = captured_payloads["experiment"]
    assert "核心指标" in str(experiment_payload["suggested_subheadings"])
    assert "对比结果" in str(experiment_payload["suggested_subheadings"])
    assert "实验结论" in str(experiment_payload["suggested_subheadings"])

    assert "summary sentence followed by 2-4 titled mini-sections" in str(experiment_payload["_system_prompt"])


def test_publish_admin_curation_job_blocks_publication_when_any_module_content_is_invalid(monkeypatch):
    paper = {
        "id": "paper-1",
        "title": "Recovered arXiv title",
        "arxiv_id": "2501.00001",
        "authors": ["Alice"],
        "categories": ["cs.CL"],
        "abstract_raw": "raw abstract",
        "abstract_translated": "中文摘要已经存在，而且长度足够支撑新的五模块导读系统。",
        "community_status": "official",
        "trans_status": "processing",
        "visibility": "private",
        "status": "curating",
    }
    update_calls = {"count": 0}

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_sync_task_assets_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={"paper": paper}),
    )
    monkeypatch.setattr(
        paper_service,
        "_extract_translated_abstract_from_task",
        lambda _task_id: "中文摘要已经存在，而且长度足够支撑新的五模块导读系统。",
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_structured_insight_sections_from_task",
        lambda **_kwargs: asyncio.sleep(
            0,
            result=[
                *(_valid_sections()[:-1]),
                {
                    "section_key": "future",
                    "content": " ",
                    "status": "ready",
                    "updated_at": "2026-04-11T00:00:00Z",
                },
            ],
        ),
        raising=False,
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda *_args, **_kwargs: update_calls.__setitem__("count", update_calls["count"] + 1),
    )

    with pytest.raises(ValueError, match="future"):
        asyncio.run(
            paper_service._publish_admin_curation_job(
                job={"paper_id": "paper-1", "created_by": "admin-1", "source_type": "arxiv"},
                metadata={
                    "title": "Recovered arXiv title",
                    "arxiv_id": "2501.00001",
                    "authors": ["Alice"],
                    "categories": ["cs.CL"],
                    "abstract_raw": "raw abstract",
                },
                translated_task_id="task-1",
            )
        )

    assert update_calls["count"] == 0


def test_publish_admin_curation_job_preserves_job_arxiv_id_when_metadata_omits_it(monkeypatch):
    inserted: dict[str, str | None] = {}
    updated_payload: dict[str, str | None] = {}

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=None),
    )

    async def _fake_insert_paper(payload):
        inserted.update(payload)
        return {
            "id": "paper-1",
            "title": payload["title"],
            "arxiv_id": payload.get("arxiv_id"),
            "authors": payload.get("authors") or [],
            "categories": payload.get("categories") or [],
            "abstract_raw": payload.get("abstract_raw"),
            "abstract_translated": None,
            "community_status": payload.get("community_status"),
            "trans_status": payload.get("trans_status"),
            "visibility": payload.get("visibility"),
            "status": payload.get("status"),
        }

    async def _fake_update_paper(_paper_id, payload):
        updated_payload.update(payload)
        return {
            "id": "paper-1",
            "title": payload["title"],
            "arxiv_id": payload.get("arxiv_id"),
            "authors": payload.get("authors") or [],
            "categories": payload.get("categories") or [],
            "abstract_raw": payload.get("abstract_raw"),
            "abstract_translated": payload.get("abstract_translated"),
            "community_status": payload.get("community_status"),
            "trans_status": payload.get("trans_status"),
            "visibility": payload.get("visibility"),
            "status": payload.get("status"),
        }

    monkeypatch.setattr(paper_service, "_insert_paper", _fake_insert_paper)
    monkeypatch.setattr(paper_service, "_sync_task_assets_for_paper", lambda **_kwargs: asyncio.sleep(0, result={}))
    monkeypatch.setattr(
        paper_service,
        "_extract_translated_abstract_from_task",
        lambda _task_id: "中文摘要已经生成，而且长度足够支撑新的五模块导读系统。",
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_structured_insight_sections_from_task",
        lambda **_kwargs: asyncio.sleep(0, result=_valid_sections()),
    )
    monkeypatch.setattr(
        paper_service,
        "_upsert_structured_insight_sections",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_similar_recommendations_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(
        paper_service,
        "_replace_persisted_similar_recommendations",
        lambda **_kwargs: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(paper_service, "_update_paper", _fake_update_paper)

    result = asyncio.run(
        paper_service._publish_admin_curation_job(
            job={
                "paper_id": "paper-1",
                "created_by": "admin-1",
                "source_type": "arxiv",
                "arxiv_id": "2508.18791",
            },
            metadata={
                "title": "Recovered arXiv title",
                "authors": ["Alice"],
                "categories": ["cs.CL"],
                "abstract_raw": "raw abstract",
            },
            translated_task_id="task-1",
        )
    )

    assert inserted["arxiv_id"] == "2508.18791"
    assert updated_payload["arxiv_id"] == "2508.18791"
    assert result["arxiv_id"] == "2508.18791"


def test_publish_admin_curation_job_uses_fallback_arxiv_metadata_when_fetch_fails(monkeypatch):
    paper = {
        "id": "paper-1",
        "title": "arXiv:2501.00001",
        "arxiv_id": "2501.00001",
        "authors": [],
        "categories": [],
        "abstract_raw": None,
        "abstract_translated": None,
        "community_status": "official",
        "trans_status": "processing",
        "visibility": "private",
        "status": "curating",
    }
    update_calls: list[dict] = []

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_metadata",
        lambda _arxiv_id: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_sync_task_assets_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={"paper": paper}),
    )
    monkeypatch.setattr(
        paper_service,
        "_extract_translated_abstract_from_task",
        lambda _task_id: "translated abstract",
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_structured_insight_sections_from_task",
        lambda **_kwargs: asyncio.sleep(0, result=_valid_sections()),
    )
    monkeypatch.setattr(
        paper_service,
        "_upsert_structured_insight_sections",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_similar_recommendations_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(
        paper_service,
        "_replace_persisted_similar_recommendations",
        lambda **_kwargs: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda _paper_id, payload: asyncio.sleep(
            0,
            result={**paper, **payload},
        )
        if not update_calls.append(dict(payload))
        else asyncio.sleep(0, result={**paper, **payload}),
    )

    result = asyncio.run(
        paper_service._publish_admin_curation_job(
            job={
                "paper_id": "paper-1",
                "created_by": "admin-1",
                "source_type": "arxiv",
                "arxiv_id": "2501.00001",
            },
            metadata={
                "title": "Curated paper",
                "authors": [],
                "categories": [],
                "abstract_raw": None,
            },
            translated_task_id="task-1",
        )
    )

    assert result["status"] == "published"
    assert result["title"] == "arXiv:2501.00001"
    assert result["authors"] == []
    assert update_calls[-1]["status"] == "published"


def test_publish_admin_curation_job_persists_similar_recommendations_before_publication(monkeypatch):
    persisted_payload: dict[str, object] = {}
    update_calls: list[dict[str, object]] = []
    paper = {
        "id": "paper-1",
        "title": "Recovered arXiv title",
        "arxiv_id": "2501.00001",
        "authors": ["Alice"],
        "categories": ["cs.CL"],
        "abstract_raw": "raw abstract",
        "abstract_translated": None,
        "community_status": "official",
        "trans_status": "processing",
        "visibility": "private",
        "status": "curating",
    }

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_sync_task_assets_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={"paper": paper}),
    )
    monkeypatch.setattr(
        paper_service,
        "_extract_translated_abstract_from_task",
        lambda _task_id: "translated abstract",
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_structured_insight_sections_from_task",
        lambda **_kwargs: asyncio.sleep(0, result=_valid_sections()),
    )
    monkeypatch.setattr(
        paper_service,
        "_upsert_structured_insight_sections",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_similar_recommendations_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result=[
                {
                    "arxiv_id": "2504.12345",
                    "title": "Neighbor Paper",
                    "abstract": "Neighbor abstract",
                    "arxiv_url": "https://arxiv.org/abs/2504.12345",
                    "community_paper_id": "paper-neighbor",
                    "link_type": "community",
                }
            ],
        ),
    )

    async def _fake_replace_persisted(*, paper_id, items):
        persisted_payload["paper_id"] = paper_id
        persisted_payload["items"] = items

    monkeypatch.setattr(
        paper_service,
        "_replace_persisted_similar_recommendations",
        _fake_replace_persisted,
    )

    async def _fake_update_paper(_paper_id, payload):
        update_calls.append(dict(payload))
        return {**paper, **payload}

    monkeypatch.setattr(paper_service, "_update_paper", _fake_update_paper)

    asyncio.run(
        paper_service._publish_admin_curation_job(
            job={"paper_id": "paper-1", "created_by": "admin-1", "source_type": "arxiv"},
            metadata={
                "title": "Recovered arXiv title",
                "arxiv_id": "2501.00001",
                "authors": ["Alice"],
                "categories": ["cs.CL"],
                "abstract_raw": "raw abstract",
            },
            translated_task_id="task-1",
        )
    )

    assert persisted_payload == {
        "paper_id": "paper-1",
        "items": [
            {
                "arxiv_id": "2504.12345",
                "title": "Neighbor Paper",
                "abstract": "Neighbor abstract",
                "arxiv_url": "https://arxiv.org/abs/2504.12345",
                "community_paper_id": "paper-neighbor",
                "link_type": "community",
            }
        ],
    }
    assert update_calls
    assert update_calls[-1]["visibility"] == "public"
    assert update_calls[-1]["status"] == "published"


def test_publish_admin_curation_job_retries_asset_sync_after_recreating_missing_placeholder(monkeypatch):
    insert_calls: list[dict[str, object]] = []
    sync_calls = {"count": 0}
    update_calls: list[dict[str, object]] = []

    async def _fetch_paper(_paper_id):
        return None

    async def _insert_paper(payload):
        insert_calls.append(dict(payload))
        return {
            "id": "paper-1",
            "title": payload["title"],
            "arxiv_id": payload.get("arxiv_id"),
            "authors": payload.get("authors") or [],
            "categories": payload.get("categories") or [],
            "abstract_raw": payload.get("abstract_raw"),
            "abstract_translated": None,
            "community_status": payload.get("community_status"),
            "trans_status": payload.get("trans_status"),
            "visibility": payload.get("visibility"),
            "status": payload.get("status"),
        }

    async def _sync_task_assets(**_kwargs):
        sync_calls["count"] += 1
        if sync_calls["count"] == 1:
            raise HTTPException(status_code=404, detail="Paper not found")
        return {
            "paper": {
                "id": "paper-1",
                "title": "Recovered arXiv title",
                "arxiv_id": "2501.00001",
                "authors": ["Alice"],
                "categories": ["cs.CL"],
                "abstract_raw": "raw abstract",
                "abstract_translated": None,
                "community_status": "official",
                "trans_status": "completed",
                "visibility": "private",
                "status": "curating",
            }
        }

    async def _update_paper(_paper_id, payload):
        update_calls.append(dict(payload))
        return {
            "id": "paper-1",
            "title": payload["title"],
            "arxiv_id": payload.get("arxiv_id"),
            "authors": payload.get("authors") or [],
            "categories": payload.get("categories") or [],
            "abstract_raw": payload.get("abstract_raw"),
            "abstract_translated": payload.get("abstract_translated"),
            "community_status": payload.get("community_status"),
            "trans_status": payload.get("trans_status"),
            "visibility": payload.get("visibility"),
            "status": payload.get("status"),
        }

    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", _fetch_paper)
    monkeypatch.setattr(paper_service, "_insert_paper", _insert_paper)
    monkeypatch.setattr(paper_service, "_sync_task_assets_for_paper", _sync_task_assets)
    monkeypatch.setattr(
        paper_service,
        "_extract_translated_abstract_from_task",
        lambda _task_id: "translated abstract",
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_structured_insight_sections_from_task",
        lambda **_kwargs: asyncio.sleep(0, result=_valid_sections()),
    )
    monkeypatch.setattr(
        paper_service,
        "_upsert_structured_insight_sections",
        lambda **_kwargs: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        paper_service,
        "_generate_similar_recommendations_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(
        paper_service,
        "_replace_persisted_similar_recommendations",
        lambda **_kwargs: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(paper_service, "_update_paper", _update_paper)

    result = asyncio.run(
        paper_service._publish_admin_curation_job(
            job={
                "paper_id": "paper-1",
                "created_by": "admin-1",
                "source_type": "arxiv",
                "arxiv_id": "2501.00001",
            },
            metadata={
                "title": "Recovered arXiv title",
                "authors": ["Alice"],
                "categories": ["cs.CL"],
                "abstract_raw": "raw abstract",
            },
            translated_task_id="task-1",
        )
    )

    assert sync_calls["count"] == 2
    assert len(insert_calls) == 2
    assert insert_calls[0]["id"] == "paper-1"
    assert update_calls[-1]["visibility"] == "public"
    assert result["status"] == "published"


def test_build_module_fallback_content_uses_excerpt_and_remains_readable():
    content = paper_service._build_structured_insight_fallback_content(
        section_key="future",
        excerpt="结论部分讨论了局限、启发和未来方向，并指出下一步最值得继续验证的研究路径。",
    )

    assert "根据论文的中文内容" in content
    assert "未来" in content or "后续" in content
