# Semantic Retrieval Architecture & Specifications

## 1. Overview

The **Semantic Retrieval Service** (`app/rag/retrieval.py`) is responsible for fetching the most relevant document chunks from the Chroma vector store in response to user queries.

It acts as the retrieval layer in the CampusAI RAG pipeline without performing LLM generation, reranking, or conversation history management.

```
[ User Query String ]
          │
          ▼
[ embeddings.embed_query() ]  ───► 768-dim Query Embedding Vector
          │
          ▼
[ vectorstore.similarity_search() ]  ───► Cosine Similarity Search + Metadata Filtering
          │
          ▼
[ Relevance Threshold & Top-K ]  ───► Filtered & Ordered Result Chunks
```

---

## 2. Query Embedding Generation

Query text is embedded using `embeddings.embed_query(query)` powered by Google Gemini Embedding 2 (`gemini-embedding-2` model).

- **Task Instruction Format**: `'task: search result | query: {query}'`
- **Output Dimensionality**: 768 floating point numbers (Matryoshka Representation Learning).
- **Validation**: Empty or whitespace-only queries return `[]` immediately without API or database calls.

---

## 3. Cosine Distance & Relevance Score Metric

ChromaDB uses **Cosine Distance** ($d \in [0, 2]$) to index and compare 768-dimensional vectors.

- **Cosine Distance ($d$)**: Measures angular distance between vectors ($0.0 = $ identical direction). Lower distance indicates higher relevance.
- **Cosine Similarity Score ($s$)**: Computed as $s = 1.0 - d$.
- **Relevance Ordering**: Results are sorted in ascending order of cosine distance (highest similarity score first).

---

## 4. Relevance Thresholding & Top-K Capping

1. **Top-K (`top_k`)**:
   - Configured globally via `RAG_TOP_K` (default `5`), or overridden per request.
   - Initial candidate pool of size `top_k * 2` is fetched from Chroma to allow downstream threshold filtering.
2. **Relevance Threshold (`relevance_threshold`)**:
   - Configured globally via `RAG_RELEVANCE_THRESHOLD` (default `0.0`), or overridden per request.
   - Candidates are retained if `score >= relevance_threshold` (or $d \le 1.0 - \text{threshold}$).
   - Irrelevant chunks falling below the similarity threshold are discarded.

---

## 5. Metadata Filtering

Chroma `$and` filtering is dynamically constructed when metadata constraints are specified.

Supported Metadata Filter Fields:
- `department` (str)
- `academic_year` (str)
- `document_type` (str)
- `document_id` (int)
- `document_version_id` (int)

---

## 6. Result Schema & Metadata Provenance

The service returns a structured list of dictionary objects representing retrieved chunks:

```python
{
    "chunk_id": "doc_10_v_1_c_0",
    "text": "Students must maintain at least 75% attendance in all enrolled courses...",
    "distance": 0.1425,
    "score": 0.8575,
    "document_id": 10,
    "document_version_id": 1,
    "page_number": 2,
    "source_pages": [2, 3],
    "title": "Student Attendance Rules 2025",
    "department": "Computer Science",
    "academic_year": "2025-2026",
    "document_type": "PDF",
    "chunk_index": 0,
    "metadata": { ... }
}
```

> [!NOTE]
> Chroma metadata strings representing multi-page provenance (e.g. `"2,3"`) are automatically parsed and converted into native Python integer lists (e.g. `[2, 3]`).

---

## 7. Limitations

- **Syntactic Keyword Matching**: Pure dense vector search may miss specific exact code numbers or acronyms if not captured semantically; future hybrid search or reranking (Milestone 8) will refine precision.
- **Scope**: Reranking (`reranking.py`) and LLM response generation (`llm.py`) are strictly decoupled and executed in subsequent RAG pipeline stages.
