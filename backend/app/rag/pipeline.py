"""
Pipeline module — RAG execution pipeline: retrieve → deduplicate → generate → structured response.
Fulfills Milestone 8 Grounded LLM Generation.
"""
import json
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.rag import retrieval, llm, citations, router
from backend.app.rag.router import QueryIntent
from backend.app.rag.prompts import NO_CONTEXT_FALLBACK_TEXT
from backend.app.rag.retrieval import RetrievalError, EmbeddingError, VectorStoreError
from backend.app.rag.llm import LLMGenerationError, LLMQuotaError, LLMTimeoutError
from backend.app.services import knowledge_service
from backend.app.db.session import SessionLocal


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
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Run Hybrid Structured Knowledge + RAG execution pipeline:
    1. Check fast query cache for repeated queries
    2. Route query to determine intent (Structured SQL vs Semantic RAG vs Hybrid)
    3. Query normalized relational tables if structured intent is active
    4. If pure structured match exists, answer immediately with 100% factual certainty
    5. If hybrid or RAG required, retrieve relevant context chunks from vector store
    6. Fuse structured records and semantic chunks in LLM prompt context
    7. Generate grounded answer via LLM with strict grounding instructions
    8. Build comprehensive source citations and cache result
    """
    logger.info(f"Running Hybrid RAG pipeline for query: '{query[:80] if query else ''}'")

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

    # Stage 1: Query Classification & Routing
    routed = router.classify_query(query)
    if department and not routed.extracted_entities.get("department_code"):
        routed.extracted_entities["department_code"] = department

    logger.info(f"[PIPELINE_ROUTE] Intent={routed.intent.value} | Structured={routed.requires_structured} | RAG={routed.requires_rag}")

    # Stage 2: Structured Knowledge Lookup
    structured_result = None
    structured_text = None
    structured_citations: List[Dict[str, Any]] = []

    if routed.requires_structured:
        active_db = db
        close_db = False
        if active_db is None and SessionLocal is not None:
            try:
                active_db = SessionLocal()
                close_db = True
            except Exception as e:
                logger.warning(f"Could not initialize local DB session: {e}")
                active_db = None

        if active_db is not None:
            try:
                structured_result = knowledge_service.resolve_structured_query(routed, active_db)
                if structured_result and structured_result.get("found"):
                    structured_text = structured_result.get("text")
                    structured_citations = structured_result.get("citations", [])
                    logger.info(f"[PIPELINE_STRUCTURED] Found match for {structured_result.get('entity_type')}")
            except Exception as exc:
                logger.warning(f"[PIPELINE_STRUCTURED] Lookup failed: {exc}")
            finally:
                if close_db and active_db is not None:
                    active_db.close()

    # Stage 3: Pure Structured Short-Circuit (if RAG not required and structured record found)
    if structured_result and structured_result.get("found") and not routed.requires_rag:
        t0_llm = time.perf_counter()
        try:
            if structured_result.get("is_ambiguous") or routed.intent == QueryIntent.FACULTY_LOOKUP:
                answer = structured_text
            else:
                answer = llm.generate_grounded_answer(
                    question=query,
                    context_chunks=[],
                    timeout_ms=LLM_TIMEOUT,
                    structured_context=structured_text,
                )
                if answer.strip() == NO_CONTEXT_FALLBACK_TEXT:
                    answer = structured_text
            grounded = True
            status_val = "SUCCESS"
        except Exception as exc:
            logger.warning(f"LLM generation failed on structured record, using structured text fallback: {exc}")
            answer = structured_text
            grounded = True
            status_val = "SUCCESS"

        total_ms = (time.perf_counter() - t_start) * 1000
        llm_ms = (time.perf_counter() - t0_llm) * 1000

        result = {
            "answer": answer,
            "grounded": grounded,
            "sources": structured_citations,
            "citations": structured_citations,
            "retrieval_count": 0,
            "had_context": True,
            "retrieval_error": False,
            "generation_error": False,
            "status": status_val,
            "embedding_ms": 0.0,
            "retrieval_ms": 0.0,
            "prompt_ms": 0.0,
            "citation_ms": 0.0,
            "llm_ms": round(llm_ms, 2),
            "total_ms": round(total_ms, 2),
            "retrieval_latency": 0.0,
            "llm_latency": llm_ms / 1000.0,
            "total_latency": total_ms / 1000.0,
        }
        _RAG_CACHE[cache_key] = {"result": result, "timestamp": time.time()}
        return result

    # Stage 4: Semantic Retrieval (Embedding + Vector Search)
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
        # If we have structured data, we can still answer!
        if structured_text:
            return {
                "answer": structured_text,
                "grounded": True,
                "sources": structured_citations,
                "citations": structured_citations,
                "retrieval_count": 0,
                "had_context": True,
                "retrieval_error": False,
                "generation_error": False,
                "status": "SUCCESS",
                "embedding_ms": round(retrieval_ms, 2),
                "retrieval_ms": round(retrieval_ms, 2),
                "total_ms": round(total_ms, 2),
                "retrieval_latency": retrieval_ms / 1000.0,
                "total_latency": total_ms / 1000.0,
            }
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
        if structured_text:
            return {
                "answer": structured_text,
                "grounded": True,
                "sources": structured_citations,
                "citations": structured_citations,
                "retrieval_count": 0,
                "had_context": True,
                "retrieval_error": False,
                "generation_error": False,
                "status": "SUCCESS",
                "retrieval_ms": round(retrieval_ms, 2),
                "total_ms": round(total_ms, 2),
                "retrieval_latency": retrieval_ms / 1000.0,
                "total_latency": total_ms / 1000.0,
            }
        exc_str = str(exc).lower()
        is_empty = any(
            pattern in exc_str
            for pattern in ["unavailable or empty", "does not exist", "not found", "404", "collection"]
        )
        status_val = "RETRIEVAL_ERROR" if is_empty else "DATABASE_ERROR"
        user_answer = (
            "Knowledge index is currently being synchronized. Please try again shortly."
            if is_empty
            else "A database error occurred during information retrieval."
        )
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
    except Exception as exc:
        retrieval_ms = (time.perf_counter() - t0_retrieval) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000
        if structured_text:
            return {
                "answer": structured_text,
                "grounded": True,
                "sources": structured_citations,
                "citations": structured_citations,
                "retrieval_count": 0,
                "had_context": True,
                "retrieval_error": False,
                "generation_error": False,
                "status": "SUCCESS",
                "retrieval_ms": round(retrieval_ms, 2),
                "total_ms": round(total_ms, 2),
                "retrieval_latency": retrieval_ms / 1000.0,
                "total_latency": total_ms / 1000.0,
            }
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

    # Stage 5: Build and Merge Citations
    t0_citations = time.perf_counter()
    rag_sources = citations.build_citations_from_chunks(chunks)
    all_sources = list(structured_citations)
    seen_urls = {c.get("source_url") for c in all_sources if c.get("source_url")}
    for s in rag_sources:
        u = s.get("source_url")
        if not u or u not in seen_urls:
            all_sources.append(s)
            if u:
                seen_urls.add(u)
    citation_ms = (time.perf_counter() - t0_citations) * 1000

    # Stage 6: Fallback if neither structured record nor chunks exist
    if not chunks and not structured_text:
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

    # Stage 7: LLM Grounded Answer Generation (Fused Context)
    t0_prompt = time.perf_counter()
    prompt_ms = (time.perf_counter() - t0_prompt) * 1000

    t0_llm = time.perf_counter()
    generation_error = False
    status_val = "SUCCESS"
    try:
        answer = llm.generate_grounded_answer(
            question=query,
            context_chunks=chunks,
            timeout_ms=LLM_TIMEOUT,
            structured_context=structured_text,
        )
        if answer.strip() == NO_CONTEXT_FALLBACK_TEXT or "I couldn't find this information" in answer:
            if structured_text:
                answer = structured_text
                grounded = True
                status_val = "SUCCESS"
            else:
                grounded = False
                status_val = "NO_CONTEXT"
                all_sources = []
        else:
            grounded = True
    except LLMQuotaError as exc:
        logger.warning(f"RAG LLM quota exceeded: {exc}")
        if structured_text:
            answer = structured_text
            grounded = True
            status_val = "SUCCESS"
        else:
            generation_error = True
            status_val = "LLM_QUOTA"
            answer = "AI generation quota is currently saturated. Please try again in a moment."
            grounded = False
    except LLMTimeoutError as exc:
        logger.warning(f"RAG LLM timeout: {exc}")
        if structured_text:
            answer = structured_text
            grounded = True
            status_val = "SUCCESS"
        else:
            generation_error = True
            status_val = "LLM_TIMEOUT"
            answer = "The official sources were retrieved, but answer generation timed out. Please try again."
            grounded = False
    except (LLMGenerationError, Exception) as exc:
        logger.warning(f"RAG LLM generation exception: {exc}")
        if structured_text:
            answer = structured_text
            grounded = True
            status_val = "SUCCESS"
        else:
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
        "sources": all_sources,
        "citations": all_sources,
        "retrieval_count": retrieval_count,
        "had_context": bool(chunks or structured_text),
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
