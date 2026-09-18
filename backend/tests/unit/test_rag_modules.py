import pytest
from unittest.mock import MagicMock, patch

from backend.app.rag import chunking, prompts, reranking, pipeline


def test_chunking_basic():
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = chunking.chunk_text(text, chunk_size=40, overlap=10)
    assert len(chunks) > 0
    assert any("sentence one" in c for c in chunks)


def test_create_chunks_from_pages():
    pages = [
        {"page_number": 1, "text_content": "Page 1 content here."},
        {"page_number": 2, "text_content": "Page 2 content here."},
    ]
    records = chunking.create_chunks_from_pages(
        doc_id=101,
        title="Test Document",
        department="CS",
        academic_year="2025-26",
        pages=pages,
    )
    assert len(records) == 2
    assert records[0]["metadata"]["doc_id"] == 101
    assert records[0]["metadata"]["department"] == "CS"


def test_reranking_pass_through():
    chunks = [
        {"id": "1", "score": 0.9},
        {"id": "2", "score": 0.8},
        {"id": "3", "score": 0.7},
    ]
    reranked = reranking.rerank_chunks("query", chunks, top_k=2)
    assert len(reranked) == 2
    assert reranked[0]["id"] == "1"


def test_prompts_formatting():
    chunks = [
        {"title": "Policy", "page_number": 1, "text": "Attendance is 75% required."}
    ]
    formatted = prompts.format_rag_prompt("What is attendance requirement?", chunks)
    assert "Attendance is 75% required." in formatted
    assert "Policy" in formatted


@patch("backend.app.rag.pipeline.knowledge_service.resolve_structured_query", return_value=None)
@patch("backend.app.rag.retrieval.retrieve_context")
@patch("backend.app.rag.llm.generate_grounded_answer")
def test_pipeline_run(mock_generate, mock_retrieve, mock_struct):
    pipeline.clear_rag_cache()
    mock_retrieve.return_value = [
        {
            "doc_id": 1,
            "title": "Regulations",
            "page_number": 5,
            "snippet": "Minimum credits needed: 160.",
            "text": "Minimum credits needed: 160.",
        }
    ]
    mock_generate.return_value = "Minimum credits required are 160."

    result = pipeline.run_pipeline("How many credits do I need?")

    assert result["answer"] == "Minimum credits required are 160."
    assert len(result["citations"]) == 1
    assert result["citations"][0]["doc_id"] == 1
    assert result["had_context"] is True


@patch("backend.app.rag.pipeline.knowledge_service.resolve_structured_query", return_value=None)
@patch("backend.app.rag.retrieval.retrieve_context")
def test_pipeline_vectorstore_error_not_found(mock_retrieve, mock_struct):
    from backend.app.rag.retrieval import VectorStoreError

    pipeline.clear_rag_cache()
    mock_retrieve.side_effect = VectorStoreError("Vector store search failed: Collection campus_docs does not exist.")

    result = pipeline.run_pipeline("What is the attendance policy?")

    assert result["status"] == "RETRIEVAL_ERROR"
    assert "synchronized" in result["answer"].lower() or "retrieved" in result["answer"].lower()
    assert result["grounded"] is False
    assert result["retrieval_error"] is True


@patch("backend.app.rag.pipeline.knowledge_service.resolve_structured_query", return_value=None)
@patch("backend.app.rag.retrieval.retrieve_context")
def test_pipeline_vectorstore_error_generic(mock_retrieve, mock_struct):
    from backend.app.rag.retrieval import VectorStoreError

    pipeline.clear_rag_cache()
    mock_retrieve.side_effect = VectorStoreError("Vector store search failed: Connection error.")

    result = pipeline.run_pipeline("What is the attendance policy?")

    assert result["status"] == "DATABASE_ERROR"
    assert "database error" in result["answer"].lower()
    assert result["grounded"] is False
    assert result["retrieval_error"] is True

