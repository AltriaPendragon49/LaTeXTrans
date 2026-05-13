from __future__ import annotations

import logging
import re
from typing import Any, Optional

from backend.app.services.rag.bm25_retriever import Bm25Retriever
from backend.app.services.rag.cross_encoder_reranker import CrossEncoderReranker
from backend.app.services.rag.embedding_client import EmbeddingClient
from backend.app.services.rag.glossary_formatter import (
    estimate_token_count,
    format_glossary_block,
    truncate_glossary,
)
from backend.app.services.rag.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class RagTerminologyPipeline:
    """Orchestrate the three-stage RAG terminology pipeline.

    Stages
    ------
    1. Query transformation (extract plain-text key phrases from a chunk).
    2. Hybrid retrieval (BM25 keyword + optional Milvus vector).
    3. Cross-Encoder reranking.
    4. Glossary formatting for prompt injection.

    Every stage is fault-tolerant: failures log a warning and fall through
    so translation is never blocked.
    """

    def __init__(
        self,
        bm25_retriever: Bm25Retriever,
        vector_retriever: Optional[VectorRetriever],
        reranker: Optional[CrossEncoderReranker],
        embedding_client: Optional[EmbeddingClient],
        # TerminologyRepository is injected here but may be None until the
        # repository layer is implemented (task 2.3).  It is used for
        # optional MySQL exact/prefix lookups that complement the hybrid
        # retrieval.
        terminology_repository: Optional[Any] = None,
    ) -> None:
        self._bm25 = bm25_retriever
        self._vector = vector_retriever
        self._reranker = reranker
        self._embedding = embedding_client
        self._repo = terminology_repository

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        chunk_text: str,
        *,
        source_lang: str = "en",
        target_lang: str = "zh",
        top_n: int = 10,
        max_glossary_tokens: int = 512,
    ) -> dict:
        """Run the full RAG terminology pipeline for a single chunk.

        Parameters
        ----------
        chunk_text : str
            Plain text (or lightly-cleaned LaTeX) of the chunk being
            translated.
        source_lang : str
            Source language code (unused in this basic implementation but
            reserved for future language-aware retrieval).
        target_lang : str
            Target language code (reserved).
        top_n : int
            How many final terms to include in the glossary block.
        max_glossary_tokens : int
            Maximum token budget for the formatted glossary block.

        Returns
        -------
        dict
            ``{
                "glossary_block": str,
                "selected_terms": list[dict],
                "total_candidates": int,
                "retrieval_sources": list[str],
            }``

            Returns an empty glossary on any unrecoverable failure.
        """
        # -- Stage 1: Query transformation --------------------------------
        query = self._transform_query(chunk_text)
        if not query:
            return self._empty_result()

        retrieval_sources: list[str] = []

        # -- Stage 2a: BM25 retrieval ------------------------------------
        bm25_candidates = self._safe_bm25_search(query, top_n=top_n * 2)
        if bm25_candidates:
            retrieval_sources.append("bm25")

        # -- Stage 2b: Vector retrieval ----------------------------------
        vector_candidates: list[dict] = []
        if self._vector is not None and self._embedding is not None:
            vector_candidates = self._safe_vector_search(query, top_n=top_n * 2)
            if vector_candidates:
                retrieval_sources.append("vector")

        # -- Optional MySQL exact/prefix lookup ---------------------------
        repo_candidates: list[dict] = []
        if self._repo is not None:
            try:
                repo_candidates = self._safe_repo_search(
                    query, source_lang, target_lang, top_n=top_n
                )
                if repo_candidates:
                    retrieval_sources.append("repository")
            except Exception:
                logger.warning("Repository search failed; skipping.", exc_info=True)

        # -- Stage 3: Merge & deduplicate ---------------------------------
        merged = self._merge_candidates(bm25_candidates, vector_candidates)
        merged = self._merge_candidates(merged, repo_candidates)

        if not merged:
            return self._empty_result()

        total_candidates = len(merged)

        # -- Stage 4: Cross-Encoder reranking -----------------------------
        if self._reranker is not None and self._reranker.is_available():
            try:
                reranked = self._reranker.rerank(query, merged, top_n=top_n)
                if reranked:
                    retrieval_sources.append("reranker")
            except Exception as exc:
                logger.warning("Reranker failed; using merged scores: %s", exc)
                reranked = self._score_merge_sort(merged)[:top_n]
        else:
            reranked = self._score_merge_sort(merged)[:top_n]

        selected_terms = reranked[:top_n]

        # -- Stage 5: Format glossary ------------------------------------
        glossary_block = format_glossary_block(selected_terms)

        # Apply token budget truncation if needed.
        if glossary_block and max_glossary_tokens > 0:
            estimated = estimate_token_count(glossary_block)
            if estimated > max_glossary_tokens:
                glossary_block = truncate_glossary(glossary_block, max_glossary_tokens)

        return {
            "glossary_block": glossary_block,
            "selected_terms": selected_terms,
            "total_candidates": total_candidates,
            "retrieval_sources": retrieval_sources,
        }

    # ------------------------------------------------------------------
    # Index maintenance
    # ------------------------------------------------------------------

    def refresh_indexes(self, approved_terms: list[dict]) -> None:
        """Rebuild the BM25 index from a fresh list of approved terms.

        Parameters
        ----------
        approved_terms : list[dict]
            List of approved term dicts, each with at least ``id`` and
            ``source_term``.
        """
        try:
            self._bm25.refresh(approved_terms)
            logger.info("BM25 index refreshed with %d terms", len(approved_terms))
        except Exception as exc:
            logger.warning("Failed to refresh BM25 index: %s", exc)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """``True`` when the BM25 index is built and ready for retrieval."""
        return self._bm25.is_ready

    # ------------------------------------------------------------------
    # Internal: query transformation
    # ------------------------------------------------------------------

    @staticmethod
    def _transform_query(chunk_text: str) -> str:
        """Extract a plain-text query from a LaTeX chunk.

        Currently strips minimal LaTeX constructs and returns the cleaned
        text as-is.  Future versions may extract key phrases or noun
        chunks.
        """
        if not chunk_text or not chunk_text.strip():
            return ""

        text = chunk_text.strip()

        # Remove common LaTeX commands and braces for cleaner query text.
        text = re.sub(r"\\(?:textbf|textit|emph|textsf|texttt)\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+(?:\{[^}]*\})?", "", text)
        text = re.sub(r"[{}]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    # ------------------------------------------------------------------
    # Internal: safe wrappers
    # ------------------------------------------------------------------

    def _safe_bm25_search(self, query: str, top_n: int) -> list[dict]:
        try:
            return self._bm25.search(query, top_n=top_n)
        except Exception as exc:
            logger.warning("BM25 search error: %s", exc)
            return []

    def _safe_vector_search(self, query: str, top_n: int) -> list[dict]:
        try:
            embedding = self._embedding.encode([query])
            if not embedding:
                return []
            return self._vector.search(embedding[0], top_n=top_n)
        except Exception as exc:
            logger.warning("Vector search error: %s", exc)
            return []

    def _safe_repo_search(
        self,
        query: str,
        source_lang: str,
        target_lang: str,
        top_n: int,
    ) -> list[dict]:
        """Delegate to TerminologyRepository.exact_search if available.

        The repository interface is expected to expose an ``exact_search``
        method that returns a list of candidate dicts with the same shape
        as BM25/vector results.
        """
        if not hasattr(self._repo, "search_approved_terms"):
            return []
        return self._repo.search_approved_terms(
            query=query,
            source_lang=source_lang,
            target_lang=target_lang,
        )[:top_n]

    # ------------------------------------------------------------------
    # Internal: merging & sorting
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_candidates(
        *candidate_lists: list[dict],
    ) -> list[dict]:
        """Deduplicate candidates by ``term_id``, keeping the higher score.

        Score preference order: ``rerank_score`` > ``vector_score`` >
        ``bm25_score``.  When a term appears from multiple sources the
        entry with the highest effective score is kept.
        """
        merged: dict[str, dict] = {}

        for candidates in candidate_lists:
            for c in candidates:
                tid = c.get("term_id")
                if tid is None:
                    continue

                if tid in merged:
                    existing = merged[tid]
                    # Pick the candidate with a better effective score.
                    if _effective_score(c) > _effective_score(existing):
                        merged[tid] = c
                else:
                    merged[tid] = c

        return list(merged.values())

    @staticmethod
    def _score_merge_sort(candidates: list[dict]) -> list[dict]:
        """Sort candidates by the best available relevance score."""
        candidates.sort(key=_effective_score, reverse=True)
        return candidates

    @staticmethod
    def _empty_result() -> dict:
        return {
            "glossary_block": "",
            "selected_terms": [],
            "total_candidates": 0,
            "retrieval_sources": [],
        }


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _effective_score(candidate: dict) -> float:
    """Return the highest available relevance score for a candidate."""
    return max(
        float(candidate.get("rerank_score", 0.0) or 0.0),
        float(candidate.get("vector_score", 0.0) or 0.0),
        float(candidate.get("bm25_score", 0.0) or 0.0),
    )
