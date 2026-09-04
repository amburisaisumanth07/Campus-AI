"""
Integration tests for Chroma Vector Database Service.
Executes against real Chroma HTTP service when available, or skips cleanly.
"""

from pathlib import Path
import pytest
from backend.app.rag import vectorstore
from backend.app.rag.chunking import chunk_document_pages
from backend.app.services.pdf_service import extract_pages


@pytest.fixture(autouse=True)
def require_chroma():
    """Ensure Chroma HTTP service is accessible before running integration tests."""
    if not vectorstore.health_check():
        pytest.skip("Chroma Docker service is not reachable on localhost:8001")


@pytest.fixture
def test_collection_name():
    return "test_chroma_integration_collection"


@pytest.fixture
def clean_collection(test_collection_name):
    """Provide clean collection and cleanup after test."""
    client = vectorstore.get_chroma_client()
    try:
        client.delete_collection(name=test_collection_name)
    except Exception:
        pass

    coll = vectorstore.get_collection(collection_name=test_collection_name)
    yield coll

    try:
        client.delete_collection(name=test_collection_name)
    except Exception:
        pass


def test_chroma_health():
    """Verify Chroma health check API returns True."""
    assert vectorstore.health_check() is True


def test_collection_creation(clean_collection):
    """Verify Chroma collection creation with cosine space."""
    assert clean_collection is not None
    assert clean_collection.name == "test_chroma_integration_collection"


def test_insert_one_and_get_chunk(clean_collection):
    """Verify inserting a single chunk and retrieving it by ID."""
    chunk = {
        "id": "single_chunk_001",
        "text": "Students must maintain at least 75% attendance.",
        "metadata": {
            "document_id": 101,
            "document_version_id": 1,
            "page_number": 1,
            "source_pages": [1],
            "chunk_index": 0,
            "title": "Attendance Policy",
            "department": "Academic Affairs",
            "academic_year": "2025-2026",
            "document_type": "PDF",
        },
    }
    embedding = [0.01 * (i % 10) for i in range(768)]

    # Patch collection in vectorstore to target integration collection
    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_collection

        added = vectorstore.add_chunks([chunk], [embedding])
        assert added == 1

        retrieved = vectorstore.get_chunk("single_chunk_001")
        assert retrieved is not None
        assert retrieved["id"] == "single_chunk_001"
        assert retrieved["text"] == "Students must maintain at least 75% attendance."
        assert retrieved["metadata"]["document_id"] == 101
        assert retrieved["metadata"]["title"] == "Attendance Policy"
        assert len(retrieved["embedding"]) == 768
    finally:
        vectorstore.get_collection = original_get_collection


def test_insert_multiple_and_count(clean_collection):
    """Verify inserting multiple chunks and checking collection count."""
    chunks = [
        {
            "id": f"multi_chunk_{i}",
            "text": f"This is rule sentence number {i}.",
            "metadata": {
                "document_id": 200,
                "document_version_id": 1,
                "page_number": i + 1,
                "source_pages": [i + 1],
                "chunk_index": i,
                "title": "Multi Rule Doc",
                "department": "CS",
                "academic_year": "2025",
                "document_type": "PDF",
            },
        }
        for i in range(5)
    ]
    embeddings = [[0.02 * (j % 5) for j in range(768)] for _ in range(5)]

    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_collection

        added = vectorstore.upsert_chunks(chunks, embeddings)
        assert added == 5
        assert vectorstore.count() == 5
    finally:
        vectorstore.get_collection = original_get_collection


def test_duplicate_upsert_behavior(clean_collection):
    """Verify duplicate IDs are safely upserted without throwing errors."""
    chunk = {
        "id": "dup_chunk_01",
        "text": "Initial text content.",
        "metadata": {"document_id": 300, "title": "Version 1"},
    }
    embedding = [0.03] * 768

    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_collection

        vectorstore.upsert_chunks([chunk], [embedding])
        assert vectorstore.count() == 1

        # Upsert with updated text
        updated_chunk = {
            "id": "dup_chunk_01",
            "text": "Updated text content.",
            "metadata": {"document_id": 300, "title": "Version 2"},
        }
        vectorstore.upsert_chunks([updated_chunk], [embedding])
        assert vectorstore.count() == 1

        retrieved = vectorstore.get_chunk("dup_chunk_01")
        assert retrieved["text"] == "Updated text content."
        assert retrieved["metadata"]["title"] == "Version 2"
    finally:
        vectorstore.get_collection = original_get_collection


def test_metadata_preservation(clean_collection):
    """Verify all required metadata fields are stored and preserved."""
    chunk = {
        "id": "meta_chunk_01",
        "text": "Metadata validation chunk text.",
        "metadata": {
            "document_id": 500,
            "document_version_id": 2,
            "page_number": 3,
            "source_pages": [3, 4],
            "chunk_index": 7,
            "title": "Preservation Test",
            "department": "Engineering",
            "academic_year": "2025-2026",
            "document_type": "PDF",
        },
    }
    embedding = [0.04] * 768

    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_collection

        vectorstore.add_chunks([chunk], [embedding])
        retrieved = vectorstore.get_chunk("meta_chunk_01")
        meta = retrieved["metadata"]

        assert meta["document_id"] == 500
        assert meta["document_version_id"] == 2
        assert meta["page_number"] == 3
        assert meta["source_pages"] == "3,4"
        assert meta["chunk_index"] == 7
        assert meta["title"] == "Preservation Test"
        assert meta["department"] == "Engineering"
        assert meta["academic_year"] == "2025-2026"
        assert meta["document_type"] == "PDF"
    finally:
        vectorstore.get_collection = original_get_collection


def test_vector_dimension_validation(clean_collection):
    """Verify vectors with dimension != 768 are rejected with ValueError."""
    invalid_chunk = {
        "id": "invalid_dim_chunk",
        "text": "Invalid vector length.",
        "metadata": {"document_id": 999},
    }
    invalid_embedding = [0.1] * 512

    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_collection

        with pytest.raises(ValueError, match="Invalid vector dimension"):
            vectorstore.add_chunks([invalid_chunk], [invalid_embedding])
    finally:
        vectorstore.get_collection = original_get_collection


def test_deletion_by_document(clean_collection):
    """Verify document-level deletion removes all chunks for that document_id."""
    chunks = [
        {"id": "doc10_c1", "text": "Doc 10 Chunk 1", "metadata": {"document_id": 10}},
        {"id": "doc10_c2", "text": "Doc 10 Chunk 2", "metadata": {"document_id": 10}},
        {"id": "doc20_c1", "text": "Doc 20 Chunk 1", "metadata": {"document_id": 20}},
    ]
    embeddings = [[0.05] * 768 for _ in range(3)]

    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_collection

        vectorstore.upsert_chunks(chunks, embeddings)
        assert vectorstore.count() == 3

        deleted = vectorstore.delete_chunks_by_document(document_id=10)
        assert deleted == 2
        assert vectorstore.count() == 1
        assert vectorstore.get_chunk("doc20_c1") is not None
        assert vectorstore.get_chunk("doc10_c1") is None
    finally:
        vectorstore.get_collection = original_get_collection


def test_real_pdf_pipeline_integration(clean_collection):
    """Integration test using real Test_Attendance_Rules.pdf chunking pipeline."""
    pdf_path = Path("data/documents/Test_Attendance_Rules.pdf")
    if not pdf_path.exists():
        pytest.skip("Test_Attendance_Rules.pdf file not found")

    pages = extract_pages(pdf_path)
    assert len(pages) > 0

    chunks = chunk_document_pages(
        pages=pages,
        document_id=999,
        document_version_id=1,
        title="Test Attendance Rules",
        department="Computer Science",
        academic_year="2025-2026",
    )
    assert len(chunks) > 0

    chunk_dicts = [c.to_dict() for c in chunks]
    embeddings = [[0.01 * ((i + j) % 10) for j in range(768)] for i in range(len(chunk_dicts))]

    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_collection

        added_count = vectorstore.add_chunks(chunk_dicts, embeddings)
        assert added_count == len(chunks)
        assert vectorstore.count() == len(chunks)

        first_chunk_id = chunk_dicts[0]["id"]
        retrieved = vectorstore.get_chunk(first_chunk_id)
        assert retrieved is not None
        assert retrieved["metadata"]["title"] == "Test Attendance Rules"
    finally:
        vectorstore.get_collection = original_get_collection
