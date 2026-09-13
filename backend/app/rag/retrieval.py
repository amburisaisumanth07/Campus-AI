"""
Semantic Retrieval Module for CampusAI RAG Pipeline.

Retrieves relevant document chunks from Chroma vector database using 768-dimensional
Gemini query embeddings, cosine distance thresholding, and metadata provenance parsing.
"""

import time
from typing import List, Dict, Any, Optional, Union, Tuple
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.rag import embeddings, vectorstore


class RetrievalError(Exception):
    """Exception raised for errors during semantic retrieval operations."""
    pass


class EmbeddingError(RetrievalError):
    """Exception raised for errors during query embedding generation."""
    pass


class VectorStoreError(RetrievalError):
    """Exception raised for errors during vector store similarity search."""
    pass


def parse_source_pages(source_pages_raw: Any, default_page: int = 1) -> List[int]:
    """
    Safely parse source_pages metadata from string ("1,2") or list ([1, 2])
    into a list of integers.
    """
    if isinstance(source_pages_raw, list):
        parsed = []
        for item in source_pages_raw:
            try:
                parsed.append(int(item))
            except (ValueError, TypeError):
                pass
        return parsed if parsed else [default_page]

    if isinstance(source_pages_raw, str) and source_pages_raw.strip():
        parsed = []
        for part in source_pages_raw.split(","):
            part_str = part.strip()
            if part_str.isdigit():
                parsed.append(int(part_str))
        return parsed if parsed else [default_page]

    if isinstance(source_pages_raw, (int, float)):
        return [int(source_pages_raw)]

    return [default_page]


def build_where_filter(
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    document_type: Optional[str] = None,
    document_id: Optional[int] = None,
    document_version_id: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build a Chroma-compatible `where` filter dictionary supporting single or $and criteria.
    """
    conditions: List[Dict[str, Any]] = []

    # Merge explicit parameters
    if department and department.strip():
        conditions.append({"department": department.strip()})
    if academic_year and academic_year.strip():
        conditions.append({"academic_year": academic_year.strip()})
    if document_type and document_type.strip():
        conditions.append({"document_type": document_type.strip()})
    if document_id is not None:
        conditions.append({"document_id": int(document_id)})
    if document_version_id is not None:
        conditions.append({"document_version_id": int(document_version_id)})

    # Merge optional filters dict
    if filters and isinstance(filters, dict):
        for k, v in filters.items():
            if v is not None and str(v).strip():
                conditions.append({k: v})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def retrieve_context(
    query: str,
    top_k: Optional[int] = None,
    relevance_threshold: Optional[float] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    document_type: Optional[str] = None,
    document_id: Optional[int] = None,
    document_version_id: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
    timeout_ms: Optional[int] = None,
    include_timing: bool = False,
) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], float, float]]:
    """
    Execute semantic search for user query against Chroma vector database.
    """
    if not query or not query.strip():
        logger.info("Empty query provided to retrieve_context; returning empty result.")
        return ([], 0.0, 0.0) if include_timing else []

    k = top_k if top_k is not None and top_k > 0 else settings.RAG_TOP_K
    threshold = (
        relevance_threshold if relevance_threshold is not None else settings.RAG_RELEVANCE_THRESHOLD
    )

    # 1. Generate query embedding with high-resolution timer
    t0_embed = time.perf_counter()
    try:
        query_vector = embeddings.embed_query(query.strip(), timeout_ms=timeout_ms)
    except Exception as exc:
        logger.error(f"[RETRIEVAL_ERROR] Stage=query_embedding failed: {type(exc).__name__}: {exc}")
        raise EmbeddingError(f"Failed to generate query embedding: {exc}") from exc
    embed_ms = (time.perf_counter() - t0_embed) * 1000

    # 2. Build Chroma metadata filter
    where_clause = build_where_filter(
        department=department,
        academic_year=academic_year,
        document_type=document_type,
        document_id=document_id,
        document_version_id=document_version_id,
        filters=filters,
    )

    # 3. Vector similarity search in Chroma DB with timer
    t0_search = time.perf_counter()
    try:
        raw_hits = vectorstore.similarity_search(
            query_embedding=query_vector,
            top_k=max(k * 2, 8),  # retrieve extra candidates for threshold filtering
            where_filter=where_clause,
        )
        logger.info(f"[RETRIEVAL_SEARCH] Raw candidates retrieved={len(raw_hits)}")
    except Exception as exc:
        logger.error(
            f"[RETRIEVAL_ERROR] Stage=vectorstore_search failed: exc_type={type(exc).__name__}, exc={exc}",
            exc_info=True,
        )
        raise VectorStoreError(f"Vector store search failed: {exc}") from exc
    search_ms = (time.perf_counter() - t0_search) * 1000

    if not raw_hits:
        logger.info("[RETRIEVAL] Zero candidates found in vector store.")
        return ([], embed_ms, search_ms) if include_timing else []

    # 4. Format structured result dictionaries and convert metadata safely
    structured_results: List[Dict[str, Any]] = []

    for hit in raw_hits:
        meta = hit.get("metadata") or {}
        doc_text = hit.get("text", "")
        raw_dist = float(hit.get("distance", 1.0))
        # Compute cosine similarity score: score = 1.0 - distance
        calc_score = float(hit.get("score", round(1.0 - raw_dist, 4)))

        # Safely parse integer and list metadata fields
        doc_id_val = meta.get("document_id") or meta.get("doc_id") or hit.get("document_id") or 0
        try:
            doc_id = int(doc_id_val)
        except (ValueError, TypeError):
            doc_id = 0

        doc_ver_val = meta.get("document_version_id", 1)
        try:
            doc_ver_id = int(doc_ver_val)
        except (ValueError, TypeError):
            doc_ver_id = 1

        page_num_val = meta.get("page_number", 1)
        try:
            page_num = int(page_num_val)
        except (ValueError, TypeError):
            page_num = 1

        chunk_idx_val = meta.get("chunk_index", 0)
        try:
            chunk_idx = int(chunk_idx_val)
        except (ValueError, TypeError):
            chunk_idx = 0

        source_pages = parse_source_pages(meta.get("source_pages"), default_page=page_num)

        chunk_id = str(hit.get("id") or hit.get("chunk_id") or meta.get("chunk_id") or f"chunk_{doc_id}_{chunk_idx}")

        result_item = {
            "chunk_id": chunk_id,
            "id": chunk_id,
            "text": doc_text,
            "distance": round(raw_dist, 4),
            "score": round(calc_score, 4),
            "document_id": doc_id,
            "document_version_id": doc_ver_id,
            "page_number": page_num,
            "source_pages": source_pages,
            "title": str(meta.get("title") or hit.get("title") or "Unknown"),
            "department": str(meta.get("department") or ""),
            "academic_year": str(meta.get("academic_year") or ""),
            "document_type": str(meta.get("document_type") or ""),
            "source_type": str(meta.get("source_type") or ""),
            "source_url": str(meta.get("source_url") or ""),
            "chunk_index": chunk_idx,
            "metadata": meta,
        }
        structured_results.append(result_item)

    # 5. Apply relevance score thresholding (score >= threshold)
    filtered = [item for item in structured_results if item["score"] >= threshold]

    # Apply freshness and official source reranking (boost score)
    query_lower = query.lower()
    is_freshness_query = any(k in query_lower for k in ["latest", "current", "today", "recent", "new", "2026", "this semester"])
    
    for item in filtered:
        boost = 0.0
        meta = item["metadata"]
        
        # Boost official MITS sources
        if "mits.ac.in" in item.get("source_url", ""):
            boost += 0.05

        # Authoritative HOD source boosting for HOD queries
        is_hod_query = any(k in query_lower for k in ["hod", "head of", "head of the", "heads of", "department head", "department heads", "head"])
        if is_hod_query and "departmentheads" in item.get("source_url", ""):
            boost += 0.20

        # Authoritative Academic Regulations boosting for attendance / grading queries
        is_reg_query = any(k in query_lower for k in ["attendance", "condonation", "detention", "regulation", "grading", "sgpa", "cgpa", "r20", "r25"])
        title_lower = item.get("title", "").lower()
        url_lower = item.get("source_url", "").lower()
        if is_reg_query:
            if any(term in title_lower or term in url_lower for term in ["academic-regulations", "regulations", "attendance", "curriculum"]):
                boost += 0.25
            elif any(term in title_lower for term in ["project", "student project", "report", "dissertation"]):
                boost -= 0.20

        # Authoritative Exam Cell boosting for examination queries
        is_exam_query = any(k in query_lower for k in ["exam", "examination", "revaluation", "recounting", "cie", "see", "malpractice", "hall ticket"])
        if is_exam_query:
            if any(term in title_lower or term in url_lower for term in ["examination", "exam", "coe", "evaluat", "revaluat"]):
                boost += 0.20

        # Authoritative Placement boosting
        is_placement_query = any(k in query_lower for k in ["placement", "recruiter", "package", "lpa", "highest package", "internship"])
        if is_placement_query:
            if any(term in title_lower or term in url_lower for term in ["placement", "recruit", "career"]):
                boost += 0.20

        # Boost newer documents or current status if metadata exists
        is_current = str(meta.get("is_current", "")).lower() == "true"
        if is_current:
            boost += 0.05
            
        if is_freshness_query and is_current:
            boost += 0.10
            
        item["score"] += boost

    # 6. Preserve relevance ordering (distance ascending / score descending) and limit to top_k
    filtered.sort(key=lambda x: (-x["score"], x["distance"]))
    final_results = filtered[:k]

    logger.info(f"Retrieved {len(final_results)} relevant chunks for query (embed: {embed_ms:.1f}ms, search: {search_ms:.1f}ms).")
    if include_timing:
        return final_results, embed_ms, search_ms
    return final_results
