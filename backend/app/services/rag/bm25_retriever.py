from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default tokenizer
# ---------------------------------------------------------------------------

_WORD_SPLIT_RE = re.compile(r"[^\w]+")


def _default_tokenize(text: str) -> list[str]:
    """Lower-case tokenisation on whitespace and common punctuation."""
    return [t for t in _WORD_SPLIT_RE.split(text.lower()) if t]


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class Bm25Retriever:
    """In-memory BM25 keyword retriever for approved terminology terms.

    Uses the ``rank_bm25`` library (BM25Okapi variant) under the hood.

    Parameters
    ----------
    tokenizer : callable, optional
        Callable ``(str) -> list[str]`` used to tokenise both index terms
        and queries.  Defaults to a lower-case split on non-word characters.
    """

    def __init__(self, tokenizer=None) -> None:
        self._tokenizer = tokenizer or _default_tokenize
        self._terms: list[dict] = []
        self._bm25 = None
        self._ready = False

    # ------------------------------------------------------------------
    # Index building / refresh
    # ------------------------------------------------------------------

    def build_index(self, terms: list[dict]) -> None:
        """Tokenise ``source_term`` from each entry and build the BM25 index.

        Parameters
        ----------
        terms : list[dict]
            Each dict **must** contain the keys ``id`` and ``source_term``.
            Additional keys (``target_term``, ``language_pair``, …) are
            preserved as-is in the internal term store.
        """
        try:
            from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
        except ImportError as exc:
            logger.warning(
                "rank_bm25 is not installed; BM25 retrieval will be unavailable. "
                "Install with: pip install rank-bm25"
            )
            self._terms = list(terms) if terms else []
            self._bm25 = None
            self._ready = False
            return

        self._terms = list(terms) if terms else []

        if not self._terms:
            self._bm25 = BM25Okapi([])
            self._ready = True
            logger.info("BM25 index built (empty corpus)")
            return

        tokenized_corpus = [
            self._tokenizer(str(t.get("source_term", ""))) for t in self._terms
        ]
        self._bm25 = BM25Okapi(tokenized_corpus)
        self._ready = True
        logger.info("BM25 index built with %d terms", len(self._terms))

    def refresh(self, terms: list[dict]) -> None:
        """Rebuild the BM25 index from scratch.

        Equivalent to calling :meth:`build_index` with the new term list.
        """
        self.build_index(terms)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(self, query: str, top_n: int = 20) -> list[dict]:
        """Score every indexed term against *query* and return top ``top_n``.

        Parameters
        ----------
        query : str
            Free-text query (e.g. a LaTeX chunk).
        top_n : int
            Maximum number of candidate terms to return.

        Returns
        -------
        list[dict]
            Each dict has the shape::

                {
                    "term_id": …,
                    "source_term": …,
                    "target_term": …,
                    "bm25_score": float,
                    "retrieval_source": "bm25",
                }

            Returns an empty list when not ready or on error.
        """
        if not self._ready or self._bm25 is None or not self._terms:
            return []

        if not query or not query.strip():
            return []

        try:
            tokenized_query = self._tokenizer(query)
            scores = self._bm25.get_scores(tokenized_query)
        except Exception as exc:
            logger.warning("BM25 search failed: %s", exc)
            return []

        candidates = []
        for idx, term in enumerate(self._terms):
            score = float(scores[idx]) if idx < len(scores) else 0.0
            candidates.append(
                {
                    "term_id": term.get("id"),
                    "source_term": str(term.get("source_term", "")),
                    "target_term": str(term.get("target_term", "")),
                    "bm25_score": score,
                    "retrieval_source": "bm25",
                }
            )

        candidates.sort(key=lambda c: c["bm25_score"], reverse=True)
        return candidates[:top_n]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """``True`` when the BM25 index has been successfully built."""
        return self._ready
