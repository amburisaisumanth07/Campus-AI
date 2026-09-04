# Vector Embeddings Architecture

This document details the design, configuration, error handling, and testing strategy for the vector embedding service in the CampusAI Retrieval-Augmented Generation (RAG) pipeline.

---

## 1. What Are Embeddings?

Vector embeddings are dense numerical array representations (floats) of textual passages that capture semantic meaning, context, and intent. Words and phrases with similar semantic meanings map to vectors positioned close together in high-dimensional vector space.

---

## 2. Why Embeddings Are Used in RAG

Traditional keyword search (e.g. searching exact strings) fails when students ask questions using synonyms, conversational phrasing, or informal terms (e.g., asking *"How many classes can I skip?"* instead of *"minimum attendance percentage requirement"*).

Vector embeddings allow CampusAI to perform **semantic search**:
1. Passage chunks from policy documents are converted into dense vector representations.
2. User queries are converted into dense vector representations in the same vector space.
3. Cosine or Euclidean similarity metrics identify the most relevant document passages based on semantic meaning, regardless of exact keyword overlap.

---

## 3. Asymmetric Retrieval & Prompt Formatting

In `gemini-embedding-2`, task-specific asymmetric retrieval optimization is performed via **task instruction content formatting** rather than legacy `task_type` API parameters:

- **Document Content Formatting**:
  `title: {title or "none"} | text: {document_chunk_text}`
  Optimizes the vector representation for document passage indexing and retrieval.

- **Search Query Formatting**:
  `task: search result | query: {student_search_query}`
  Optimizes the vector representation for search questions matching policy document passages.

---

## 4. Model Selection & Dimensionality

| Attribute | Configuration / Value |
| :--- | :--- |
| **Provider** | Google GenAI SDK (`google-genai`) |
| **Model Name** | `gemini-embedding-2` |
| **Vector Dimension** | `768` floats (Matryoshka Representation Learning) |
| **Environment Config** | `GEMINI_EMBEDDING_MODEL` in `.env` |

### Why We Selected 768 Dimensions:
`gemini-embedding-2` uses Matryoshka Representation Learning (MRL), supporting vector truncation from its default 3072 dimensions down to smaller sizes via `output_dimensionality=768`. Selecting 768 dimensions reduces vector storage footprint by 75% and speeds up similarity search comparisons while maintaining over 98% of semantic retrieval accuracy.

---

## 5. API Key Configuration

The embedding service reads `GEMINI_API_KEY` from `app.core.config.Settings`:

```bash
# .env file
GEMINI_API_KEY="your-gemini-api-key-here"
GEMINI_EMBEDDING_MODEL="gemini-embedding-2"
```

*Note: API keys are never logged or exposed in client responses or error tracebacks.*

---

## 6. Current Implementation Scope & Chroma Status

> [!NOTE]
> **Status Notice:** As of Milestone 5, the embedding service (`app.rag.embeddings`) is fully implemented and unit-tested in isolation. **ChromaDB vector indexing has not started yet** and document upload hooks remain unchanged. Chroma vector indexing will be integrated in Milestone 6.

---

## 7. Error Handling Strategy

The embedding service (`app.rag.embeddings`) enforces strict input and response validation:

- **Empty Input Validation (`ValueError`)**: Empty strings or empty text lists raise `ValueError` before calling external API endpoints.
- **Missing API Key (`ValueError`)**: Unconfigured or blank API keys raise `ValueError` immediately.
- **Provider Failure (`EmbeddingError`)**: API timeouts, connection errors, or rate limits are caught and wrapped in `EmbeddingError` with clean logging.
- **Response Validation (`EmbeddingError`)**: Malformed API responses missing vector values trigger `EmbeddingError`.

---

## 8. Testing Strategy

1. **Automated Unit Tests (`backend/tests/unit/test_embeddings.py`)**:
   - All Gemini API calls are mocked using `unittest.mock`.
   - Tests verify 100% of input validation, `gemini-embedding-2` task instruction prompt formatting (`task: search result | query: ...` and `title: ... | text: ...`), batch handling, exception propagation, and 768-dimensional vector outputs with `output_dimensionality=768`.
   - Zero live network/API calls during pytest execution.

2. **Manual Integration Test (`evaluation/scripts/test_gemini_embeddings.py`)**:
   - Standalone script for testing real API key connectivity.
   - Executes live `embed_document` and `embed_query` calls.
   - Outputs vector dimensions only; never prints full vectors.
