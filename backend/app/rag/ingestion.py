"""
Ingestion module — orchestrates chunking, embedding generation, and vectorstore insertion for document pages.
"""
from typing import List, Dict, Any

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.rag import chunking, embeddings, vectorstore


def index_document(
    doc_id: int,
    title: str,
    department: str | None,
    academic_year: str | None,
    pages: List[Dict[str, Any]],
    source_type: str | None = None,
    source_url: str | None = None,
) -> int:
    """
    Orchestrate full document vector indexing:
    1. Chunk document pages into records with metadata
    2. Generate embeddings for all chunk texts
    3. Add chunk records and embeddings to vectorstore
    """
    if not pages:
        logger.info(f"Document {doc_id} has no pages to index.")
        return 0

    # 1. Chunk pages
    chunk_records = chunking.create_chunks_from_pages(
        doc_id=doc_id,
        title=title,
        department=department,
        academic_year=academic_year,
        pages=pages,
        chunk_size=settings.RAG_CHUNK_SIZE,
        overlap=settings.RAG_CHUNK_OVERLAP,
        source_type=source_type,
        source_url=source_url,
    )

    if not chunk_records:
        logger.info(f"Document {doc_id} produced no text chunks.")
        return 0

    # 2. Embed texts
    texts = [c["text"] for c in chunk_records]
    vectors = embeddings.embed_documents(texts)

    # 3. Store in Chroma
    count = vectorstore.add_chunks(chunk_records, vectors)
    logger.info(f"Indexed {count} chunks for document {doc_id}.")
    return count


def remove_document_index(doc_id: int) -> None:
    """Orchestrate document index removal."""
    vectorstore.delete_document_chunks(doc_id)
