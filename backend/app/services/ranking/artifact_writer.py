"""Artifact writer for the hot ranking system.

Writes JSON and Markdown artifacts for time-window rankings and daily
intake summaries, following the same patterns as export_alphaxiv_catalog.py.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .schemas import DailyIntakeSummary, RankedCandidate


def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO-8601 string with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _candidate_to_dict(candidate: RankedCandidate) -> dict[str, Any]:
    """Convert a RankedCandidate to a plain dict suitable for JSON serialization.

    Handles nested dataclasses (ScoreBreakdown, SourceEvidence) by converting
    them through asdict.
    """
    result: dict[str, Any] = {}
    result["arxiv_id"] = candidate.arxiv_id
    result["window"] = candidate.window
    result["hot_score"] = candidate.hot_score
    result["evidence_score"] = candidate.evidence_score
    result["age_days"] = candidate.age_days
    result["half_life_days"] = candidate.half_life_days
    result["time_decay"] = candidate.time_decay
    result["score_breakdown"] = asdict(candidate.score_breakdown)
    result["source_evidence"] = [
        asdict(se) if hasattr(se, "__dataclass_fields__") else se
        for se in candidate.source_evidence
    ]
    result["title"] = candidate.title
    result["authors"] = list(candidate.authors) if candidate.authors else []
    result["categories"] = list(candidate.categories) if candidate.categories else []
    result["publication_date"] = candidate.publication_date
    result["selected_reason"] = candidate.selected_reason
    result["exclusion_reasons"] = list(candidate.exclusion_reasons) if candidate.exclusion_reasons else []
    result["rank"] = candidate.rank
    return result


def write_json_payload(
    candidates: Sequence[RankedCandidate],
    output_path: Path,
    *,
    window: str = "30d",
    exported_at: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    """Write ranked candidates to a JSON file.

    JSON format matches backend/arxiv_id/daily_hot/latest.json pattern:

        {
          "source_mode": "hot-ranked",
          "source_family": "hot_ranking",
          "window": "30d",
          "translation_priority": 0,
          "dedupe_key": "arxiv_id",
          "skip_retranslation_if_translated": true,
          "count": N,
          "exported_at": "...",
          "records": [...]
        }
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = [_candidate_to_dict(c) for c in candidates]
    payload: dict[str, Any] = {
        "source_mode": "hot-ranked",
        "source_family": "hot_ranking",
        "window": window,
        "translation_priority": 0,
        "dedupe_key": "arxiv_id",
        "skip_retranslation_if_translated": True,
        "count": len(records),
        "exported_at": exported_at or (records[0].get("publication_date") if records else utc_now_iso()),
        "records": records,
    }
    if extra_metadata:
        payload.update(extra_metadata)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown(
    candidates: Sequence[RankedCandidate],
    output_path: Path,
    *,
    window: str = "30d",
    exported_at: str | None = None,
) -> None:
    """Write ranked candidates to a Markdown file.

    Format: header with window, count, time, half-life, then per-line records.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    exported = exported_at or utc_now_iso()
    half_life = candidates[0].half_life_days if candidates else 10.0

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Hot Ranking Results\n\n")
        handle.write(f"- Window: `{window}`\n")
        handle.write(f"- Exported at: {exported}\n")
        handle.write(f"- Candidates: {len(candidates)}\n")
        handle.write(f"- Half-life: {half_life} days\n")
        handle.write(f"- Source family: `hot_ranking`\n")
        handle.write(f"- Translation priority: 0\n")
        handle.write("\n")
        for c in candidates:
            line = f"{c.rank}. `{c.arxiv_id}`"
            if c.title:
                line += f": {c.title}"
            line += f" | hot_score `{c.hot_score}`"
            line += f" | evidence `{c.evidence_score}`"
            line += f" | attention `{c.score_breakdown.attention:.1f}`"
            line += f" | authority `{c.score_breakdown.authority:.1f}`"
            line += f" | impl `{c.score_breakdown.implementation:.1f}`"
            line += f" | local `{c.score_breakdown.local:.1f}`"
            if c.publication_date:
                line += f" | published `{c.publication_date}`"
            if c.selected_reason:
                line += f" | reason: {c.selected_reason}"
            handle.write(f"{line}\n")


def write_window_artifacts(
    candidates: Sequence[RankedCandidate],
    window: str,
    base_dir: Path,
    exported_at: str | None = None,
) -> dict[str, Path]:
    """Write latest.json and latest.md for a time window.

    Args:
        candidates: List of RankedCandidate.
        window: "3d"|"7d"|"30d"|"90d"|"all"
        base_dir: Path to the hot_ranked/ directory.
        exported_at: Optional ISO timestamp string.

    Returns:
        {"json": Path, "md": Path}
    """
    window_dir = base_dir / window
    window_dir.mkdir(parents=True, exist_ok=True)

    exported = exported_at or utc_now_iso()
    json_path = window_dir / "latest.json"
    md_path = window_dir / "latest.md"

    write_json_payload(candidates, json_path, window=window, exported_at=exported)
    write_markdown(candidates, md_path, window=window, exported_at=exported)

    return {"json": json_path, "md": md_path}


def write_daily_intake_artifacts(
    summary: DailyIntakeSummary,
    base_dir: Path,
) -> dict[str, Path]:
    """Write YYYY-MM-DD.md and YYYY-MM-DD.json to the daily_intake/ directory.

    Args:
        summary: DailyIntakeSummary dataclass.
        base_dir: Path to the hot_ranked/ directory.

    Returns:
        {"json": Path, "md": Path}
    """
    if not summary.date:
        summary.date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    intake_dir = base_dir / "daily_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)

    # --- JSON ---
    json_path = intake_dir / f"{summary.date}.json"
    json_payload: dict[str, Any] = {
        "date": summary.date,
        "window": summary.window,
        "triggered_at": summary.triggered_at or utc_now_iso(),
        "total_candidates": summary.total_candidates,
        "existing_count": summary.existing_count,
        "below_threshold_count": summary.below_threshold_count,
        "intaken_count": summary.intaken_count,
        "intaken_papers": summary.intaken_papers,
        "skipped_papers": summary.skipped_papers,
        "quality_gate_failures": summary.quality_gate_failures_from_prior_runs,
    }
    json_path.write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- Markdown ---
    md_path = intake_dir / f"{summary.date}.md"
    with md_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# Daily Hot Ranking Intake: {summary.date}\n\n")
        handle.write(f"- Window: `{summary.window}`\n")
        handle.write(f"- Triggered at: {summary.triggered_at or utc_now_iso()}\n")
        handle.write(f"- Total candidates: {summary.total_candidates}\n")
        handle.write(f"- Already existing: {summary.existing_count}\n")
        handle.write(f"- Below threshold: {summary.below_threshold_count}\n")
        handle.write(f"- Intaken: {summary.intaken_count}\n")
        handle.write("\n")

        if summary.intaken_papers:
            handle.write("## Intaken Papers\n\n")
            handle.write(
                "| # | arXiv ID | Title | Hot Score | attention | authority | implementation | local | Intake Reason |\n"
            )
            handle.write(
                "|---|----------|-------|-----------|-----------|-----------|----------------|-------|---------------|\n"
            )
            for idx, paper in enumerate(summary.intaken_papers, start=1):
                arxiv_id = paper.get("arxiv_id", "")
                title = paper.get("title", "") or ""
                hot_score = paper.get("hot_score", "")
                bd = paper.get("score_breakdown", {}) or {}
                att = bd.get("attention", "")
                aut = bd.get("authority", "")
                imp = bd.get("implementation", "")
                loc = bd.get("local", "")
                reason = paper.get("selected_reason", "") or paper.get("intake_reason", "")
                handle.write(
                    f"| {idx} | `{arxiv_id}` | {title} | {hot_score} | {att} | {aut} | {imp} | {loc} | {reason} |\n"
                )
            handle.write("\n")

        if summary.skipped_papers:
            handle.write("## Skipped\n\n")
            for skipped in summary.skipped_papers:
                arxiv_id = skipped.get("arxiv_id", "")
                reason = skipped.get("reason", skipped.get("skip_reason", ""))
                handle.write(f"- `{arxiv_id}`: {reason}\n")
            handle.write("\n")

        if summary.quality_gate_failures_from_prior_runs:
            handle.write("## Quality Gate Failures from Prior Runs\n\n")
            for failure in summary.quality_gate_failures_from_prior_runs:
                handle.write(f"- {failure}\n")
            handle.write("\n")

    return {"json": json_path, "md": md_path}
