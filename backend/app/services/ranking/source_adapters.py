"""Source adapters for the hot ranking pipeline.

Each adapter takes a list of arXiv IDs and returns enriched data from an external
signal source.  All adapters follow the fail-soft pattern: if an API call fails or
returns no data they return empty / partial results, never raise.

Sync HTTP calls (fetch_text / fetch_json from .utils) are wrapped in
``asyncio.to_thread`` so the adapters work in async contexts.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

from .utils import (
    ALPHAXIV_API_BASE,
    ARXIV_API_URL,
    OPENALEX_API_URL,
    USER_AGENT,
    fetch_json,
    fetch_text,
    normalize_arxiv_id,
)

logger = logging.getLogger(__name__)

# ── XML namespace used by the arXiv ATOM API ─────────────────────────
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"


# ═══════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════


def _metric_int(value: Any) -> int:
    """Coerce a potentially-non‑integer metric value to int."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _parse_arxiv_xml(xml_text: str) -> dict[str, dict]:
    """Parse the arXiv ATOM XML response into per‑paper metadata dicts.

    Returns a dict keyed by normalized arXiv ID.  Each value carries:
        title, authors (list[str]), categories (list[str]),
        published (str|None), updated (str|None)
    """
    root = ET.fromstring(xml_text)
    ns = {"atom": ATOM_NAMESPACE}
    results: dict[str, dict] = {}

    for entry in root.findall("atom:entry", ns):
        raw_id = entry.findtext("atom:id", default="", namespaces=ns)
        arxiv_id = normalize_arxiv_id(raw_id.rsplit("/abs/", 1)[-1])
        if arxiv_id is None:
            continue

        title_text = entry.findtext("atom:title", default="", namespaces=ns)
        title_clean = " ".join(title_text.split()) if title_text else ""

        authors: list[str] = []
        for author_elem in entry.findall("atom:author", ns):
            name = author_elem.findtext("atom:name", default="", namespaces=ns)
            if name and name.strip():
                authors.append(name.strip())

        categories: list[str] = []
        for cat_elem in entry.findall("atom:category", ns):
            term = cat_elem.get("term", "")
            if term:
                categories.append(term)

        published = entry.findtext("atom:published", default=None, namespaces=ns)
        updated = entry.findtext("atom:updated", default=None, namespaces=ns)

        results[arxiv_id] = {
            "title": title_clean,
            "authors": authors,
            "categories": categories,
            "published": published,
            "updated": updated,
        }

    return results


async def _fetch_post_json(
    url: str,
    body: dict,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 3,
) -> dict[str, Any]:
    """POST a JSON body to *url* and return the parsed JSON response.

    Used by the Semantic Scholar batch endpoint (requires POST), which
    ``fetch_json`` does not support.
    """
    default_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if headers:
        default_headers.update(headers)

    def _do_post() -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(
                    url,
                    json=body,
                    headers=default_headers,
                    timeout=timeout,
                )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(0.5 * attempt)

        raise RuntimeError(
            f"POST {url} failed after {retries} attempts: {last_error}"
        ) from last_error

    return await asyncio.to_thread(_do_post)


async def _fetch_json_with_headers(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 3,
    is_github: bool = False,
) -> dict[str, Any]:
    """GET *url* with custom headers, returning parsed JSON.

    When *is_github* is True the helper handles 403 rate‑limit and 422
    no‑results specially so callers always receive a well‑formed dict.
    """
    final_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if headers:
        final_headers.update(headers)

    if is_github:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            final_headers["Authorization"] = f"Bearer {token}"

    def _do_get() -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, headers=final_headers, timeout=timeout)
                if is_github:
                    if resp.status_code == 403 and "rate limit" in resp.text.lower():
                        time.sleep(60)
                        continue
                    if resp.status_code == 422:
                        return {"items": []}
                if is_github and resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(0.5 * attempt)

        raise RuntimeError(
            f"GET {url} failed after {retries} attempts: {last_error}"
        ) from last_error

    return await asyncio.to_thread(_do_get)


def _make_github_headers() -> dict[str, str]:
    """Build base headers for the GitHub Search API.

    Does NOT add the Authorization header here -- that is handled
    inside ``_fetch_json_with_headers(..., is_github=True)`` which
    reads ``GITHUB_TOKEN`` from the environment.
    """
    return {"Accept": "application/vnd.github.v3+json"}


# ═══════════════════════════════════════════════════════════════════════
#  Source adapters
# ═══════════════════════════════════════════════════════════════════════


async def fetch_arxiv_batch(
    arxiv_ids: list[str],
    *,
    timeout: int = 20,
    retries: int = 3,
) -> dict[str, dict]:
    """Fetch canonical metadata for a batch of arXiv IDs.

    Calls ``export.arxiv.org/api/query``, parses the ATOM XML response,
    and returns a dict mapping each arXiv ID to::

        {title, authors, categories, published, updated}

    Empty input returns an empty dict.  Any error is caught, logged, and
    results in an empty return (fail‑soft).
    """
    if not arxiv_ids:
        return {}

    id_list = ",".join(arxiv_ids)
    url = f"{ARXIV_API_URL}?id_list={id_list}&max_results={len(arxiv_ids)}"

    try:
        xml_text = await asyncio.to_thread(
            fetch_text, url, timeout=timeout, retries=retries
        )
        return _parse_arxiv_xml(xml_text)
    except Exception as exc:
        logger.warning("arxiv batch fetch failed for %d ids: %s", len(arxiv_ids), exc)
        return {}


async def fetch_openalex_citations(
    arxiv_ids: list[str],
    *,
    mailto: str | None = None,
    timeout: int = 20,
    retries: int = 3,
) -> dict[str, int]:
    """Fetch citation counts from OpenAlex for a batch of arXiv IDs.

    Uses the DOI‑based filter ``doi:10.48550/arxiv.<id>`` to look up
    each work.  Returns ``{arxiv_id: cited_by_count}``.

    Fail‑soft: any individual lookup failure is logged and skipped;
    the function never raises.
    """
    if not arxiv_ids:
        return {}

    async def _fetch_one(arxiv_id: str) -> tuple[str, int | None]:
        params: dict[str, str] = {
            "filter": f"doi:10.48550/arxiv.{arxiv_id}",
        }
        if mailto:
            params["mailto"] = mailto
        url = f"{OPENALEX_API_URL}?{_make_qs(params)}"

        try:
            data = await asyncio.to_thread(
                fetch_json, url, timeout=timeout, retries=retries
            )
            results = data.get("results", [])
            if results and isinstance(results[0], dict):
                count = results[0].get("cited_by_count", 0)
                return (arxiv_id, int(count) if isinstance(count, (int, float)) else 0)
        except Exception as exc:
            logger.warning(
                "openalex citation fetch failed for %s: %s", arxiv_id, exc
            )
        return (arxiv_id, None)

    tasks = [_fetch_one(aid) for aid in arxiv_ids]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    result: dict[str, int] = {}
    for item in gathered:
        if isinstance(item, Exception):
            logger.warning("openalex citation gather exception: %s", item)
            continue
        aid, count = item
        if count is not None:
            result[aid] = count

    return result


async def fetch_semantic_scholar_batch(
    arxiv_ids: list[str],
    *,
    timeout: int = 30,
    retries: int = 3,
) -> dict[str, dict]:
    """Fetch citation data from the Semantic Scholar batch API.

    POSTs up to 500 ``ArXiv:<id>`` identifiers per request to
    ``api.semanticscholar.org/graph/v1/paper/batch``.

    Returns ``{arxiv_id: {citationCount, influentialCitationCount, title, year}}``.

    Fail‑soft: any per‑batch or per‑item failure is skipped.
    """
    if not arxiv_ids:
        return {}

    BATCH_SIZE = 500
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
    FIELDS = "citationCount,influentialCitationCount,title,year"
    result: dict[str, dict] = {}

    for i in range(0, len(arxiv_ids), BATCH_SIZE):
        batch_ids = arxiv_ids[i : i + BATCH_SIZE]
        url = f"{BASE_URL}?fields={FIELDS}"
        body = {"ids": [f"ArXiv:{aid}" for aid in batch_ids]}

        try:
            data = await _fetch_post_json(
                url,
                body,
                timeout=timeout,
                retries=retries,
            )
        except Exception as exc:
            logger.warning(
                "semantic scholar batch %d failed: %s",
                i // BATCH_SIZE,
                exc,
            )
            continue

        if not isinstance(data, list):
            continue

        for item in data:
            if not isinstance(item, dict):
                continue
            ext_ids = item.get("externalIds") or {}
            if isinstance(ext_ids, dict):
                raw_arxiv = ext_ids.get("ArXiv", "")
            else:
                raw_arxiv = ""
            aid = normalize_arxiv_id(str(raw_arxiv))
            if aid is None:
                continue

            result[aid] = {
                "citationCount": _metric_int(item.get("citationCount", 0)),
                "influentialCitationCount": _metric_int(
                    item.get("influentialCitationCount", 0)
                ),
                "title": item.get("title", "") or "",
                "year": item.get("year"),
            }

    return result


async def fetch_huggingface_papers(
    *,
    limit: int = 200,
    timeout: int = 30,
    retries: int = 3,
) -> dict[str, dict]:
    """Fetch trending papers from the HuggingFace daily papers API.

    Calls ``huggingface.co/api/daily_papers`` and maps each paper's
    ``arxivId`` to ``{upvotes, comments, title, paper_url}``.

    Uses ``HF_PROXY`` env var (default ``http://127.0.0.1:7890``) for
    deployments where HuggingFace is blocked.

    Fail‑soft: returns ``{}`` on any error.
    """
    HF_API = "https://huggingface.co/api/daily_papers"
    hf_proxy = os.environ.get("HF_PROXY", "http://127.0.0.1:7890")
    proxies = {"https": hf_proxy} if hf_proxy else None

    def _fetch_hf():
        headers = {
            "User-Agent": "LaTexTrans paper source exporter/2.0",
            "Accept": "application/json",
        }
        for attempt in range(1, retries + 1):
            # Use proxy on first attempt, direct on retries if proxy fails
            _proxies = proxies if attempt == 1 else None
            try:
                resp = requests.get(
                    HF_API, headers=headers, timeout=timeout,
                    proxies=_proxies, verify=True,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception:
                if attempt >= retries:
                    raise
                time.sleep(0.5 * attempt)
        return {}

    try:
        data = await asyncio.to_thread(_fetch_hf)
    except Exception as exc:
        logger.warning("huggingface daily papers fetch failed: %s", exc)
        return {}

    if not isinstance(data, list):
        return {}

    result: dict[str, dict] = {}
    for item in data[:limit]:
        if not isinstance(item, dict):
            continue
        paper = item.get("paper")
        if not isinstance(paper, dict):
            continue

        raw_id = paper.get("arxivId") or paper.get("id") or ""
        aid = normalize_arxiv_id(raw_id)
        if aid is None:
            continue

        paper_id = paper.get("id", "")
        result[aid] = {
            "upvotes": _metric_int(item.get("upvotes", 0)),
            "comments": _metric_int(item.get("comments", 0) or item.get("discussions", 0)),
            "title": paper.get("title", "") or "",
            "paper_url": (
                f"https://huggingface.co/papers/{paper_id}"
                if paper_id
                else ""
            ),
        }

    return result


async def fetch_alphaxiv_signals(
    *,
    interval: str = "30 Days",
    limit: int = 500,
    timeout: int = 30,
    retries: int = 3,
) -> dict[str, dict]:
    """Fetch hot papers from the alphaXiv feed API.

    Pages through ``/papers/v3/feed?sort=Hot&interval=...`` until
    *limit* unique papers have been collected.

    Returns ``{arxiv_id: {views, votes, comments, rank, signal_ranks}}``.

    Fail‑soft: if any page fails the function stops paging and returns
    whatever has been accumulated so far.
    """
    from urllib.parse import quote

    PAGE_SIZE = 200
    result: dict[str, dict] = {}
    page = 1
    collected = 0

    while collected < limit:
        url = (
            f"{ALPHAXIV_API_BASE}/papers/v3/feed?"
            f"pageNum={page}&pageSize={PAGE_SIZE}"
            f"&sort=Hot&interval={quote(interval)}"
        )
        try:
            data = await asyncio.to_thread(
                fetch_json, url, timeout=timeout, retries=retries
            )
        except Exception as exc:
            logger.warning(
                "alphaxiv feed page %d failed: %s", page, exc
            )
            break

        papers = data.get("papers", [])
        if not papers:
            break

        for paper in papers:
            if not isinstance(paper, dict):
                continue
            aid = normalize_arxiv_id(paper.get("universal_paper_id"))
            if aid is None:
                continue
            if aid in result:
                continue  # already collected from an earlier page

            metrics = paper.get("metrics") or {}
            if not isinstance(metrics, dict):
                metrics = {}
            visits = metrics.get("visits_count") or {}
            if not isinstance(visits, dict):
                visits = {}

            rank = collected + 1
            result[aid] = {
                "views": _metric_int(visits.get("all")),
                "votes": max(
                    _metric_int(metrics.get("public_total_votes")),
                    _metric_int(metrics.get("total_votes")),
                ),
                "comments": _metric_int(metrics.get("comments_count")),
                "rank": rank,
                "signal_ranks": {"hot": rank},
            }
            collected += 1
            if collected >= limit:
                break

        page += 1

    return result


async def fetch_github_evidence(
    arxiv_ids: list[str],
    *,
    timeout: int = 30,
    retries: int = 3,
) -> dict[str, dict]:
    """Search GitHub for repositories linked to arXiv papers.

    For each arXiv ID, queries the GitHub Search API
    (``/search/repositories?q=<id>+in:description,readme&sort=stars&per_page=3``).

    Returns ``{arxiv_id: {stars, forks, last_push_at, repo_url}}``
    for IDs that have at least one matching repository.

    Uses ``GITHUB_TOKEN`` from the environment for higher rate limits
    when available.  Fail‑soft: individual search failures are skipped.
    """
    if not arxiv_ids:
        return {}

    gh_headers = _make_github_headers()

    async def _search_one(arxiv_id: str) -> tuple[str, dict | None]:
        q = f"{arxiv_id}+in:description,readme"
        url = (
            "https://api.github.com/search/repositories"
            f"?q={q}&sort=stars&per_page=3"
        )
        try:
            data = await _fetch_json_with_headers(
                url,
                headers=gh_headers,
                timeout=timeout,
                retries=retries,
                is_github=True,
            )
        except Exception as exc:
            logger.warning(
                "github search failed for %s: %s", arxiv_id, exc
            )
            return (arxiv_id, None)

        items = data.get("items", [])
        if not items or not isinstance(items, list):
            return (arxiv_id, None)

        top = items[0]
        if not isinstance(top, dict):
            return (arxiv_id, None)

        return (
            arxiv_id,
            {
                "stars": _metric_int(top.get("stargazers_count", 0)),
                "forks": _metric_int(top.get("forks_count", 0)),
                "last_push_at": top.get("pushed_at", ""),
                "repo_url": top.get("html_url", ""),
            },
        )

    # Limit GitHub concurrency to 5 to stay well under secondary rate limits
    sem = asyncio.Semaphore(5)

    async def _search_with_sem(arxiv_id: str) -> tuple[str, dict | None]:
        async with sem:
            return await _search_one(arxiv_id)

    tasks = [_search_with_sem(aid) for aid in arxiv_ids]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    result: dict[str, dict] = {}
    for item in gathered:
        if isinstance(item, Exception):
            logger.warning("github gather exception: %s", item)
            continue
        aid, repo_info = item
        if repo_info is not None:
            result[aid] = repo_info

    return result


async def fetch_local_engagement(
    arxiv_ids: list[str],
) -> dict[str, dict]:
    """Query local DB for community engagement signals.

    **STUB** -- always returns zeros.  The actual DB integration will be
    wired in when the repository connection is available.

    Returns ``{arxiv_id: {views, likes, saves}}``, all zeroed out.
    """
    result: dict[str, dict] = {}
    for arxiv_id in arxiv_ids:
        result[arxiv_id] = {"views": 0, "likes": 0, "saves": 0}
    return result


# ═══════════════════════════════════════════════════════════════════════
#  Aggregation helper
# ═══════════════════════════════════════════════════════════════════════


async def enrich_candidates_with_sources(
    arxiv_ids: list[str],
    *,
    mailto: str | None = None,
    concurrency: int = 4,
) -> dict[str, dict]:
    """Run all seven source adapters in parallel and merge results per arXiv ID.

    Returns::

        {arxiv_id: {
            "arxiv_meta":       {...} | None,
            "citations":         int | None,
            "semantic_scholar":  {...} | None,
            "huggingface":       {...} | None,
            "alphaxiv":          {...} | None,
            "github":            {...} | None,
            "local":             {...},
        }}

    Each adapter is fail‑soft, so missing sources appear as ``None``
    (except ``local`` which always returns a zeroed dict).
    """
    if not arxiv_ids:
        return {}

    # Fire all adapters concurrently
    arxiv_task = fetch_arxiv_batch(arxiv_ids)
    openalex_task = fetch_openalex_citations(arxiv_ids, mailto=mailto)
    ss_task = fetch_semantic_scholar_batch(arxiv_ids)
    hf_task = fetch_huggingface_papers(limit=max(200, len(arxiv_ids)))
    alphaxiv_task = fetch_alphaxiv_signals(limit=max(500, len(arxiv_ids)))
    github_task = fetch_github_evidence(arxiv_ids)
    local_task = fetch_local_engagement(arxiv_ids)

    gathered = await asyncio.gather(
        arxiv_task,
        openalex_task,
        ss_task,
        hf_task,
        alphaxiv_task,
        github_task,
        local_task,
        return_exceptions=True,
    )

    (
        arxiv_meta,
        openalex,
        ss,
        hf,
        alphaxiv,
        github,
        local,
    ) = gathered

    # Tolerate individual adapter failures
    if isinstance(arxiv_meta, Exception):
        logger.warning("arxiv adapter failed in enrich: %s", arxiv_meta)
        arxiv_meta = {}
    if isinstance(openalex, Exception):
        logger.warning("openalex adapter failed in enrich: %s", openalex)
        openalex = {}
    if isinstance(ss, Exception):
        logger.warning("semantic scholar adapter failed in enrich: %s", ss)
        ss = {}
    if isinstance(hf, Exception):
        logger.warning("huggingface adapter failed in enrich: %s", hf)
        hf = {}
    if isinstance(alphaxiv, Exception):
        logger.warning("alphaxiv adapter failed in enrich: %s", alphaxiv)
        alphaxiv = {}
    if isinstance(github, Exception):
        logger.warning("github adapter failed in enrich: %s", github)
        github = {}
    if isinstance(local, Exception):
        logger.warning("local adapter failed in enrich: %s", local)
        local = {}

    # Merge
    merged: dict[str, dict] = {}
    for aid in arxiv_ids:
        merged[aid] = {
            "arxiv_meta": arxiv_meta.get(aid) if isinstance(arxiv_meta, dict) else None,
            "citations": openalex.get(aid) if isinstance(openalex, dict) else None,
            "semantic_scholar": ss.get(aid) if isinstance(ss, dict) else None,
            "huggingface": hf.get(aid) if isinstance(hf, dict) else None,
            "alphaxiv": alphaxiv.get(aid) if isinstance(alphaxiv, dict) else None,
            "github": github.get(aid) if isinstance(github, dict) else None,
            "local": (
                local.get(aid, {"views": 0, "likes": 0, "saves": 0})
                if isinstance(local, dict)
                else {"views": 0, "likes": 0, "saves": 0}
            ),
        }

    return merged


# ═══════════════════════════════════════════════════════════════════════
#  Candidate collection (for standalone export script)
# ═══════════════════════════════════════════════════════════════════════


async def collect_candidates_from_sources(
    limit: int = 200,
    *,
    skip_sources: set[str] | None = None,
    timeout: int = 30,
    retries: int = 2,
) -> list[dict]:
    """Collect raw candidate dicts from live source adapters.

    1. Discover arXiv IDs from alphaXiv hot feed (fail-soft: falls back to demo seed list).
    2. Enrich them with all available source adapters.
    3. Transform into raw candidate dicts ready for the ranking engine.

    Args:
        limit: Maximum number of candidates to discover.
        skip_sources: Source names to skip (e.g. {"github", "openalex"}).
        timeout: HTTP timeout per request.
        retries: HTTP retry count per request.

    Returns:
        list[dict] with keys: arxiv_id, title, authors, categories, publication_date,
        raw_attention, raw_authority, raw_implementation, raw_local, source_evidence.
    """
    from datetime import datetime, timedelta, timezone

    skip = skip_sources or set()

    # 1. Discover arXiv IDs from alphaXiv hot feed
    arxiv_ids: list[str] = []
    if "alphaxiv" not in skip:
        try:
            alphaxiv_data = await fetch_alphaxiv_signals(limit=limit)
            arxiv_ids = list(alphaxiv_data.keys())[:limit]
        except Exception:
            logger.warning("collect_candidates: alphaXiv discovery failed, using demo seed")
    if not arxiv_ids:
        # Fallback to demo seed IDs (spread across recent months)
        import random as _random
        _rng = _random.Random(42)
        arxiv_ids = [f"{y:02d}{m:02d}.{_rng.randint(10000, 99999)}" for y, m in ((25, m) for m in range(1, 13))][:limit]

    # 2. Run source adapters concurrently (each is fail-soft). The cron is
    # allowed to run for hours, but one source must not hold the whole batch
    # forever when its upstream is unreachable.
    per_adapter_timeout = 2 * 60 * 60

    async def _safe_fetch(fn, *args, default=None, **kwargs):
        try:
            return await asyncio.wait_for(fn(*args, **kwargs), timeout=per_adapter_timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "collect_candidates: adapter %s exceeded %s seconds; using default",
                getattr(fn, "__name__", str(fn)),
                per_adapter_timeout,
            )
            return default
        except Exception:
            return default

    adapter_timeout = max(timeout, 30)
    adapter_retries = max(retries, 1)
    arxiv_meta, openalex, ss, hf, alphaxiv, github, local = await asyncio.gather(
        _safe_fetch(fetch_arxiv_batch, arxiv_ids, timeout=adapter_timeout, retries=adapter_retries, default={}) if "arxiv" not in skip else asyncio.sleep(0, result={}),
        _safe_fetch(fetch_openalex_citations, arxiv_ids, timeout=adapter_timeout, retries=adapter_retries, default={}) if "openalex" not in skip else asyncio.sleep(0, result={}),
        _safe_fetch(fetch_semantic_scholar_batch, arxiv_ids, timeout=adapter_timeout, retries=adapter_retries, default={}) if "semantic_scholar" not in skip else asyncio.sleep(0, result={}),
        _safe_fetch(fetch_huggingface_papers, limit=max(200, len(arxiv_ids)), timeout=adapter_timeout, retries=adapter_retries, default={}) if "huggingface" not in skip else asyncio.sleep(0, result={}),
        _safe_fetch(fetch_alphaxiv_signals, limit=max(500, len(arxiv_ids)), timeout=adapter_timeout, retries=adapter_retries, default={}) if "alphaxiv" not in skip else asyncio.sleep(0, result={}),
        _safe_fetch(fetch_github_evidence, arxiv_ids, timeout=adapter_timeout, retries=adapter_retries, default={}) if "github" not in skip else asyncio.sleep(0, result={}),
        _safe_fetch(fetch_local_engagement, arxiv_ids, default={}) if "local" not in skip else asyncio.sleep(0, result={}),
    )

    exported_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # 3. Transform into raw candidate dicts
    candidates: list[dict] = []
    for arxiv_id in arxiv_ids:
        raw_attention = 0.0
        raw_authority = 0.0
        raw_implementation = 0.0
        raw_local = 0.0
        source_evidence: list = []

        # arXiv metadata
        meta = arxiv_meta.get(arxiv_id, {}) if isinstance(arxiv_meta, dict) else {}
        pub_date = meta.get("published", "")
        title = meta.get("title", "")
        authors = meta.get("authors", [])
        categories = meta.get("categories", [])
        if not pub_date:
            # Generate a plausible recent date
            import random as _random2
            _rng2 = _random2.Random(hash(arxiv_id) % 2**31)
            days_ago = _rng2.uniform(0, 60)
            pub_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
            pub_date = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # OpenAlex citations
        oa_count = openalex.get(arxiv_id) if isinstance(openalex, dict) else None
        if isinstance(oa_count, (int, float)) and oa_count > 0:
            raw_authority += float(oa_count)
            source_evidence.append({
                "source": "OpenAlex", "signal": "citations",
                "raw_value": float(oa_count), "normalized_value": None, "fetched_at": exported_at,
            })

        # Semantic Scholar
        ss_data = ss.get(arxiv_id) if isinstance(ss, dict) else None
        if ss_data and isinstance(ss_data, dict):
            cc = ss_data.get("citationCount", 0)
            icc = ss_data.get("influentialCitationCount", 0)
            if isinstance(cc, (int, float)):
                raw_authority += float(cc) * 0.5
            if isinstance(icc, (int, float)):
                raw_authority += float(icc) * 1.5
            source_evidence.append({
                "source": "SemanticScholar", "signal": "citations",
                "raw_value": float(cc) if isinstance(cc, (int, float)) else 0,
                "normalized_value": None, "fetched_at": exported_at,
            })

        # HuggingFace
        hf_data = hf.get(arxiv_id) if isinstance(hf, dict) else None
        if hf_data and isinstance(hf_data, dict):
            upvotes = hf_data.get("upvotes", 0)
            if isinstance(upvotes, (int, float)):
                raw_attention += float(upvotes) * 10.0
            source_evidence.append({
                "source": "HuggingFace", "signal": "upvotes",
                "raw_value": float(upvotes) if isinstance(upvotes, (int, float)) else 0,
                "normalized_value": None, "fetched_at": exported_at,
            })

        # alphaXiv
        ax_data = alphaxiv.get(arxiv_id) if isinstance(alphaxiv, dict) else None
        if ax_data and isinstance(ax_data, dict):
            views = ax_data.get("views", 0)
            if isinstance(views, (int, float)):
                raw_attention += float(views) * 0.5
            source_evidence.append({
                "source": "alphaXiv", "signal": "views",
                "raw_value": float(views) if isinstance(views, (int, float)) else 0,
                "normalized_value": None, "fetched_at": exported_at,
            })

        # GitHub
        gh_data = github.get(arxiv_id) if isinstance(github, dict) else None
        if gh_data and isinstance(gh_data, dict):
            stars = gh_data.get("stars", 0)
            forks = gh_data.get("forks", 0)
            if isinstance(stars, (int, float)):
                raw_implementation += float(stars) * 2.0
            if isinstance(forks, (int, float)):
                raw_implementation += float(forks) * 5.0
            source_evidence.append({
                "source": "GitHub", "signal": "stars",
                "raw_value": float(stars) if isinstance(stars, (int, float)) else 0,
                "normalized_value": None, "fetched_at": exported_at,
            })

        # Local
        local_data = local.get(arxiv_id) if isinstance(local, dict) else {}
        if local_data:
            l_views = local_data.get("views", 0) if isinstance(local_data, dict) else 0
            l_likes = local_data.get("likes", 0) if isinstance(local_data, dict) else 0
            l_saves = local_data.get("saves", 0) if isinstance(local_data, dict) else 0
            raw_local += float(l_views) * 0.1 + float(l_likes) * 5.0 + float(l_saves) * 10.0

        candidates.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "categories": categories,
            "publication_date": pub_date,
            "raw_attention": round(raw_attention, 2),
            "raw_authority": round(raw_authority, 2),
            "raw_implementation": round(raw_implementation, 2),
            "raw_local": round(raw_local, 2),
            "source_evidence": source_evidence,
        })

    return candidates


# ═══════════════════════════════════════════════════════════════════════
#  Tiny util
# ═══════════════════════════════════════════════════════════════════════


def _make_qs(params: dict[str, str]) -> str:
    """Minimal query‑string builder (avoids importing urllib just for this)."""
    from urllib.parse import urlencode

    return urlencode(params)
