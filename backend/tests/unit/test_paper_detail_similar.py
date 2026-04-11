import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Current paper",
        "authors": ["Ada Lovelace"],
        "categories": ["cs.AI"],
        "abstract_raw": "Current abstract",
        "abstract_translated": "当前摘要",
        "community_status": "official",
        "trans_status": "completed",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T02:00:00+00:00",
        "community_selected_task_id": "task-1",
        "community_selected_asset_id": "asset-1",
        "visibility": "public",
        "status": "published",
    }
    base.update(overrides)
    return base


def test_similar_recommendations_rerank_merged_local_and_arxiv_candidates(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_local_bm25_similar_candidates",
        lambda *, paper, limit=5: asyncio.sleep(
            0,
            result=[
                {
                    "arxiv_id": "2504.12345",
                    "title": "Machine Translation Planning for Technical Documents",
                    "abstract": "Planning-oriented machine translation for technical documents.",
                    "arxiv_url": "https://arxiv.org/abs/2504.12345",
                    "community_paper_id": "paper-neighbor",
                    "link_type": "community",
                },
            ],
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_similar_candidates",
        lambda *, arxiv_id, title, abstract, categories=None, limit=5: asyncio.sleep(
            0,
            result=[
                {
                    "arxiv_id": "2504.99999",
                    "title": "Structured LaTeX Translation for Scientific Documents",
                    "abstract": "A machine translation workflow for scientific LaTeX documents.",
                    "arxiv_url": "https://arxiv.org/abs/2504.99999",
                }
            ],
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_arxiv_id",
        lambda arxiv_id: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(
        paper_service._generate_similar_recommendations_for_paper(
            paper=_paper(
                title="Structured LaTeX Translation with Multi-Agent Coordination",
                abstract_raw="A machine translation system for scientific LaTeX documents.",
                categories=["cs.CL"],
            ),
        )
    )

    assert [item["arxiv_id"] for item in result] == ["2504.99999", "2504.12345"]
    assert result[0]["link_type"] == "arxiv"
    assert result[1]["link_type"] == "community"


def test_similar_recommendations_merge_duplicate_community_and_arxiv_candidates(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_similar_candidates",
        lambda *, arxiv_id, title, abstract, categories=None, limit=5: asyncio.sleep(
            0,
            result=[
                {
                    "arxiv_id": "2504.12345",
                    "title": "Structured LaTeX Translation for Scientific Documents",
                    "abstract": "A machine translation workflow for scientific LaTeX documents.",
                    "arxiv_url": "https://arxiv.org/abs/2504.12345",
                },
                {
                    "arxiv_id": "2504.12346",
                    "title": "Layout-Aware Scientific Translation",
                    "abstract": "Translation systems for structured scientific documents.",
                    "arxiv_url": "https://arxiv.org/abs/2504.12346",
                },
            ],
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_local_bm25_similar_candidates",
        lambda *, paper, limit=5: asyncio.sleep(
            0,
            result=[
                {
                    "arxiv_id": "2504.12345",
                    "title": "Structured LaTeX Translation for Scientific Documents",
                    "abstract": "A machine translation workflow for scientific LaTeX documents.",
                    "arxiv_url": "https://arxiv.org/abs/2504.12345",
                    "community_paper_id": "paper-neighbor",
                    "link_type": "community",
                }
            ],
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_arxiv_id",
        lambda arxiv_id: asyncio.sleep(
            0,
            result=_paper(id="paper-neighbor", arxiv_id="2504.12345")
            if arxiv_id == "2504.12345"
            else None,
        ),
    )

    result = asyncio.run(
        paper_service._generate_similar_recommendations_for_paper(
            paper=_paper(
                title="Structured LaTeX Translation with Multi-Agent Coordination",
                abstract_raw="A machine translation system for scientific LaTeX documents.",
                categories=["cs.CL"],
            )
        )
    )

    assert [item["arxiv_id"] for item in result] == ["2504.12345", "2504.12346"]
    assert result[0]["community_paper_id"] == "paper-neighbor"
    assert result[0]["link_type"] == "community"


def test_similar_recommendations_limit_to_top_ten_items(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_local_bm25_similar_candidates",
        lambda *, paper, limit=5: asyncio.sleep(0, result=[]),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_similar_candidates",
        lambda *, arxiv_id, title, abstract, categories=None, limit=5: asyncio.sleep(
            0,
            result=[
                {
                    "arxiv_id": f"2504.{10000 + index}",
                    "title": f"Structured LaTeX Translation Variant {index}",
                    "abstract": "A machine translation workflow for scientific LaTeX documents.",
                    "arxiv_url": f"https://arxiv.org/abs/2504.{10000 + index}",
                }
                for index in range(12)
            ],
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_arxiv_id",
        lambda arxiv_id: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(
        paper_service._generate_similar_recommendations_for_paper(
            paper=_paper(
                title="Structured LaTeX Translation with Multi-Agent Coordination",
                abstract_raw="A machine translation system for scientific LaTeX documents.",
                categories=["cs.CL"],
            )
        )
    )

    assert len(result) == 10


def test_similar_recommendations_return_persisted_results_without_live_retrieval(monkeypatch):
    persisted_items = [
        {
            "arxiv_id": "2504.12345",
            "title": "Persisted Neighbor Paper",
            "abstract": "Persisted abstract.",
            "arxiv_url": "https://arxiv.org/abs/2504.12345",
            "community_paper_id": "paper-neighbor",
            "link_type": "community",
        }
    ]

    class _FakeRepository:
        def list_similar_recommendations(self, paper_id):
            assert paper_id == "paper-1"
            return persisted_items

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeRepository())
    monkeypatch.setattr(
        paper_service,
        "_ensure_public_paper",
        lambda _paper_id: asyncio.sleep(0, result=_paper()),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_local_bm25_similar_candidates",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("live local retrieval should not run")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_similar_candidates",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("live arXiv retrieval should not run")),
    )

    result = asyncio.run(paper_service.get_community_paper_similar(paper_id="paper-1"))

    assert result == {"items": persisted_items}


def test_similar_recommendations_return_empty_for_legacy_paper_without_persisted_results(monkeypatch):
    class _FakeRepository:
        def list_similar_recommendations(self, paper_id):
            assert paper_id == "paper-1"
            return []

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeRepository())
    monkeypatch.setattr(
        paper_service,
        "_ensure_public_paper",
        lambda _paper_id: asyncio.sleep(0, result=_paper()),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_local_bm25_similar_candidates",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy papers should not trigger live local retrieval")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_similar_candidates",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy papers should not trigger live arXiv retrieval")),
    )

    result = asyncio.run(paper_service.get_community_paper_similar(paper_id="paper-1"))

    assert result == {"items": []}


def test_local_bm25_similarity_ranks_related_community_papers_first(monkeypatch):
    class _FakeRepository:
        def list_public_papers(self):
            return [
                _paper(),
                _paper(
                    id="paper-neighbor",
                    arxiv_id="2504.12345",
                    title="Structured LaTeX Translation for Scientific Documents",
                    abstract_raw="A machine translation workflow for LaTeX scientific papers with structure preservation.",
                    categories=["cs.CL"],
                ),
                _paper(
                    id="paper-far",
                    arxiv_id="2501.99999",
                    title="Graph Reinforcement Learning for Traffic Control",
                    abstract_raw="An unrelated reinforcement learning paper for signal control.",
                    categories=["cs.LG"],
                ),
            ]

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeRepository())

    items = asyncio.run(
        paper_service._fetch_local_bm25_similar_candidates(
            paper=_paper(
                id="paper-1",
                arxiv_id="2503.01010",
                title="Structured LaTeX Translation with Multi-Agent Coordination",
                abstract_raw="A machine translation system for scientific LaTeX documents.",
                categories=["cs.CL"],
            ),
            limit=5,
        )
    )

    assert [item["community_paper_id"] for item in items] == ["paper-neighbor"]


def test_local_bm25_similarity_excludes_stopword_and_category_only_matches(monkeypatch):
    class _FakeRepository:
        def list_public_papers(self):
            return [
                _paper(),
                _paper(
                    id="paper-neighbor",
                    arxiv_id="2504.12345",
                    title="Document-Level Machine Translation with Layout Awareness",
                    abstract_raw="Machine translation for structured scientific documents with layout preservation.",
                    categories=["cs.CL"],
                ),
                _paper(
                    id="paper-category-only",
                    arxiv_id="2603.25723",
                    title="Natural-Language Agent Harnesses",
                    abstract_raw="Tooling patterns for evaluating agent systems.",
                    categories=["cs.CL", "cs.AI"],
                ),
                _paper(
                    id="paper-stopword-only",
                    arxiv_id="2603.12111",
                    title="Breaching the Barrier: Transition Pathways of Coral Larval Connectivity Across the Eastern Pacific",
                    abstract_raw="A study of coral larval connectivity across the eastern Pacific.",
                    categories=["physics.ao-ph", "math.PR", "nlin.CD"],
                ),
            ]

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeRepository())

    items = asyncio.run(
        paper_service._fetch_local_bm25_similar_candidates(
            paper=_paper(
                id="paper-1",
                arxiv_id="2503.01010",
                title="Structured LaTeX Translation with Multi-Agent Coordination",
                abstract_raw=(
                    "Despite remarkable progress of modern machine translation, "
                    "scientific LaTeX documents remain difficult to translate reliably."
                ),
                categories=["cs.CL"],
            ),
            limit=5,
        )
    )

    assert [item["community_paper_id"] for item in items] == ["paper-neighbor"]


def test_fetch_arxiv_similar_candidates_sync_falls_back_to_broader_queries(monkeypatch):
    responses = [
        """<?xml version='1.0' encoding='UTF-8'?>
        <feed xmlns='http://www.w3.org/2005/Atom'>
          <entry>
            <id>http://arxiv.org/abs/2508.18791v3</id>
            <title>LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination</title>
            <summary>Current abstract</summary>
          </entry>
        </feed>
        """,
        """<?xml version='1.0' encoding='UTF-8'?>
        <feed xmlns='http://www.w3.org/2005/Atom'>
          <entry>
            <id>http://arxiv.org/abs/2508.18791v3</id>
            <title>LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination</title>
            <summary>Current abstract</summary>
          </entry>
          <entry>
            <id>http://arxiv.org/abs/2504.12345v2</id>
            <title>Document-Level Machine Translation with Layout Awareness</title>
            <summary>Translation systems for structured scientific documents.</summary>
          </entry>
        </feed>
        """,
    ]
    called_queries = []

    def fake_get(_url, *, params, headers, timeout):
        assert headers["User-Agent"] == "LaTexTrans/CommunitySimilar"
        assert timeout == 15
        called_queries.append(params["search_query"])
        return SimpleNamespace(
            text=responses[min(len(called_queries) - 1, len(responses) - 1)],
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr(paper_service.requests, "get", fake_get)

    items = paper_service._fetch_arxiv_similar_candidates_sync(
        arxiv_id="2508.18791",
        title="LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination",
        abstract="Structured translation for scientific LaTeX papers with multi-agent coordination.",
        categories=["cs.CL"],
        limit=5,
    )

    assert len(called_queries) >= 2
    assert items == [
        {
            "arxiv_id": "2504.12345",
            "title": "Document-Level Machine Translation with Layout Awareness",
            "abstract": "Translation systems for structured scientific documents.",
            "arxiv_url": "https://arxiv.org/abs/2504.12345",
            "_categories": [],
        }
    ]
