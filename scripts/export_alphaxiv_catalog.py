from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import time
from typing import Sequence
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


SITEMAP_INDEX_URL = "https://www.alphaxiv.org/sitemaps/sitemap-index.xml"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "alphaxiv" / "papers.md"
USER_AGENT = "LaTexTrans alphaXiv catalog exporter/1.0"


@dataclass(frozen=True, order=True)
class PaperRecord:
    arxiv_id: str
    title: str | None
    url: str


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


def fetch_text(url: str, *, timeout: int = 20, retries: int = 3, retry_delay: float = 0.5) -> str:
    last_error: Exception | None = None
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(retry_delay * attempt)

    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


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


def parse_paper_sitemap(xml_text: str) -> list[str]:
    paper_urls: list[str] = []
    for loc in _parse_loc_values(xml_text):
        if is_primary_paper_url(loc):
            paper_urls.append(loc)
    return paper_urls


def is_primary_paper_url(url: str) -> bool:
    path = urlparse(url).path.rstrip("/")
    parts = path.split("/")
    return len(parts) == 3 and parts[1] == "abs" and bool(parts[2])


def extract_arxiv_id(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    parts = path.split("/")
    if len(parts) != 3 or parts[1] != "abs" or not parts[2]:
        raise ValueError(f"Unsupported alphaXiv paper URL: {url}")
    return parts[2]


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
    return PaperRecord(
        arxiv_id=extract_arxiv_id(url),
        title=extract_title_from_html(html_text),
        url=url,
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
    index_xml = fetch_text(index_url, timeout=timeout, retries=retries)
    sitemap_urls = parse_sitemap_index(index_xml)
    if not sitemap_urls:
        raise RuntimeError(f"No paper sitemap shards found in {index_url}")

    unique_ids: dict[str, None] = {}
    for idx, sitemap_url in enumerate(sitemap_urls, start=1):
        sitemap_xml = fetch_text(sitemap_url, timeout=timeout, retries=retries)
        shard_urls = parse_paper_sitemap(sitemap_xml)
        for paper_url in shard_urls:
            unique_ids.setdefault(extract_arxiv_id(paper_url), None)
        log(f"[sitemaps] {idx}/{len(sitemap_urls)} loaded: {sitemap_url} ({len(shard_urls)} papers)")

    return sorted(unique_ids.keys())


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

    records.sort()
    return records, failures


def write_markdown(
    records: Sequence[PaperRecord],
    output_path: Path,
    *,
    index_url: str = SITEMAP_INDEX_URL,
    failure_count: int = 0,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# alphaXiv Papers\n\n")
        handle.write(f"- Generated at: {timestamp}\n")
        handle.write(f"- Source sitemap index: `{index_url}`\n")
        handle.write(f"- Exported papers: {len(records)}\n")
        handle.write(f"- Failed pages skipped: {failure_count}\n\n")
        for record in records:
            if record.title:
                handle.write(f"- `{record.arxiv_id}`: {record.title}\n")
            else:
                handle.write(f"- `{record.arxiv_id}`\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export alphaXiv paper titles and arXiv IDs to Markdown.")
    parser.add_argument("--index-url", default=SITEMAP_INDEX_URL, help="alphaXiv sitemap index URL")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH.with_name("paper_ids.md")),
        help="output Markdown path",
    )
    parser.add_argument("--workers", type=int, default=8, help="number of concurrent paper fetch workers")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retry attempts per request")
    parser.add_argument("--limit", type=int, default=0, help="optional limit for paper pages to process")
    parser.add_argument(
        "--with-titles",
        action="store_true",
        help="slow mode: fetch each paper page and include titles in the Markdown export",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    log(f"[start] loading sitemap index: {args.index_url}")
    if args.with_titles:
        paper_urls = collect_paper_urls(args.index_url, timeout=args.timeout, retries=args.retries)
        log(f"[start] discovered {len(paper_urls)} unique paper URLs")

        if args.limit > 0:
            paper_urls = paper_urls[: args.limit]
            log(f"[start] limiting export to first {len(paper_urls)} paper URLs")

        records, failures = collect_paper_records(
            paper_urls,
            workers=args.workers,
            timeout=args.timeout,
            retries=args.retries,
        )
    else:
        paper_ids = collect_paper_ids(args.index_url, timeout=args.timeout, retries=args.retries)
        log(f"[start] discovered {len(paper_ids)} unique paper IDs")
        if args.limit > 0:
            paper_ids = paper_ids[: args.limit]
            log(f"[start] limiting export to first {len(paper_ids)} paper IDs")
        records = [
            PaperRecord(arxiv_id=arxiv_id, title=None, url=f"https://www.alphaxiv.org/abs/{arxiv_id}")
            for arxiv_id in paper_ids
        ]
        failures = []
    write_markdown(records, output_path, index_url=args.index_url, failure_count=len(failures))
    log(f"[done] wrote {len(records)} papers to {output_path}")
    if failures:
        log(f"[done] skipped {len(failures)} failed pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
