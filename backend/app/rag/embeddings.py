"""
Embeddings module — provides document and query embedding generation via google-genai SDK
using the gemini-embedding-2 model with 768-dimensional Matryoshka Representation Learning (MRL),
with resilient fallback for rate limits or quota constraints.
"""
import hashlib
import math
import re
import time
from typing import List, Optional, Any
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.core.logging import logger


class EmbeddingError(Exception):
    """Exception raised for errors during embedding generation."""
    pass


def _deterministic_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Generate a deterministic normalized 768-dimensional pseudo-embedding from text.
    Used as a fallback if remote Gemini embedding quota is exhausted.
    """
    vec = [0.0] * dim
    words = text.lower().split()
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        for i in range(16):
            idx = (h + i * 37) % dim
            val = ((h >> (i * 4)) & 0xFF) / 255.0 - 0.5
            vec[idx] += val

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 6) for x in vec]
    else:
        vec[0] = 1.0
    return vec


_cached_embed_client: Optional[genai.Client] = None
_cached_embed_key: Optional[str] = None
_cached_embed_timeout: Optional[int] = None
_fallback_active: bool = False


def _get_client(api_key: Optional[str] = None, timeout_ms: Optional[int] = None) -> genai.Client:
    """Retrieve an initialized, cached Google GenAI client instance."""
    global _cached_embed_client, _cached_embed_key, _cached_embed_timeout
    key = api_key or settings.GEMINI_API_KEY
    if not key or not key.strip():
        raise ValueError("GEMINI_API_KEY is not configured or is empty.")
    
    eff_timeout = int(timeout_ms) if timeout_ms else 10000
    if _cached_embed_client is None or _cached_embed_key != key or _cached_embed_timeout != eff_timeout:
        http_options = {"timeout": eff_timeout}
        _cached_embed_client = genai.Client(api_key=key, http_options=http_options)
        _cached_embed_key = key
        _cached_embed_timeout = eff_timeout
    return _cached_embed_client


def _extract_embedding_values(response: Any) -> List[float]:
    """Safely extract vector values from SDK response supporting both singular and plural attributes."""
    if not response:
        raise EmbeddingError("Received malformed or empty response from Gemini Embedding API.")

    values = None
    if hasattr(response, "embedding") and response.embedding is not None:
        values = getattr(response.embedding, "values", None)
    elif hasattr(response, "embeddings") and response.embeddings:
        first_emb = response.embeddings[0]
        values = getattr(first_emb, "values", None)
    else:
        raise EmbeddingError("Received malformed or empty response from Gemini Embedding API.")

    if values is None:
        raise EmbeddingError("Embedding response did not contain vector values.")

    return list(values)


def embed_document(
    text: str,
    title: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout_ms: Optional[int] = None,
) -> List[float]:
    """
    Generate a 768-dimensional vector embedding for a single document chunk.
    Formats input using Gemini Embedding 2 document task instruction format:
    'title: {title or "none"} | text: {text}'
    """
    global _fallback_active
    if not text or not text.strip():
        raise ValueError("Text content for document embedding cannot be empty.")

    if _fallback_active:
        return _deterministic_fallback_embedding(text, 768)

    formatted_title = title.strip() if title and title.strip() else "none"
    formatted_content = f"title: {formatted_title} | text: {text.strip()}"

    model_name = model or settings.GEMINI_EMBEDDING_MODEL
    client = _get_client(api_key, timeout_ms)

    max_retries = 6
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model=model_name,
                contents=formatted_content,
                config=types.EmbedContentConfig(
                    output_dimensionality=768,
                ),
            )
            return _extract_embedding_values(response)
        except (ValueError, EmbeddingError):
            raise
        except Exception as e:
            err_str = str(e)
            is_rate_limit = any(k in err_str for k in ["RESOURCE_EXHAUSTED", "QuotaFailure", "429"])
            is_network_err = any(k in err_str for k in ["10054", "connection", "Connection", "socket", "Socket", "reset", "Reset", "closed", "Closed", "timeout", "Timeout"]) or isinstance(e, (OSError, ConnectionError, TimeoutError))

            is_daily_quota = "embed_content_free_tier_requests" in err_str or "Quota exceeded" in err_str or "503" in err_str or "UNAVAILABLE" in err_str
            if is_rate_limit or is_network_err or is_daily_quota:
                if is_daily_quota:
                    _fallback_active = True
                    logger.warning(f"[EMBEDDINGS] Remote Gemini embedding API limit/unavailable ({err_str[:80]}). Using deterministic fallback embedding for all remaining chunks.")
                    return _deterministic_fallback_embedding(text, 768)
                if attempt == max_retries - 1:
                    logger.error(f"[EMBEDDINGS] Exceeded max retries ({max_retries}) for Gemini embedding call: {e}")
                    raise EmbeddingError(f"Failed to generate document embedding after {max_retries} attempts: {e}") from e
                
                delay = base_delay * (2 ** attempt)
                m = re.search(r'retryDelay[\'"]?\s*:\s*[\'"]?(\d+)', err_str)
                if m:
                    delay = max(float(m.group(1)), delay) + 1.0
                
                reason_str = "rate limit" if is_rate_limit else "network interruption"
                logger.warning(f"[EMBEDDINGS] Gemini {reason_str} for {model_name} (attempt {attempt + 1}/{max_retries}: {err_str[:100]}). Retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                logger.error(f"Gemini document embedding request failed: {type(e).__name__} ({err_str[:120]})")
                raise EmbeddingError(f"Failed to generate document embedding: {e}") from e


def embed_query(
    query: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout_ms: Optional[int] = None,
) -> List[float]:
    """
    Generate a 768-dimensional vector embedding for a user search query.
    Formats input using Gemini Embedding 2 search query task instruction format:
    'task: search result | query: {query}'
    """
    global _fallback_active
    if not query or not query.strip():
        raise ValueError("Query text for embedding cannot be empty.")

    if _fallback_active:
        return _deterministic_fallback_embedding(query, 768)

    formatted_query = f"task: search result | query: {query.strip()}"

    try:
        client = _get_client(api_key, timeout_ms)
        model_name = model or settings.GEMINI_EMBEDDING_MODEL
        response = client.models.embed_content(
            model=model_name,
            contents=formatted_query,
            config=types.EmbedContentConfig(
                output_dimensionality=768,
            ),
        )
        return _extract_embedding_values(response)
    except (ValueError, EmbeddingError):
        raise
    except Exception as e:
        err_str = str(e)
        is_rate_limit = any(k in err_str for k in ["RESOURCE_EXHAUSTED", "QuotaFailure", "429"])
        if is_rate_limit:
            _fallback_active = True
            logger.warning(f"[EMBEDDINGS] Gemini query embedding quota exhausted. Using deterministic fallback embedding.")
            return _deterministic_fallback_embedding(query, 768)
        logger.error(f"Gemini query embedding request failed: {type(e).__name__} ({err_str[:120]})")
        raise EmbeddingError(f"Failed to generate query embedding: {e}") from e


def embed_documents(
    texts: List[str],
    titles: Optional[List[Optional[str]]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate 768-dimensional vector embeddings for a batch of document chunk texts.
    """
    if not texts:
        raise ValueError("List of document texts for embedding cannot be empty.")

    cleaned_items = []
    for idx, t in enumerate(texts):
        if t and t.strip():
            doc_title = titles[idx] if titles and idx < len(titles) else None
            cleaned_items.append((t.strip(), doc_title))

    if not cleaned_items:
        raise ValueError("All document texts in batch are empty.")

    model_name = model or settings.GEMINI_EMBEDDING_MODEL
    embeddings_list: List[List[float]] = []

    for text_str, doc_title in cleaned_items:
        vec = embed_document(text_str, title=doc_title, api_key=api_key, model=model_name)
        embeddings_list.append(vec)

    return embeddings_list
