# Chroma Vector Database Architecture & Integration

## 1. Overview & Rationale

CampusAI utilizes **Chroma Vector Database** (`chromadb`) as the dedicated vector store for the RAG pipeline.

### Why Chroma?
- **Native Support for Vector Search**: Optimized HNSW (Hierarchical Navigable Small World) index for fast approximate nearest neighbor search.
- **Rich Metadata Filtering**: Enables strict filtering by `document_id`, `department`, `academic_year`, and `page_number`.
- **Open-Source & Light Footprint**: High performance without heavy external cloud dependencies.
- **Docker & HTTP Client Standard**: Decoupled deployment allowing FastAPI and Chroma to scale independently.

---

## 2. Architecture & Service Topology

CampusAI employs a decoupled **separate-service architecture**:

| Service | Technology | Port Mapping | Description |
| :--- | :--- | :--- | :--- |
| **Frontend** | React + Vite | `localhost:5173` | User interface |
| **Backend API** | FastAPI | `localhost:8000` | Application API & RAG orchestration |
| **Vector Store** | Chroma DB (Docker) | `localhost:8001` → `8000` | Vector storage & similarity search |
| **Database** | PostgreSQL | `localhost:5432` | Relational document metadata & user data |

```
[ FastAPI Backend ]  --- HTTP (HttpClient) ---> [ Chroma Docker Container (Port 8001) ]
                                                          |
                                                    Volume Mount
                                                          |
                                                    [ chromadata ]
```

---

## 3. Client & Connection Configuration

The backend connects to Chroma using the official `chromadb.HttpClient` interface via settings defined in `app/core/config.py`:

```env
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION=campus_docs
```

> [!NOTE]
> `chromadb.PersistentClient` is explicitly avoided in favor of `chromadb.HttpClient` to maintain standard client-server isolation over Docker.

---

## 4. Collection Design & Vector Space

- **Collection Name**: `campus_docs` (configurable via `CHROMA_COLLECTION`)
- **Distance Metric**: Cosine Distance (`metadata={"hnsw:space": "cosine"}`)
- **Dimensionality**: **768** dimensions matching Google Gemini Embedding 2 (`gemini-embedding-2` with Matryoshka Representation Learning).

> [!IMPORTANT]
> **Why Cosine Similarity?**
> Gemini 768-dimensional embeddings generated with Matryoshka dimensionality reduction are not guaranteed to be unit-length normalized across all inputs. Cosine similarity evaluates direction rather than vector magnitude, ensuring accurate similarity scores for variable-length document chunks.

---

## 5. Metadata Schema & Preservation

Chroma metadata preserves document provenance for retrieval and source citation.

Supported Metadata Fields:
- `document_id` (int / str): Unique identifier of parent document
- `document_version_id` (int): Version of the document
- `page_number` (int): Primary page number where chunk resides
- `source_pages` (str): Comma-separated list of all source pages (e.g. `"1,2"`)
- `chunk_index` (int): Zero-based sequential index of the chunk
- `title` (str): Document title
- `department` (str): Owning department/faculty
- `academic_year` (str): Applicable academic year
- `document_type` (str): File type (e.g. `"PDF"`)

*Note: Complex metadata objects (such as lists) are sanitized into primitive string types before storage to conform to ChromaDB storage requirements.*

---

## 6. Persistence & Lifecycle Management

- **Persistence**: Chroma runs with `IS_PERSISTENT=TRUE` in Docker, backed by a persistent named volume (`chromadata`).
- **Deletion & Re-indexing**:
  - `delete_chunks_by_document(document_id: int)` removes all vector records and metadata associated with a given `document_id`.
  - Re-indexing a document involves calling `delete_chunks_by_document(document_id)` followed by `add_chunks(...)` / `upsert_chunks(...)`.
- **Duplicate ID Handling**: All additions use `collection.upsert(...)`, ensuring duplicate chunk IDs update existing records cleanly without crashing or introducing duplicate records.

---

## 7. Testing & Verification Strategy

1. **Unit Tests** (`backend/tests/unit/test_vectorstore.py`):
   - Mocks `chromadb.HttpClient` behavior.
   - Tests vector validation (rejecting vectors with dimension != 768), metadata sanitization, chunk insertion, retrieval by ID, deletion, and collection counting.
2. **Integration Tests** (`backend/tests/integration/test_chroma_integration.py`):
   - Tests against live Chroma HTTP container when online.
   - Automatically skips gracefully if Chroma Docker service is offline.
   - Verifies real PDF chunking pipeline integration using `data/documents/Test_Attendance_Rules.pdf`.
3. **Evaluation Script** (`evaluation/scripts/test_chroma.py`):
   - Standalone CLI utility to test Chroma HTTP health, insertion, retrieval, and deletion without dumping large floating point arrays to console.
