from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class EmbeddingError(RuntimeError):
    """Raised when embedding generation fails."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class EmbeddingClient:
    """Generate text embeddings using sentence-transformers.

    Parameters
    ----------
    model_name : str
        HuggingFace model name compatible with ``sentence-transformers``.
        Defaults to ``"sentence-transformers/all-MiniLM-L6-v2"`` (384-d).
    device : str, optional
        Torch device string (e.g. ``"cpu"``, ``"cuda"``).  If *None* the
        library chooses automatically.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self._device = device
        self._model = None

    # ------------------------------------------------------------------
    # Lazy-load the model so missing dependencies don't break imports
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
        except ImportError as exc:
            raise EmbeddingError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        logger.info(
            "Loading embedding model %s (device=%s)", self.model_name, self._device
        )
        self._model = SentenceTransformer(self.model_name, device=self._device)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts into dense vector embeddings.

        Parameters
        ----------
        texts : list[str]
            One or more text strings to embed.

        Returns
        -------
        list[list[float]]
            Embeddings, one per input text.

        Raises
        ------
        EmbeddingError
            If the model failed to load or encoding raised an error.
        """
        if not texts:
            return []

        try:
            self._load_model()
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(f"Failed to load embedding model: {exc}") from exc

        try:
            embeddings = self._model.encode(texts, show_progress_bar=False)
            return [emb.tolist() for emb in embeddings]
        except Exception as exc:
            logger.warning("Embedding encoding failed: %s", exc)
            raise EmbeddingError(f"Embedding encoding failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------


def compute_similarity(embedding1: list[float], embedding2: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors.

    Parameters
    ----------
    embedding1, embedding2 : list[float]
        Dense vectors of equal length.

    Returns
    -------
    float
        Cosine similarity in ``[-1, 1]``.  Returns ``0.0`` on zero-vector
        input or if the lengths differ.
    """
    if len(embedding1) != len(embedding2):
        logger.warning(
            "Embedding dimension mismatch: %d vs %d",
            len(embedding1),
            len(embedding2),
        )
        return 0.0

    dot = sum(a * b for a, b in zip(embedding1, embedding2))
    norm1 = sum(a * a for a in embedding1) ** 0.5
    norm2 = sum(b * b for b in embedding2) ** 0.5

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (norm1 * norm2)
