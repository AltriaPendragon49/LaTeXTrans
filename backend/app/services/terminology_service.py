"""Orchestrating service for RAG terminology management.

Connects the terminology repository, knowledge-base importers,
extraction pipeline, and the RAG terminology pipeline together.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from backend.app.core.config import get_settings
from backend.app.repositories import TerminologyRepository

from backend.app.services.rag.knowledge_base.csv_importer import (
    ImporterResult,
    parse_csv_content,
    validate_row,
)
from backend.app.services.rag.knowledge_base.bibtex_parser import (
    extract_term_candidates as bibtex_extract_candidates,
    parse_bibtex_content,
)
from backend.app.services.rag.knowledge_base.extractor import (
    extract_terms_from_translation as run_extraction,
)

logger = logging.getLogger(__name__)

# Lazy pipeline imports — external deps may not be installed
_pipeline_imported = False
RagTerminologyPipeline = None
Bm25Retriever = None
VectorRetriever = None
CrossEncoderReranker = None
EmbeddingClient = None


def _import_pipeline_deps():
    global _pipeline_imported, RagTerminologyPipeline, Bm25Retriever, VectorRetriever, CrossEncoderReranker, EmbeddingClient
    if _pipeline_imported:
        return True
    try:
        from backend.app.services.rag.pipeline import RagTerminologyPipeline as _R  # noqa: N812
        from backend.app.services.rag.bm25_retriever import Bm25Retriever as _B  # noqa: N812
        from backend.app.services.rag.embedding_client import EmbeddingClient as _E  # noqa: N812
        from backend.app.services.rag.vector_retriever import VectorRetriever as _V  # noqa: N812
        from backend.app.services.rag.cross_encoder_reranker import CrossEncoderReranker as _C  # noqa: N812
        RagTerminologyPipeline = _R
        Bm25Retriever = _B
        VectorRetriever = _V
        CrossEncoderReranker = _C
        EmbeddingClient = _E
        _pipeline_imported = True
        return True
    except ImportError:
        logger.warning("RAG pipeline dependencies not available; pipeline features disabled.")
        return False


class TerminologyService:
    """High-level service for RAG terminology operations.

    Wraps TerminologyRepository and provides ingestion, retrieval,
    review, and index-management workflows.  Integrates the full
    RAG terminology pipeline (BM25 + Vector + Cross-Encoder) when
    external dependencies are installed.
    """

    def __init__(self, *, repository: Optional[TerminologyRepository] = None):
        self._settings = get_settings()
        self._repository = repository or TerminologyRepository()
        self._pipeline: Any = None
        self._last_bm25_refresh: float = 0.0

    # ---- Feature flag ----

    @property
    def is_enabled(self) -> bool:
        """Whether RAG terminology is enabled at the server level."""
        return bool(
            getattr(self._settings, "rag_terminology_enabled", False)
        )

    # ---- Lazy pipeline initialisation ----

    def _get_pipeline(self) -> Any:
        """Return a cached RagTerminologyPipeline, building it on first call."""
        if not _import_pipeline_deps():
            return None

        now = time.time()

        # Return existing pipeline if still fresh
        if self._pipeline is not None:
            refresh_interval = getattr(self._settings, "rag_terminology_bm25_refresh_interval", 60)
            if now - self._last_bm25_refresh > refresh_interval:
                try:
                    approved = self._repository.get_all_approved_terms(source_lang="en")
                    self._pipeline.refresh_indexes(approved)
                    self._last_bm25_refresh = now
                except Exception:
                    logger.warning("Failed to refresh BM25 index", exc_info=True)
            return self._pipeline

        # Build pipeline from settings
        try:
            bm25 = Bm25Retriever()
            vector = None  # type: Any
            reranker = None  # type: Any
            embedding = None  # type: Any

            approved = self._repository.get_all_approved_terms(source_lang="en")
            if approved:
                bm25.build_index(approved)
                self._last_bm25_refresh = now

            milvus_uri = getattr(self._settings, "rag_terminology_milvus_uri", None)
            if milvus_uri:
                try:
                    embedding = EmbeddingClient(
                        model_name=getattr(self._settings, "rag_terminology_embedding_model",
                                           "sentence-transformers/all-MiniLM-L6-v2"),
                    )
                    vector = VectorRetriever(
                        uri=milvus_uri,
                        collection_name=getattr(self._settings, "rag_terminology_milvus_collection",
                                                "terminology_terms"),
                    )
                    vector.ensure_collection()
                    reranker = CrossEncoderReranker(
                        model_name=getattr(self._settings, "rag_terminology_rerank_model",
                                           "cross-encoder/ms-marco-MiniLM-L-6-v2"),
                    )
                except Exception:
                    logger.warning("Failed to initialise vector/reranker components", exc_info=True)

            self._pipeline = RagTerminologyPipeline(
                bm25_retriever=bm25,
                vector_retriever=vector,
                reranker=reranker,
                embedding_client=embedding,
                terminology_repository=self._repository,
            )
            logger.info("RAG terminology pipeline initialised")
        except Exception:
            logger.exception("Failed to build RAG pipeline")

        return self._pipeline

    # ---- Ingestion ----

    def import_csv(
        self, content: str | bytes, user_id: str, task_id: Optional[str] = None
    ) -> ImporterResult:
        """Parse and import a CSV file into the terminology database.

        Args:
            content: Raw CSV content.
            user_id: The importing user's ID.
            task_id: Optional originating task ID for provenance.

        Returns:
            An ImporterResult summarising accepted/rejected rows.
        """
        rows = parse_csv_content(content)
        if not rows:
            return ImporterResult(
                accepted=0, rejected=0, errors=["No valid rows found in CSV"]
            )

        accepted: list[dict[str, Any]] = []
        errors: list[str] = []

        for i, row in enumerate(rows):
            error = validate_row(row)
            if error:
                errors.append(f"Row {i + 1}: {error}")
                continue
            accepted.append(
                {
                    "source_term": row.get("source_term", "").strip(),
                    "target_term": row.get("target_term", "").strip(),
                    "source_lang": row.get("source_lang", "en"),
                    "target_lang": row.get("target_lang", "zh"),
                    "domain": row.get("domain"),
                    "source_type": "imported",
                    "owner_user_id": user_id,
                    "created_by_user_id": user_id,
                    "extracted_from_task_id": task_id,
                }
            )

        if not accepted:
            return ImporterResult(
                accepted=0,
                rejected=len(rows),
                errors=errors,
                term_ids=[],
            )

        try:
            term_ids = self._repository.insert_terms_batch(accepted)
        except Exception:
            logger.exception("Failed to insert CSV terms batch")
            return ImporterResult(
                accepted=0,
                rejected=len(accepted),
                errors=["Database error during batch insert"],
                term_ids=[],
            )

        return ImporterResult(
            accepted=len(accepted),
            rejected=len(rows) - len(accepted),
            errors=errors,
            term_ids=term_ids,
        )

    def import_bibtex(
        self, content: str, user_id: str, task_id: Optional[str] = None
    ) -> list[str]:
        """Parse and import terms from a BibTeX file.

        Extracts term candidates from BibTeX entry titles and inserts
        them as pending-review terms.

        Args:
            content: Raw .bib content.
            user_id: The importing user's ID.
            task_id: Optional originating task ID.

        Returns:
            List of inserted term IDs.
        """
        entries = parse_bibtex_content(content)
        if not entries:
            logger.warning("No entries found in BibTeX content")
            return []

        candidates = bibtex_extract_candidates(entries)

        if not candidates:
            return []

        terms: list[dict[str, Any]] = []
        for cand in candidates:
            terms.append(
                {
                    "source_term": cand["source_term"],
                    "target_term": cand.get("target_term", ""),
                    "source_lang": "en",
                    "target_lang": "zh",
                    "domain": cand.get("domain"),
                    "source_type": "bibtex_imported",
                    "owner_user_id": user_id,
                    "created_by_user_id": user_id,
                    "extracted_from_task_id": task_id,
                    "provenance": cand.get("provenance"),
                }
            )

        try:
            return self._repository.insert_terms_batch(terms)
        except Exception:
            logger.exception("Failed to insert BibTeX terms batch")
            return []

    def extract_and_store(
        self,
        task_id: str,
        source_text: str,
        target_text: str,
        llm_extract_fn: Optional[
            Callable[[str, str], list[tuple[str, str]]]
        ] = None,
        user_id: Optional[str] = None,
    ) -> list[str]:
        """Extract term pairs from a translation and store as pending terms.

        Args:
            task_id: The translation task ID for provenance.
            source_text: Source-language text.
            target_text: Target-language (translated) text.
            llm_extract_fn: Optional LLM-based extraction callable.
            user_id: Optional user ID (defaults to "system").

        Returns:
            List of inserted term IDs.
        """
        result = run_extraction(source_text, target_text, llm_extract_fn)
        if not result.extracted_terms:
            return []

        terms: list[dict[str, Any]] = []
        for term in result.extracted_terms:
            terms.append(
                {
                    "source_term": term["source_term"],
                    "target_term": term.get("target_term", ""),
                    "source_lang": "en",
                    "target_lang": "zh",
                    "domain": term.get("domain", ""),
                    "source_type": "auto_extracted",
                    "owner_user_id": user_id or "system",
                    "created_by_user_id": user_id or "system",
                    "extracted_from_task_id": task_id,
                }
            )

        if not terms:
            return []

        try:
            return self._repository.insert_terms_batch(terms)
        except Exception:
            logger.exception("Failed to insert auto-extracted terms")
            return []

    # ---- Retrieval (full RAG pipeline with fallback) ----

    def get_rag_glossary(
        self,
        chunk_text: str,
        *,
        source_lang: str = "en",
        target_lang: str = "zh",
        top_n: int = 10,
        domain: Optional[str] = None,
    ) -> dict[str, Any]:
        """Build a glossary block for a text chunk from approved terms.

        Uses the full RAG pipeline (BM25 + optional Vector + optional
        Cross-Encoder reranking) when available.  Falls back to simple
        substring matching if the pipeline is not ready.

        Args:
            chunk_text: The source-language chunk to look up terms for.
            source_lang: Source language code.
            target_lang: Target language code.
            top_n: Maximum number of terms to return (default 10).
            domain: Optional domain filter. When set, only terms from this
                    domain are returned. Pass ``None`` or ``"*"`` to return
                    all domains.

        Returns:
            Dict with keys:
              - ``terms``: list of matched term dicts
              - ``glossary_block``: formatted glossary string
              - ``match_count``: number of unique terms matched
        """
        if not self.is_enabled:
            return {"terms": [], "glossary_block": "", "match_count": 0}

        # Try full RAG pipeline first
        pipeline = self._get_pipeline()
        if pipeline is not None and pipeline.is_ready:
            try:
                result = pipeline.run_pipeline(
                    chunk_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    top_n=top_n,
                )
                # If domain filter is set, post-filter the pipeline results
                if result.get("glossary_block"):
                    terms = result.get("selected_terms", [])
                    if domain and domain != "*":
                        terms = [t for t in terms if t.get("domain") == domain]
                    return {
                        "terms": terms,
                        "glossary_block": result.get("glossary_block", ""),
                        "match_count": len(terms),
                    }
            except Exception:
                logger.warning("RAG pipeline run failed, falling back to substring matching", exc_info=True)

        # ---- Fallback: substring matching ----
        try:
            approved = self._repository.get_all_approved_terms(
                source_lang=source_lang, domain=domain if domain and domain != "*" else None
            )
        except Exception:
            logger.exception("Failed to retrieve approved terms")
            return {"terms": [], "glossary_block": "", "match_count": 0}

        chunk_lower = chunk_text.lower()
        matched: list[dict[str, Any]] = []

        for term in approved:
            source = (term.get("source_term") or "").strip()
            if not source:
                continue
            if source.lower() in chunk_lower:
                matched.append(term)

        matched.sort(key=lambda t: len(t.get("source_term", "")), reverse=True)
        matched = matched[:top_n]

        if not matched:
            return {"terms": [], "glossary_block": "", "match_count": 0}

        from backend.app.services.rag.glossary_formatter import format_glossary_block

        return {
            "terms": matched,
            "glossary_block": format_glossary_block(matched),
            "match_count": len(matched),
        }

    # ---- Review ----

    def approve_term(self, term_id: str, reviewer_id: str) -> bool:
        """Approve a pending term."""
        try:
            return self._repository.approve_term(term_id, reviewer_id)
        except Exception:
            logger.exception("Failed to approve term %s", term_id)
            return False

    def reject_term(
        self, term_id: str, reviewer_id: str, reason: Optional[str] = None
    ) -> bool:
        """Reject a pending term with an optional reason."""
        try:
            return self._repository.reject_term(term_id, reviewer_id, reason)
        except Exception:
            logger.exception("Failed to reject term %s", term_id)
            return False

    # ---- Batch operations ----

    def batch_approve_terms(self, term_ids: list[str], reviewer_id: str) -> int:
        """Approve multiple terms in a single DB operation. Returns count of affected rows."""
        if not term_ids:
            return 0
        try:
            return self._repository.batch_approve_terms(term_ids, reviewer_id)
        except Exception:
            logger.exception("Batch approve failed for %d terms", len(term_ids))
            return 0

    def batch_reject_terms(self, term_ids: list[str], reviewer_id: str, reason: Optional[str] = None) -> int:
        """Reject multiple terms in a single DB operation. Returns count of affected rows."""
        if not term_ids:
            return 0
        try:
            return self._repository.batch_reject_terms(term_ids, reviewer_id, reason)
        except Exception:
            logger.exception("Batch reject failed for %d terms", len(term_ids))
            return 0

    def batch_delete_terms(self, term_ids: list[str]) -> int:
        """Delete multiple terms in a single DB operation. Returns count of affected rows."""
        if not term_ids:
            return 0
        try:
            return self._repository.batch_delete_terms(term_ids)
        except Exception:
            logger.exception("Batch delete failed for %d terms", len(term_ids))
            return 0

    def list_pending(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        source_lang: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> dict[str, Any]:
        """List pending-review terms with pagination."""
        try:
            rows, total = self._repository.list_pending_terms(
                page=page,
                page_size=page_size,
                source_lang=source_lang,
                domain=domain,
            )
        except Exception:
            logger.exception("Failed to list pending terms")
            return {"terms": [], "total": 0, "page": page, "page_size": page_size}

        return {
            "terms": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_terms(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        domain: Optional[str] = None,
        source_lang: Optional[str] = None,
        query: Optional[str] = None,
    ) -> dict[str, Any]:
        """List all terms with optional filters and pagination.

        Uses SQL-level pagination via ``search_terms`` for efficient
        database access.
        """
        if status == "pending_review" and not source_type and not domain and not source_lang and not query:
            return self.list_pending(page=page, page_size=page_size)

        try:
            rows, total = self._repository.search_terms(
                status=status,
                source_type=source_type,
                domain=domain,
                source_lang=source_lang,
                query=query,
                page=page,
                page_size=page_size,
            )
        except Exception:
            logger.exception("Failed to list terms")
            return {"terms": [], "total": 0, "page": page, "page_size": page_size}

        return {
            "terms": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ---- Seed Official Terms ----

    def seed_official_terms(self) -> int:
        """Seed the terminology database with official pre-defined terms.

        Reads ``seed_terminology.json`` and inserts terms that do not
        already exist in the database (matched by ``source_term``).
        Only runs when the ``terminology_terms`` table is empty or
        contains no ``source_type = 'system'`` terms.

        Returns:
            Number of newly inserted terms.
        """
        if not self.is_enabled:
            logger.info("RAG terminology disabled; skipping seed.")
            return 0

        try:
            existing = self._repository.search_terms(source_type="system", page=1, page_size=1)
            if existing[1] > 0:
                logger.info("System terms already seeded (%d found); skipping.", existing[1])
                return 0
        except Exception:
            logger.info("Could not check existing system terms; proceeding with seed anyway.")

        import json
        import os

        seed_path = os.path.join(
            os.path.dirname(__file__),
            "rag",
            "seed_terminology.json",
        )
        if not os.path.exists(seed_path):
            logger.warning("Seed file not found at %s; skipping.", seed_path)
            return 0

        with open(seed_path, "r", encoding="utf-8") as f:
            entries = json.load(f)

        if not entries:
            return 0

        inserted = 0
        for entry in entries:
            try:
                existing_terms, _ = self._repository.search_terms(
                    source_lang=entry.get("source_lang", "en"),
                    query=entry.get("source_term", ""),
                    page=1,
                    page_size=1,
                )
                if existing_terms:
                    continue
                self._repository.insert_term({
                    "source_term": entry["source_term"],
                    "target_term": entry.get("target_term", ""),
                    "source_lang": entry.get("source_lang", "en"),
                    "target_lang": entry.get("target_lang", "zh"),
                    "domain": entry.get("domain", ""),
                    "source_type": "system",
                    "status": "approved",
                })
                inserted += 1
            except Exception:
                logger.warning("Failed to insert seed term '%s'", entry.get("source_term"), exc_info=True)

        logger.info("Seeded %d official terminology terms.", inserted)
        return inserted

    def get_all_approved_terms_dict(self, *, domain: Optional[str] = None) -> dict[str, str]:
        """Get all approved terms as a flat dict mapping source→target.

        Used by the translator agent for glossary injection into LLM prompts.

        Args:
            domain: Optional domain filter. When set, only terms matching this
                    domain are returned. Pass ``"*"`` to return all domains.

        Returns:
            Dict mapping source_term -> target_term.
        """
        try:
            if domain and domain != "*":
                terms = self._repository.search_approved_terms(source_lang="en", domain=domain)
            else:
                terms = self._repository.get_all_approved_terms(source_lang="en")
        except Exception:
            logger.exception("Failed to load approved terms")
            return {}
        return {t["source_term"]: t["target_term"] for t in terms if t.get("source_term") and t.get("target_term")}

    # ---- CRUD ----

    def create_term(self, payload: dict) -> Optional[dict]:
        """Create a new terminology term."""
        try:
            return self._repository.insert_term(payload)
        except Exception:
            logger.exception("Failed to create term")
            return None

    def update_term(self, term_id: str, updates: dict) -> bool:
        """Update an existing terminology term."""
        try:
            return self._repository.update_term(term_id, updates)
        except Exception:
            logger.exception("Failed to update term %s", term_id)
            return False

    def delete_term(self, term_id: str) -> bool:
        """Delete a terminology term."""
        try:
            return self._repository.delete_term(term_id)
        except Exception:
            logger.exception("Failed to delete term %s", term_id)
            return False

    # ---- Evaluation / Match Logs ----

    def get_match_logs(self, task_id: str) -> list[dict[str, Any]]:
        """Get match logs for a translation task."""
        try:
            return self._repository.get_match_logs_for_task(task_id)
        except Exception:
            logger.exception("Failed to get match logs for task %s", task_id)
            return []

    def record_match_log(
        self,
        task_id: str,
        term_id: str,
        chunk_index: int,
        retrieval_source: str,
        was_injected: bool = False,
        rerank_score: Optional[float] = None,
    ) -> Optional[str]:
        """Record a glossary match event."""
        try:
            return self._repository.insert_match_log(
                {
                    "task_id": task_id,
                    "term_id": term_id,
                    "chunk_index": chunk_index,
                    "retrieval_source": retrieval_source,
                    "was_injected": was_injected,
                    "rerank_score": rerank_score,
                }
            )
        except Exception:
            logger.exception("Failed to record match log")
            return None

    # ---- Index Management ----

    def refresh_bm25_index(self) -> bool:
        """Rebuild the BM25 index from approved terms in the database."""
        try:
            approved = self._repository.get_all_approved_terms(source_lang="en")
            pipeline = self._get_pipeline()
            if pipeline is not None:
                pipeline.refresh_indexes(approved)
                self._last_bm25_refresh = time.time()
                logger.info("BM25 index refreshed with %d terms", len(approved))
                return True
            logger.warning("Pipeline not available; BM25 index refresh skipped")
            return False
        except Exception:
            logger.exception("Failed to refresh BM25 index")
            return False

    def build_vector_index(self) -> bool:
        """Build vector embeddings for all approved terms in Milvus."""
        settings = self._settings
        milvus_uri = getattr(settings, "rag_terminology_milvus_uri", None)
        if not milvus_uri:
            logger.warning("Milvus URI not configured; vector index build skipped")
            return False

        if not _import_pipeline_deps():
            return False

        try:
            approved = self._repository.get_all_approved_terms(source_lang="en")
            if not approved:
                logger.info("No approved terms to embed")
                return True

            embedding = EmbeddingClient(
                model_name=getattr(settings, "rag_terminology_embedding_model",
                                   "sentence-transformers/all-MiniLM-L6-v2"),
            )
            vector = VectorRetriever(
                uri=milvus_uri,
                collection_name=getattr(settings, "rag_terminology_milvus_collection",
                                        "terminology_terms"),
            )
            if not vector.ensure_collection():
                logger.warning("Failed to ensure Milvus collection")
                return False

            logger.info("Building vector index for %d approved terms ...", len(approved))
            for term in approved:
                try:
                    emb = embedding.encode([term.get("source_term", "")])
                    if emb:
                        vector.upsert_term(
                            term_id=term["id"],
                            embedding=emb[0],
                            source_term=term.get("source_term", ""),
                            target_term=term.get("target_term", ""),
                        )
                except Exception:
                    logger.warning("Failed to embed term %s", term.get("id"), exc_info=True)

            logger.info("Vector index built for %d terms", len(approved))
            return True
        except Exception:
            logger.exception("Failed to build vector index")
            return False
