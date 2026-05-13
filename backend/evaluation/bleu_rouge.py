"""
BLEU and ROUGE evaluation for comparing baseline vs RAG-enabled translations.
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import nltk for BLEU, with graceful fallback
try:
    from nltk.translate.bleu_score import sentence_bleu, corpus_bleu, SmoothingFunction
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False
    logger.warning("nltk not available, BLEU scoring will use fallback")

# Try to import rouge_score
try:
    from rouge_score import rouge_scorer
    HAS_ROUGE = True
except ImportError:
    HAS_ROUGE = False
    logger.warning("rouge_score not available, ROUGE scoring will use fallback")


def _tokenize(text: str) -> list[str]:
    """Simple whitespace tokenization, lowercased."""
    return text.lower().split()


def _get_ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    """Generate n-grams from token list."""
    if n <= 0 or len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _count_ngrams(tokens: list[str], n: int) -> dict[tuple[str, ...], int]:
    """Count n-gram occurrences."""
    counts: dict[tuple[str, ...], int] = {}
    for ng in _get_ngrams(tokens, n):
        counts[ng] = counts.get(ng, 0) + 1
    return counts


def _clipped_precision(
    reference_counts: dict[tuple[str, ...], int],
    hypothesis_counts: dict[tuple[str, ...], int],
) -> int:
    """Sum of min(hyp_count, ref_count) across all n-grams in hypothesis."""
    total = 0
    for ng, hyp_cnt in hypothesis_counts.items():
        total += min(hyp_cnt, reference_counts.get(ng, 0))
    return total


def _simple_bleu(reference_tokens: list[str], hypothesis_tokens: list[str], max_n: int = 4) -> dict:
    """
    BLEU-like scoring without nltk dependency.

    Implements modified n-gram precision with brevity penalty.
    Returns dict with keys: bleu_1, bleu_2, bleu_3, bleu_4, bleu.
    """
    if not hypothesis_tokens:
        return {"bleu_1": 0.0, "bleu_2": 0.0, "bleu_3": 0.0, "bleu_4": 0.0, "bleu": 0.0}

    ref_len = len(reference_tokens)
    hyp_len = len(hypothesis_tokens)

    precisions = []
    for n in range(1, max_n + 1):
        ref_counts = _count_ngrams(reference_tokens, n)
        hyp_counts = _count_ngrams(hypothesis_tokens, n)
        clipped = _clipped_precision(ref_counts, hyp_counts)
        total = sum(hyp_counts.values())
        if total == 0:
            precisions.append(0.0)
        else:
            precisions.append(clipped / total)

    # Brevity penalty
    if hyp_len == 0:
        bp = 0.0
    elif hyp_len > ref_len:
        bp = 1.0
    else:
        bp = 2.718281828459045 ** (1.0 - ref_len / hyp_len)

    # Geometric mean of precisions
    if any(p == 0.0 for p in precisions):
        bleu = 0.0
    else:
        log_avg = sum(1.0 / max_n * __import__("math").log(p) for p in precisions)
        bleu = bp * (2.718281828459045 ** log_avg)

    result: dict = {}
    for i, p in enumerate(precisions, 1):
        result[f"bleu_{i}"] = round(p, 6)
    result["bleu"] = round(bleu, 6)
    return result


def _lcs_length(X: list[str], Y: list[str]) -> int:
    """Compute the length of the longest common subsequence between two token lists."""
    m, n = len(X), len(Y)
    # Use 1D DP array for memory efficiency
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if X[i - 1] == Y[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, [0] * (n + 1)
    return prev[n]


def _simple_rouge_lcs(reference_tokens: list[str], hypothesis_tokens: list[str]) -> dict:
    """
    ROUGE-L computation using longest common subsequence.
    Returns dict with: rouge_l_p, rouge_l_r, rouge_l_f.
    """
    if not reference_tokens or not hypothesis_tokens:
        return {"rouge_l_p": 0.0, "rouge_l_r": 0.0, "rouge_l_f": 0.0}

    lcs = _lcs_length(hypothesis_tokens, reference_tokens)
    ref_len = len(reference_tokens)
    hyp_len = len(hypothesis_tokens)

    if hyp_len == 0:
        precision = 0.0
    else:
        precision = lcs / hyp_len

    if ref_len == 0:
        recall = 0.0
    else:
        recall = lcs / ref_len

    if precision + recall == 0.0:
        f1 = 0.0
    else:
        f1 = 2.0 * precision * recall / (precision + recall)

    return {
        "rouge_l_p": round(precision, 6),
        "rouge_l_r": round(recall, 6),
        "rouge_l_f": round(f1, 6),
    }


def _simple_rouge_n(reference_tokens: list[str], hypothesis_tokens: list[str], n: int) -> dict:
    """
    ROUGE-N computation using simple n-gram overlap.
    Returns dict with: rouge_{n}_p, rouge_{n}_r, rouge_{n}_f.
    """
    prefix = f"rouge_{n}"
    if not reference_tokens or not hypothesis_tokens:
        return {f"{prefix}_p": 0.0, f"{prefix}_r": 0.0, f"{prefix}_f": 0.0}

    ref_ngrams = _count_ngrams(reference_tokens, n)
    hyp_ngrams = _count_ngrams(hypothesis_tokens, n)

    if not ref_ngrams or not hyp_ngrams:
        return {f"{prefix}_p": 0.0, f"{prefix}_r": 0.0, f"{prefix}_f": 0.0}

    overlap = 0
    for ng, hyp_cnt in hyp_ngrams.items():
        overlap += min(hyp_cnt, ref_ngrams.get(ng, 0))

    hyp_total = sum(hyp_ngrams.values())
    ref_total = sum(ref_ngrams.values())

    precision = overlap / hyp_total if hyp_total > 0 else 0.0
    recall = overlap / ref_total if ref_total > 0 else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        f"{prefix}_p": round(precision, 6),
        f"{prefix}_r": round(recall, 6),
        f"{prefix}_f": round(f1, 6),
    }


class BleuRougeEvaluator:
    """Computes BLEU and ROUGE scores comparing translation outputs."""

    def __init__(self):
        self._smooth_fn = None
        if HAS_NLTK:
            try:
                self._smooth_fn = SmoothingFunction().method1
            except Exception:
                logger.warning("Failed to create nltk SmoothingFunction", exc_info=True)

    def compute_bleu(self, reference: str, hypothesis: str) -> dict:
        """
        Compute sentence-level BLEU score.

        Returns dict with: bleu_1, bleu_2, bleu_3, bleu_4, bleu.
        """
        ref_tokens = _tokenize(reference)
        hyp_tokens = _tokenize(hypothesis)

        if not hyp_tokens:
            return {"bleu_1": 0.0, "bleu_2": 0.0, "bleu_3": 0.0, "bleu_4": 0.0, "bleu": 0.0}

        if HAS_NLTK:
            try:
                bleu = sentence_bleu(
                    [ref_tokens],
                    hyp_tokens,
                    weights=(0.25, 0.25, 0.25, 0.25),
                    smoothing_function=self._smooth_fn,
                )
                # Also get individual n-gram scores
                bleu_1 = sentence_bleu([ref_tokens], hyp_tokens, weights=(1, 0, 0, 0),
                                       smoothing_function=self._smooth_fn)
                bleu_2 = sentence_bleu([ref_tokens], hyp_tokens, weights=(0.5, 0.5, 0, 0),
                                       smoothing_function=self._smooth_fn)
                bleu_3 = sentence_bleu([ref_tokens], hyp_tokens, weights=(0.33, 0.33, 0.34, 0),
                                       smoothing_function=self._smooth_fn)
                bleu_4 = sentence_bleu([ref_tokens], hyp_tokens, weights=(0.25, 0.25, 0.25, 0.25),
                                       smoothing_function=self._smooth_fn)
                return {
                    "bleu_1": round(bleu_1, 6),
                    "bleu_2": round(bleu_2, 6),
                    "bleu_3": round(bleu_3, 6),
                    "bleu_4": round(bleu_4, 6),
                    "bleu": round(bleu, 6),
                }
            except Exception as e:
                logger.warning("nltk sentence_bleu failed, falling back to simple BLEU: %s", e)

        return _simple_bleu(ref_tokens, hyp_tokens)

    def compute_rouge(self, reference: str, hypothesis: str) -> dict:
        """
        Compute ROUGE-1, ROUGE-2, ROUGE-L scores.

        Returns dict with:
            rouge_1_f, rouge_1_p, rouge_1_r,
            rouge_2_f, rouge_2_p, rouge_2_r,
            rouge_l_f, rouge_l_p, rouge_l_r.
        """
        ref_tokens = _tokenize(reference)
        hyp_tokens = _tokenize(hypothesis)

        if HAS_ROUGE:
            try:
                scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=False)
                scores = scorer.score(reference, hypothesis)
                result: dict = {}
                for key, score in scores.items():
                    mapping_key = "rouge_l" if key == "rougeL" else key.replace("rouge", "rouge_")
                    result[f"{mapping_key}_p"] = round(score.precision, 6)
                    result[f"{mapping_key}_r"] = round(score.recall, 6)
                    result[f"{mapping_key}_f"] = round(score.fmeasure, 6)
                return result
            except Exception as e:
                logger.warning("rouge_scorer failed, falling back to simple ROUGE: %s", e)

        result = {}
        result.update(_simple_rouge_n(ref_tokens, hyp_tokens, 1))
        result.update(_simple_rouge_n(ref_tokens, hyp_tokens, 2))
        result.update(_simple_rouge_lcs(ref_tokens, hyp_tokens))
        return result

    def evaluate_pair(
        self,
        baseline_output: str,
        rag_output: str,
        reference: str,
    ) -> dict:
        """
        Full evaluation of a pair of translations against reference.

        Returns dict with:
        {
            "baseline": {bleu, rouge_1_f, rouge_2_f, rouge_l_f},
            "rag": {bleu, rouge_1_f, rouge_2_f, rouge_l_f},
            "delta": {bleu_delta, rouge_1_f_delta, rouge_2_f_delta, rouge_l_f_delta}
        }
        """
        baseline_bleu = self.compute_bleu(reference, baseline_output)
        baseline_rouge = self.compute_rouge(reference, baseline_output)
        rag_bleu = self.compute_bleu(reference, rag_output)
        rag_rouge = self.compute_rouge(reference, rag_output)

        def _extract(bleu_scores: dict, rouge_scores: dict) -> dict:
            return {
                "bleu": bleu_scores.get("bleu", 0.0),
                "bleu_1": bleu_scores.get("bleu_1", 0.0),
                "bleu_2": bleu_scores.get("bleu_2", 0.0),
                "bleu_3": bleu_scores.get("bleu_3", 0.0),
                "bleu_4": bleu_scores.get("bleu_4", 0.0),
                "rouge_1_f": rouge_scores.get("rouge_1_f", 0.0),
                "rouge_1_p": rouge_scores.get("rouge_1_p", 0.0),
                "rouge_1_r": rouge_scores.get("rouge_1_r", 0.0),
                "rouge_2_f": rouge_scores.get("rouge_2_f", 0.0),
                "rouge_2_p": rouge_scores.get("rouge_2_p", 0.0),
                "rouge_2_r": rouge_scores.get("rouge_2_r", 0.0),
                "rouge_l_f": rouge_scores.get("rouge_l_f", 0.0),
                "rouge_l_p": rouge_scores.get("rouge_l_p", 0.0),
                "rouge_l_r": rouge_scores.get("rouge_l_r", 0.0),
            }

        baseline_flat = _extract(baseline_bleu, baseline_rouge)
        rag_flat = _extract(rag_bleu, rag_rouge)

        delta: dict = {}
        for key in baseline_flat:
            if key in rag_flat:
                delta[f"{key}_delta"] = round(rag_flat[key] - baseline_flat[key], 6)

        return {
            "baseline": baseline_flat,
            "rag": rag_flat,
            "delta": delta,
        }

    def evaluate_corpus(self, pairs: list[dict]) -> dict:
        """
        Evaluate multiple papers.

        Args:
            pairs: list of dicts, each containing:
                - baseline: str, baseline translation output
                - rag: str, RAG-enabled translation output
                - reference: str, reference translation
                - paper_id: Optional[str], paper identifier

        Returns:
            Aggregated stats with per-paper results and corpus-averaged scores.
        """
        if not pairs:
            return {
                "num_papers": 0,
                "corpus_average": {},
                "per_paper": [],
            }

        per_paper: list[dict] = []
        for item in pairs:
            paper_id = item.get("paper_id", "unknown")
            result = self.evaluate_pair(
                baseline_output=item["baseline"],
                rag_output=item["rag"],
                reference=item["reference"],
            )
            result["paper_id"] = paper_id
            per_paper.append(result)

        # Corpus-level averages
        corpus_baseline: dict[str, float] = {}
        corpus_rag: dict[str, float] = {}
        corpus_delta: dict[str, float] = {}

        metric_keys = [
            "bleu", "bleu_1", "bleu_2", "bleu_3", "bleu_4",
            "rouge_1_f", "rouge_1_p", "rouge_1_r",
            "rouge_2_f", "rouge_2_p", "rouge_2_r",
            "rouge_l_f", "rouge_l_p", "rouge_l_r",
        ]

        for key in metric_keys:
            baseline_vals = [p["baseline"][key] for p in per_paper]
            rag_vals = [p["rag"][key] for p in per_paper]
            delta_key = f"{key}_delta"
            delta_vals = [p["delta"][delta_key] for p in per_paper]

            corpus_baseline[key] = round(sum(baseline_vals) / len(baseline_vals), 6)
            corpus_rag[key] = round(sum(rag_vals) / len(rag_vals), 6)
            corpus_delta[delta_key] = round(sum(delta_vals) / len(delta_vals), 6)

        return {
            "num_papers": len(pairs),
            "corpus_average": {
                "baseline": corpus_baseline,
                "rag": corpus_rag,
                "delta": corpus_delta,
            },
            "per_paper": per_paper,
        }
