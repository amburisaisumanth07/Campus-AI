import pytest
from unittest.mock import MagicMock, patch

from backend.app.rag import vectorstore


@patch("backend.app.rag.vectorstore.chromadb.HttpClient")
def test_get_chroma_client(mock_http_client):
    vectorstore._chroma_client = None
    client = vectorstore.get_chroma_client()
    mock_http_client.assert_called_once()
    assert client is not None


@patch("backend.app.rag.vectorstore.get_chroma_client")
def test_get_collection(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    coll = vectorstore.get_collection("test_col")
    mock_client.get_or_create_collection.assert_called_once_with(
        name="test_col",
        metadata={"hnsw:space": "cosine"},
    )
    assert coll is not None


@patch("backend.app.rag.vectorstore.get_chroma_client")
def test_health_check_success_and_failure(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Success
    mock_client.heartbeat.return_value = 123456789
    assert vectorstore.health_check() is True

    # Failure
    mock_client.heartbeat.side_effect = Exception("Connection refused")
    assert vectorstore.health_check() is False


def test_validate_vector_dimension():
    valid_vec = [0.1] * 768
    invalid_vec_short = [0.1] * 512
    invalid_vec_empty = []

    # Should not raise exception
    vectorstore.validate_vector_dimension(valid_vec)

    # Should raise ValueError
    with pytest.raises(ValueError, match="Invalid vector dimension"):
        vectorstore.validate_vector_dimension(invalid_vec_short)

    with pytest.raises(ValueError, match="Invalid vector dimension"):
        vectorstore.validate_vector_dimension(invalid_vec_empty)


def test_sanitize_metadata():
    raw_meta = {
        "document_id": 42,
        "title": "Attendance Policy",
        "page_number": 3,
        "source_pages": [3, 4],
        "department": None,
        "is_active": True,
    }
    sanitized = vectorstore.sanitize_metadata(raw_meta)
    
    assert sanitized["document_id"] == 42
    assert sanitized["doc_id"] == 42
    assert sanitized["title"] == "Attendance Policy"
    assert sanitized["page_number"] == 3
    assert sanitized["source_pages"] == "3,4"
    assert sanitized["department"] == ""
    assert sanitized["is_active"] is True


@patch("backend.app.rag.vectorstore.get_collection")
def test_add_chunks_and_upsert_chunks(mock_get_collection):
    mock_coll = MagicMock()
    mock_get_collection.return_value = mock_coll

    chunk_records = [
        {
            "id": "doc_1_v_1_c_0",
            "text": "Chunk content paragraph.",
            "metadata": {
                "document_id": 1,
                "document_version_id": 1,
                "page_number": 1,
                "source_pages": [1],
                "chunk_index": 0,
                "title": "Doc 1",
                "department": "CS",
                "academic_year": "2025",
                "document_type": "PDF",
            },
        }
    ]
    valid_embeddings = [[0.01] * 768]

    count = vectorstore.add_chunks(chunk_records, valid_embeddings)
    assert count == 1
    mock_coll.upsert.assert_called_once()

    # Mismatch length error
    with pytest.raises(ValueError, match="Mismatch between chunk records count"):
        vectorstore.add_chunks(chunk_records, [valid_embeddings[0], valid_embeddings[0]])

    # Invalid vector dimension error
    with pytest.raises(ValueError, match="Invalid vector dimension"):
        vectorstore.add_chunks(chunk_records, [[0.1] * 512])


@patch("backend.app.rag.vectorstore.get_collection")
def test_get_chunk(mock_get_collection):
    mock_coll = MagicMock()
    mock_get_collection.return_value = mock_coll

    mock_coll.get.return_value = {
        "ids": ["doc_1_v_1_c_0"],
        "documents": ["Chunk text content"],
        "metadatas": [{"document_id": 1, "title": "Test"}],
        "embeddings": [[0.05] * 768],
    }

    item = vectorstore.get_chunk("doc_1_v_1_c_0")
    assert item is not None
    assert item["id"] == "doc_1_v_1_c_0"
    assert item["text"] == "Chunk text content"
    assert item["metadata"]["document_id"] == 1
    assert len(item["embedding"]) == 768

    # Test missing chunk
    mock_coll.get.return_value = {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
    assert vectorstore.get_chunk("non_existent_id") is None


@patch("backend.app.rag.vectorstore.get_collection")
def test_delete_chunks_by_document(mock_get_collection):
    mock_coll = MagicMock()
    mock_coll.get.return_value = {"ids": ["doc_1_v_1_c_0", "doc_1_v_1_c_1"]}
    mock_get_collection.return_value = mock_coll

    deleted_count = vectorstore.delete_chunks_by_document(document_id=1)
    assert deleted_count == 2
    mock_coll.delete.assert_called_once_with(ids=["doc_1_v_1_c_0", "doc_1_v_1_c_1"])


@patch("backend.app.rag.vectorstore.get_collection")
def test_count(mock_get_collection):
    mock_coll = MagicMock()
    mock_coll.count.return_value = 15
    mock_get_collection.return_value = mock_coll

    assert vectorstore.count() == 15


@patch("backend.app.rag.vectorstore.get_collection")
def test_similarity_search(mock_get_collection):
    mock_coll = MagicMock()
    mock_coll.query.return_value = {
        "documents": [["Retrieved text snippet"]],
        "metadatas": [[{"document_id": 1, "title": "Test Doc", "page_number": 1, "chunk_index": 0}]],
        "distances": [[0.1]],
    }
    mock_get_collection.return_value = mock_coll

    query_vec = [0.02] * 768
    hits = vectorstore.similarity_search(query_vec, top_k=1)
    assert len(hits) == 1
    assert hits[0]["document_id"] == 1
    assert hits[0]["title"] == "Test Doc"
    assert hits[0]["score"] == 0.9
