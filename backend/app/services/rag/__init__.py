# RAG terminology services

from backend.app.services.rag.embedding_client import EmbeddingClient
from backend.app.services.rag.bm25_retriever import Bm25Retriever
from backend.app.services.rag.vector_retriever import VectorRetriever
from backend.app.services.rag.cross_encoder_reranker import CrossEncoderReranker
from backend.app.services.rag.glossary_formatter import (
    format_glossary_block,
    estimate_token_count,
    truncate_glossary,
)
from backend.app.services.rag.pipeline import RagTerminologyPipeline
from backend.app.services.rag.translation_hook import (
    build_glossary_for_chunk,
    build_glossary_from_terms,
    inject_glossary_into_prompt,
    run_post_translation_extraction,
    should_run_rag,
)

__all__ = [
    "EmbeddingClient",
    "Bm25Retriever",
    "VectorRetriever",
    "CrossEncoderReranker",
    "format_glossary_block",
    "estimate_token_count",
    "truncate_glossary",
    "RagTerminologyPipeline",
    "build_glossary_for_chunk",
    "build_glossary_from_terms",
    "inject_glossary_into_prompt",
    "run_post_translation_extraction",
    "should_run_rag",
]
