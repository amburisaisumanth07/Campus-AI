"""
Vectorstore module — Chroma vector database integration over HTTP (HttpClient)
and vector CRUD operations for 768-dimensional Gemini embeddings.
"""

from typing import List, Dict, Any, Optional
import chromadb

from backend.app.core.config import settings
from backend.app.core.logging import logger

EXPECTED_VECTOR_DIM = 768


_chroma_client = None

def get_chroma_client() -> chromadb.HttpClient:
    """Return a Chroma HTTP client connected to the Chroma container."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
    return _chroma_client


def get_collection(collection_name: Optional[str] = None) -> chromadb.Collection:
    """Get or create the ChromaDB collection configured with cosine distance using cached HTTP client."""
    client = get_chroma_client()
    target_collection = collection_name or settings.CHROMA_COLLECTION
    return client.get_or_create_collection(
        name=target_collection,
        metadata={"hnsw:space": "cosine"},
    )


def health_check() -> bool:
    """
    Verify connectivity to the Chroma HTTP service.
    Returns True if healthy, False otherwise.
    """
    try:
        client = get_chroma_client()
        client.heartbeat()
        return True
    except Exception as exc:
        logger.warning(f"Chroma health check failed: {exc}")
        return False


def validate_vector_dimension(embedding: List[float], expected_dim: int = EXPECTED_VECTOR_DIM) -> None:
    """
    Validate that an embedding vector has the expected dimensionality (768).
    Raises ValueError if invalid.
    """
    if not isinstance(embedding, list) or len(embedding) != expected_dim:
        raise ValueError(
            f"Invalid vector dimension: expected {expected_dim}, got {len(embedding) if isinstance(embedding, list) else type(embedding)}"
        )


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize metadata dictionary so values conform to ChromaDB constraints
    (str, int, float, bool only). Converts lists/dicts to strings.
    """
    sanitized: Dict[str, Any] = {}
    for key, val in metadata.items():
        if val is None:
            sanitized[key] = ""
        elif isinstance(val, (int, float, str, bool)):
            sanitized[key] = val
        elif isinstance(val, list):
            sanitized[key] = ",".join(str(item) for item in val)
        else:
            sanitized[key] = str(val)

    # Ensure doc_id compatibility alias
    if "document_id" in sanitized and "doc_id" not in sanitized:
        sanitized["doc_id"] = sanitized["document_id"]
    elif "doc_id" in sanitized and "document_id" not in sanitized:
        sanitized["document_id"] = sanitized["doc_id"]

    return sanitized


def add_chunks(
    chunk_records: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """
    Add chunks and embeddings into ChromaDB collection.
    Validates 768-dim embeddings and handles chunk metadata cleanly.
    """
    return upsert_chunks(chunk_records, embeddings)


def upsert_chunks(
    chunk_records: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """
    Upsert chunks and embeddings into ChromaDB collection (safe for duplicate IDs).
    """
    if not chunk_records:
        return 0

    if len(chunk_records) != len(embeddings):
        raise ValueError(
            f"Mismatch between chunk records count ({len(chunk_records)}) and embeddings count ({len(embeddings)})"
        )

    for emb in embeddings:
        validate_vector_dimension(emb)

    collection = get_collection()
    ids = [str(c.get("id") or c.get("chunk_id")) for c in chunk_records]
    documents = [c.get("text", "") for c in chunk_records]
    metadatas = [sanitize_metadata(c.get("metadata", {})) for c in chunk_records]

    batch_size = 100
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            documents=documents[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    logger.info(f"Upserted {len(ids)} chunks into ChromaDB HTTP vector store.")
    return len(ids)


def get_chunk(chunk_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a stored chunk by its chunk ID.
    Returns dictionary with chunk text, metadata, and embedding, or None if missing.
    """
    collection = get_collection()
    res = collection.get(
        ids=[chunk_id],
        include=["documents", "metadatas", "embeddings"],
    )

    if not res or not res.get("ids") or len(res["ids"]) == 0:
        return None

    doc_text = res["documents"][0] if res.get("documents") else ""
    meta = res["metadatas"][0] if res.get("metadatas") else {}
    emb = res["embeddings"][0] if res.get("embeddings") is not None and len(res["embeddings"]) > 0 else []

    return {
        "id": chunk_id,
        "chunk_id": chunk_id,
        "text": doc_text,
        "metadata": meta,
        "embedding": list(emb) if hasattr(emb, "tolist") else list(emb),
    }


def delete_chunks_by_document(document_id: int) -> int:
    """
    Remove all chunks associated with document_id from ChromaDB collection.
    Returns count of deleted chunks.
    """
    try:
        collection = get_collection()
        # Query by document_id or doc_id filter
        results = collection.get(where={"document_id": document_id})
        ids_to_delete = results.get("ids", []) if results else []

        if not ids_to_delete:
            results_alt = collection.get(where={"doc_id": document_id})
            ids_to_delete = results_alt.get("ids", []) if results_alt else []

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} chunks for document_id {document_id} from Chroma.")
            return len(ids_to_delete)
        return 0
    except Exception as exc:
        logger.warning(f"Failed to delete chunks for document_id {document_id} from Chroma: {exc}")
        return 0


def delete_document_chunks(doc_id: int) -> int:
    """Backwards-compatible alias for delete_chunks_by_document."""
    return delete_chunks_by_document(doc_id)


def count() -> int:
    """Return the total number of vector items stored in Chroma collection."""
    collection = get_collection()
    return collection.count()


def similarity_search(
    query_embedding: List[float],
    top_k: int = 5,
    where_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Execute vector similarity query against ChromaDB using cosine distance.
    """
    validate_vector_dimension(query_embedding)
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    ids = results.get("ids", [[]])[0] if results.get("ids") else []
    docs = results.get("documents", [[]])[0] if results.get("documents") else []
    metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    distances = results.get("distances", [[]])[0] if results.get("distances") else []

    for i in range(len(docs)):
        chunk_id = ids[i] if i < len(ids) else ""
        doc_text = docs[i]
        meta = metas[i] if i < len(metas) else {}
        dist = distances[i] if i < len(distances) else 0.0

        hits.append({
            "id": chunk_id,
            "chunk_id": chunk_id,
            "doc_id": meta.get("doc_id") or meta.get("document_id"),
            "document_id": meta.get("document_id") or meta.get("doc_id"),
            "title": meta.get("title", "Unknown"),
            "page_number": meta.get("page_number", 0),
            "chunk_index": meta.get("chunk_index", 0),
            "text": doc_text,
            "snippet": doc_text[:500],
            "distance": round(dist, 4),
            "score": round(1.0 - dist, 4) if dist <= 1.0 else round(1.0 / (1.0 + dist), 4),
            "metadata": meta,
        })

    return hits
