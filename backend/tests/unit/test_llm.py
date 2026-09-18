import pytest
from unittest.mock import MagicMock, patch
from backend.app.rag import llm, prompts, pipeline
from backend.app.core.config import settings


def test_successful_grounded_answer():
    """Test generating a grounded answer with mocked Gemini client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Students must maintain a minimum 75% attendance in each course."
    mock_client.models.generate_content.return_value = mock_response

    chunks = [
        {
            "doc_id": 1,
            "title": "Academic Regulations",
            "page_number": 4,
            "source_pages": [4, 5],
            "department": "CSE",
            "academic_year": "2025-26",
            "document_type": "Handbook",
            "text": "Students must maintain a minimum 75% attendance in each course.",
        }
    ]

    answer = llm.generate_grounded_answer(
        question="What is the attendance policy?",
        context_chunks=chunks,
        client=mock_client,
    )

    assert answer == "Students must maintain a minimum 75% attendance in each course."
    mock_client.models.generate_content.assert_called_once()


def test_multiple_retrieved_chunks():
    """Test generating an answer with multiple context chunks."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Exams start Dec 1 and registration closes Nov 15."
    mock_client.models.generate_content.return_value = mock_response

    chunks = [
        {
            "doc_id": 1,
            "title": "Exam Calendar",
            "page_number": 2,
            "source_pages": [2],
            "department": "ALL",
            "academic_year": "2025-26",
            "document_type": "Schedule",
            "text": "Final semester exams begin on December 1st.",
        },
        {
            "doc_id": 2,
            "title": "Registration Guidelines",
            "page_number": 1,
            "source_pages": [1],
            "department": "ALL",
            "academic_year": "2025-26",
            "document_type": "Policy",
            "text": "Exam fee payment deadline is November 15th.",
        },
    ]

    answer = llm.generate_grounded_answer(
        question="When are exams and what is the registration deadline?",
        context_chunks=chunks,
        client=mock_client,
    )

    assert answer == "Exams start Dec 1 and registration closes Nov 15."
    call_args = mock_client.models.generate_content.call_args
    prompt_sent = call_args.kwargs["contents"]
    assert "Exam Calendar" in prompt_sent
    assert "Registration Guidelines" in prompt_sent


def test_empty_context():
    """Test behavior when context chunks list is empty."""
    mock_client = MagicMock()

    answer = llm.generate_grounded_answer(
        question="What is the hostel fee?",
        context_chunks=[],
        client=mock_client,
    )

    assert answer == prompts.NO_CONTEXT_FALLBACK_TEXT
    mock_client.models.generate_content.assert_not_called()


def test_insufficient_context_prompt():
    """Test fallback response requirement in system prompt."""
    assert "I couldn't find this information in the available college documents." in prompts.SYSTEM_GROUNDING_PROMPT
    assert "I couldn't find this information in the available college documents." in prompts.NO_CONTEXT_FALLBACK_TEXT


def test_missing_api_key(monkeypatch):
    """Test missing API key handling."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        llm.generate_grounded_answer(
            question="What is the grading system?",
            context_chunks=[{"text": "Grades are A-F"}],
            client=None,
        )


def test_gemini_failure():
    """Test handling of Gemini API call exception."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API rate limit or connection timeout")

    chunks = [{"text": "Sample policy text"}]

    with pytest.raises(llm.LLMGenerationError, match="Gemini API generation call failed"):
        llm.generate_grounded_answer(
            question="What is the fee?",
            context_chunks=chunks,
            client=mock_client,
        )


def test_malformed_response():
    """Test handling when response from Gemini is empty or missing text attribute."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = None
    mock_client.models.generate_content.return_value = mock_response

    chunks = [{"text": "Sample policy text"}]

    with pytest.raises(llm.LLMGenerationError, match="Received empty or malformed response"):
        llm.generate_grounded_answer(
            question="What is the fee?",
            context_chunks=chunks,
            client=mock_client,
        )


def test_prompt_construction():
    """Test prompt construction separates SYSTEM, CONTEXT, and QUESTION sections."""
    chunks = [
        {
            "doc_id": 10,
            "title": "Scholarship Rules",
            "page_number": 3,
            "source_pages": [3],
            "department": "ECE",
            "academic_year": "2025-26",
            "document_type": "Notice",
            "text": "Merit scholarships require CGPA > 8.5.",
        }
    ]

    formatted_prompt = prompts.format_rag_prompt("How to get scholarship?", chunks)

    assert "=== SYSTEM INSTRUCTIONS ===" in formatted_prompt
    assert "=== RETRIEVED CONTEXT ===" in formatted_prompt
    assert "=== USER QUESTION ===" in formatted_prompt
    assert "Merit scholarships require CGPA > 8.5." in formatted_prompt


def test_metadata_inclusion():
    """Test that document metadata is preserved and formatted in the context block."""
    chunks = [
        {
            "doc_id": 99,
            "title": "Lab Safety Regulations",
            "page_number": 7,
            "source_pages": [7, 8],
            "department": "CHEM",
            "academic_year": "2024-25",
            "document_type": "Manual",
            "text": "Goggles must be worn in the lab.",
        }
    ]

    formatted_prompt = prompts.format_rag_prompt("Are lab goggles mandatory?", chunks)

    assert "- Title: Lab Safety Regulations" in formatted_prompt
    assert "- Document Type: Manual" in formatted_prompt
    assert "- Department: CHEM" in formatted_prompt
    assert "- Academic Year: 2024-25" in formatted_prompt
    assert "- Page Number: 7" in formatted_prompt
    assert "- Source Pages: [7, 8]" in formatted_prompt
    assert "Goggles must be worn in the lab." in formatted_prompt


def test_no_citation_fabrication_rule():
    """Test that system grounding instructions forbid inventing citations."""
    assert "Do NOT claim or cite a source or page number unless that source metadata is explicitly present" in prompts.SYSTEM_GROUNDING_PROMPT
    assert "Do NOT fabricate or invent citations" in prompts.SYSTEM_GROUNDING_PROMPT


def test_deterministic_pipeline_no_context():
    """Test pipeline short-circuiting when retrieval returns zero chunks."""
    pipeline.clear_rag_cache()
    with patch("backend.app.rag.pipeline.knowledge_service.resolve_structured_query", return_value=None), \
         patch("backend.app.rag.retrieval.retrieve_context", return_value=[]), \
         patch("backend.app.rag.llm.generate_grounded_answer") as mock_generate:

        result = pipeline.run_pipeline("What is the hostel curfew?")

        assert result["answer"] == prompts.NO_CONTEXT_FALLBACK_TEXT
        assert result["grounded"] is False
        assert result["sources"] == []
        assert result["retrieval_count"] == 0
        assert result["had_context"] is False
        mock_generate.assert_not_called()


def test_deterministic_pipeline_with_context():
    """Test pipeline execution when retrieval returns valid chunks."""
    pipeline.clear_rag_cache()
    retrieved = [
        {
            "doc_id": 5,
            "title": "Hostel Rules",
            "page_number": 12,
            "source_pages": [12],
            "department": "ALL",
            "academic_year": "2025-26",
            "document_type": "Handbook",
            "text": "Hostel curfew is 10 PM.",
            "snippet": "Hostel curfew is 10 PM.",
        }
    ]

    with patch("backend.app.rag.pipeline.knowledge_service.resolve_structured_query", return_value=None), \
         patch("backend.app.rag.retrieval.retrieve_context", return_value=retrieved), \
         patch("backend.app.rag.llm.generate_grounded_answer", return_value="The hostel curfew is 10 PM.") as mock_generate:

        result = pipeline.run_pipeline("What is the hostel curfew?")

        assert result["answer"] == "The hostel curfew is 10 PM."
        assert result["grounded"] is True
        assert len(result["sources"]) == 1
        assert result["sources"][0]["doc_id"] == 5
        assert result["sources"][0]["title"] == "Hostel Rules"
        assert result["retrieval_count"] == 1
        mock_generate.assert_called_once()
