import asyncio

from backend.app.services import paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Insight-ready paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "This paper studies a translation pipeline.",
        "abstract_translated": "本文研究一个翻译流水线，并为新的论文导读系统提供基础语义锚点。",
        "community_status": "official",
        "trans_status": "completed",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T02:00:00+00:00",
        "community_selected_task_id": "task-1",
        "community_selected_asset_id": "asset-preview",
        "visibility": "public",
        "status": "published",
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
    }
    base.update(overrides)
    return base


def test_detail_returns_not_ready_structured_insight_payload_for_legacy_visible_paper(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper()),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0,
            result={"paper-1": {"liked": False, "favorited": False}},
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_sanitized_arxiv_html",
        lambda _arxiv_id: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_structured_insight_sections",
        lambda paper_id: asyncio.sleep(0, result=[]),
        raising=False,
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1", fast_path=True))

    assert result["structured_insights"]["state"] == "not_ready"
    assert [section["section_key"] for section in result["structured_insights"]["sections"]] == [
        "problem",
        "solution",
        "innovation",
        "experiment",
        "future",
    ]
    assert all("content" in section for section in result["structured_insights"]["sections"])


def test_structured_insights_payload_normalizes_markdown_style_subsections():
    content = (
        "\u8fd9\u7bc7\u8bba\u6587\u65e8\u5728\u89e3\u51b3\u7ed3\u6784\u5316LaTeX\u683c\u5f0f\u6587\u6863\u7684"
        "\u673a\u5668\u7ffb\u8bd1\u96be\u9898\uff0c\u5e76\u6307\u51fa\u4e86\u73b0\u6709\u901a\u7528\u673a\u5668"
        "\u7ffb\u8bd1\u7cfb\u7edf\u5728\u6b64\u4efb\u52a1\u4e0a\u7684\u5173\u952e\u4e0d\u8db3\u3002 "
        "**\u95ee\u9898\u672c\u8d28** \u8bba\u6587\u660e\u786e\u6307\u51fa\uff0c\u5c3d\u7ba1\u901a\u7528\u6587\u672c"
        "\u7684\u673a\u5668\u7ffb\u8bd1\u5df2\u53d6\u5f97\u663e\u8457\u8fdb\u5c55\uff0c\u4f46\u7ffb\u8bd1\u5305\u542b"
        "\u6570\u5b66\u516c\u5f0f\u3001\u8868\u683c\u3001\u56fe\u5f62\u548c\u4ea4\u53c9\u5f15\u7528\u7b49\u7279\u5b9a"
        "\u9886\u57df\u8bed\u6cd5\u7684LaTeX\u683c\u5f0f\u6587\u6863\u4ecd\u7136\u662f\u4e00\u4e2a\u91cd\u5927\u6311\u6218\u3002 "
        "**\u4e3a\u4ec0\u4e48\u91cd\u8981** \u51c6\u786e\u7ffb\u8bd1LaTeX\u6587\u6863\u7684\u91cd\u8981\u6027\u5728"
        "\u4e8e\uff0c\u5fc5\u987b\u4fdd\u6301\u5176\u683c\u5f0f\u3001\u7ed3\u6784\u4fdd\u771f\u5ea6\u548c\u672f\u8bed"
        "\u4e00\u81f4\u6027\u3002 "
        "**\u73b0\u6709\u65b9\u6cd5\u7684\u5c40\u9650** \u73b0\u6709\u4e3b\u6d41\u673a\u5668\u7ffb\u8bd1\u7cfb\u7edf"
        "\u662f\u9488\u5bf9\u901a\u7528\u9886\u57df\u6587\u672c\u8bbe\u8ba1\u7684\uff0c\u96be\u4ee5\u7a33\u5b9a\u4fdd"
        "\u6301\u7ed3\u6784\u548c\u4ea4\u53c9\u5f15\u7528\u3002"
    )
    sections = [
        {
            "section_key": section_key,
            "content": content,
            "status": "ready",
            "updated_at": "2026-04-12T00:00:00+00:00",
        }
        for section_key in ("problem", "solution", "innovation", "experiment", "future")
    ]

    payload = paper_service._build_structured_insights_payload(sections)
    normalized_problem = payload["sections"][0]

    assert payload["state"] == "ready"
    assert normalized_problem["raw_content"] == content
    assert normalized_problem["summary"].startswith("\u8fd9\u7bc7\u8bba\u6587\u65e8\u5728\u89e3\u51b3")
    assert [block["heading"] for block in normalized_problem["blocks"]] == [
        "\u95ee\u9898\u672c\u8d28",
        "\u4e3a\u4ec0\u4e48\u91cd\u8981",
        "\u73b0\u6709\u65b9\u6cd5\u7684\u5c40\u9650",
    ]
    assert all(block["content"] for block in normalized_problem["blocks"])


def test_structured_insights_payload_falls_back_to_single_block_for_plain_text():
    content = (
        "\u8fd9\u6bb5\u5bfc\u8bfb\u53ea\u63d0\u4f9b\u4e86\u4e00\u6bb5\u8fde\u7eed\u6b63\u6587\uff0c\u6ca1\u6709\u663e\u5f0f"
        "\u5c0f\u6807\u9898\uff0c\u4f46\u4ecd\u7136\u5e94\u8be5\u88ab\u6536\u655b\u6210\u7a33\u5b9a\u7684 API \u5951\u7ea6\uff0c"
        "\u8ba9\u524d\u7aef\u53ef\u4ee5\u76f4\u63a5\u4f7f\u7528\u7edf\u4e00\u7ed3\u6784\u6e32\u67d3\uff0c\u800c\u4e0d\u662f"
        "\u518d\u53bb\u731c\u6d4b\u5b57\u7b26\u4e32\u91cc\u9762\u7684\u5c42\u6b21\u3002\u8fd9\u79cd\u515c\u5e95\u80fd\u786e\u4fdd"
        "\u8be6\u60c5\u9875\u81f3\u5c11\u4ee5\u5355\u4e2a\u6a21\u5757\u7684\u5f62\u5f0f\u7a33\u5b9a\u5c55\u793a\uff0c\u907f\u514d"
        "\u56e0\u4e3a\u6a21\u578b\u8f93\u51fa\u98ce\u683c\u6f02\u79fb\u800c\u8ba9\u6574\u4e2a\u63a5\u53e3\u6216\u89c6\u56fe"
        "\u964d\u7ea7\u4e3a\u4e0d\u53ef\u7528\u72b6\u6001\u3002"
    )
    sections = [
        {
            "section_key": section_key,
            "content": content,
            "status": "ready",
            "updated_at": "2026-04-12T00:00:00+00:00",
        }
        for section_key in ("problem", "solution", "innovation", "experiment", "future")
    ]

    payload = paper_service._build_structured_insights_payload(sections)
    normalized_problem = payload["sections"][0]

    assert payload["state"] == "ready"
    assert normalized_problem["summary"] is None
    assert normalized_problem["blocks"] == [
        {
            "heading": "\u6838\u5fc3\u5185\u5bb9",
            "content": content,
        }
    ]
