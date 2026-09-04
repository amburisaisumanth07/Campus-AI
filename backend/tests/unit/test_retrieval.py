"""
Unit tests for backend/app/rag/retrieval.py
Tests semantic retrieval with mocked query embeddings and mocked Chroma vectorstore.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.app.rag import retrieval
from backend.app.rag.retrieval import RetrievalError


@pytest.fixture
def mock_embed_query():
    with patch("backend.app.rag.retrieval.embeddings.embed_query") as mock_embed:
        mock_embed.return_value = [0.01] * 768
        yield mock_embed


@pytest.fixture
def mock_similarity_search():
    with patch("backend.app.rag.retrieval.vectorstore.similarity_search") as mock_search:
        yield mock_search


def test_empty_and_whitespace_query():
    """Verify empty or whitespace-only queries return empty list immediately."""
    assert retrieval.retrieve_context("") == []
    assert retrieval.retrieve_context("   ") == []
    assert retrieval.retrieve_context(None) == []


def test_successful_retrieval(mock_embed_query, mock_similarity_search):
    """Verify successful semantic retrieval with structured response formatting."""
    mock_similarity_search.return_value = [
        {
            "id": "doc_10_c_0",
            "text": "Attendance rules state 75% requirement.",
            "distance": 0.15,
            "score": 0.85,
            "metadata": {
                "document_id": 10,
                "document_version_id": 1,
                "page_number": 2,
                "source_pages": "2,3",
                "title": "Attendance Policy",
                "department": "CS",
                "academic_year": "2025",
                "document_type": "PDF",
                "chunk_index": 0,
            },
        }
    ]

    results = retrieval.retrieve_context("attendance rules", top_k=5)

    mock_embed_query.assert_called_once_with("attendance rules", timeout_ms=None)
    mock_similarity_search.assert_called_once()
    assert len(results) == 1

    item = results[0]
    assert item["chunk_id"] == "doc_10_c_0"
    assert item["text"] == "Attendance rules state 75% requirement."
    assert item["distance"] == pytest.approx(0.15)
    assert item["score"] == 0.85
    assert item["document_id"] == 10
    assert item["document_version_id"] == 1
    assert item["page_number"] == 2
    assert item["source_pages"] == [2, 3]
    assert item["title"] == "Attendance Policy"
    assert item["department"] == "CS"
    assert item["academic_year"] == "2025"
    assert item["document_type"] == "PDF"
    assert item["chunk_index"] == 0


def test_top_k_parameter_limiting(mock_embed_query, mock_similarity_search):
    """Verify results are limited to top_k parameter."""
    raw_hits = [
        {
            "id": f"chunk_{i}",
            "text": f"Content {i}",
            "distance": 0.05 * i,
            "score": 1.0 - (0.05 * i),
            "metadata": {"document_id": 10, "chunk_index": i},
        }
        for i in range(10)
    ]
    mock_similarity_search.return_value = raw_hits

    results = retrieval.retrieve_context("test query", top_k=3, relevance_threshold=0.0)
    assert len(results) == 3
    assert [r["chunk_id"] for r in results] == ["chunk_0", "chunk_1", "chunk_2"]


def test_relevance_ordering_and_distance_interpretation(mock_embed_query, mock_similarity_search):
    """Verify lower cosine distance / higher similarity score comes first."""
    mock_similarity_search.return_value = [
        {"id": "c2", "text": "Match 2", "distance": 0.30, "score": 0.70, "metadata": {}},
        {"id": "c1", "text": "Match 1", "distance": 0.10, "score": 0.90, "metadata": {}},
        {"id": "c3", "text": "Match 3", "distance": 0.40, "score": 0.60, "metadata": {}},
    ]

    results = retrieval.retrieve_context("query", relevance_threshold=0.0)
    assert len(results) == 3
    assert results[0]["chunk_id"] == "c1"
    assert results[1]["chunk_id"] == "c2"
    assert results[2]["chunk_id"] == "c3"


def test_relevance_threshold_filtering(mock_embed_query, mock_similarity_search):
    """Verify hits below relevance threshold are filtered out."""
    mock_similarity_search.return_value = [
        {"id": "high", "text": "High match", "distance": 0.1, "score": 0.9, "metadata": {}},
        {"id": "low", "text": "Low match", "distance": 0.6, "score": 0.4, "metadata": {}},
    ]

    # Threshold 0.70 should filter out 'low' (score 0.4)
    results = retrieval.retrieve_context("query", relevance_threshold=0.70)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "high"


def test_metadata_filters_construction(mock_embed_query, mock_similarity_search):
    """Verify metadata filters construct valid Chroma $and where clause."""
    mock_similarity_search.return_value = []

    retrieval.retrieve_context(
        "query",
        department="Computer Science",
        academic_year="2025-2026",
        document_type="PDF",
        document_id=5,
    )

    _, kwargs = mock_similarity_search.call_args
    where = kwargs.get("where_filter")
    assert "$and" in where
    conditions = where["$and"]
    assert {"department": "Computer Science"} in conditions
    assert {"academic_year": "2025-2026"} in conditions
    assert {"document_type": "PDF"} in conditions
    assert {"document_id": 5} in conditions


def test_no_results(mock_embed_query, mock_similarity_search):
    """Verify empty list is returned when Chroma returns no hits."""
    mock_similarity_search.return_value = []
    results = retrieval.retrieve_context("unmatched query")
    assert results == []


def test_embedding_failure(mock_embed_query):
    """Verify RetrievalError is raised when embed_query fails."""
    mock_embed_query.side_effect = Exception("API rate limit exceeded")

    with pytest.raises(RetrievalError, match="Failed to generate query embedding"):
        retrieval.retrieve_context("query")


def test_chroma_failure(mock_embed_query, mock_similarity_search):
    """Verify RetrievalError is raised when Chroma search fails."""
    mock_similarity_search.side_effect = Exception("Chroma connection timeout")

    with pytest.raises(RetrievalError, match="Vector store search failed"):
        retrieval.retrieve_context("query")


def test_metadata_safe_conversion():
    """Verify string source_pages and missing integer fields convert safely."""
    # Test string source_pages "1, 2, 3"
    assert retrieval.parse_source_pages("1, 2, 3", default_page=1) == [1, 2, 3]
    # Test list source_pages
    assert retrieval.parse_source_pages([10, 11], default_page=1) == [10, 11]
    # Test fallback
    assert retrieval.parse_source_pages("invalid", default_page=5) == [5]
