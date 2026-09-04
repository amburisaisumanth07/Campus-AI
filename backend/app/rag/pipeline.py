"""
Pipeline module — RAG execution pipeline: retrieve → deduplicate → generate → structured response.
Fulfills Milestone 8 Grounded LLM Generation.
"""
import json
from typing import Optional, List, Dict, Any

from backend.app.core.logging import logger
from backend.app.rag import retrieval, llm, citations
from backend.app.rag.prompts import NO_CONTEXT_FALLBACK_TEXT
from backend.app.rag.retrieval import RetrievalError, EmbeddingError, VectorStoreError
from backend.app.rag.llm import LLMGenerationError, LLMQuotaError, LLMTimeoutError


import time

_RAG_CACHE: Dict[str, Dict[str, Any]] = {}
_RAG_CACHE_TTL_SECONDS = 3600  # 1 hour

EMBEDDING_TIMEOUT = 8000
RETRIEVAL_TIMEOUT = 12000
LLM_TIMEOUT = 12000

_RAG_CACHE_VERSION = 0

def invalidate_rag_cache() -> None:
    """Increment cache version to invalidate all cached RAG responses (e.g. after sync or document updates)."""
    global _RAG_CACHE_VERSION
    _RAG_CACHE_VERSION += 1
    logger.info(f"RAG cache invalidated. New version: {_RAG_CACHE_VERSION}")


def clear_rag_cache() -> None:
    """Clear all cached RAG responses."""
    global _RAG_CACHE
    _RAG_CACHE.clear()
    invalidate_rag_cache()


def _make_cache_key(query: str, department: Optional[str], academic_year: Optional[str]) -> str:
    q_norm = " ".join(query.strip().lower().split())
    d_norm = department.strip().lower() if department else ""
    y_norm = academic_year.strip().lower() if academic_year else ""
    return f"v{_RAG_CACHE_VERSION}::{q_norm}::{d_norm}::{y_norm}"


def run_pipeline(
    query: str,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    bypass_cache: bool = False,
) -> Dict[str, Any]:
    """
    Run full RAG pipeline:
    1. Check fast query cache for repeated static/common queries
    2. Retrieve relevant context chunks (embedding + vector search)
    3. Build & deduplicate deterministic citations from retrieved chunks
    4. Short-circuit: If no context, return structured fallback without calling LLM
    5. If context exists, generate grounded answer via LLM
    6. Cache and return stable structured result with source metadata provenance and latency profile
    """
    logger.info(f"Running RAG pipeline for query: '{query[:80] if query else ''}'")

    if not query or not query.strip():
        return {
            "answer": NO_CONTEXT_FALLBACK_TEXT,
            "grounded": False,
            "sources": [],
            "citations": [],
            "retrieval_count": 0,
            "had_context": False,
            "status": "NO_CONTEXT",
            "total_ms": 0.0,
        }

    cache_key = _make_cache_key(query, department, academic_year)
    t_start = time.perf_counter()

    if not bypass_cache and cache_key in _RAG_CACHE:
        entry = _RAG_CACHE[cache_key]
        if time.time() - entry["timestamp"] < _RAG_CACHE_TTL_SECONDS:
            logger.info(f"[RAG_CACHE] Cache HIT for query '{query[:60]}'")
            cached_res = dict(entry["result"])
            cached_res["cached"] = True
            total_elapsed = (time.perf_counter() - t_start) * 1000
            cached_res["total_latency"] = total_elapsed / 1000.0
            cached_res["total_ms"] = round(total_elapsed, 2)
            return cached_res

    # Stage 1: Retrieval (Embedding + Vector Search)
    t0_retrieval = time.perf_counter()
    chunks: List[Dict[str, Any]] = []
    embedding_ms = 0.0
    search_ms = 0.0
    try:
        ret_result = retrieval.retrieve_context(
            query=query,
            department=department,
            academic_year=academic_year,
            timeout_ms=EMBEDDING_TIMEOUT,
            include_timing=True,
        )
        if isinstance(ret_result, tuple):
            chunks, embedding_ms, search_ms = ret_result
        else:
            chunks = ret_result
    except EmbeddingError as exc:
        retrieval_ms = (time.perf_counter() - t0_retrieval) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000
        logger.error(f"[PIPELINE_ERROR] Stage=embedding failed: {exc}")
        return {
            "answer": "The embedding service is temporarily unavailable. Please try again.",
            "grounded": False,
            "sources": [],
            "citations": [],
            "retrieval_count": 0,
            "had_context": False,
            "retrieval_error": True,
            "generation_error": False,
            "status": "EMBEDDING_ERROR",
            "embedding_ms": round(retrieval_ms, 2),
            "retrieval_ms": round(retrieval_ms, 2),
            "total_ms": round(total_ms, 2),
            "retrieval_latency": retrieval_ms / 1000.0,
            "total_latency": total_ms / 1000.0,
        }
    except VectorStoreError as exc:
        retrieval_ms = (time.perf_counter() - t0_retrieval) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000
        is_empty = "unavailable or empty" in str(exc).lower()
        status_val = "RETRIEVAL_ERROR" if is_empty else "DATABASE_ERROR"
        user_answer = (
            "Knowledge index is currently being synchronized. Please try again shortly."
            if is_empty
            else "A database error occurred during information retrieval."
        )
        logger.error(f"[PIPELINE_ERROR] Stage=vectorstore failed: {exc}")
        return {
            "answer": user_answer,
            "grounded": False,
            "sources": [],
            "citations": [],
            "retrieval_count": 0,
            "had_context": False,
            "retrieval_error": True,
            "generation_error": False,
            "status": status_val,
            "retrieval_ms": round(retrieval_ms, 2),
            "total_ms": round(total_ms, 2),
            "retrieval_latency": retrieval_ms / 1000.0,
            "total_latency": total_ms / 1000.0,
        }
    except RetrievalError as exc:
        retrieval_ms = (time.perf_counter() - t0_retrieval) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000
        logger.error(f"[PIPELINE_ERROR] Stage=retrieval failed: {exc}")
        return {
            "answer": "The official information could not be retrieved at this time.",
            "grounded": False,
            "sources": [],
            "citations": [],
            "retrieval_count": 0,
            "had_context": False,
            "retrieval_error": True,
            "generation_error": False,
            "status": "RETRIEVAL_ERROR",
            "retrieval_ms": round(retrieval_ms, 2),
            "total_ms": round(total_ms, 2),
            "retrieval_latency": retrieval_ms / 1000.0,
            "total_latency": total_ms / 1000.0,
        }
    except Exception as exc:
        retrieval_ms = (time.perf_counter() - t0_retrieval) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000
        logger.error(f"[PIPELINE_ERROR] Unexpected retrieval error: {exc}")
        return {
            "answer": "An unexpected error occurred while retrieving official records.",
            "grounded": False,
            "sources": [],
            "citations": [],
            "retrieval_count": 0,
            "had_context": False,
            "retrieval_error": True,
            "generation_error": False,
            "status": "DATABASE_ERROR",
            "retrieval_ms": round(retrieval_ms, 2),
            "total_ms": round(total_ms, 2),
            "retrieval_latency": retrieval_ms / 1000.0,
            "total_latency": total_ms / 1000.0,
        }

    retrieval_ms = (time.perf_counter() - t0_retrieval) * 1000
    retrieval_count = len(chunks)

    # Stage 2: Citations building
    t0_citations = time.perf_counter()
    sources = citations.build_citations_from_chunks(chunks)
    citation_ms = (time.perf_counter() - t0_citations) * 1000

    # Stage 3: Short-circuit if no relevant context
    if not chunks:
        total_ms = (time.perf_counter() - t_start) * 1000
        logger.info(f"[RAG_TIMING] Query='{query[:40]}' | Stage=NO_CONTEXT | Total={total_ms:.1f}ms")
        return {
            "answer": NO_CONTEXT_FALLBACK_TEXT,
            "grounded": False,
            "sources": [],
            "citations": [],
            "retrieval_count": 0,
            "had_context": False,
            "retrieval_error": False,
            "generation_error": False,
            "status": "NO_CONTEXT",
            "retrieval_ms": round(retrieval_ms, 2),
            "citation_ms": round(citation_ms, 2),
            "total_ms": round(total_ms, 2),
            "retrieval_latency": retrieval_ms / 1000.0,
            "total_latency": total_ms / 1000.0,
        }

    # Stage 3.5: Prompt Preparation
    t0_prompt = time.perf_counter()
    prompt_ms = (time.perf_counter() - t0_prompt) * 1000

    # Stage 4: LLM Generation
    t0_llm = time.perf_counter()
    generation_error = False
    status_val = "SUCCESS"
    try:
        answer = llm.generate_grounded_answer(query, chunks, timeout_ms=LLM_TIMEOUT)
        if answer.strip() == NO_CONTEXT_FALLBACK_TEXT or "I couldn't find this information" in answer:
            grounded = False
            status_val = "NO_CONTEXT"
            sources = []
        else:
            grounded = True
    except LLMQuotaError as exc:
        logger.warning(f"RAG LLM quota exceeded: {exc}")
        generation_error = True
        status_val = "LLM_QUOTA"
        answer = "AI generation quota is currently saturated. Please try again in a moment."
        grounded = False
    except LLMTimeoutError as exc:
        logger.warning(f"RAG LLM timeout: {exc}")
        generation_error = True
        status_val = "LLM_TIMEOUT"
        answer = "The official sources were retrieved, but answer generation timed out. Please try again."
        grounded = False
    except LLMGenerationError as exc:
        logger.warning(f"RAG LLM generation exception: {exc}")
        generation_error = True
        status_val = "LLM_ERROR"
        answer = "The official information was retrieved, but the answer-generation service is temporarily unavailable."
        grounded = False
    except Exception as exc:
        logger.warning(f"Unknown RAG LLM exception: {exc}")
        generation_error = True
        status_val = "LLM_ERROR"
        answer = "The official information was retrieved, but the answer-generation service is temporarily unavailable."
        grounded = False

    llm_ms = (time.perf_counter() - t0_llm) * 1000
    total_ms = (time.perf_counter() - t_start) * 1000

    logger.info(
        f"[RAG_TIMING] Query='{query[:40]}' | Status={status_val} | "
        f"Embedding={embedding_ms:.1f}ms | Retrieval={retrieval_ms:.1f}ms | "
        f"Prompt={prompt_ms:.1f}ms | Citations={citation_ms:.1f}ms | "
        f"LLM={llm_ms:.1f}ms | Total={total_ms:.1f}ms"
    )

    result = {
        "answer": answer,
        "grounded": grounded,
        "sources": sources,
        "citations": sources,
        "retrieval_count": retrieval_count,
        "had_context": len(chunks) > 0,
        "retrieval_error": False,
        "generation_error": generation_error,
        "status": status_val,
        "embedding_ms": round(embedding_ms, 2) if embedding_ms > 0 else round(retrieval_ms * 0.5, 2),
        "retrieval_ms": round(retrieval_ms, 2),
        "prompt_ms": round(prompt_ms, 2),
        "citation_ms": round(citation_ms, 2),
        "llm_ms": round(llm_ms, 2),
        "total_ms": round(total_ms, 2),
        "retrieval_latency": retrieval_ms / 1000.0,
        "llm_latency": llm_ms / 1000.0,
        "total_latency": total_ms / 1000.0,
    }

    if status_val == "SUCCESS":
        _RAG_CACHE[cache_key] = {
            "result": result,
            "timestamp": time.time(),
        }

    return result


def citations_to_json(citations: List[Dict[str, Any]]) -> str:
    """Serialize citations list to JSON string for DB storage."""
    return json.dumps(citations)


def json_to_citations(json_str: Optional[str]) -> List[Dict[str, Any]]:
    """Deserialize citations JSON string from DB."""
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except Exception:
        return []
