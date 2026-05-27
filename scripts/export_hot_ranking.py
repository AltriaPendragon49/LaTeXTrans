"""
Standalone CLI for hot ranking export.

Usage:
  python scripts/export_hot_ranking.py --window 30d --limit 200
  python scripts/export_hot_ranking.py --window 7d --output-dir /custom/path
  python scripts/export_hot_ranking.py --window all --skip-enrich  # skip source enrichment
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ── Ensure backend is importable from the scripts directory ──────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.services.ranking.engine import rank_candidates, WINDOW_HALF_LIVES  # noqa: E402
from backend.app.services.ranking.schemas import RankedCandidate, ScoreBreakdown  # noqa: E402

# ── Constants ────────────────────────────────────────────────────────
BACKEND_ARXIV_ID_DIR = _REPO_ROOT / "backend" / "arxiv_id"
DEFAULT_LIMIT = 200
DEFAULT_WINDOW = "30d"
VALID_WINDOWS = ("3d", "7d", "30d", "90d", "all")
VALID_SKIP_SOURCES = ("arxiv", "openalex", "semantic_scholar", "huggingface", "alphaxiv", "github", "local")
DEMO_TOPICS = ("AI", "Physics", "Math", "Biology", "CS", "Chemistry", "Economics", "Materials", "Astronomy", "Engineering")


# ── Helpers ──────────────────────────────────────────────────────────

def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ── Demo / synthetic data ────────────────────────────────────────────

def generate_demo_candidates(limit: int = 50) -> list[dict[str, Any]]:
    """Generate synthetic candidates for testing the ranking pipeline."""
    random.seed(42)
    candidates: list[dict[str, Any]] = []
    for i in range(limit):
        year = random.randint(2020, 2026)
        num = random.randint(1, 99999)
        arxiv_id = f"{year:04d}.{num:05d}"

        days_ago = random.uniform(0, 365)
        pub_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()

        candidates.append({
            "arxiv_id": arxiv_id,
            "title": f"Demo Paper {i + 1}: Research on Topic {random.choice(DEMO_TOPICS)}",
            "authors": [f"Author {chr(65 + random.randint(0, 25))}"],
            "categories": [random.choice(["cs.AI", "physics", "math.ST", "q-bio", "stat", "cond-mat", "astro-ph"])],
            "publication_date": pub_date,
            "raw_attention": random.uniform(0, 500),
            "raw_authority": random.uniform(0, 200),
            "raw_implementation": random.uniform(0, 100),
            "raw_local": random.uniform(0, 50),
            "source_evidence": [],
        })
    return candidates


# ── Candidate collection ─────────────────────────────────────────────

def collect_candidates(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Collect candidates from source adapters or fall back to demo mode."""
    if args.skip_enrich:
        log("[demo] --skip-enrich flag set, using synthetic data")
        return generate_demo_candidates(limit=args.limit)

    # Try to import source adapters
    try:
        from backend.app.services.ranking.source_adapters import collect_candidates_from_sources  # noqa: F811
    except ImportError as exc:
        log(f"[demo] Source adapters not available ({exc}), falling back to synthetic data")
        return generate_demo_candidates(limit=args.limit)

    # Build skip list
    skip_sources: set[str] = set(args.skip_sources) if args.skip_sources else set()

    try:
        candidates = collect_candidates_from_sources(
            limit=args.limit,
            skip_sources=skip_sources,
            timeout=args.timeout,
            retries=args.retries,
        )
        log(f"[collect] Gathered {len(candidates)} candidates from source adapters")
        return candidates
    except Exception as exc:
        log(f"[demo] Source adapter collection failed ({exc}), falling back to synthetic data")
        return generate_demo_candidates(limit=args.limit)


# ── Artifact writing ─────────────────────────────────────────────────

def ranked_candidate_to_record(candidate: RankedCandidate) -> dict[str, Any]:
    """Convert a RankedCandidate to a JSON-serializable record dict."""
    breakdown = candidate.score_breakdown
    return {
        "arxiv_id": candidate.arxiv_id,
        "title": candidate.title,
        "authors": candidate.authors,
        "categories": candidate.categories,
        "publication_date": candidate.publication_date,
        "window": candidate.window,
        "hot_score": candidate.hot_score,
        "evidence_score": candidate.evidence_score,
        "age_days": candidate.age_days,
        "half_life_days": candidate.half_life_days,
        "time_decay": candidate.time_decay,
        "score_breakdown": asdict(breakdown) if isinstance(breakdown, ScoreBreakdown) else {},
        "source_evidence": candidate.source_evidence,
        "selected_reason": candidate.selected_reason,
        "rank": candidate.rank,
    }


def write_json_artifact(
    candidates: list[RankedCandidate],
    output_path: Path,
    *,
    window: str,
    exported_at: str,
) -> None:
    """Write the JSON artifact (latest.json)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    half_life = WINDOW_HALF_LIVES.get(window, 10.0)

    payload: dict[str, Any] = {
        "source_mode": "hot-ranked",
        "source_family": "hot_ranking",
        "translation_priority": 0,
        "dedupe_key": "arxiv_id",
        "skip_retranslation_if_translated": True,
        "window": window,
        "half_life_days": half_life,
        "count": len(candidates),
        "exported_at": exported_at,
        "records": [ranked_candidate_to_record(c) for c in candidates],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown_artifact(
    candidates: list[RankedCandidate],
    output_path: Path,
    *,
    window: str,
    exported_at: str,
) -> None:
    """Write the human-readable Markdown artifact (latest.md)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    half_life = WINDOW_HALF_LIVES.get(window, 10.0)

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Hot Ranking Export\n\n")
        handle.write(f"- Window: `{window}`\n")
        handle.write(f"- Exported papers: {len(candidates)}\n")
        handle.write(f"- Exported at: {exported_at}\n")
        handle.write(f"- Half-life: {half_life} days\n")
        handle.write(f"- Source family: `hot_ranking`\n")
        handle.write("\n")

        for c in candidates:
            bd = c.score_breakdown
            att = round(bd.attention, 1) if isinstance(bd, ScoreBreakdown) else 0
            aut = round(bd.authority, 1) if isinstance(bd, ScoreBreakdown) else 0
            imp = round(bd.implementation, 1) if isinstance(bd, ScoreBreakdown) else 0
            loc = round(bd.local, 1) if isinstance(bd, ScoreBreakdown) else 0

            line = (
                f"{c.rank}. `{c.arxiv_id}`: {c.title or '(no title)'} "
                f"| score `{c.hot_score:.2f}` "
                f"| attention `{att}` "
                f"| authority `{aut}` "
                f"| impl `{imp}` "
                f"| local `{loc}` "
                f"| age `{c.age_days:.1f}d` "
                f"| reason: {c.selected_reason}"
            )
            handle.write(f"{line}\n")


# ── Argument parsing ─────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export ranked hot papers using multi-source evidence scoring.",
    )
    parser.add_argument(
        "--window",
        choices=VALID_WINDOWS,
        default=DEFAULT_WINDOW,
        help="Time window for ranking (default: 30d). 'all' uses a 0.15 decay floor.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum candidates to rank (default: 200).",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Minimum hot_score filter after ranking (default: 0.0).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory (default: backend/arxiv_id/hot_ranked/{window}/).",
    )
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="Skip source enrichment entirely and use synthetic demo data.",
    )
    parser.add_argument(
        "--skip-sources",
        nargs="*",
        default=[],
        choices=VALID_SKIP_SOURCES,
        help="Skip specific sources during enrichment (e.g. --skip-sources openalex github).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds per request (default: 30).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="HTTP retry attempts per request (default: 3).",
    )
    return parser.parse_args(argv)


# ── Main ─────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exported_at = utc_now_iso()

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = BACKEND_ARXIV_ID_DIR / "hot_ranked" / args.window

    log(f"[start] window={args.window} limit={args.limit} min_score={args.min_score}")

    # 1. Collect candidates (from source adapters or demo mode)
    raw_candidates = collect_candidates(args)
    if not raw_candidates:
        log("[error] No candidates collected. Aborting.")
        return 1

    log(f"[candidates] {len(raw_candidates)} raw candidates before ranking")

    # 2. Rank
    ranked = rank_candidates(raw_candidates, window=args.window)
    log(f"[ranked] {len(ranked)} candidates within window after ranking")

    # 3. Filter by min_score
    if args.min_score > 0.0:
        before = len(ranked)
        ranked = [c for c in ranked if c.hot_score >= args.min_score]
        log(f"[filter] {len(ranked)} candidates after min_score >= {args.min_score} (removed {before - len(ranked)})")

    # 4. Limit
    if len(ranked) > args.limit:
        ranked = ranked[: args.limit]

    if not ranked:
        log("[error] No candidates after filtering. Aborting.")
        return 1

    # 5. Write artifacts
    json_path = output_dir / "latest.json"
    md_path = output_dir / "latest.md"

    write_json_artifact(ranked, json_path, window=args.window, exported_at=exported_at)
    write_markdown_artifact(ranked, md_path, window=args.window, exported_at=exported_at)

    log(f"[done] Exported {len(ranked)} candidates to {output_dir}")
    log(f"       json: {json_path}")
    log(f"       md:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
