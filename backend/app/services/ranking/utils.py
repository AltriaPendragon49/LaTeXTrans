"""Shared utility functions for paper source export and ranking.

These functions are extracted from scripts/export_alphaxiv_catalog.py so they
can be used by both the legacy export script and the new ranking system.
"""

import json
import re
import time
from datetime import datetime
from typing import Any, Sequence
from urllib.parse import unquote

import requests

ARXIV_API_URL = "https://export.arxiv.org/api/query"
OPENALEX_API_URL = "https://api.openalex.org/works"
ALPHAXIV_API_BASE = "https://api.alphaxiv.org"
USER_AGENT = "LaTexTrans paper source exporter/2.0"

ARXIV_ID_PATTERN = re.compile(
    r"^(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))(?:v\d+)?$",
    re.IGNORECASE,
)
ARXIV_ID_PREFIX_PATTERN = re.compile(
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))(?:v\d+)?",
    re.IGNORECASE,
)
TITLE_KEY_PATTERN = re.compile(r"[^a-z0-9]+")

BROAD_TOPIC_TO_MAJOR_CATEGORY = {
    "computer science": "cs",
    "mathematics": "math",
    "physics": "physics",
    "statistics": "stat",
    "quantitative biology": "q-bio",
    "quantitative finance": "q-fin",
    "electrical engineering and systems science": "eess",
    "economics": "econ",
}


def fetch_text(url: str, *, timeout: int = 20, retries: int = 3, retry_delay: float = 0.5) -> str:
    last_error: Exception | None = None
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html,application/xml;q=0.9,*/*;q=0.8",
    }
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(retry_delay * attempt)

    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def fetch_json(url: str, *, timeout: int = 20, retries: int = 3) -> dict[str, Any]:
    return json.loads(fetch_text(url, timeout=timeout, retries=retries))


def normalize_arxiv_id(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    value = unquote(raw_value.strip())
    if not value:
        return None

    if value.lower().startswith("arxiv:"):
        value = value.split(":", 1)[1]

    value = value.split("?", 1)[0].split("#", 1)[0]
    if value.endswith(".pdf"):
        value = value[:-4]

    match = ARXIV_ID_PATTERN.match(value)
    if match:
        return match.group("id")

    prefix_match = ARXIV_ID_PREFIX_PATTERN.match(value)
    if prefix_match:
        return prefix_match.group("id")

    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def infer_submission_date_from_arxiv_id(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    match = re.match(r"^(?P<yy>\d{2})(?P<mm>\d{2})\.\d{4,5}$", arxiv_id)
    if not match:
        return None

    year = 2000 + int(match.group("yy"))
    month = int(match.group("mm"))
    if month < 1 or month > 12:
        return None
    return f"{year:04d}-{month:02d}-01T00:00:00Z"


def _title_key(title: str | None) -> str:
    if not title:
        return ""
    return TITLE_KEY_PATTERN.sub("", title.casefold())


def major_category_from_topic(topic: str | None) -> str | None:
    if topic is None:
        return None

    normalized = topic.strip().lower()
    if not normalized:
        return None

    if normalized in BROAD_TOPIC_TO_MAJOR_CATEGORY:
        return BROAD_TOPIC_TO_MAJOR_CATEGORY[normalized]

    prefix = normalized.split(".", 1)[0]
    if prefix in {"cs", "math", "stat", "q-bio", "q-fin", "eess", "econ"}:
        return prefix
    if prefix in {
        "astro-ph",
        "cond-mat",
        "gr-qc",
        "math-ph",
        "nlin",
        "physics",
        "quant-ph",
    }:
        return "physics"
    if prefix.startswith("hep-") or prefix.startswith("nucl-"):
        return "physics"
    return None


def _pick_openalex_match(
    results: Sequence[dict[str, Any]],
    *,
    title: str,
    arxiv_id: str,
    publication_year: int | None,
) -> dict[str, Any] | None:
    expected_key = _title_key(title)
    best_match: dict[str, Any] | None = None
    best_score: tuple[int, int, int] | None = None

    for result in results:
        display_name = result.get("display_name") or result.get("title") or ""
        if _title_key(display_name) != expected_key:
            continue

        ids = result.get("ids") or {}
        contains_arxiv_id = 0
        for value in ids.values():
            if isinstance(value, str) and arxiv_id in value:
                contains_arxiv_id = 1
                break

        result_year = result.get("publication_year")
        year_distance = 999
        if publication_year is not None and isinstance(result_year, int):
            year_distance = abs(publication_year - result_year)
        elif isinstance(result_year, int):
            year_distance = 0

        score = (
            contains_arxiv_id,
            -year_distance,
            result.get("cited_by_count") or 0,
        )
        if best_score is None or score > best_score:
            best_score = score
            best_match = result
    return best_match
