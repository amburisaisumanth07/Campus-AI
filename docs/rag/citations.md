# Source Citation and Provenance System (Milestone 9)

## Overview

The Citation and Source Provenance module provides reliable, deterministic, application-side source citations derived directly from retrieved document metadata.

---

## Core Principles & Architecture

### 1. Separation of Concerns
* **LLM Responsibility**: Gemini generates the text answer grounded exclusively in the provided context text.
* **Application Responsibility**: The application extracts, normalizes, deduplicates, and orders source citations directly from vector search metadata.

### 2. Why the LLM Does Not Generate Citations
Asking an LLM to generate document titles, page numbers, version IDs, or citation footnotes introduces significant hallucination risks. LLMs frequently hallucinate plausible-sounding page numbers, misquote document titles, or invent non-existent policy citations. 

By handling citation extraction deterministically in Python application logic, CampusAI guarantees **100% provenance accuracy** with zero possibility of invented source metadata.

---

## End-to-End Provenance Flow

```
PDF Ingestion & Chunking
    ↓
Preserve metadata (doc_id, doc_version_id, page_number, source_pages, title, department, academic_year)
    ↓
Chroma Vector Store
    ↓
Semantic Retrieval (retrieve_context)
    ↓
Citation Engine (citations.py: parse, normalize, preserve missingness, deduplicate, preserve rank order)
    ↓
Pipeline Response Payload (answer, grounded, retrieval_count, sources)
```

---

## Key Provenance Behaviors

### Page Preservation & Multi-Page Chunks
During document chunking:
- Chunks originating from single pages carry `page_number` and `source_pages = [page_number]`.
- Chunks spanning multiple pages (cross-page sliding windows) preserve all contributing pages in `source_pages` (e.g., `source_pages = [14, 15]`).
- Page ranges are strictly preserved across the retrieval pipeline.

### Document Version Handling
Documents may undergo revisions across academic years (e.g. 2025 Handbook vs 2026 Handbook). 
- Every chunk tracks both `document_id` and `document_version_id`.
- Chunks from different versions of the same document retain distinct deduplication keys and remain clearly distinguishable in the output citations list.

### Deduplication Strategy
If semantic search retrieves multiple chunks originating from the exact same document page(s):
- **Deduplication Key**: `(document_id, document_version_id, page_number/source_pages)`
- Only the **first** (highest relevant rank) chunk for that page combination is emitted as a citation entry.
- Subsequent chunks from the same page combination are filtered out.

### Preservation of Relevance Ordering
Retrieval returns chunks sorted by cosine similarity distance. The citation engine processes chunks in exact rank order, ensuring that the most relevant source documents appear first in `sources`.

### Strict Metadata Preservation (No Invented Metadata)
If a metadata field (such as `page_number` or `title`) is unavailable or omitted in the vector store:
- The engine sets the field to `null` (`None` in Python).
- The engine **never** invents fallback defaults (such as defaulting missing page numbers to `1` or missing titles to `"Untitled Document"`).

---

## Pipeline Response Schema

```json
{
  "answer": "Passing criteria is 40% in each subject.",
  "grounded": true,
  "retrieval_count": 2,
  "sources": [
    {
      "document_id": 10,
      "document_version_id": 1,
      "title": "Examination Ordinance",
      "document_type": "Ordinance",
      "department": "CSE",
      "academic_year": "2025-26",
      "page_number": 4,
      "source_pages": [4],
      "snippet": "Passing criteria is 40% in each subject."
    }
  ]
}
```

---

## Current Limitations & Milestone 10 Deferral

- **Inline Footnote Anchors (`[1]`, `[2]`)**: In Milestone 9, citations are provided as a top-level list of source objects (`sources`). Inline text bracket matching and UI citation chips are reserved for **Milestone 10** (Citation Rendering & Source Provenance UI).
- **Backend-Only Scope**: Milestone 9 establishes the backend citation contract, unit tests, and integration verification.
