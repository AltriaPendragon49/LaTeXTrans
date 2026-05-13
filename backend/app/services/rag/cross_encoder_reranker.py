from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reranker
# ---------------------------------------------------------------------------


class CrossEncoderReranker:
    """Cross-Encoder reranker for fine-grained candidate term scoring.

    Uses ``sentence-transformers`` ``CrossEncoder`` under the hood.

    Parameters
    ----------
    model_name : str
        HuggingFace cross-encoder model name.
        Defaults to ``"cross-encoder/ms-marco-MiniLM-L-6-v2"``.
    device : str, optional
        Torch device (``"cpu"``, ``"cuda"``).  *None* lets the library decide.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self._device = device
        self._model = None
        self._load_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]
        except ImportError as exc:
            msg = (
                "sentence-transformers is not installed. "
                "Install with: pip install sentence-transformers"
            )
            logger.warning(msg)
            self._load_error = msg
            return

        try:
            logger.info(
                "Loading CrossEncoder model %s (device=%s)",
                self.model_name,
                self._device,
            )
            self._model = CrossEncoder(self.model_name, device=self._device)
            self._load_error = None
        except Exception as exc:
            msg = f"Failed to load CrossEncoder model {self.model_name}: {exc}"
            logger.warning(msg)
            self._load_error = msg

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_n: int = 10,
    ) -> list[dict]:
        """Score candidate terms and return the top ``top_n`` by relevance.

        Parameters
        ----------
        query : str
            The query text (e.g. a LaTeX chunk).
        candidates : list[dict]
            Candidate term dicts.  Each **must** contain a ``"source_term"``
            key.  May also have ``"bm25_score"`` and/or ``"vector_score"``.
        top_n : int
            Number of highest-scoring candidates to return.

        Returns
        -------
        list[dict]
            Input dicts augmented with a ``"rerank_score"`` field, sorted by
            descending ``rerank_score``, truncated to ``top_n``.  On failure
            the original candidates (sorted by their existing scores) are
            returned unchanged.
        """
        if not query or not query.strip() or not candidates:
            return candidates[:top_n] if candidates else []

        # Fallback if model is not available.
        if self._model is None:
            logger.warning(
                "CrossEncoder model not loaded; "
                "falling back to existing candidate scores."
            )
            return self._fallback_sort(candidates, top_n)

        # Build (query, source_term) pairs.
        pairs = []
        valid_candidates = []
        for c in candidates:
            source_term = str(c.get("source_term", "") or "")
            if source_term.strip():
                pairs.append((query, source_term))
                valid_candidates.append(c)

        if not pairs:
            return candidates[:top_n] if candidates else []

        try:
            scores = self._model.predict(pairs)
        except Exception as exc:
            logger.warning("CrossEncoder prediction failed: %s", exc)
            return self._fallback_sort(candidates, top_n)

        for idx, c in enumerate(valid_candidates):
            c["rerank_score"] = float(scores[idx]) if idx < len(scores) else 0.0

        valid_candidates.sort(key=lambda c: c.get("rerank_score", 0.0), reverse=True)
        return valid_candidates[:top_n]

    def is_available(self) -> bool:
        """``True`` if the CrossEncoder model was loaded successfully."""
        return self._model is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_sort(candidates: list[dict], top_n: int) -> list[dict]:
        """Fallback: sort candidates by the best available score."""
        for c in candidates:
            c.setdefault("rerank_score", 0.0)

        def _best_score(c: dict) -> float:
            return max(
                float(c.get("rerank_score", 0.0) or 0.0),
                float(c.get("bm25_score", 0.0) or 0.0),
                float(c.get("vector_score", 0.0) or 0.0),
            )

        candidates.sort(key=_best_score, reverse=True)
        return candidates[:top_n]
