"""
Integration tests for Milestone 9: Citation and Source Provenance Module.
Executes RAG pipeline end-to-end with deterministic mock retrieval and mocked LLM calls.
"""

from unittest.mock import patch
import pytest

from backend.app.rag import pipeline


def test_pipeline_citation_integration_single_source():
    """Test pipeline integration returning structured citation for single source."""
    mock_chunks = [
        {
            "chunk_id": "chunk_10_1_0",
            "document_id": 10,
            "document_version_id": 1,
            "title": "Examination Ordinance",
            "department": "CSE",
            "academic_year": "2025-26",
            "document_type": "Ordinance",
            "page_number": 4,
            "source_pages": [4],
            "text": "Passing criteria is 40% in each subject.",
            "snippet": "Passing criteria is 40% in each subject.",
        }
    ]

    with patch("backend.app.rag.retrieval.retrieve_context", return_value=mock_chunks), \
         patch("backend.app.rag.llm.generate_grounded_answer", return_value="The passing grade is 40% in each subject."):

        result = pipeline.run_pipeline("What is the passing criteria?", department="CSE")

        assert result["answer"] == "The passing grade is 40% in each subject."
        assert result["grounded"] is True
        assert result["retrieval_count"] == 1
        assert len(result["sources"]) == 1
        src = result["sources"][0]
        assert src["document_id"] == 10
        assert src["document_version_id"] == 1
        assert src["title"] == "Examination Ordinance"
        assert src["page_number"] == 4
        assert src["source_pages"] == [4]
        assert src["department"] == "CSE"


def test_pipeline_citation_integration_deduplicated_multi_sources():
    """Test pipeline integration with multiple chunks including duplicate pages."""
    mock_chunks = [
        {
            "document_id": 101,
            "document_version_id": 1,
            "title": "Scholarship Guidelines",
            "page_number": 1,
            "source_pages": [1],
            "text": "Merit scholarship is 50% waiver.",
        },
        {
            "document_id": 101,
            "document_version_id": 1,
            "title": "Scholarship Guidelines",
            "page_number": 1,
            "source_pages": [1],
            "text": "Merit scholarship requires CGPA 9.0.",
        },
        {
            "document_id": 102,
            "document_version_id": 1,
            "title": "Financial Aid Manual",
            "page_number": 3,
            "source_pages": [3, 4],
            "text": "Need-based aid application opens in July.",
        },
    ]

    with patch("backend.app.rag.retrieval.retrieve_context", return_value=mock_chunks), \
         patch("backend.app.rag.llm.generate_grounded_answer", return_value="Scholarship details and financial aid info."):

        result = pipeline.run_pipeline("How to apply for scholarship?")

        assert result["grounded"] is True
        assert result["retrieval_count"] == 3
        # Should be deduplicated from 3 chunks down to 2 distinct sources
        assert len(result["sources"]) == 2
        assert result["sources"][0]["document_id"] == 101
        assert result["sources"][1]["document_id"] == 102
        assert result["sources"][1]["source_pages"] == [3, 4]


def test_pipeline_citation_integration_no_context():
    """Test pipeline integration when retrieval yields no context."""
    with patch("backend.app.rag.retrieval.retrieve_context", return_value=[]):
        result = pipeline.run_pipeline("Unknown query?")

        assert result["grounded"] is False
        assert result["retrieval_count"] == 0
        assert result["sources"] == []
        assert "couldn't find this information" in result["answer"]
