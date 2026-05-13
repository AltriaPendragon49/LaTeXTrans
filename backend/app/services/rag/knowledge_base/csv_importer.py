"""CSV importer for RAG terminology knowledge base.

Parses CSV content with auto-detected delimiter, validates rows,
and produces structured data ready for TerminologyRepository.insert_terms_batch.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = {"source_term", "target_term", "source_lang", "target_lang", "domain"}

REQUIRED_COLUMNS = {"source_term", "target_term"}


@dataclass
class ImporterResult:
    """Result of a CSV import operation."""

    accepted: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)
    term_ids: list[str] = field(default_factory=list)


def _detect_delimiter(sample: str) -> str:
    """Auto-detect CSV delimiter from a sample string.

    Tries comma, semicolon, and tab. Returns the one that produces
    the most consistent column count across lines.
    """
    candidates = [",", ";", "\t"]
    best_delimiter = ","
    best_score = 0

    lines = [line for line in sample.splitlines() if line.strip()]
    if not lines:
        return best_delimiter

    for delimiter in candidates:
        scores = []
        for line in lines:
            count = line.count(delimiter)
            scores.append(count)
        if not scores:
            continue
        consistent = sum(1 for s in scores if s == scores[0])
        if consistent > best_score:
            best_score = consistent
            best_delimiter = delimiter

    return best_delimiter


def _strip_bom(content: str) -> str:
    """Remove BOM if present."""
    if content.startswith("﻿"):
        return content[1:]
    return content


def parse_csv_content(content: str | bytes) -> list[dict]:
    """Parse CSV content and return a list of row dicts.

    Handles:
      - BOM (byte-order mark)
      - Auto-detected delimiter (comma, semicolon, tab)
      - CSV quoting and escaping

    Expected columns (case-insensitive): source_term, target_term
    Optional columns: source_lang, target_lang, domain

    Returns:
        List of dicts with normalised keys, ready for
        TerminologyRepository.insert_terms_batch.
    """
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = content.decode("utf-8", errors="replace")
    else:
        content = _strip_bom(content)

    content = content.strip()
    if not content:
        return []

    delimiter = _detect_delimiter(content)
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

    if reader.fieldnames is None:
        return []

    normalised_fieldnames = {name.strip().lower(): name.strip() for name in reader.fieldnames}
    rows: list[dict] = []
    for line_num, row in enumerate(reader, start=2):
        normalised: dict[str, str] = {}
        for raw_key, raw_value in row.items():
            if raw_key is None:
                continue
            key = raw_key.strip().lower()
            value = raw_value.strip() if raw_value else ""
            normalised[key] = value

        mapped: dict[str, str] = {}
        for expected in EXPECTED_COLUMNS:
            if expected in normalised:
                mapped[expected] = normalised[expected]

        rows.append(mapped)

    return rows


def validate_row(row: dict) -> Optional[str]:
    """Validate a single parsed CSV row.

    Returns:
        An error message string if the row is invalid, or None if valid.
    """
    source_term = (row.get("source_term") or "").strip()
    target_term = (row.get("target_term") or "").strip()

    if not source_term:
        return "source_term is empty"
    if not target_term:
        return "target_term is empty"

    return None
