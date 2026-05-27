"""Unit tests for ranking source adapters.

Focuses on behaviour that does not require real network access:
- Stub / local adapter
- XML parsing of arXiv ATOM responses
- Aggregation merge logic
- Empty-input safety
- Fail‑soft behaviour with mocked HTTP failures
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from backend.app.services.ranking.source_adapters import (
    _metric_int,
    _parse_arxiv_xml,
    enrich_candidates_with_sources,
    fetch_arxiv_batch,
    fetch_github_evidence,
    fetch_huggingface_papers,
    fetch_local_engagement,
    fetch_openalex_citations,
    fetch_semantic_scholar_batch,
)

# ── Reusable sample data ──────────────────────────────────────────────

SAMPLE_ARXIV_IDS = ["2301.00001", "2301.00002", "2301.00003"]

SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Test Paper One</title>
    <author><name>Alice Author</name></author>
    <author><name>Bob Coauthor</name></author>
    <category term="cs.AI"/>
    <category term="cs.CL"/>
    <published>2023-01-01T00:00:00Z</published>
    <updated>2023-01-02T12:00:00Z</updated>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00002v2</id>
    <title>  Test Paper Two  </title>
    <author><name>Charlie Writer</name></author>
    <category term="math.OC"/>
    <published>2023-01-02T08:00:00Z</published>
    <updated>2023-06-15T00:00:00Z</updated>
  </entry>
</feed>"""


# ═══════════════════════════════════════════════════════════════════════
#  _metric_int
# ═══════════════════════════════════════════════════════════════════════


class TestMetricInt:
    def test_int_passthrough(self):
        assert _metric_int(42) == 42

    def test_float_truncated(self):
        assert _metric_int(3.9) == 3

    def test_bool(self):
        assert _metric_int(True) == 1
        assert _metric_int(False) == 0

    def test_none_returns_zero(self):
        assert _metric_int(None) == 0

    def test_string_returns_zero(self):
        assert _metric_int("123") == 0

    def test_dict_returns_zero(self):
        assert _metric_int({"a": 1}) == 0


# ═══════════════════════════════════════════════════════════════════════
#  _parse_arxiv_xml
# ═══════════════════════════════════════════════════════════════════════


class TestParseArxivXml:
    def test_parses_entries_correctly(self):
        result = _parse_arxiv_xml(SAMPLE_ARXIV_XML)

        assert "2301.00001" in result
        assert result["2301.00001"]["title"] == "Test Paper One"
        assert result["2301.00001"]["authors"] == ["Alice Author", "Bob Coauthor"]
        assert result["2301.00001"]["categories"] == ["cs.AI", "cs.CL"]
        assert result["2301.00001"]["published"] == "2023-01-01T00:00:00Z"
        assert result["2301.00001"]["updated"] == "2023-01-02T12:00:00Z"

        assert "2301.00002" in result
        assert result["2301.00002"]["title"] == "Test Paper Two"
        assert result["2301.00002"]["authors"] == ["Charlie Writer"]
        assert result["2301.00002"]["categories"] == ["math.OC"]

    def test_empty_feed(self):
        xml = (
            '<?xml version="1.0"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        )
        assert _parse_arxiv_xml(xml) == {}

    def test_skips_entries_with_unparseable_id(self):
        xml = (
            '<?xml version="1.0"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            "<entry><id>http://example.com/not-an-arxiv-id</id>"
            "<title>Bad</title></entry>"
            "</feed>"
        )
        assert _parse_arxiv_xml(xml) == {}

    def test_handles_missing_optional_fields(self):
        xml = (
            '<?xml version="1.0"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            "<entry><id>http://arxiv.org/abs/2301.00001v1</id></entry>"
            "</feed>"
        )
        result = _parse_arxiv_xml(xml)
        assert "2301.00001" in result
        assert result["2301.00001"]["title"] == ""
        assert result["2301.00001"]["authors"] == []
        assert result["2301.00001"]["categories"] == []
        assert result["2301.00001"]["published"] is None

    def test_rejects_malformed_xml(self):
        with pytest.raises(ET.ParseError):
            _parse_arxiv_xml("not xml at all")


# ═══════════════════════════════════════════════════════════════════════
#  fetch_local_engagement  (stub)
# ═══════════════════════════════════════════════════════════════════════


class TestFetchLocalEngagement:
    @pytest.mark.asyncio
    async def test_returns_zeros_for_all_ids(self):
        result = await fetch_local_engagement(SAMPLE_ARXIV_IDS)
        for aid in SAMPLE_ARXIV_IDS:
            assert aid in result
            assert result[aid] == {"views": 0, "likes": 0, "saves": 0}

    @pytest.mark.asyncio
    async def test_empty_input(self):
        result = await fetch_local_engagement([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_single_id(self):
        result = await fetch_local_engagement(["2301.00001"])
        assert result == {"2301.00001": {"views": 0, "likes": 0, "saves": 0}}


# ═══════════════════════════════════════════════════════════════════════
#  Empty-input safety for all adapters
# ═══════════════════════════════════════════════════════════════════════


class TestEmptyInputSafety:
    @pytest.mark.asyncio
    async def test_arxiv_batch_empty(self):
        assert await fetch_arxiv_batch([]) == {}

    @pytest.mark.asyncio
    async def test_openalex_empty(self):
        assert await fetch_openalex_citations([]) == {}

    @pytest.mark.asyncio
    async def test_semantic_scholar_empty(self):
        assert await fetch_semantic_scholar_batch([]) == {}

    @pytest.mark.asyncio
    async def test_github_empty(self):
        assert await fetch_github_evidence([]) == {}

    @pytest.mark.asyncio
    async def test_enrich_empty(self):
        assert await enrich_candidates_with_sources([]) == {}


# ═══════════════════════════════════════════════════════════════════════
#  Fail-soft: adapters catch exceptions and return empty/partial results
# ═══════════════════════════════════════════════════════════════════════


class TestFailSoft:
    @pytest.mark.asyncio
    async def test_arxiv_batch_fetch_failure(self):
        """When fetch_text raises, arxiv adapter returns {}."""
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_text",
            side_effect=RuntimeError("boom"),
        ):
            result = await fetch_arxiv_batch(["2301.00001"])
            assert result == {}

    @pytest.mark.asyncio
    async def test_openalex_partial_failure(self):
        """One failing ID should not affect others."""
        call_count = 0

        def _fake_fetch_json(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "2301.00002" in url:
                raise RuntimeError("timeout")
            return {"results": [{"cited_by_count": 42}]}

        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            side_effect=_fake_fetch_json,
        ):
            result = await fetch_openalex_citations(
                ["2301.00001", "2301.00002"]
            )
            assert "2301.00001" in result
            assert result["2301.00001"] == 42
            assert "2301.00002" not in result

    @pytest.mark.asyncio
    async def test_huggingface_fetch_failure(self):
        """When API call fails, returns {}."""
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            side_effect=RuntimeError("hf down"),
        ):
            result = await fetch_huggingface_papers()
            assert result == {}

    @pytest.mark.asyncio
    async def test_huggingface_non_list_response(self):
        """Non-list response yields {}."""
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            return_value={"error": "not a list"},
        ):
            result = await fetch_huggingface_papers()
            assert result == {}

    @pytest.mark.asyncio
    async def test_github_partial_failure(self):
        """When one search fails others still succeed."""
        call_count = 0

        async def _fake_search(url, *, headers=None, timeout=30, retries=3, is_github=False):
            nonlocal call_count
            call_count += 1
            if "2301.00002" in url:
                raise RuntimeError("rate limit")
            return {"items": [{"stargazers_count": 10, "forks_count": 2, "pushed_at": "2023-01-01", "html_url": "https://github.com/x/y"}]}

        with patch(
            "backend.app.services.ranking.source_adapters._fetch_json_with_headers",
            side_effect=_fake_search,
        ), patch(
            "backend.app.services.ranking.source_adapters._make_github_headers",
            return_value={},
        ):
            result = await fetch_github_evidence(
                ["2301.00001", "2301.00002"]
            )
            assert "2301.00001" in result
            assert result["2301.00001"]["stars"] == 10
            assert "2301.00002" not in result

    @pytest.mark.asyncio
    async def test_semantic_scholar_batch_failure(self):
        """When the POST helper raises, the adapter returns {}."""
        with patch(
            "backend.app.services.ranking.source_adapters._fetch_post_json",
            side_effect=RuntimeError("ss down"),
        ):
            result = await fetch_semantic_scholar_batch(["2301.00001"])
            assert result == {}

    @pytest.mark.asyncio
    async def test_semantic_scholar_non_list_response(self):
        """Non-list response yields {}."""
        with patch(
            "backend.app.services.ranking.source_adapters._fetch_post_json",
            return_value={"error": "oops"},
        ):
            result = await fetch_semantic_scholar_batch(["2301.00001"])
            assert result == {}

    @pytest.mark.asyncio
    async def test_arxiv_batch_xml_parse_failure(self):
        """When the arXiv API returns non-XML, the adapter fails soft."""
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_text",
            return_value="<html>not atom</html>",
        ) as mock_fetch:
            result = await fetch_arxiv_batch(["2301.00001"])
            assert result == {}
            # XXX: ET.fromstring on HTML raises ParseError, caught in adapter
            mock_fetch.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════
#  enrich_candidates_with_sources  (aggregation)
# ═══════════════════════════════════════════════════════════════════════


class TestEnrichCandidates:
    @pytest.mark.asyncio
    async def test_merges_all_sources_per_id(self):
        """All adapters return data for the same IDs; they are merged correctly."""
        ids = ["2301.00001"]

        async def _fake_arxiv(arxiv_ids, **kw):
            return {"2301.00001": {"title": "T", "authors": [], "categories": [], "published": None, "updated": None}}

        async def _fake_openalex(arxiv_ids, **kw):
            return {"2301.00001": 123}

        async def _fake_ss(arxiv_ids, **kw):
            return {"2301.00001": {"citationCount": 10}}

        async def _fake_hf(**kw):
            return {"2301.00001": {"upvotes": 5}}

        async def _fake_ax(**kw):
            return {"2301.00001": {"views": 100}}

        async def _fake_gh(arxiv_ids, **kw):
            return {"2301.00001": {"stars": 3}}

        with patch(
            "backend.app.services.ranking.source_adapters.fetch_arxiv_batch",
            side_effect=_fake_arxiv,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_openalex_citations",
            side_effect=_fake_openalex,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_semantic_scholar_batch",
            side_effect=_fake_ss,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_huggingface_papers",
            side_effect=_fake_hf,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_alphaxiv_signals",
            side_effect=_fake_ax,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_github_evidence",
            side_effect=_fake_gh,
        ):
            result = await enrich_candidates_with_sources(ids)

            assert "2301.00001" in result
            entry = result["2301.00001"]
            assert entry["arxiv_meta"] == {"title": "T", "authors": [], "categories": [], "published": None, "updated": None}
            assert entry["citations"] == 123
            assert entry["semantic_scholar"] == {"citationCount": 10}
            assert entry["huggingface"] == {"upvotes": 5}
            assert entry["alphaxiv"] == {"views": 100}
            assert entry["github"] == {"stars": 3}
            assert entry["local"] == {"views": 0, "likes": 0, "saves": 0}

    @pytest.mark.asyncio
    async def test_missing_sources_become_none(self):
        """When an adapter returns nothing for an ID, its slot is None."""
        ids = ["2301.00001"]

        async def _fake_arxiv(arxiv_ids, **kw):
            return {}  # no data

        async def _fake_openalex(arxiv_ids, **kw):
            return {}

        async def _fake_ss(arxiv_ids, **kw):
            return {}

        async def _fake_hf(**kw):
            return {}

        async def _fake_ax(**kw):
            return {}

        async def _fake_gh(arxiv_ids, **kw):
            return {}

        with patch(
            "backend.app.services.ranking.source_adapters.fetch_arxiv_batch",
            side_effect=_fake_arxiv,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_openalex_citations",
            side_effect=_fake_openalex,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_semantic_scholar_batch",
            side_effect=_fake_ss,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_huggingface_papers",
            side_effect=_fake_hf,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_alphaxiv_signals",
            side_effect=_fake_ax,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_github_evidence",
            side_effect=_fake_gh,
        ):
            result = await enrich_candidates_with_sources(ids)

            entry = result["2301.00001"]
            assert entry["arxiv_meta"] is None
            assert entry["citations"] is None
            assert entry["semantic_scholar"] is None
            assert entry["huggingface"] is None
            assert entry["alphaxiv"] is None
            assert entry["github"] is None
            assert entry["local"] == {"views": 0, "likes": 0, "saves": 0}

    @pytest.mark.asyncio
    async def test_adapter_exceptions_produce_none(self):
        """When an adapter raises, it is caught and its slots become None/empty."""
        ids = ["2301.00001"]

        async def _failing(arxiv_ids, **kw):
            raise RuntimeError("kaboom")

        with patch(
            "backend.app.services.ranking.source_adapters.fetch_arxiv_batch",
            side_effect=_failing,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_openalex_citations",
            side_effect=_failing,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_semantic_scholar_batch",
            side_effect=_failing,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_huggingface_papers",
            side_effect=_failing,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_alphaxiv_signals",
            side_effect=_failing,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_github_evidence",
            side_effect=_failing,
        ):
            result = await enrich_candidates_with_sources(ids)
            # enrich should still return a dict keyed by arxiv_id
            assert "2301.00001" in result
            entry = result["2301.00001"]
            assert entry["arxiv_meta"] is None
            assert entry["citations"] is None
            assert entry["semantic_scholar"] is None
            assert entry["huggingface"] is None
            assert entry["alphaxiv"] is None
            assert entry["github"] is None
            assert entry["local"] == {"views": 0, "likes": 0, "saves": 0}

    @pytest.mark.asyncio
    async def test_multiple_ids_merged_independently(self):
        """Each arXiv ID gets its own merged entry."""
        ids = ["2301.00001", "2301.00002"]

        async def _fake_arxiv(arxiv_ids, **kw):
            return {aid: {"title": aid} for aid in arxiv_ids}

        async def _fake_others(*args, **kw):
            return {}

        with patch(
            "backend.app.services.ranking.source_adapters.fetch_arxiv_batch",
            side_effect=_fake_arxiv,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_openalex_citations",
            side_effect=_fake_others,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_semantic_scholar_batch",
            side_effect=_fake_others,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_huggingface_papers",
            side_effect=_fake_others,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_alphaxiv_signals",
            side_effect=_fake_others,
        ), patch(
            "backend.app.services.ranking.source_adapters.fetch_github_evidence",
            side_effect=_fake_others,
        ):
            result = await enrich_candidates_with_sources(ids)

            assert set(result.keys()) == set(ids)
            assert result["2301.00001"]["arxiv_meta"] == {"title": "2301.00001"}
            assert result["2301.00002"]["arxiv_meta"] == {"title": "2301.00002"}


# ═══════════════════════════════════════════════════════════════════════
#  fetch_huggingface_papers  (without network)
# ═══════════════════════════════════════════════════════════════════════


class TestHuggingFacePapers:
    @pytest.mark.asyncio
    async def test_maps_arxiv_id_correctly(self):
        response = [
            {
                "paper": {
                    "id": "2312.12345",
                    "arxivId": "2312.12345v1",
                    "title": "Cool Paper",
                },
                "upvotes": 42,
                "comments": 7,
            },
            {
                "paper": {
                    "id": "2312.99999",
                    "arxivId": "2312.99999",
                    "title": "Another Paper",
                },
                "upvotes": 3,
                "comments": 0,
            },
        ]
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            return_value=response,
        ):
            result = await fetch_huggingface_papers()
            assert "2312.12345" in result
            assert result["2312.12345"]["upvotes"] == 42
            assert result["2312.12345"]["comments"] == 7
            assert result["2312.12345"]["title"] == "Cool Paper"
            assert "2312.99999" in result
            assert result["2312.99999"]["upvotes"] == 3

    @pytest.mark.asyncio
    async def test_skips_items_without_paper_dict(self):
        response = [
            {"upvotes": 1},  # no "paper" key
            {"paper": None, "upvotes": 2},  # paper is not a dict
        ]
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            return_value=response,
        ):
            result = await fetch_huggingface_papers()
            assert result == {}

    @pytest.mark.asyncio
    async def test_skips_unparseable_arxiv_ids(self):
        response = [
            {
                "paper": {
                    "id": "garbage",
                    "arxivId": None,
                    "title": "Bad",
                },
                "upvotes": 1,
            }
        ]
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            return_value=response,
        ):
            result = await fetch_huggingface_papers()
            assert result == {}

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        response = [
            {
                "paper": {"id": f"2301.{i:05d}", "arxivId": f"2301.{i:05d}", "title": f"P{i}"},
                "upvotes": i,
                "comments": 0,
            }
            for i in range(100)
        ]
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            return_value=response,
        ):
            result = await fetch_huggingface_papers(limit=10)
            assert len(result) == 10

    @pytest.mark.asyncio
    async def test_handles_discussions_field_as_comments(self):
        response = [
            {
                "paper": {"id": "2301.00001", "arxivId": "2301.00001", "title": "P"},
                "upvotes": 5,
                "discussions": 12,
            }
        ]
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            return_value=response,
        ):
            result = await fetch_huggingface_papers()
            assert result["2301.00001"]["comments"] == 12

    @pytest.mark.asyncio
    async def test_uses_arxiv_id_from_paper_id_fallback(self):
        response = [
            {
                "paper": {
                    "id": "2301.00001",
                    "title": "No arxivId key",
                },
                "upvotes": 1,
            }
        ]
        with patch(
            "backend.app.services.ranking.source_adapters.fetch_json",
            return_value=response,
        ):
            result = await fetch_huggingface_papers()
            assert "2301.00001" in result
