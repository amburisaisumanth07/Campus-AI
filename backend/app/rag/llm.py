"""
LLM module — generation client using official google-genai SDK.
Fulfills Milestone 8 Grounded LLM Generation.
"""
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.rag.prompts import (
    SYSTEM_GROUNDING_PROMPT,
    NO_CONTEXT_FALLBACK_TEXT,
    format_rag_prompt,
)


class LLMGenerationError(Exception):
    """Exception raised for general LLM generation errors."""
    pass


class LLMQuotaError(LLMGenerationError):
    """Exception raised when Gemini API quota or rate limit is exhausted."""
    pass


class LLMTimeoutError(LLMGenerationError):
    """Exception raised when Gemini API request times out."""
    pass


_cached_client: Optional[genai.Client] = None
_cached_client_timeout: Optional[int] = None


def _get_client(timeout_ms: Optional[int] = None) -> genai.Client:
    """Returns an authenticated, cached Google GenAI client."""
    global _cached_client, _cached_client_timeout
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        raise ValueError("GEMINI_API_KEY is not configured.")
    
    eff_timeout = int(timeout_ms) if timeout_ms else 12000
    if _cached_client is None or _cached_client_timeout != eff_timeout:
        http_options = {"timeout": eff_timeout}
        _cached_client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)
        _cached_client_timeout = eff_timeout
    return _cached_client


def _synthesize_grounded_fallback(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """
    Synthesize an accurate, grounded answer directly from retrieved context chunks
    when remote LLM API quota is temporarily exhausted or unavailable.
    """
    seen_texts = set()
    key_points = []
    for chunk in context_chunks[:3]:
        txt = (chunk.get("text") or "").strip()
        if not txt or txt in seen_texts:
            continue
        seen_texts.add(txt)
        key_points.append(txt)

    if not key_points:
        return NO_CONTEXT_FALLBACK_TEXT

    return (
        "Based on official MITS institutional documents:\n\n"
        + "\n\n".join(key_points)
    )


def generate_grounded_answer(
    question: str,
    context_chunks: Optional[List[Dict[str, Any]]] = None,
    client: Optional[genai.Client] = None,
    timeout_ms: Optional[int] = None,
    structured_context: Optional[str] = None,
) -> str:
    """
    Generates a grounded factual answer using Gemini via the official google-genai SDK.

    Args:
        question: Student/user query string.
        context_chunks: Retrieved document chunks with metadata.
        client: Optional pre-initialized genai.Client (useful for testing).
        timeout_ms: Timeout in milliseconds for the generation API call.
        structured_context: Optional formatted official structured database facts.

    Returns:
        Grounded answer string.
    """
    if not question or not question.strip():
        return NO_CONTEXT_FALLBACK_TEXT

    chunks = context_chunks or []
    if not chunks and not structured_context:
        return NO_CONTEXT_FALLBACK_TEXT

    if client is None:
        eff_timeout = timeout_ms if timeout_ms else 12000
        client = _get_client(eff_timeout)

    prompt = format_rag_prompt(question, chunks, structured_context=structured_context)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_GROUNDING_PROMPT,
        temperature=settings.GEMINI_TEMPERATURE,
        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
    )

    last_exc = None
    # Attempt call with at most 1 fast retry for transient gateway spikes
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            if response and hasattr(response, "text") and response.text and response.text.strip():
                return response.text.strip()
            raise LLMGenerationError("Received empty or malformed response from Gemini API.")
        except Exception as exc:
            last_exc = exc
            exc_str = str(exc).lower()
            logger.error(f"Gemini API generation call failed (attempt {attempt + 1}/2): {exc}")
            if attempt == 0 and ("503" in exc_str or "504" in exc_str or "unavailable" in exc_str or "deadline" in exc_str):
                import time
                time.sleep(0.5)
                continue
            break

    exc_str = str(last_exc).lower()
    if "429" in exc_str or "resource_exhausted" in exc_str or "quota" in exc_str or "rate limit" in exc_str:
        raise LLMQuotaError(f"Gemini API generation call failed (quota exceeded): {last_exc}") from last_exc
    elif "timeout" in exc_str or "deadline" in exc_str or "timed out" in exc_str or "504" in exc_str:
        raise LLMTimeoutError(f"Gemini API generation call failed (timed out): {last_exc}") from last_exc
    raise LLMGenerationError(f"Gemini API generation call failed: {last_exc}") from last_exc


def generate_rag_answer(
    query: str,
    context_chunks: Optional[List[Dict[str, Any]]] = None,
    structured_context: Optional[str] = None,
) -> str:
    """Alias function for backwards compatibility with earlier milestones."""
    return generate_grounded_answer(question=query, context_chunks=context_chunks, structured_context=structured_context)

