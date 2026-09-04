"""
Unit tests for Milestone 9: Citation and Source Provenance Module.
Covers all 12 required unit testing scenarios.
"""

from unittest.mock import patch
import pytest

from backend.app.rag import citations, pipeline, prompts


def test_one_source():
    """1. Test citation building for a single source chunk."""
    chunk = {
        "document_id": 10,
        "document_version_id": 1,
        "title": "Academic Calendar",
        "document_type": "Policy",
        "department": "CSE",
        "academic_year": "2025-26",
        "page_number": 3,
        "source_pages": [3],
        "snippet": "Exams begin May 10.",
    }
    cits = citations.build_citations_from_chunks([chunk])
    assert len(cits) == 1
    assert cits[0]["document_id"] == 10
    assert cits[0]["document_version_id"] == 1
    assert cits[0]["title"] == "Academic Calendar"
    assert cits[0]["page_number"] == 3
    assert cits[0]["source_pages"] == [3]
    assert cits[0]["snippet"] == "Exams begin May 10."


def test_multiple_sources():
    """2. Test citation building for multiple distinct source chunks."""
    chunks = [
        {
            "document_id": 1,
            "document_version_id": 1,
            "title": "Hostel Policy",
            "page_number": 2,
            "snippet": "Curfew is 10 PM.",
        },
        {
            "document_id": 2,
            "document_version_id": 1,
            "title": "Mess Menu",
            "page_number": 5,
            "snippet": "Breakfast is 8 AM.",
        },
    ]
    cits = citations.build_citations_from_chunks(chunks)
    assert len(cits) == 2
    assert cits[0]["document_id"] == 1
    assert cits[1]["document_id"] == 2


def test_duplicate_source_chunks():
    """3. Test deduplication of identical chunks sharing doc_id, doc_version_id, and pages."""
    chunks = [
        {
            "document_id": 1,
            "document_version_id": 1,
            "title": "Hostel Policy",
            "page_number": 2,
            "source_pages": [2],
            "snippet": "Curfew is 10 PM.",
        },
        {
            "document_id": 1,
            "document_version_id": 1,
            "title": "Hostel Policy",
            "page_number": 2,
            "source_pages": [2],
            "snippet": "Duplicate chunk of curfew 10 PM.",
        },
    ]
    cits = citations.build_citations_from_chunks(chunks)
    assert len(cits) == 1
    assert cits[0]["document_id"] == 1
    assert cits[0]["page_number"] == 2


def test_multi_page_source():
    """4. Test preservation and sorting of multi-page chunks."""
    chunk = {
        "document_id": 5,
        "document_version_id": 1,
        "title": "Course Curriculum",
        "page_number": 14,
        "source_pages": [15, 14],
        "snippet": "Multi-page content.",
    }
    cits = citations.build_citations_from_chunks([chunk])
    assert len(cits) == 1
    assert cits[0]["source_pages"] == [14, 15]


def test_different_document_versions():
    """5. Test that different versions of the same document remain distinct citations."""
    chunks = [
        {
            "document_id": 100,
            "document_version_id": 1,
            "title": "Fee Structure 2025",
            "page_number": 1,
            "snippet": "Fee is $1000.",
        },
        {
            "document_id": 100,
            "document_version_id": 2,
            "title": "Fee Structure 2026",
            "page_number": 1,
            "snippet": "Fee is $1200.",
        },
    ]
    cits = citations.build_citations_from_chunks(chunks)
    assert len(cits) == 2
    assert cits[0]["document_version_id"] == 1
    assert cits[1]["document_version_id"] == 2


def test_missing_page_metadata():
    """6. Test that missing page metadata returns None/[] rather than invented defaults."""
    chunk = {
        "document_id": 42,
        "document_version_id": 1,
        "title": "Notice Board",
        "page_number": None,
        "source_pages": None,
        "snippet": "Holiday tomorrow.",
    }
    cits = citations.build_citations_from_chunks([chunk])
    assert len(cits) == 1
    assert cits[0]["page_number"] is None
    assert cits[0]["source_pages"] == []


def test_missing_title():
    """7. Test that missing title returns None rather than invented 'Untitled Document'."""
    chunk = {
        "document_id": 42,
        "document_version_id": 1,
        "title": None,
        "page_number": 1,
        "snippet": "No title chunk.",
    }
    cits = citations.build_citations_from_chunks([chunk])
    assert len(cits) == 1
    assert cits[0]["title"] is None


def test_metadata_normalization():
    """8. Test normalization of strings, numbers, floats, and comma-separated pages."""
    chunk = {
        "document_id": "101",
        "document_version_id": 2.0,
        "title": "  Lab Manual  ",
        "page_number": "5",
        "source_pages": "5, 6, 7",
        "snippet": "  Wear goggles.  ",
    }
    cits = citations.build_citations_from_chunks([chunk])
    assert len(cits) == 1
    cit = cits[0]
    assert cit["document_id"] == 101
    assert cit["document_version_id"] == 2
    assert cit["title"] == "Lab Manual"
    assert cit["page_number"] == 5
    assert cit["source_pages"] == [5, 6, 7]
    assert cit["snippet"] == "Wear goggles."


def test_source_ordering():
    """9. Test that citations strictly preserve the input relevance rank ordering."""
    chunks = [
        {"document_id": 1, "page_number": 10, "score": 0.95},
        {"document_id": 2, "page_number": 2, "score": 0.88},
        {"document_id": 3, "page_number": 1, "score": 0.72},
    ]
    cits = citations.build_citations_from_chunks(chunks)
    assert len(cits) == 3
    assert [c["document_id"] for c in cits] == [1, 2, 3]


def test_no_context_behavior():
    """10. Test pipeline short-circuiting when zero chunks are retrieved."""
    with patch("backend.app.rag.retrieval.retrieve_context", return_value=[]):
        res = pipeline.run_pipeline("Non-existent policy?")
        assert res["answer"] == prompts.NO_CONTEXT_FALLBACK_TEXT
        assert res["grounded"] is False
        assert res["retrieval_count"] == 0
        assert res["sources"] == []


def test_grounded_flag():
    """11. Test grounded flag status when generation succeeds vs when LLM fails."""
    pipeline.clear_rag_cache()
    chunks = [{"document_id": 1, "page_number": 1, "text": "Valid context."}]
    with patch("backend.app.rag.retrieval.retrieve_context", return_value=chunks):
        # Case A: Success -> grounded = True
        with patch("backend.app.rag.llm.generate_grounded_answer", return_value="Valid answer."):
            res = pipeline.run_pipeline("Test query A")
            assert res["grounded"] is True

        # Case B: LLM failure -> grounded = False
        with patch("backend.app.rag.llm.generate_grounded_answer", side_effect=Exception("API error")):
            res = pipeline.run_pipeline("Test query B")
            assert res["grounded"] is False
            assert res["generation_error"] is True
            assert "answer-generation service is temporarily unavailable" in res["answer"]


def test_citation_stability_determinism():
    """12. Test that citation generation is deterministic across multiple calls."""
    chunks = [
        {"document_id": 10, "document_version_id": 1, "page_number": 2, "source_pages": [2, 3]},
        {"document_id": 20, "document_version_id": 1, "page_number": 1, "source_pages": [1]},
    ]
    res1 = citations.build_citations_from_chunks(chunks)
    res2 = citations.build_citations_from_chunks(chunks)
    assert res1 == res2
