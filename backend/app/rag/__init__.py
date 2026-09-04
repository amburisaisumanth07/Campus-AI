"""
RAG (Retrieval-Augmented Generation) package.
"""

from backend.app.rag.chunking import (
    DocumentChunk,
    chunk_document_pages,
    chunk_text,
    create_chunks_from_pages,
)
from backend.app.rag.embeddings import (
    EmbeddingError,
    embed_document,
    embed_documents,
    embed_query,
)

__all__ = [
    "DocumentChunk",
    "chunk_document_pages",
    "chunk_text",
    "create_chunks_from_pages",
    "EmbeddingError",
    "embed_document",
    "embed_documents",
    "embed_query",
]
