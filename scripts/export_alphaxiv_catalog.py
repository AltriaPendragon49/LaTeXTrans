from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import requests
import sys
import time
from typing import Any, Sequence
from urllib.parse import quote, unquote, urlencode, urlparse
import xml.etree.ElementTree as ET

# ── Import shared utilities from the ranking package ───────────────
# Keep the legacy export script thin by sharing fetch/normalize/category helpers
# with the new ranking system.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.services.ranking.utils import (  # noqa: E402
    ALPHAXIV_API_BASE,
    ARXIV_API_URL,
    ARXIV_ID_PATTERN,
    ARXIV_ID_PREFIX_PATTERN,
    BROAD_TOPIC_TO_MAJOR_CATEGORY,
    OPENALEX_API_URL,
    TITLE_KEY_PATTERN,
    USER_AGENT,
    _parse_datetime,
    _pick_openalex_match,
    _title_key,
    fetch_json,
    fetch_text,
    infer_submission_date_from_arxiv_id,
    major_category_from_topic,
    normalize_arxiv_id,
)


SITEMAP_INDEX_URL = "https://www.alphaxiv.org/sitemaps/sitemap-index.xml"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
OPENSEARCH_NAMESPACE = "http://a9.com/-/spec/opensearch/1.1/"
BACKEND_ARXIV_ID_DIR = Path(__file__).resolve().parent.parent / "backend" / "arxiv_id"
MODE_OUTPUT_DIRS = {
    "hot-top-n": "all_hot",
    "hot-new-24h": "daily_hot",
    "new-24h": "daily_new",
    "core-pool": "core_pool",
    "sitemap-all-ids": "all_hot",
}
DEFAULT_HOT_INTERVAL = "All time"
RECENT_HOT_INTERVAL = "3 Days"
DEFAULT_CORE_POOL_SIZE = 4000
DEFAULT_CORE_POOL_LOOKBACK_YEARS = 9
DEFAULT_CORE_POOL_RECENT_CUTOFF_DAYS = 90
DEFAULT_CORE_SIGNAL_LIMIT = 4000
DEFAULT_CORE_MIN_CATEGORY_FLOOR = 50
DEFAULT_CORE_CITATION_SHORTLIST_BUFFER = 50
DEFAULT_OPENALEX_WORKERS = 4
DEFAULT_OPENALEX_PER_QUERY = 5
DEFAULT_OPENALEX_FIELD_PAGE_SIZE = 100
DEFAULT_OPENALEX_FIELD_CANDIDATE_LIMIT = 800
CORE_POOL_SIGNAL_SORTS = ("Views", "Likes", "Comments")
OPENALEX_FIELD_ID_BY_CATEGORY = {
    "cs": 17,
    "math": 26,
    "physics": 31,
    "eess": 22,
    "econ": 20,
    "q-bio": 13,
}


@dataclass(frozen=True)
class PaperRecord:
    arxiv_id: str
    title: str | None
    source_mode: str
    source_rank: int | None
    publication_date: str | None
    updated_at: str | None
    source_url: str
    exported_at: str
    source_family: str = ""
    translation_priority: int = 0
    skip_retranslation_if_translated: bool = True
    primary_category: str | None = None
    score: float | None = None
    score_breakdown: dict[str, float] | None = None
    selection_bucket: str | None = None
    selected_reason: str | None = None
    citation_count: int | None = None
    views_count: int | None = None
    vote_count: int | None = None
    signal_ranks: dict[str, int] | None = None


@dataclass
class CorePoolCandidate:
    arxiv_id: str
    title: str | None
    publication_date: str | None
    updated_at: str | None
    source_url: str
    primary_category: str | None
    signal_ranks: dict[str, int]
    views_count: int = 0
    vote_count: int = 0
    citation_count: int | None = None
    topics: tuple[str, ...] = ()


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.og_title: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs if key and value is not None}
        if tag.lower() == "meta":
            property_name = attrs_dict.get("property", "").lower()
            name = attrs_dict.get("name", "").lower()
            if property_name == "og:title" or name == "og:title":
                content = attrs_dict.get("content", "").strip()
                if content:
                    self.og_title = content
        elif tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    @property
    def title_text(self) -> str:
        return "".join(self._title_parts).strip()


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_loc_values(xml_text: str) -> list[str]:
    try:
        root = ET.fromstring(xml_text)
        return [
            element.text.strip()
            for element in root.findall(f".//{{{SITEMAP_NAMESPACE}}}loc")
            if element.text and element.text.strip()
        ]
    except ET.ParseError:
        return [
            unescape(match.strip())
            for match in re.findall(r"<loc>\s*(.*?)\s*</loc>", xml_text, flags=re.DOTALL)
            if match.strip()
        ]


def parse_sitemap_index(xml_text: str) -> list[str]:
    paper_sitemaps: list[str] = []
    for loc in _parse_loc_values(xml_text):
        if "/sitemaps/papers/" in loc:
            paper_sitemaps.append(loc)
    return paper_sitemaps


def is_primary_paper_url(url: str) -> bool:
    path = urlparse(url).path.rstrip("/")
    parts = path.split("/")
    return len(parts) == 3 and parts[1] == "abs" and bool(parts[2])


def parse_paper_sitemap(xml_text: str) -> list[str]:
    return [loc for loc in _parse_loc_values(xml_text) if is_primary_paper_url(loc)]


def is_valid_arxiv_id(raw_value: str | None) -> bool:
    return normalize_arxiv_id(raw_value) is not None


def extract_arxiv_id(url: str) -> str:
    normalized = normalize_arxiv_id(urlparse(url).path.rsplit("/abs/", 1)[-1])
    if normalized is None:
        raise ValueError(f"Unsupported alphaXiv paper URL: {url}")
    return normalized


def _normalize_title(raw_title: str) -> str:
    cleaned = " ".join(raw_title.split()).strip()
    if cleaned.endswith("| alphaXiv"):
        cleaned = cleaned[: -len("| alphaXiv")].strip()
    return cleaned


def extract_title_from_html(html_text: str) -> str:
    parser = _TitleParser()
    parser.feed(html_text)
    parser.close()

    for candidate in (parser.og_title, parser.title_text):
        if candidate:
            normalized = _normalize_title(candidate)
            if normalized:
                return normalized

    raise ValueError("Unable to find title in alphaXiv paper HTML")


def fetch_paper_record(url: str, *, timeout: int = 20, retries: int = 3) -> PaperRecord:
    html_text = fetch_text(url, timeout=timeout, retries=retries)
    exported_at = utc_now_iso()
    return PaperRecord(
        arxiv_id=extract_arxiv_id(url),
        title=extract_title_from_html(html_text),
        source_mode="sitemap-all-ids",
        source_rank=None,
        publication_date=None,
        updated_at=None,
        source_url=url,
        exported_at=exported_at,
        source_family="legacy",
        translation_priority=99,
    )


def collect_paper_urls(index_url: str, *, timeout: int = 20, retries: int = 3) -> list[str]:
    index_xml = fetch_text(index_url, timeout=timeout, retries=retries)
    sitemap_urls = parse_sitemap_index(index_xml)
    if not sitemap_urls:
        raise RuntimeError(f"No paper sitemap shards found in {index_url}")

    paper_urls: dict[str, None] = {}
    for idx, sitemap_url in enumerate(sitemap_urls, start=1):
        sitemap_xml = fetch_text(sitemap_url, timeout=timeout, retries=retries)
        shard_urls = parse_paper_sitemap(sitemap_xml)
        for paper_url in shard_urls:
            paper_urls.setdefault(paper_url, None)
        log(f"[sitemaps] {idx}/{len(sitemap_urls)} loaded: {sitemap_url} ({len(shard_urls)} papers)")

    return sorted(paper_urls.keys())


def collect_paper_ids(index_url: str, *, timeout: int = 20, retries: int = 3) -> list[str]:
    return [extract_arxiv_id(url) for url in collect_paper_urls(index_url, timeout=timeout, retries=retries)]


def collect_paper_records(
    paper_urls: Sequence[str],
    *,
    workers: int = 8,
    timeout: int = 20,
    retries: int = 3,
) -> tuple[list[PaperRecord], list[str]]:
    records: list[PaperRecord] = []
    failures: list[str] = []
    total = len(paper_urls)
    if total == 0:
        return records, failures

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_to_url = {
            executor.submit(fetch_paper_record, url, timeout=timeout, retries=retries): url
            for url in paper_urls
        }
        for index, future in enumerate(as_completed(future_to_url), start=1):
            paper_url = future_to_url[future]
            try:
                records.append(future.result())
            except Exception as exc:
                failures.append(f"{paper_url} :: {exc}")
                if len(failures) <= 10:
                    log(f"[paper-error] {paper_url} -> {exc}")

            if index % 100 == 0 or index == total:
                log(f"[papers] processed {index}/{total} pages")

    records.sort(key=lambda record: record.arxiv_id)
    return records, failures


def source_family_for_mode(source_mode: str) -> str:
    if source_mode == "core-pool":
        return "core"
    if source_mode == "sitemap-all-ids":
        return "legacy"
    return "hot" if source_mode.startswith("hot") else "new"


def translation_priority_for_mode(source_mode: str) -> int:
    source_family = source_family_for_mode(source_mode)
    if source_family == "hot":
        return 0
    if source_family == "new":
        return 1
    if source_family == "core":
        return 2
    return 99


def _candidate_publication_date(paper: dict[str, Any]) -> str | None:
    return paper.get("first_publication_date") or paper.get("publication_date")


def core_pool_lookback_start(now: datetime, lookback_years: int) -> datetime:
    start_year = max(1900, now.year - lookback_years)
    return datetime(start_year, 1, 1, tzinfo=UTC)


def core_pool_publication_date_for_openalex_work(arxiv_id: str, work: dict[str, Any]) -> str | None:
    inferred = infer_submission_date_from_arxiv_id(arxiv_id)
    if inferred:
        return inferred

    publication_date = work.get("publication_date")
    if isinstance(publication_date, str) and publication_date:
        return f"{publication_date}T00:00:00Z"
    return None


def _core_candidate_publication_date(arxiv_id: str, paper: dict[str, Any]) -> str | None:
    inferred = infer_submission_date_from_arxiv_id(arxiv_id)
    if inferred:
        return inferred
    return _candidate_publication_date(paper)


def _normalize_topic_strings(topics: Any) -> tuple[str, ...]:
    if not isinstance(topics, list):
        return ()
    values: list[str] = []
    for topic in topics:
        if isinstance(topic, str):
            cleaned = topic.strip()
            if cleaned:
                values.append(cleaned)
    return tuple(values)


def infer_primary_category(topics: Sequence[str]) -> str | None:
    for topic in topics:
        if " " in topic:
            continue
        category = major_category_from_topic(topic)
        if category:
            return category

    for topic in topics:
        category = major_category_from_topic(topic)
        if category:
            return category
    return None


def _metric_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def make_alphaxiv_record(
    paper: dict[str, Any],
    *,
    source_mode: str,
    source_rank: int,
    exported_at: str,
) -> PaperRecord | None:
    arxiv_id = normalize_arxiv_id(paper.get("universal_paper_id"))
    if arxiv_id is None:
        return None

    return PaperRecord(
        arxiv_id=arxiv_id,
        title=paper.get("title"),
        source_mode=source_mode,
        source_rank=source_rank,
        publication_date=paper.get("publication_date"),
        updated_at=paper.get("updated_at"),
        source_url=f"https://www.alphaxiv.org/abs/{arxiv_id}",
        exported_at=exported_at,
        source_family=source_family_for_mode(source_mode),
        translation_priority=translation_priority_for_mode(source_mode),
    )


def upsert_core_pool_candidate(
    candidates: dict[str, CorePoolCandidate],
    paper: dict[str, Any],
    *,
    signal_name: str,
    signal_rank: int,
) -> None:
    arxiv_id = normalize_arxiv_id(paper.get("universal_paper_id"))
    if arxiv_id is None:
        return

    topics = _normalize_topic_strings(paper.get("topics"))
    existing = candidates.get(arxiv_id)
    if existing is None:
        existing = CorePoolCandidate(
            arxiv_id=arxiv_id,
            title=paper.get("title"),
            publication_date=_core_candidate_publication_date(arxiv_id, paper),
            updated_at=paper.get("updated_at"),
            source_url=f"https://www.alphaxiv.org/abs/{arxiv_id}",
            primary_category=infer_primary_category(topics),
            signal_ranks={},
            topics=topics,
        )
        candidates[arxiv_id] = existing

    if signal_name not in existing.signal_ranks:
        existing.signal_ranks[signal_name] = signal_rank

    metrics = paper.get("metrics") or {}
    visits = metrics.get("visits_count") or {}
    existing.views_count = max(existing.views_count, _metric_value(visits.get("all")))
    existing.vote_count = max(
        existing.vote_count,
        _metric_value(metrics.get("public_total_votes")) or _metric_value(metrics.get("total_votes")),
    )
    if not existing.title and paper.get("title"):
        existing.title = paper.get("title")
    if not existing.publication_date:
        existing.publication_date = _core_candidate_publication_date(arxiv_id, paper)
    if not existing.updated_at and paper.get("updated_at"):
        existing.updated_at = paper.get("updated_at")
    if existing.primary_category is None:
        existing.primary_category = infer_primary_category(topics)
    if not existing.topics and topics:
        existing.topics = topics


def normalize_alphaxiv_feed_records(
    papers: Sequence[dict[str, Any]],
    *,
    source_mode: str,
    exported_at: str,
) -> list[PaperRecord]:
    seen_ids: set[str] = set()
    records: list[PaperRecord] = []
    next_rank = 1
    for paper in papers:
        record = make_alphaxiv_record(
            paper,
            source_mode=source_mode,
            source_rank=next_rank,
            exported_at=exported_at,
        )
        if record is None or record.arxiv_id in seen_ids:
            continue
        seen_ids.add(record.arxiv_id)
        records.append(record)
        next_rank += 1
    return records


def parse_arxiv_feed_entries(
    xml_text: str,
    *,
    source_mode: str,
    exported_at: str,
    start_rank: int = 1,
) -> list[PaperRecord]:
    root = ET.fromstring(xml_text)
    ns = {"atom": ATOM_NAMESPACE}
    records: list[PaperRecord] = []
    next_rank = start_rank
    seen_ids: set[str] = set()
    for entry in root.findall("atom:entry", ns):
        raw_id = entry.findtext("atom:id", default="", namespaces=ns)
        arxiv_id = normalize_arxiv_id(raw_id.rsplit("/abs/", 1)[-1])
        if arxiv_id is None or arxiv_id in seen_ids:
            continue
        seen_ids.add(arxiv_id)
        title = entry.findtext("atom:title", default="", namespaces=ns)
        published = entry.findtext("atom:published", default=None, namespaces=ns)
        updated = entry.findtext("atom:updated", default=None, namespaces=ns)
        records.append(
            PaperRecord(
                arxiv_id=arxiv_id,
                title=" ".join(title.split()) if title else None,
                source_mode=source_mode,
                source_rank=next_rank,
                publication_date=published,
                updated_at=updated,
                source_url=f"https://arxiv.org/abs/{arxiv_id}",
                exported_at=exported_at,
                source_family=source_family_for_mode(source_mode),
                translation_priority=translation_priority_for_mode(source_mode),
            )
        )
        next_rank += 1
    return records


def _fetch_alphaxiv_feed_page(
    *,
    page_num: int,
    page_size: int,
    sort: str,
    interval: str,
    timeout: int,
    retries: int,
) -> list[dict[str, Any]]:
    url = (
        f"{ALPHAXIV_API_BASE}/papers/v3/feed?"
        f"pageNum={page_num}&pageSize={page_size}&sort={quote(sort)}&interval={quote(interval)}"
    )
    return fetch_json(url, timeout=timeout, retries=retries).get("papers", [])


def collect_hot_top_n_records(
    *,
    limit: int,
    exported_at: str,
    interval: str = DEFAULT_HOT_INTERVAL,
    page_size: int = 200,
    timeout: int = 20,
    retries: int = 3,
) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    page = 1
    while len(records) < limit:
        papers = _fetch_alphaxiv_feed_page(
            page_num=page,
            page_size=page_size,
            sort="Hot",
            interval=interval,
            timeout=timeout,
            retries=retries,
        )
        if not papers:
            break
        normalized = normalize_alphaxiv_feed_records(
            papers,
            source_mode="hot-top-n",
            exported_at=exported_at,
        )
        page_added = 0
        for record in normalized:
            if record.arxiv_id in seen_ids:
                continue
            seen_ids.add(record.arxiv_id)
            records.append(
                PaperRecord(
                    **{
                        **asdict(record),
                        "source_rank": len(records) + 1,
                    }
                )
            )
            page_added += 1
            if len(records) >= limit:
                break
        log(f"[hot-top-n] page={page} rows={len(papers)} added={page_added} total={len(records)}")
        page += 1
    return records[:limit]


def collect_hot_new_records(
    *,
    lookback_hours: int,
    exported_at: str,
    interval: str = RECENT_HOT_INTERVAL,
    page_size: int = 200,
    timeout: int = 20,
    retries: int = 3,
    stop_after_empty_pages: int = 3,
) -> list[PaperRecord]:
    threshold = datetime.now(UTC) - timedelta(hours=lookback_hours)
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    page = 1
    empty_pages = 0
    while True:
        papers = _fetch_alphaxiv_feed_page(
            page_num=page,
            page_size=page_size,
            sort="Hot",
            interval=interval,
            timeout=timeout,
            retries=retries,
        )
        if not papers:
            break

        page_recent = 0
        page_added = 0
        normalized = normalize_alphaxiv_feed_records(
            papers,
            source_mode="hot-new-24h",
            exported_at=exported_at,
        )
        for record in normalized:
            publication_dt = _parse_datetime(record.publication_date)
            if publication_dt is None or publication_dt < threshold:
                continue
            page_recent += 1
            if record.arxiv_id in seen_ids:
                continue
            seen_ids.add(record.arxiv_id)
            records.append(
                PaperRecord(
                    **{
                        **asdict(record),
                        "source_rank": len(records) + 1,
                    }
                )
            )
            page_added += 1

        log(
            f"[hot-new-24h] page={page} rows={len(papers)} recent_rows={page_recent} "
            f"added={page_added} total={len(records)}"
        )

        if page_recent == 0:
            empty_pages += 1
            if empty_pages >= stop_after_empty_pages:
                break
        else:
            empty_pages = 0

        page += 1
    return records


def collect_new_24h_records(
    *,
    lookback_hours: int,
    exported_at: str,
    page_size: int = 500,
    timeout: int = 30,
    retries: int = 3,
) -> list[PaperRecord]:
    now = datetime.now(UTC)
    threshold = now - timedelta(hours=lookback_hours)
    start_value = threshold.strftime("%Y%m%d%H%M")
    end_value = now.strftime("%Y%m%d%H%M")
    start_index = 0
    records: list[PaperRecord] = []
    while True:
        query = (
            f"{ARXIV_API_URL}?search_query=submittedDate:[{start_value} TO {end_value}]"
            f"&start={start_index}&max_results={page_size}&sortBy=submittedDate&sortOrder=descending"
        )
        xml_text = fetch_text(query, timeout=timeout, retries=retries)
        batch = parse_arxiv_feed_entries(
            xml_text,
            source_mode="new-24h",
            exported_at=exported_at,
            start_rank=len(records) + 1,
        )
        records.extend(batch)
        log(f"[new-24h] start={start_index} rows={len(batch)} total={len(records)}")
        if len(batch) < page_size:
            break
        start_index += page_size
    return records


def collect_core_pool_candidates(
    *,
    per_signal_limit: int,
    interval: str,
    page_size: int,
    timeout: int,
    retries: int,
) -> list[CorePoolCandidate]:
    candidates: dict[str, CorePoolCandidate] = {}
    for signal_name in CORE_POOL_SIGNAL_SORTS:
        signal_key = signal_name.lower()
        seen_ids: set[str] = set()
        page = 1
        signal_rank = 1
        while len(seen_ids) < per_signal_limit:
            papers = _fetch_alphaxiv_feed_page(
                page_num=page,
                page_size=page_size,
                sort=signal_name,
                interval=interval,
                timeout=timeout,
                retries=retries,
            )
            if not papers:
                break

            page_added = 0
            for paper in papers:
                arxiv_id = normalize_arxiv_id(paper.get("universal_paper_id"))
                if arxiv_id is None or arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)
                upsert_core_pool_candidate(
                    candidates,
                    paper,
                    signal_name=signal_key,
                    signal_rank=signal_rank,
                )
                signal_rank += 1
                page_added += 1
                if len(seen_ids) >= per_signal_limit:
                    break

            log(
                f"[core-pool:{signal_key}] page={page} rows={len(papers)} "
                f"added={page_added} unique_signal={len(seen_ids)} total_candidates={len(candidates)}"
            )
            if page_added == 0 and len(papers) < page_size:
                break
            page += 1
    return list(candidates.values())


def _candidate_is_recent(
    candidate: CorePoolCandidate,
    *,
    recent_cutoff_days: int,
    now: datetime,
) -> bool:
    publication_dt = _parse_datetime(candidate.publication_date)
    if publication_dt is None:
        return False
    return publication_dt >= (now - timedelta(days=recent_cutoff_days))


def allocate_category_quotas(
    baseline_counts: dict[str, int],
    available_counts: dict[str, int],
    *,
    target_size: int,
    min_floor: int,
) -> dict[str, int]:
    eligible = {category: count for category, count in available_counts.items() if count > 0}
    if not eligible or target_size <= 0:
        return {}

    capped_target = min(target_size, sum(eligible.values()))
    floor_candidates = [
        category
        for category, count in eligible.items()
        if count >= min_floor
    ]
    floor_candidates.sort(
        key=lambda category: (
            -baseline_counts.get(category, eligible[category]),
            -eligible[category],
            category,
        )
    )

    included_floor_categories: list[str] = []
    for category in floor_candidates:
        if (len(included_floor_categories) + 1) * min_floor > capped_target:
            break
        included_floor_categories.append(category)

    quotas = {category: 0 for category in eligible}
    for category in included_floor_categories:
        quotas[category] = min_floor

    remaining = capped_target - sum(quotas.values())
    if remaining <= 0:
        return {category: quota for category, quota in quotas.items() if quota > 0}

    weights = {
        category: max(baseline_counts.get(category, 0), eligible[category])
        for category in eligible
    }

    while remaining > 0:
        expandable = [
            category
            for category, available in eligible.items()
            if quotas[category] < available
        ]
        if not expandable:
            break

        weight_total = sum(weights.get(category, 0) for category in expandable)
        if weight_total <= 0:
            weight_total = len(expandable)
            fractional_targets = {category: 1.0 for category in expandable}
        else:
            fractional_targets = {
                category: remaining * (weights.get(category, 0) / weight_total)
                for category in expandable
            }

        progressed = False
        for category in expandable:
            extra = min(
                eligible[category] - quotas[category],
                int(fractional_targets[category]),
            )
            if extra <= 0:
                continue
            quotas[category] += extra
            remaining -= extra
            progressed = True
            if remaining == 0:
                break

        if remaining == 0:
            break

        if not progressed:
            for category in sorted(
                expandable,
                key=lambda item: (
                    -(fractional_targets[item] - math.floor(fractional_targets[item])),
                    -weights.get(item, 0),
                    item,
                ),
            ):
                if quotas[category] >= eligible[category]:
                    continue
                quotas[category] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break

        if not progressed:
            break

    return {category: quota for category, quota in quotas.items() if quota > 0}


def _score_from_rank(rank: int | None, max_rank: int) -> float:
    if rank is None or max_rank <= 0:
        return 0.0
    return max(0.0, 1.0 - ((rank - 1) / max_rank))


def _score_from_count(value: int | None, max_value: int) -> float:
    if value is None or value <= 0 or max_value <= 0:
        return 0.0
    return math.log1p(value) / math.log1p(max_value)


def _candidate_score_breakdown(
    candidate: CorePoolCandidate,
    *,
    signal_max_ranks: dict[str, int],
    max_views: int,
    max_votes: int,
    max_citations: int,
    now: datetime,
) -> dict[str, float]:
    age_days = 0.0
    publication_dt = _parse_datetime(candidate.publication_date)
    if publication_dt is not None:
        age_days = max((now - publication_dt).days, 0)

    return {
        "views_rank": round(0.18 * _score_from_rank(candidate.signal_ranks.get("views"), signal_max_ranks.get("views", 0)), 6),
        "likes_rank": round(0.15 * _score_from_rank(candidate.signal_ranks.get("likes"), signal_max_ranks.get("likes", 0)), 6),
        "comments_rank": round(0.12 * _score_from_rank(candidate.signal_ranks.get("comments"), signal_max_ranks.get("comments", 0)), 6),
        "views": round(0.18 * _score_from_count(candidate.views_count, max_views), 6),
        "votes": round(0.12 * _score_from_count(candidate.vote_count, max_votes), 6),
        "citations": round(0.20 * _score_from_count(candidate.citation_count, max_citations), 6),
        "maturity": round(0.05 * min(age_days / 365.0, 4.0) / 4.0, 6),
    }


def build_core_pool_records(
    candidates: Sequence[CorePoolCandidate],
    *,
    baseline_counts: dict[str, int],
    exported_at: str,
    target_size: int,
    min_floor: int,
    recent_cutoff_days: int,
    now: datetime | None = None,
) -> list[PaperRecord]:
    active_now = now or datetime.now(UTC)
    eligible = [
        candidate
        for candidate in candidates
        if candidate.primary_category
        and not _candidate_is_recent(candidate, recent_cutoff_days=recent_cutoff_days, now=active_now)
    ]
    if not eligible:
        return []

    available_counts: dict[str, int] = defaultdict(int)
    for candidate in eligible:
        available_counts[candidate.primary_category or "unknown"] += 1

    quotas = allocate_category_quotas(
        baseline_counts=baseline_counts,
        available_counts=dict(available_counts),
        target_size=target_size,
        min_floor=min_floor,
    )
    if not quotas:
        return []

    signal_max_ranks = {
        signal_name: max(
            (candidate.signal_ranks.get(signal_name, 0) for candidate in eligible),
            default=0,
        )
        for signal_name in ("views", "likes", "comments")
    }
    max_views = max((candidate.views_count for candidate in eligible), default=0)
    max_votes = max((candidate.vote_count for candidate in eligible), default=0)
    max_citations = max((candidate.citation_count or 0 for candidate in eligible), default=0)

    scored_candidates: list[tuple[CorePoolCandidate, float, dict[str, float]]] = []
    for candidate in eligible:
        breakdown = _candidate_score_breakdown(
            candidate,
            signal_max_ranks=signal_max_ranks,
            max_views=max_views,
            max_votes=max_votes,
            max_citations=max_citations,
            now=active_now,
        )
        scored_candidates.append((candidate, round(sum(breakdown.values()), 6), breakdown))

    grouped: dict[str, list[tuple[CorePoolCandidate, float, dict[str, float]]]] = defaultdict(list)
    for item in scored_candidates:
        grouped[item[0].primary_category or "unknown"].append(item)
    for category in grouped:
        grouped[category].sort(
            key=lambda item: (
                -item[1],
                -(item[0].citation_count or 0),
                -item[0].views_count,
                item[0].arxiv_id,
            )
        )

    selected_items: list[tuple[CorePoolCandidate, float, dict[str, float], str, str]] = []
    selected_ids: set[str] = set()
    category_selected_counts: dict[str, int] = defaultdict(int)
    year_selected_counts: dict[int, int] = defaultdict(int)

    year_groups: dict[int, list[tuple[CorePoolCandidate, float, dict[str, float]]]] = defaultdict(list)
    for item in scored_candidates:
        publication_dt = _parse_datetime(item[0].publication_date)
        if publication_dt is None:
            continue
        year_groups[publication_dt.year].append(item)
    for year in year_groups:
        year_groups[year].sort(
            key=lambda item: (
                -item[1],
                -(item[0].citation_count or 0),
                -item[0].views_count,
                item[0].arxiv_id,
            )
        )

    years = sorted(year_groups)
    year_floor = 0
    year_cap = target_size
    if years:
        year_floor = max(5, min(125, target_size // max(1, len(years) * 5)))
        year_cap = max(year_floor, math.ceil(target_size / max(3, min(len(years), 4))))

    for category, quota in quotas.items():
        anchor_quota = min(quota, max(1, quota // 5))
        citation_ranked = sorted(
            grouped.get(category, []),
            key=lambda item: (
                -(item[0].citation_count or 0),
                -item[1],
                -item[0].views_count,
                item[0].arxiv_id,
            ),
        )
        for item in citation_ranked:
            if category_selected_counts[category] >= anchor_quota:
                break
            if item[0].arxiv_id in selected_ids:
                continue
            publication_dt = _parse_datetime(item[0].publication_date)
            publication_year = publication_dt.year if publication_dt is not None else None
            selected_items.append(
                (
                    item[0],
                    item[1],
                    item[2],
                    f"citation-anchor:{category}",
                    f"selected as one of the most cited {category} anchor papers",
                )
            )
            selected_ids.add(item[0].arxiv_id)
            category_selected_counts[category] += 1
            if publication_year is not None:
                year_selected_counts[publication_year] += 1

    for year in years:
        needed = min(year_floor, len(year_groups[year]))
        for item in year_groups[year]:
            category = item[0].primary_category or "unknown"
            if year_selected_counts[year] >= needed:
                break
            if category_selected_counts[category] >= quotas.get(category, 0):
                continue
            if item[0].arxiv_id in selected_ids:
                continue
            selected_items.append(
                (
                    item[0],
                    item[1],
                    item[2],
                    f"quota:{category}",
                    f"selected to maintain year coverage within the {category} quota",
                )
            )
            selected_ids.add(item[0].arxiv_id)
            category_selected_counts[category] += 1
            year_selected_counts[year] += 1

    if len(selected_items) < min(target_size, len(eligible)):
        all_ranked = sorted(
            scored_candidates,
            key=lambda item: (
                -item[1],
                -(item[0].citation_count or 0),
                -item[0].views_count,
                item[0].arxiv_id,
            ),
        )
        for item in all_ranked:
            if item[0].arxiv_id in selected_ids:
                continue
            category = item[0].primary_category or "unknown"
            publication_dt = _parse_datetime(item[0].publication_date)
            publication_year = publication_dt.year if publication_dt is not None else None
            if category_selected_counts[category] >= quotas.get(category, 0):
                continue
            if publication_year is not None and year_selected_counts[publication_year] >= year_cap:
                continue
            selected_items.append(
                (
                    item[0],
                    item[1],
                    item[2],
                    f"quota:{category}",
                    f"selected for {category} evergreen quota with blended long-horizon score",
                )
            )
            selected_ids.add(item[0].arxiv_id)
            category_selected_counts[category] += 1
            if publication_year is not None:
                year_selected_counts[publication_year] += 1
            if len(selected_items) >= min(target_size, len(eligible)):
                break

    if len(selected_items) < min(target_size, len(eligible)):
        all_ranked = sorted(
            scored_candidates,
            key=lambda item: (
                -item[1],
                -(item[0].citation_count or 0),
                -item[0].views_count,
                item[0].arxiv_id,
            ),
        )
        for item in all_ranked:
            if item[0].arxiv_id in selected_ids:
                continue
            category = item[0].primary_category or "unknown"
            if category_selected_counts[category] >= quotas.get(category, 0):
                continue
            selected_items.append(
                (
                    item[0],
                    item[1],
                    item[2],
                    f"quota:{category}",
                    f"selected for {category} evergreen quota with blended long-horizon score",
                )
            )
            selected_ids.add(item[0].arxiv_id)
            category_selected_counts[category] += 1
            if len(selected_items) >= min(target_size, len(eligible)):
                break

    selected_items.sort(
        key=lambda item: (
            -item[1],
            0 if item[3].startswith("citation-anchor:") else 1,
            -(item[0].citation_count or 0),
            -item[0].views_count,
            item[0].arxiv_id,
        )
    )

    records: list[PaperRecord] = []
    for rank, (candidate, score, breakdown, selection_bucket, selected_reason) in enumerate(selected_items[:target_size], start=1):
        category = candidate.primary_category
        records.append(
            PaperRecord(
                arxiv_id=candidate.arxiv_id,
                title=candidate.title,
                source_mode="core-pool",
                source_rank=rank,
                publication_date=candidate.publication_date,
                updated_at=candidate.updated_at,
                source_url=candidate.source_url,
                exported_at=exported_at,
                source_family=source_family_for_mode("core-pool"),
                translation_priority=translation_priority_for_mode("core-pool"),
                primary_category=category,
                score=score,
                score_breakdown=breakdown,
                selection_bucket=selection_bucket,
                selected_reason=selected_reason,
                citation_count=candidate.citation_count,
                views_count=candidate.views_count,
                vote_count=candidate.vote_count,
                signal_ranks=dict(candidate.signal_ranks),
            )
        )
    return records


def load_json_cache(cache_path: Path | None) -> dict[str, Any]:
    if cache_path is None or not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_json_cache(cache_path: Path | None, payload: dict[str, Any]) -> None:
    if cache_path is None:
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch_openalex_citation_count(
    candidate: CorePoolCandidate,
    *,
    timeout: int,
    retries: int,
    mailto: str | None,
    cache: dict[str, Any],
) -> int | None:
    if not candidate.title:
        return None

    cache_key = candidate.arxiv_id
    if cache_key in cache:
        cached = cache[cache_key]
        if isinstance(cached, dict):
            value = cached.get("citation_count")
            return int(value) if isinstance(value, int) else None

    params = {
        "search": candidate.title,
        "per_page": str(DEFAULT_OPENALEX_PER_QUERY),
    }
    if mailto:
        params["mailto"] = mailto

    data = fetch_json(
        f"{OPENALEX_API_URL}?{urlencode(params)}",
        timeout=timeout,
        retries=retries,
    )
    publication_year = None
    publication_dt = _parse_datetime(candidate.publication_date)
    if publication_dt is not None:
        publication_year = publication_dt.year

    match = _pick_openalex_match(
        data.get("results", []),
        title=candidate.title,
        arxiv_id=candidate.arxiv_id,
        publication_year=publication_year,
    )
    citation_count = None
    if match is not None:
        raw_count = match.get("cited_by_count")
        if isinstance(raw_count, int):
            citation_count = raw_count

    cache[cache_key] = {
        "citation_count": citation_count,
        "title_key": _title_key(candidate.title),
    }
    return citation_count


def enrich_candidates_with_openalex(
    candidates: Sequence[CorePoolCandidate],
    *,
    shortlist_size: int,
    timeout: int,
    retries: int,
    mailto: str | None,
    cache_path: Path | None,
    workers: int,
) -> None:
    if shortlist_size <= 0:
        return

    cache = load_json_cache(cache_path)
    ranked_candidates = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.views_count,
            -candidate.vote_count,
            candidate.signal_ranks.get("views", sys.maxsize),
            candidate.signal_ranks.get("likes", sys.maxsize),
            candidate.signal_ranks.get("comments", sys.maxsize),
            candidate.arxiv_id,
        ),
    )[:shortlist_size]

    pending = [candidate for candidate in ranked_candidates if candidate.arxiv_id not in cache]
    if pending:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            future_to_candidate = {
                executor.submit(
                    fetch_openalex_citation_count,
                    candidate,
                    timeout=timeout,
                    retries=retries,
                    mailto=mailto,
                    cache=cache,
                ): candidate
                for candidate in pending
            }
            for index, future in enumerate(as_completed(future_to_candidate), start=1):
                candidate = future_to_candidate[future]
                try:
                    candidate.citation_count = future.result()
                except Exception as exc:
                    log(f"[core-pool:openalex] {candidate.arxiv_id} failed: {exc}")
                    cache[candidate.arxiv_id] = {"citation_count": None, "title_key": _title_key(candidate.title)}
                if index % 100 == 0 or index == len(pending):
                    log(f"[core-pool:openalex] enriched {index}/{len(pending)} candidates")

    for candidate in ranked_candidates:
        cached = cache.get(candidate.arxiv_id)
        if isinstance(cached, dict):
            value = cached.get("citation_count")
            candidate.citation_count = int(value) if isinstance(value, int) else None

    save_json_cache(cache_path, cache)


def fallback_core_pool_baseline_counts(candidates: Sequence[CorePoolCandidate]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        if candidate.primary_category:
            counts[candidate.primary_category] += 1
    return dict(counts)


def _extract_arxiv_id_from_openalex_work(work: dict[str, Any]) -> str | None:
    candidates: list[str] = []
    doi_values = [work.get("doi")]
    ids = work.get("ids") or {}
    if isinstance(ids, dict):
        doi_values.extend(value for value in ids.values() if isinstance(value, str))
    primary_location = work.get("primary_location") or {}
    if isinstance(primary_location, dict):
        landing_page_url = primary_location.get("landing_page_url")
        if isinstance(landing_page_url, str):
            candidates.append(landing_page_url)

    for value in doi_values:
        if not isinstance(value, str):
            continue
        match = re.search(r"10\.48550/arxiv\.(?P<id>[^/?#]+)", value, flags=re.IGNORECASE)
        if match:
            normalized = normalize_arxiv_id(match.group("id"))
            if normalized:
                return normalized
        candidates.append(value)

    for value in candidates:
        normalized = normalize_arxiv_id(value.rsplit("/abs/", 1)[-1])
        if normalized:
            return normalized
    return None


def collect_openalex_field_candidates(
    *,
    lookback_years: int,
    per_category_limit: int,
    timeout: int,
    retries: int,
    mailto: str | None,
) -> tuple[list[CorePoolCandidate], dict[str, int]]:
    end_date = datetime.now(UTC).date()
    start_date = core_pool_lookback_start(datetime.now(UTC), lookback_years).date()
    baseline_counts: dict[str, int] = {}
    merged: dict[str, CorePoolCandidate] = {}

    for category, field_id in OPENALEX_FIELD_ID_BY_CATEGORY.items():
        page = 1
        per_page = min(DEFAULT_OPENALEX_FIELD_PAGE_SIZE, per_category_limit)
        collected = 0
        while collected < per_category_limit:
            params = {
                "filter": ",".join(
                    [
                        "doi_starts_with:10.48550/arxiv.",
                        f"primary_topic.field.id:{field_id}",
                        f"from_publication_date:{start_date.isoformat()}",
                        f"to_publication_date:{end_date.isoformat()}",
                    ]
                ),
                "sort": "cited_by_count:desc",
                "per_page": str(per_page),
                "page": str(page),
            }
            if mailto:
                params["mailto"] = mailto
            payload = fetch_json(
                f"{OPENALEX_API_URL}?{urlencode(params)}",
                timeout=timeout,
                retries=retries,
            )
            if page == 1:
                meta = payload.get("meta") or {}
                count = meta.get("count")
                if isinstance(count, int):
                    baseline_counts[category] = count

            results = payload.get("results", [])
            if not results:
                break

            page_added = 0
            for work in results:
                arxiv_id = _extract_arxiv_id_from_openalex_work(work)
                if arxiv_id is None:
                    continue

                candidate = merged.get(arxiv_id)
                if candidate is None:
                    candidate = CorePoolCandidate(
                        arxiv_id=arxiv_id,
                        title=work.get("display_name") or work.get("title"),
                        publication_date=core_pool_publication_date_for_openalex_work(arxiv_id, work),
                        updated_at=None,
                        source_url=f"https://arxiv.org/abs/{arxiv_id}",
                        primary_category=category,
                        signal_ranks={},
                    )
                    merged[arxiv_id] = candidate

                cited_by_count = work.get("cited_by_count")
                if isinstance(cited_by_count, int):
                    candidate.citation_count = max(candidate.citation_count or 0, cited_by_count)
                if candidate.primary_category is None:
                    candidate.primary_category = category
                if not candidate.publication_date:
                    candidate.publication_date = core_pool_publication_date_for_openalex_work(arxiv_id, work)
                if not candidate.title and (work.get("display_name") or work.get("title")):
                    candidate.title = work.get("display_name") or work.get("title")
                page_added += 1
                collected += 1
                if collected >= per_category_limit:
                    break

            log(
                f"[core-pool:openalex:{category}] page={page} rows={len(results)} "
                f"added={page_added} total_category={collected}"
            )
            if page_added == 0 or len(results) < per_page:
                break
            page += 1

    return list(merged.values()), baseline_counts


def collect_core_pool_records(
    *,
    exported_at: str,
    target_size: int,
    lookback_years: int,
    recent_cutoff_days: int,
    min_floor: int,
    per_signal_limit: int,
    interval: str,
    page_size: int,
    timeout: int,
    retries: int,
    openalex_mailto: str | None,
    openalex_workers: int,
    citation_shortlist_size: int | None,
    cache_path: Path | None,
) -> list[PaperRecord]:
    alphaxiv_candidates = collect_core_pool_candidates(
        per_signal_limit=per_signal_limit,
        interval=interval,
        page_size=page_size,
        timeout=timeout,
        retries=retries,
    )
    openalex_candidates, baseline_counts = collect_openalex_field_candidates(
        lookback_years=lookback_years,
        per_category_limit=max(
            DEFAULT_OPENALEX_FIELD_CANDIDATE_LIMIT,
            min_floor * 6,
            math.ceil(target_size / max(1, len(OPENALEX_FIELD_ID_BY_CATEGORY))),
        ),
        timeout=timeout,
        retries=retries,
        mailto=openalex_mailto,
    )

    merged_candidates: dict[str, CorePoolCandidate] = {candidate.arxiv_id: candidate for candidate in alphaxiv_candidates}
    for candidate in openalex_candidates:
        existing = merged_candidates.get(candidate.arxiv_id)
        if existing is None:
            merged_candidates[candidate.arxiv_id] = candidate
            continue
        existing.citation_count = max(existing.citation_count or 0, candidate.citation_count or 0) or None
        if existing.primary_category is None:
            existing.primary_category = candidate.primary_category
        if not existing.publication_date:
            existing.publication_date = candidate.publication_date
        if not existing.title:
            existing.title = candidate.title
        if existing.views_count == 0:
            existing.views_count = candidate.views_count
        if existing.vote_count == 0:
            existing.vote_count = candidate.vote_count

    candidates = list(merged_candidates.values())
    now = datetime.now(UTC)
    lookback_threshold = core_pool_lookback_start(now, lookback_years)
    candidates = [
        candidate
        for candidate in candidates
        if _parse_datetime(candidate.publication_date) is None
        or _parse_datetime(candidate.publication_date) >= lookback_threshold
    ]
    fallback_counts = fallback_core_pool_baseline_counts(candidates)
    if not baseline_counts:
        baseline_counts = fallback_counts
    else:
        for category, count in fallback_counts.items():
            baseline_counts.setdefault(category, count)

    shortlist_size = citation_shortlist_size
    if shortlist_size is None:
        shortlist_size = min(len(candidates), target_size + max(500, DEFAULT_CORE_CITATION_SHORTLIST_BUFFER * 8))

    enrich_candidates_with_openalex(
        candidates,
        shortlist_size=shortlist_size,
        timeout=timeout,
        retries=max(1, retries),
        mailto=openalex_mailto,
        cache_path=cache_path,
        workers=openalex_workers,
    )
    return build_core_pool_records(
        candidates,
        baseline_counts=baseline_counts,
        exported_at=exported_at,
        target_size=target_size,
        min_floor=min_floor,
        recent_cutoff_days=recent_cutoff_days,
        now=now,
    )


def write_markdown(
    records: Sequence[PaperRecord],
    output_path: Path,
    *,
    source_mode: str | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    active_mode = source_mode or (records[0].source_mode if records else "unknown")
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# alphaXiv Papers\n\n")
        handle.write(f"- Source mode: `{active_mode}`\n")
        handle.write(f"- Exported papers: {len(records)}\n")
        if records:
            handle.write(f"- Exported at: {records[0].exported_at}\n")
            handle.write(f"- Source family: `{records[0].source_family}`\n")
            handle.write(f"- Translation priority: {records[0].translation_priority}\n")
        handle.write("\n")
        for record in records:
            prefix = f"{record.source_rank}. " if record.source_rank is not None else "- "
            line = f"{prefix}`{record.arxiv_id}`"
            if record.title:
                line += f": {record.title}"
            line += f" | `{record.source_mode}`"
            if record.primary_category:
                line += f" | category `{record.primary_category}`"
            if record.publication_date:
                line += f" | published `{record.publication_date}`"
            if record.updated_at:
                line += f" | updated `{record.updated_at}`"
            if record.score is not None:
                line += f" | score `{record.score:.6f}`"
            if record.citation_count is not None:
                line += f" | citations `{record.citation_count}`"
            if record.views_count is not None:
                line += f" | views `{record.views_count}`"
            if record.vote_count is not None:
                line += f" | votes `{record.vote_count}`"
            if record.signal_ranks:
                rank_bits = ", ".join(f"{name}:{value}" for name, value in sorted(record.signal_ranks.items()))
                line += f" | signal_ranks `{rank_bits}`"
            if record.selection_bucket:
                line += f" | bucket `{record.selection_bucket}`"
            handle.write(f"{line}\n")


def write_json_payload(
    records: Sequence[PaperRecord],
    output_path: Path,
    *,
    source_mode: str,
    export_metadata: dict[str, Any] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_family = source_family_for_mode(source_mode)
    payload = {
        "source_mode": source_mode,
        "source_family": source_family,
        "translation_priority": translation_priority_for_mode(source_mode),
        "dedupe_key": "arxiv_id",
        "skip_retranslation_if_translated": True,
        "count": len(records),
        "exported_at": records[0].exported_at if records else utc_now_iso(),
        "records": [asdict(record) for record in records],
    }
    if source_mode == "core-pool":
        payload["selection_policy"] = {
            "lookback_years": DEFAULT_CORE_POOL_LOOKBACK_YEARS,
            "recent_cutoff_days": DEFAULT_CORE_POOL_RECENT_CUTOFF_DAYS,
            "min_category_floor": DEFAULT_CORE_MIN_CATEGORY_FLOOR,
            "score_weights": {
                "views_rank": 0.18,
                "likes_rank": 0.15,
                "comments_rank": 0.12,
                "views": 0.18,
                "votes": 0.12,
                "citations": 0.20,
                "maturity": 0.05,
            },
        }
    if export_metadata:
        payload.update(export_metadata)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_output_dir(base_dir: Path, source_mode: str) -> Path:
    try:
        subdir = MODE_OUTPUT_DIRS[source_mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported source mode: {source_mode}") from exc
    return base_dir / subdir


def write_mode_artifacts(
    records: Sequence[PaperRecord],
    *,
    base_dir: Path,
    source_mode: str,
    export_metadata: dict[str, Any] | None = None,
) -> dict[str, Path]:
    output_dir = resolve_output_dir(base_dir, source_mode)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "latest.json"
    markdown_path = output_dir / "latest.md"
    write_json_payload(records, json_path, source_mode=source_mode, export_metadata=export_metadata)
    write_markdown(records, markdown_path, source_mode=source_mode)
    return {"json": json_path, "markdown": markdown_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export reusable hot/new paper source artifacts.")
    parser.add_argument(
        "--mode",
        default="hot-top-n",
        choices=["hot-top-n", "hot-new-24h", "new-24h", "core-pool", "sitemap-all-ids"],
        help="export mode",
    )
    parser.add_argument("--limit", type=int, default=10000, help="maximum records for top-N or legacy modes")
    parser.add_argument("--lookback-hours", type=int, default=24, help="lookback window for daily modes")
    parser.add_argument("--hot-interval", default=DEFAULT_HOT_INTERVAL, help="alphaXiv hot interval for top-N mode")
    parser.add_argument(
        "--recent-hot-interval",
        default=RECENT_HOT_INTERVAL,
        help="alphaXiv hot interval for the recent hot mode",
    )
    parser.add_argument("--page-size", type=int, default=100, help="page size for alphaXiv hot feeds")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retry attempts per request")
    parser.add_argument("--core-pool-size", type=int, default=DEFAULT_CORE_POOL_SIZE, help="target size for core pool mode")
    parser.add_argument(
        "--core-lookback-years",
        type=int,
        default=DEFAULT_CORE_POOL_LOOKBACK_YEARS,
        help="only keep papers published in the last N years for core pool mode",
    )
    parser.add_argument(
        "--core-recent-cutoff-days",
        type=int,
        default=DEFAULT_CORE_POOL_RECENT_CUTOFF_DAYS,
        help="exclude papers newer than this many days from core pool mode",
    )
    parser.add_argument(
        "--core-min-category-floor",
        type=int,
        default=DEFAULT_CORE_MIN_CATEGORY_FLOOR,
        help="minimum selected papers per included core-pool category",
    )
    parser.add_argument(
        "--core-signal-limit",
        type=int,
        default=DEFAULT_CORE_SIGNAL_LIMIT,
        help="maximum unique candidates to pull per alphaXiv all-time signal for core pool mode",
    )
    parser.add_argument(
        "--core-citation-shortlist-size",
        type=int,
        default=None,
        help="maximum number of core-pool candidates to enrich with OpenAlex citations",
    )
    parser.add_argument(
        "--openalex-mailto",
        default=None,
        help="optional contact email for OpenAlex polite-pool requests",
    )
    parser.add_argument(
        "--openalex-workers",
        type=int,
        default=DEFAULT_OPENALEX_WORKERS,
        help="parallel workers for OpenAlex citation enrichment",
    )
    parser.add_argument(
        "--base-dir",
        default=str(BACKEND_ARXIV_ID_DIR),
        help="base directory for hot/new source artifacts",
    )
    parser.add_argument("--index-url", default=SITEMAP_INDEX_URL, help="legacy sitemap index URL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exported_at = utc_now_iso()
    base_dir = Path(args.base_dir)
    export_metadata: dict[str, Any] | None = None

    if args.mode == "hot-top-n":
        log(f"[start] mode=hot-top-n limit={args.limit} interval={args.hot_interval}")
        records = collect_hot_top_n_records(
            limit=args.limit,
            exported_at=exported_at,
            interval=args.hot_interval,
            page_size=args.page_size,
            timeout=args.timeout,
            retries=args.retries,
        )
    elif args.mode == "hot-new-24h":
        log(f"[start] mode=hot-new-24h lookback_hours={args.lookback_hours}")
        records = collect_hot_new_records(
            lookback_hours=args.lookback_hours,
            exported_at=exported_at,
            interval=args.recent_hot_interval,
            page_size=args.page_size,
            timeout=args.timeout,
            retries=args.retries,
        )
    elif args.mode == "new-24h":
        log(f"[start] mode=new-24h lookback_hours={args.lookback_hours}")
        records = collect_new_24h_records(
            lookback_hours=args.lookback_hours,
            exported_at=exported_at,
            timeout=max(args.timeout, 30),
            retries=args.retries,
        )
    elif args.mode == "core-pool":
        log(
            "[start] mode=core-pool "
            f"target={args.core_pool_size} lookback_years={args.core_lookback_years} "
            f"recent_cutoff_days={args.core_recent_cutoff_days}"
        )
        cache_path = resolve_output_dir(base_dir, "core-pool") / ".openalex_cache.json"
        records = collect_core_pool_records(
            exported_at=exported_at,
            target_size=args.core_pool_size,
            lookback_years=args.core_lookback_years,
            recent_cutoff_days=args.core_recent_cutoff_days,
            min_floor=args.core_min_category_floor,
            per_signal_limit=args.core_signal_limit,
            interval=args.hot_interval,
            page_size=args.page_size,
            timeout=args.timeout,
            retries=args.retries,
            openalex_mailto=args.openalex_mailto,
            openalex_workers=args.openalex_workers,
            citation_shortlist_size=args.core_citation_shortlist_size,
            cache_path=cache_path,
        )
        export_metadata = {
            "selection_policy": {
                "lookback_years": args.core_lookback_years,
                "lookback_start": core_pool_lookback_start(datetime.now(UTC), args.core_lookback_years).date().isoformat(),
                "recent_cutoff_days": args.core_recent_cutoff_days,
                "min_category_floor": args.core_min_category_floor,
                "target_size": args.core_pool_size,
                "signal_limit_per_source": args.core_signal_limit,
                "openalex_field_candidate_limit": max(
                    DEFAULT_OPENALEX_FIELD_CANDIDATE_LIMIT,
                    args.core_min_category_floor * 6,
                    math.ceil(args.core_pool_size / max(1, len(OPENALEX_FIELD_ID_BY_CATEGORY))),
                ),
                "citation_shortlist_size": args.core_citation_shortlist_size,
                "score_weights": {
                    "views_rank": 0.18,
                    "likes_rank": 0.15,
                    "comments_rank": 0.12,
                    "views": 0.18,
                    "votes": 0.12,
                    "citations": 0.20,
                    "maturity": 0.05,
                },
            }
        }
    else:
        log("[start] mode=sitemap-all-ids (legacy)")
        paper_urls = collect_paper_urls(args.index_url, timeout=args.timeout, retries=args.retries)
        if args.limit > 0:
            paper_urls = paper_urls[: args.limit]
        records = [
            PaperRecord(
                arxiv_id=extract_arxiv_id(url),
                title=None,
                source_mode="sitemap-all-ids",
                source_rank=index,
                publication_date=None,
                updated_at=None,
                source_url=url,
                exported_at=exported_at,
                source_family="legacy",
                translation_priority=99,
            )
            for index, url in enumerate(paper_urls, start=1)
        ]

    paths = write_mode_artifacts(records, base_dir=base_dir, source_mode=args.mode, export_metadata=export_metadata)
    log(f"[done] wrote {len(records)} records to {paths['json']} and {paths['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
