#!/usr/bin/env python3
"""
Run full evaluation comparing baseline vs RAG terminology translation.
Generates report for graduation-design thesis.

Usage:
    python -m backend.evaluation.run_evaluation --task-id <rag_task_id> --baseline-id <baseline_task_id>
    python -m backend.evaluation.run_evaluation --paper-dir <path>  # Both outputs in directory
    python -m backend.evaluation.run_evaluation --rag-file <path> --baseline-file <path> --reference-file <path>
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.evaluation.bleu_rouge import BleuRougeEvaluator
from backend.evaluation.term_consistency import TermConsistencyEvaluator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Expected file layout helpers
# ---------------------------------------------------------------------------

# By default, the backend stores translation results under:
#   outputs/<task_id>/<paper_id>/translated.tex
# or similar. The evaluation script can read these when --task-id / --baseline-id
# are given and a common --outputs-root is provided.
_OUTPUTS_ROOT_DEFAULT = Path("outputs")


def _discover_paper_ids(task_output_dir: Path) -> list[str]:
    """List paper IDs from a task output directory (one subdir per paper)."""
    if not task_output_dir.is_dir():
        return []
    return sorted(
        p.name for p in task_output_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def _read_translation(paper_dir: Path, filename: str = "translated.tex") -> Optional[str]:
    """Read a translation file, returning None if it does not exist."""
    path = paper_dir / filename
    if not path.is_file():
        logger.warning("Translation file not found: %s", path)
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _read_file_or_none(path: Path) -> Optional[str]:
    """Read a file returning its content, or None on failure."""
    if not path.is_file():
        logger.warning("File not found: %s", path)
        return None
    return path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Core evaluation pipeline
# ---------------------------------------------------------------------------


def run_full_evaluation(
    rag_output_path: Optional[Path] = None,
    baseline_output_path: Optional[Path] = None,
    reference_path: Optional[Path] = None,
    rag_text: Optional[str] = None,
    baseline_text: Optional[str] = None,
    reference_text: Optional[str] = None,
    key_terms_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> dict:
    """
    Full evaluation pipeline.

    Provide either paths (to read from disk) or direct text strings.
    If both are supplied, text strings take precedence.

    1. Read outputs
    2. Compute BLEU/ROUGE
    3. Compute terminology consistency
    4. Generate report
    """
    # ---- Resolve texts ----
    if rag_text is None and rag_output_path is not None:
        rag_text = _read_file_or_none(rag_output_path)
    if baseline_text is None and baseline_output_path is not None:
        baseline_text = _read_file_or_none(baseline_output_path)
    if reference_text is None and reference_path is not None:
        reference_text = _read_file_or_none(reference_path)

    if rag_text is None or baseline_text is None:
        raise ValueError(
            "Both RAG and baseline outputs are required. "
            f"rag_text={'provided' if rag_text else 'MISSING'}, "
            f"baseline_text={'provided' if baseline_text else 'MISSING'}"
        )

    # If no reference provided, use baseline as reference (relative comparison)
    if reference_text is None:
        logger.warning("No reference provided; using baseline output as reference.")
        reference_text = baseline_text

    # ---- Load key terms ----
    if key_terms_path is not None and key_terms_path.is_file():
        try:
            with open(key_terms_path, "r", encoding="utf-8") as f:
                term_data = json.load(f)
                all_terms: list[tuple[str, str]] = []
                for domain, terms in term_data.items():
                    for entry in terms:
                        all_terms.append((entry["source"], entry["target"]))
            logger.info("Loaded %d key terms from %s", len(all_terms), key_terms_path)
        except Exception as e:
            logger.error("Failed to load key terms from %s: %s", key_terms_path, e)
            all_terms = []
    else:
        all_terms = []

    # ---- BLEU / ROUGE evaluation ----
    logger.info("Computing BLEU/ROUGE scores ...")
    bleu_rouge = BleuRougeEvaluator()
    bleu_rouge_results = bleu_rouge.evaluate_pair(
        baseline_output=baseline_text,
        rag_output=rag_text,
        reference=reference_text,
    )

    # ---- Terminology consistency evaluation ----
    term_results = None
    if all_terms:
        logger.info("Computing terminology consistency ...")
        term_eval = TermConsistencyEvaluator()
        term_eval.set_key_terms(all_terms)
        term_results = term_eval.compare_runs(
            baseline_output=baseline_text,
            rag_output=rag_text,
            key_terms=all_terms,
        )
    else:
        logger.info("No key terms provided; skipping terminology consistency.")

    # ---- Assemble report ----
    report: dict = {
        "metadata": {
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tool": "rag-terminology-evaluation",
            "version": "1.0.0",
        },
        "inputs": {
            "rag_output_path": str(rag_output_path) if rag_output_path else None,
            "baseline_output_path": str(baseline_output_path) if baseline_output_path else None,
            "reference_path": str(reference_path) if reference_path else None,
            "key_terms_path": str(key_terms_path) if key_terms_path else None,
            "has_reference": reference_text is not None,
        },
        "bleu_rouge": bleu_rouge_results,
        "terminology_consistency": term_results,
        "summary": _generate_summary(bleu_rouge_results, term_results),
    }

    # ---- Write output ----
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generate_report(report, output_path)
        logger.info("Report written to %s", output_path)

    return report


def _generate_summary(bleu_rouge_results: dict, term_results: Optional[dict]) -> dict:
    """Generate a concise summary of evaluation results for the report."""
    baseline = bleu_rouge_results.get("baseline", {})
    rag = bleu_rouge_results.get("rag", {})
    delta = bleu_rouge_results.get("delta", {})

    summary = {
        "bleu_rouge": {
            "baseline_bleu": baseline.get("bleu"),
            "rag_bleu": rag.get("bleu"),
            "bleu_delta": delta.get("bleu_delta"),
            "baseline_rouge_l": baseline.get("rouge_l_f"),
            "rag_rouge_l": rag.get("rouge_l_f"),
            "rouge_l_delta": delta.get("rouge_l_f_delta"),
        },
        "terminology": None,
    }

    if term_results is not None:
        term_delta = term_results.get("delta", {})
        baseline_term = term_results.get("baseline", {})
        rag_term = term_results.get("rag", {})
        summary["terminology"] = {
            "baseline_consistency": baseline_term.get("aggregate_consistency"),
            "rag_consistency": rag_term.get("aggregate_consistency"),
            "consistency_delta": term_delta.get("consistency_delta"),
            "improved_term_count": len(term_results.get("improved_terms", [])),
            "regressed_term_count": len(term_results.get("regressed_terms", [])),
        }

    return summary


def generate_report(results: dict, output_path: Path):
    """Generate structured JSON report."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Report saved to %s (%d bytes)", output_path, f.tell())


# ---------------------------------------------------------------------------
# Corpus-level evaluation (multi-paper)
# ---------------------------------------------------------------------------


def run_corpus_evaluation(
    rag_dir: Path,
    baseline_dir: Path,
    reference_dir: Optional[Path] = None,
    key_terms_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> dict:
    """
    Evaluate multiple papers by scanning task output directories.

    Expects directory layout:
        rag_dir/<paper_id>/translated.tex
        baseline_dir/<paper_id>/translated.tex
        reference_dir/<paper_id>/translated.tex   (optional)

    If reference_dir is omitted, baseline outputs serve as reference.
    """
    rag_papers = _discover_paper_ids(rag_dir)
    baseline_papers = _discover_paper_ids(baseline_dir)

    common_papers = sorted(set(rag_papers) & set(baseline_papers))
    if not common_papers:
        logger.warning("No common papers found between RAG and baseline directories.")
        return {"num_papers": 0, "per_paper": [], "corpus_average": {}}

    logger.info(
        "Found %d common papers for corpus evaluation (out of %d RAG, %d baseline).",
        len(common_papers), len(rag_papers), len(baseline_papers),
    )

    # Load key terms
    all_terms: list[tuple[str, str]] = []
    if key_terms_path is not None and key_terms_path.is_file():
        try:
            with open(key_terms_path, "r", encoding="utf-8") as f:
                term_data = json.load(f)
                for domain, terms in term_data.items():
                    for entry in terms:
                        all_terms.append((entry["source"], entry["target"]))
        except Exception as e:
            logger.error("Failed to load key terms: %s", e)

    # Build pair list
    pairs: list[dict] = []
    for paper_id in common_papers:
        rag_text = _read_translation(rag_dir / paper_id)
        baseline_text = _read_translation(baseline_dir / paper_id)

        reference_text = None
        if reference_dir is not None:
            reference_text = _read_translation(reference_dir / paper_id)

        if rag_text is None or baseline_text is None:
            logger.warning("Skipping paper %s: missing translation output.", paper_id)
            continue

        pairs.append({
            "paper_id": paper_id,
            "baseline": baseline_text,
            "rag": rag_text,
            "reference": reference_text or baseline_text,
        })

    if not pairs:
        logger.warning("No valid paper pairs to evaluate.")
        return {"num_papers": 0, "per_paper": [], "corpus_average": {}}

    logger.info("Running corpus evaluation on %d papers ...", len(pairs))

    # BLEU/ROUGE corpus evaluation
    bleu_rouge = BleuRougeEvaluator()
    bleu_rouge_results = bleu_rouge.evaluate_corpus(pairs)

    # Terminology consistency per paper + corpus average
    term_results = None
    if all_terms:
        term_eval = TermConsistencyEvaluator()
        term_eval.set_key_terms(all_terms)

        per_paper_term: list[dict] = []
        for p in pairs:
            term_result = term_eval.compare_runs(
                baseline_output=p["baseline"],
                rag_output=p["rag"],
                key_terms=all_terms,
            )
            term_result["paper_id"] = p["paper_id"]
            per_paper_term.append(term_result)

        # Aggregate terminology consistency
        baseline_consistencies = [
            t["baseline"]["aggregate_consistency"] for t in per_paper_term
        ]
        rag_consistencies = [
            t["rag"]["aggregate_consistency"] for t in per_paper_term
        ]

        term_results = {
            "corpus_average": {
                "baseline_consistency": round(
                    sum(baseline_consistencies) / len(baseline_consistencies), 4
                ),
                "rag_consistency": round(
                    sum(rag_consistencies) / len(rag_consistencies), 4
                ),
                "consistency_delta": round(
                    (sum(rag_consistencies) - sum(baseline_consistencies))
                    / len(rag_consistencies),
                    4,
                ),
            },
            "per_paper": per_paper_term,
        }

    report: dict = {
        "metadata": {
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tool": "rag-terminology-evaluation",
            "version": "1.0.0",
            "type": "corpus_evaluation",
        },
        "inputs": {
            "rag_dir": str(rag_dir),
            "baseline_dir": str(baseline_dir),
            "reference_dir": str(reference_dir) if reference_dir else None,
            "key_terms_path": str(key_terms_path) if key_terms_path else None,
            "num_papers_requested": len(common_papers),
            "num_papers_evaluated": len(pairs),
        },
        "bleu_rouge": bleu_rouge_results,
        "terminology_consistency": term_results,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generate_report(report, output_path)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate baseline vs RAG-enabled translations for graduation-design thesis.",
    )

    # Single-paper evaluation options
    single_group = parser.add_argument_group("Single-paper evaluation")
    single_group.add_argument(
        "--rag-file", type=Path,
        help="Path to RAG-enabled translation output file.",
    )
    single_group.add_argument(
        "--baseline-file", type=Path,
        help="Path to baseline (no RAG) translation output file.",
    )
    single_group.add_argument(
        "--reference-file", type=Path,
        help="Path to reference translation file (optional; if omitted, baseline is used).",
    )

    # Corpus evaluation options
    corpus_group = parser.add_argument_group("Corpus evaluation (multi-paper)")
    corpus_group.add_argument(
        "--rag-dir", type=Path,
        help="Directory containing RAG task outputs (subdirs per paper).",
    )
    corpus_group.add_argument(
        "--baseline-dir", type=Path,
        help="Directory containing baseline task outputs (subdirs per paper).",
    )
    corpus_group.add_argument(
        "--reference-dir", type=Path,
        help="Directory containing reference translations (subdirs per paper).",
    )

    # Task-ID-based lookup
    task_group = parser.add_argument_group("Task-ID-based lookup")
    task_group.add_argument(
        "--task-id", type=str,
        help="RAG task ID. Looks for outputs under --outputs-root/<task-id>/.",
    )
    task_group.add_argument(
        "--baseline-id", type=str,
        help="Baseline task ID. Looks for outputs under --outputs-root/<baseline-id>/.",
    )
    task_group.add_argument(
        "--outputs-root", type=Path, default=_OUTPUTS_ROOT_DEFAULT,
        help="Root directory for task outputs (default: %(default)s).",
    )

    # Common options
    common_group = parser.add_argument_group("Common options")
    common_group.add_argument(
        "--key-terms", type=Path,
        help="Path to JSON file with key terms (default: use built-in defaults).",
    )
    common_group.add_argument(
        "-o", "--output", type=Path, default=Path("evaluation_report.json"),
        help="Output path for the evaluation report JSON (default: %(default)s).",
    )
    common_group.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging.",
    )

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine evaluation mode
    has_single_files = args.rag_file is not None or args.baseline_file is not None
    has_task_ids = args.task_id is not None or args.baseline_id is not None
    has_corpus_dirs = args.rag_dir is not None or args.baseline_dir is not None

    modes = sum([bool(has_single_files), bool(has_task_ids), bool(has_corpus_dirs)])
    if modes > 1:
        parser.error(
            "Conflicting options: specify --rag-file/--baseline-file OR "
            "--rag-dir/--baseline-dir OR --task-id/--baseline-id, not multiple."
        )
    if modes == 0:
        parser.error(
            "No input specified. Use --rag-file/--baseline-file for single-paper, "
            "--rag-dir/--baseline-dir for corpus, or --task-id/--baseline-id for task lookup."
        )

    # ---- Mode: task-ID-based lookup ----
    if has_task_ids:
        if not args.task_id or not args.baseline_id:
            parser.error("Both --task-id and --baseline-id are required for task-ID-based lookup.")

        rag_dir = args.outputs_root / args.task_id
        baseline_dir = args.outputs_root / args.baseline_id
        logger.info(
            "Task-ID mode: RAG=%s (%s), Baseline=%s (%s)",
            args.task_id, rag_dir, args.baseline_id, baseline_dir,
        )

        result = run_corpus_evaluation(
            rag_dir=rag_dir,
            baseline_dir=baseline_dir,
            reference_dir=None,
            key_terms_path=args.key_terms,
            output_path=args.output,
        )

    # ---- Mode: corpus evaluation ----
    elif has_corpus_dirs:
        if not args.rag_dir or not args.baseline_dir:
            parser.error("Both --rag-dir and --baseline-dir are required for corpus evaluation.")

        result = run_corpus_evaluation(
            rag_dir=args.rag_dir,
            baseline_dir=args.baseline_dir,
            reference_dir=args.reference_dir,
            key_terms_path=args.key_terms,
            output_path=args.output,
        )

    # ---- Mode: single-paper file evaluation ----
    else:
        if not args.rag_file or not args.baseline_file:
            parser.error("Both --rag-file and --baseline-file are required for single-paper evaluation.")

        result = run_full_evaluation(
            rag_output_path=args.rag_file,
            baseline_output_path=args.baseline_file,
            reference_path=args.reference_file,
            key_terms_path=args.key_terms,
            output_path=args.output,
        )

    num_papers = (
        result.get("bleu_rouge", {}).get("num_papers")
        or result.get("inputs", {}).get("num_papers_evaluated")
        or 1
    )

    summary = result.get("summary") or result.get("bleu_rouge", {}).get("corpus_average", {})
    logger.info("Evaluation complete: %d paper(s) evaluated.", num_papers)
    logger.info("Report saved to: %s", args.output)

    # Print quick summary to stdout
    print(json.dumps({
        "status": "success",
        "num_papers": num_papers,
        "report_path": str(args.output),
        "summary": summary,
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
