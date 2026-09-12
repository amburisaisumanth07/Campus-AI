import pytest
from unittest.mock import MagicMock, patch
from backend.app.rag.embeddings import (
    embed_document,
    embed_query,
    embed_documents,
    EmbeddingError,
)
from backend.app.core.config import settings


@pytest.fixture
def mock_genai_client():
    from backend.app.rag import embeddings
    embeddings._cached_embed_client = None
    embeddings._cached_embed_key = None
    embeddings._cached_embed_timeout = None
    with patch("backend.app.rag.embeddings.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client
    embeddings._cached_embed_client = None


def test_successful_document_embedding(mock_genai_client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")

    mock_response = MagicMock()
    mock_response.embedding.values = [0.1] * 768
    mock_genai_client.models.embed_content.return_value = mock_response

    vector = embed_document("Sample document text for embedding.", title="Attendance Policy")

    assert len(vector) == 768
    assert vector[0] == 0.1
    mock_genai_client.models.embed_content.assert_called_once()

    call_args = mock_genai_client.models.embed_content.call_args
    assert call_args.kwargs["model"] == settings.GEMINI_EMBEDDING_MODEL
    assert call_args.kwargs["contents"] == "Sample document text for embedding."
    assert call_args.kwargs["config"].output_dimensionality == 768
    assert not hasattr(call_args.kwargs["config"], "task_type") or getattr(call_args.kwargs["config"], "task_type", None) is None


def test_successful_query_embedding(mock_genai_client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")

    mock_response = MagicMock()
    mock_response.embedding.values = [0.2] * 768
    mock_genai_client.models.embed_content.return_value = mock_response

    vector = embed_query("What is the attendance policy?")

    assert len(vector) == 768
    assert vector[0] == 0.2

    call_args = mock_genai_client.models.embed_content.call_args
    assert call_args.kwargs["model"] == settings.GEMINI_EMBEDDING_MODEL
    assert call_args.kwargs["contents"] == "What is the attendance policy?"
    assert call_args.kwargs["config"].output_dimensionality == 768


def test_batch_document_embeddings(mock_genai_client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")

    mock_response = MagicMock()
    mock_response.embedding.values = [0.5] * 768
    mock_genai_client.models.embed_content.return_value = mock_response

    texts = ["First chunk text.", "Second chunk text.", "Third chunk text."]
    titles = ["Policy A", "Policy B", None]
    vectors = embed_documents(texts, titles=titles)

    assert len(vectors) == 3
    assert all(len(v) == 768 for v in vectors)
    assert mock_genai_client.models.embed_content.call_count == 3


def test_empty_input_validation(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")

    with pytest.raises(ValueError, match="cannot be empty"):
        embed_document("")

    with pytest.raises(ValueError, match="cannot be empty"):
        embed_document("   ")

    with pytest.raises(ValueError, match="cannot be empty"):
        embed_query("")

    with pytest.raises(ValueError, match="cannot be empty"):
        embed_documents([])

    with pytest.raises(ValueError, match="empty"):
        embed_documents(["   ", ""])


def test_missing_api_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        embed_document("Test content")

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        embed_query("Test query")


def test_provider_failure_handling(mock_genai_client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")
    mock_genai_client.models.embed_content.side_effect = Exception("API connection timeout")

    with pytest.raises(EmbeddingError, match="Failed to generate document embedding"):
        embed_document("Sample text")

    with pytest.raises(EmbeddingError, match="Failed to generate query embedding"):
        embed_query("Sample query")


def test_malformed_response_validation(mock_genai_client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")

    # Test case 1: None response
    mock_genai_client.models.embed_content.return_value = None
    with pytest.raises(EmbeddingError, match="malformed or empty response"):
        embed_document("Sample text")

    # Test case 2: Missing values attribute
    mock_response = MagicMock()
    mock_response.embedding.values = None
    mock_genai_client.models.embed_content.return_value = mock_response
    with pytest.raises(EmbeddingError, match="did not contain vector values"):
        embed_query("Sample query")


def test_embedding_dimensionality(mock_genai_client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")
    dim = 768
    mock_response = MagicMock()
    mock_response.embedding.values = [0.0] * dim
    mock_genai_client.models.embed_content.return_value = mock_response

    doc_vec = embed_document("Doc text")
    query_vec = embed_query("Query text")

    assert len(doc_vec) == dim
    assert len(query_vec) == dim


def test_attendance_regulations_ranking_regression(mock_genai_client, monkeypatch):
    """
    Regression test ensuring that document and query embeddings use identical
    unprefixed content formatting so that attendance regulations rank above unrelated chunks.
    """
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")
    mock_response = MagicMock()
    mock_response.embedding.values = [0.1] * 768
    mock_genai_client.models.embed_content.return_value = mock_response

    test_queries = [
        "What is the minimum attendance requirement for semester exams?",
        "What attendance is required for semester exams?",
        "How much attendance is needed to write end semester exams?",
        "What happens if attendance is below 75%?",
    ]

    attendance_doc_chunk = (
        "A student shall be eligible to appear for semester end examinations if he/she acquires "
        "a minimum of 75% of attendance in aggregate of all subjects. Condonation of shortage of attendance "
        "in aggregate up to 10% (65% and above and below 75%) may be granted on medical grounds."
    )

    doc_vec = embed_document(attendance_doc_chunk, title="MITS Academic Regulations")
    assert mock_genai_client.models.embed_content.call_args.kwargs["contents"] == attendance_doc_chunk

    for q in test_queries:
        q_vec = embed_query(q)
        assert mock_genai_client.models.embed_content.call_args.kwargs["contents"] == q

