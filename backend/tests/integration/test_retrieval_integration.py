"""
Integration tests for Semantic Retrieval service against real Chroma HTTP database.
Uses deterministic 768-dimensional vectors without calling live Gemini API.
"""

from unittest.mock import patch
import pytest

from backend.app.rag import retrieval, vectorstore


@pytest.fixture(autouse=True)
def require_chroma():
    """Ensure Chroma HTTP service is accessible before running integration tests."""
    if not vectorstore.health_check():
        pytest.skip("Chroma Docker service is not reachable on localhost:8001")


@pytest.fixture
def integration_collection_name():
    return "test_retrieval_integration_collection"


@pytest.fixture
def clean_retrieval_collection(integration_collection_name):
    """Provide clean collection and cleanup after test."""
    client = vectorstore.get_chroma_client()
    try:
        client.delete_collection(name=integration_collection_name)
    except Exception:
        pass

    coll = vectorstore.get_collection(collection_name=integration_collection_name)
    yield coll

    try:
        client.delete_collection(name=integration_collection_name)
    except Exception:
        pass


def test_retrieval_integration_flow(clean_retrieval_collection):
    """
    Full integration test:
    - Insert deterministic chunks & vectors into Chroma
    - Mock embed_query to return matching target query vector
    - Call retrieve_context()
    - Verify ordering, top_k, metadata, threshold, and no-result filtering.
    """
    # 1. Prepare 3 deterministic chunks and 768-dim vectors
    # Target vector (Query matches chunk 1 closest, chunk 2 second, chunk 3 furthest)
    # Target vector (Query matches chunk 1 closest [score 1.0], chunk 2 second [score ~0.71], chunk 3 furthest [score 0.0])
    target_query_vec = [1.0] + [0.0] * 767

    vec1 = [1.0] + [0.0] * 767  # Distance 0.0, score 1.0
    vec2 = [0.5] + [0.5] + [0.0] * 766  # Distance ~0.29, score ~0.71
    vec3 = [-1.0] + [0.0] * 767  # Distance 2.0, score 0.0

    chunks = [
        {
            "id": "ret_chunk_1",
            "text": "Computer Science department attendance rules require 75% minimum.",
            "metadata": {
                "document_id": 101,
                "document_version_id": 1,
                "page_number": 1,
                "source_pages": [1],
                "chunk_index": 0,
                "title": "CS Attendance Policy",
                "department": "Computer Science",
                "academic_year": "2025-2026",
                "document_type": "PDF",
            },
        },
        {
            "id": "ret_chunk_2",
            "text": "Electronics department attendance policy requires 75% attendance.",
            "metadata": {
                "document_id": 102,
                "document_version_id": 1,
                "page_number": 2,
                "source_pages": [2],
                "chunk_index": 0,
                "title": "ECE Attendance Policy",
                "department": "Electronics",
                "academic_year": "2025-2026",
                "document_type": "PDF",
            },
        },
        {
            "id": "ret_chunk_3",
            "text": "Sports policy guidelines for varsity athletes.",
            "metadata": {
                "document_id": 103,
                "document_version_id": 1,
                "page_number": 5,
                "source_pages": [5, 6],
                "chunk_index": 0,
                "title": "Sports Policy",
                "department": "Sports",
                "academic_year": "2024-2025",
                "document_type": "PDF",
            },
        },
    ]

    # Patch vectorstore to target integration test collection
    original_get_collection = vectorstore.get_collection
    try:
        vectorstore.get_collection = lambda col_name=None: clean_retrieval_collection

        # Insert chunks
        added = vectorstore.upsert_chunks(chunks, [vec1, vec2, vec3])
        assert added == 3
        assert vectorstore.count() == 3

        # Mock embed_query to return target_query_vec without Gemini API call
        with patch("backend.app.rag.retrieval.embeddings.embed_query") as mock_embed:
            mock_embed.return_value = target_query_vec

            # A. Basic Retrieval Test
            results = retrieval.retrieve_context("attendance rules", top_k=2, relevance_threshold=0.0)
            assert len(results) == 2
            assert results[0]["chunk_id"] == "ret_chunk_1"
            assert results[0]["department"] == "Computer Science"
            assert results[0]["source_pages"] == [1]

            # B. Filter by Department Test
            cs_results = retrieval.retrieve_context(
                "attendance rules",
                top_k=5,
                department="Computer Science",
                relevance_threshold=0.0,
            )
            assert len(cs_results) == 1
            assert cs_results[0]["chunk_id"] == "ret_chunk_1"

            # C. Relevance Threshold Test (High threshold filters out distant matches)
            high_thresh_results = retrieval.retrieve_context(
                "attendance rules",
                top_k=5,
                relevance_threshold=0.95,
            )
            assert len(high_thresh_results) >= 1
            for res in high_thresh_results:
                assert res["score"] >= 0.95

            # D. No Match Filter Test
            no_match_results = retrieval.retrieve_context(
                "attendance rules",
                top_k=5,
                department="NonExistentDept",
                relevance_threshold=0.0,
            )
            assert len(no_match_results) == 0

    finally:
        vectorstore.get_collection = original_get_collection
