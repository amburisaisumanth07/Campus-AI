# Document Chunking Architecture

This document describes the design, implementation, and configuration of the deterministic document chunking strategy used in the CampusAI Retrieval-Augmented Generation (RAG) pipeline.

---

## 1. Why Chunking Is Needed

Raw college policy documents (such as academic regulations, examination rules, and attendance guidelines) can span dozens of pages. Passing an entire document into an LLM context window or generating a single embedding vector for a whole multi-page PDF is suboptimal for several reasons:

1. **Embedding Granularity**: Vector embedding models work best on semantically dense, targeted text passages. A single embedding for a 20-page PDF loses specific sub-clause details.
2. **Context Window Efficiency**: Injecting only the most relevant passages into the prompt minimizes LLM token consumption and reduces cost while focusing the LLM on exact facts.
3. **Retrieval Precision**: Chunking breaks large documents into discrete units that can be independently matched against student search queries.

---

## 2. Chunking Strategy & Algorithm

CampusAI uses a **sentence and word boundary-aware sliding window chunking algorithm**.

### Core Principles:
- **Deterministic**: Given identical page texts and configuration settings (`chunk_size`, `overlap`), the chunker guarantees 100% reproducible output.
- **Natural Boundary Breaking**: The chunker prioritizes splitting at sentence endings (`.`, `!`, `?` followed by space or newline) or paragraph breaks, avoiding arbitrary mid-word breaks where practical.
- **No Empty Chunks**: Extraction artifacts, redundant whitespace, and null bytes are cleaned during text normalization. Empty passages produce no chunks.

---

## 3. Configuration & Defaults

Chunking parameters are configured centrally in `app.core.config.Settings` via environment variables:

| Setting | Default Value | Description |
| :--- | :--- | :--- |
| `RAG_CHUNK_SIZE` | `1000` characters | Target maximum length of each text chunk (~150-200 words). |
| `RAG_CHUNK_OVERLAP` | `200` characters | Character overlap between consecutive chunks (~30-40 words). |

### Rationale for Default Values:
- **`RAG_CHUNK_SIZE = 1000`**: College policy clauses and academic rules are typically structured as 1–3 dense paragraphs. A 1000-character window captures complete policy statements without truncating context or diluting vector search similarity.
- **`RAG_CHUNK_OVERLAP = 200`**: Ensures that key condition statements bridging two adjacent passages or crossing page boundaries appear in both chunks, preventing context loss at chunk boundaries during vector search retrieval.

---

## 4. Page Provenance & Metadata Preservation

Maintaining exact source provenance is critical for student-facing academic support tools. Each `DocumentChunk` records:

- **Primary Page Number (`page_number`)**: The starting page number of the chunk text.
- **Source Pages (`source_pages`)**: A complete, ordered list of all page numbers spanned by the chunk (e.g., `[1, 2]`).
- **Chunk Index (`chunk_index`)**: Zero-indexed sequential integer identifying chunk order within the document version.
- **Document & Version Attributes**: `document_id`, `document_version_id`, `title`, `department`, `academic_year`.
- **Length Metrics**: `character_count` and `token_count` (estimated word count).

### Data Structure (`DocumentChunk`):
```python
@dataclass
class DocumentChunk:
    chunk_id: str             # Format: doc_{id}_v_{version}_c_{index}
    document_id: int
    document_version_id: int
    page_number: int          # Primary / starting page
    text: str
    chunk_index: int
    character_count: int
    token_count: int
    metadata: Dict[str, Any]  # Includes source_pages list and document metadata
```

---

## 5. Limitations

- **Tables & Code Blocks**: Complex multi-row tables or non-standard formatting extracted from PDF files may span multiple lines; basic sentence boundary detection does not reconstruct tabular relationships.
- **Header/Footer Repetition**: Running headers and footers extracted from PDF pages remain part of page text streams; future preprocessing iterations can strip recurring header strings.

---

## 6. Future Embedding & Vector Indexing Stage

In subsequent pipeline milestones:
1. Each `DocumentChunk.text` will be passed to `google-genai` (`text-embedding-004`) to generate dense vector embeddings.
2. The resulting vector along with `DocumentChunk.metadata` will be stored in ChromaDB for similarity searching during user chat interactions.
