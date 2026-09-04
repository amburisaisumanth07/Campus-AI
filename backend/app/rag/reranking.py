"""
Reranking module — provides an abstraction interface for re-ordering retrieved context chunks.
Currently implements a simple pass-through (no-op) reranker.
"""
from typing import List, Dict, Any


def rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Pass-through (no-op) reranker.
    Preserves the initial similarity score order from vector search.
    Future implementations can plug in a cross-encoder model here.
    """
    if top_k is not None:
        return chunks[:top_k]
    return chunks
