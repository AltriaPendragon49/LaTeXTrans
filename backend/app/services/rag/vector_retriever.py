from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful degradation: pymilvus is optional
# ---------------------------------------------------------------------------

try:
    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        connections,
        utility,
    )
except ImportError:  # pragma: no cover
    Collection = None
    CollectionSchema = None
    DataType = None
    FieldSchema = None
    connections = None
    utility = None
    logger.info("pymilvus is not installed; vector retrieval will be unavailable.")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRIMARY_FIELD = "term_id"
_VECTOR_FIELD = "embedding"
_SOURCE_FIELD = "source_term"
_TARGET_FIELD = "target_term"
_METADATA_FIELD = "metadata"


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class VectorRetriever:
    """Milvus-based vector retriever for approved-term embeddings.

    Parameters
    ----------
    uri : str
        Milvus server URI (e.g. ``"http://localhost:19530"``).
    collection_name : str
        Name of the Milvus collection for terminology embeddings.
    embedding_dim : int
        Dimension of the embedding vectors (default 384 for
        all-MiniLM-L6-v2).
    """

    def __init__(
        self,
        uri: str,
        collection_name: str,
        embedding_dim: int = 384,
    ) -> None:
        self._uri = uri
        self._collection_name = collection_name
        self._embedding_dim = embedding_dim
        self._collection: Optional[Any] = None
        self._connected = False

    # ------------------------------------------------------------------
    # Connection & collection lifecycle
    # ------------------------------------------------------------------

    def _connect(self) -> bool:
        if self._connected:
            return True
        if connections is None:
            logger.warning("pymilvus is not available; skipping Milvus connection.")
            return False

        try:
            connections.connect(alias="default", uri=self._uri)
            self._connected = True
            logger.info("Connected to Milvus at %s", self._uri)
            return True
        except Exception as exc:
            logger.warning("Failed to connect to Milvus: %s", exc)
            return False

    def ensure_collection(self) -> bool:
        """Create the collection if it does not already exist.

        Returns
        -------
        bool
            ``True`` if the collection is ready, ``False`` on failure.
        """
        if not self._connect():
            return False
        if Collection is None:
            return False

        try:
            if utility.has_collection(self._collection_name):
                self._collection = Collection(self._collection_name)
                logger.info(
                    "Using existing Milvus collection: %s", self._collection_name
                )
                return True
        except Exception as exc:
            logger.warning(
                "Error checking Milvus collection existence: %s", exc
            )
            return False

        try:
            fields = [
                FieldSchema(
                    name=_PRIMARY_FIELD,
                    dtype=DataType.VARCHAR,
                    max_length=128,
                    is_primary=True,
                ),
                FieldSchema(
                    name=_VECTOR_FIELD,
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self._embedding_dim,
                ),
                FieldSchema(
                    name=_SOURCE_FIELD,
                    dtype=DataType.VARCHAR,
                    max_length=512,
                ),
                FieldSchema(
                    name=_TARGET_FIELD,
                    dtype=DataType.VARCHAR,
                    max_length=512,
                ),
                FieldSchema(
                    name=_METADATA_FIELD,
                    dtype=DataType.JSON,
                ),
            ]
            schema = CollectionSchema(
                fields,
                description="Approved terminology embeddings",
            )
            self._collection = Collection(
                name=self._collection_name, schema=schema
            )

            # Create an IVF_FLAT index on the vector field for ANN search
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }
            self._collection.create_index(
                field_name=_VECTOR_FIELD, index_params=index_params
            )
            logger.info(
                "Created Milvus collection: %s (dim=%d)",
                self._collection_name,
                self._embedding_dim,
            )

        # Load collection into memory for search readiness
        try:
            self._collection.load()
        except Exception as exc:
            logger.warning("Failed to load Milvus collection: %s", exc)
        return True
        except Exception as exc:
            logger.warning("Failed to create Milvus collection: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert_term(
        self,
        term_id: str,
        embedding: list[float],
        source_term: str,
        target_term: str,
        metadata: dict | None = None,
    ) -> bool:
        """Insert or update a single term embedding in Milvus.

        Returns
        -------
        bool
            ``True`` on success, ``False`` on failure.
        """
        if not self._ensure_ready():
            return False

        try:
            entities = [
                [term_id],
                [embedding],
                [source_term],
                [target_term],
                [metadata or {}],
            ]
            self._collection.insert(entities)
            self._collection.flush()
            return True
        except Exception as exc:
            logger.warning("Milvus upsert_term failed for %s: %s", term_id, exc)
            return False

    def batch_upsert(self, entries: list[dict]) -> bool:
        """Insert or update multiple term embeddings in Milvus.

        Each *entry* dict must have keys: ``term_id``, ``embedding``,
        ``source_term``, ``target_term``, and optionally ``metadata``.

        Returns
        -------
        bool
            ``True`` on success, ``False`` on failure.
        """
        if not self._ensure_ready():
            return False
        if not entries:
            return True

        try:
            ids = [e["term_id"] for e in entries]
            embeddings = [e["embedding"] for e in entries]
            source_terms = [e.get("source_term", "") for e in entries]
            target_terms = [e.get("target_term", "") for e in entries]
            metadata_list = [e.get("metadata", {}) for e in entries]

            entities = [ids, embeddings, source_terms, target_terms, metadata_list]
            self._collection.insert(entities)
            self._collection.flush()
            logger.info("Milvus batch_upsert: %d terms", len(entries))
            return True
        except Exception as exc:
            logger.warning("Milvus batch_upsert failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def search(
        self,
        embedding: list[float],
        top_n: int = 20,
    ) -> list[dict]:
        """Search for the nearest neighbour terms in Milvus.

        Parameters
        ----------
        embedding : list[float]
            Query vector.
        top_n : int
            Number of results to return.

        Returns
        -------
        list[dict]
            Each entry::

                {
                    "term_id": …,
                    "source_term": …,
                    "target_term": …,
                    "vector_score": float,
                    "retrieval_source": "vector",
                }

            Empty list on failure.
        """
        if not self._ensure_ready():
            return []

        try:
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10},
            }
            results = self._collection.search(
                data=[embedding],
                anns_field=_VECTOR_FIELD,
                param=search_params,
                limit=top_n,
                output_fields=[_PRIMARY_FIELD, _SOURCE_FIELD, _TARGET_FIELD],
            )

            candidates = []
            for hits in results:
                for hit in hits:
                    candidates.append(
                        {
                            "term_id": hit.entity.get(_PRIMARY_FIELD),
                            "source_term": str(
                                hit.entity.get(_SOURCE_FIELD, "")
                            ),
                            "target_term": str(
                                hit.entity.get(_TARGET_FIELD, "")
                            ),
                            "vector_score": float(hit.score),
                            "retrieval_source": "vector",
                        }
                    )
            return candidates
        except Exception as exc:
            logger.warning("Milvus search failed: %s", exc)
            return []

    def delete_term(self, term_id: str) -> bool:
        """Delete a term from Milvus by ``term_id``.

        Returns
        -------
        bool
            ``True`` on success, ``False`` on failure.
        """
        if not self._ensure_ready():
            return False

        try:
            self._collection.delete(f'{_PRIMARY_FIELD} == "{term_id}"')
            self._collection.flush()
            return True
        except Exception as exc:
            logger.warning("Milvus delete_term failed for %s: %s", term_id, exc)
            return False

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Return whether the Milvus connection and collection are usable."""
        if not self._connect():
            return False
        if utility is None:
            return False
        try:
            return utility.has_collection(self._collection_name)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_ready(self) -> bool:
        if self._collection is not None:
            return True
        return self.ensure_collection()
