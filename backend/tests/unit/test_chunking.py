import os
import pytest
from pathlib import Path
from backend.app.rag.chunking import (
    DocumentChunk,
    chunk_text,
    chunk_document_pages,
    create_chunks_from_pages,
    normalize_text,
)
from backend.app.core.config import settings


def test_single_short_page():
    """Test chunking a single short page that fits in one chunk."""
    pages = [{"page_number": 1, "text_content": "Attendance is mandatory for all students."}]
    chunks = chunk_document_pages(pages, document_id=1, document_version_id=1, chunk_size=500, chunk_overlap=100)

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "doc_1_v_1_c_0"
    assert chunks[0].page_number == 1
    assert chunks[0].metadata["source_pages"] == [1]
    assert chunks[0].text == "Attendance is mandatory for all students."
    assert chunks[0].character_count == len(chunks[0].text)
    assert chunks[0].token_count == 6


def test_long_single_page():
    """Test chunking a long single page that requires multiple chunks."""
    long_text = "Sentence number " + ". Sentence number ".join(str(i) for i in range(1, 100)) + "."
    pages = [{"page_number": 1, "text_content": long_text}]
    chunks = chunk_document_pages(pages, document_id=10, document_version_id=2, chunk_size=300, chunk_overlap=50)

    assert len(chunks) > 1
    assert all(c.page_number == 1 for c in chunks)
    assert all(c.metadata["source_pages"] == [1] for c in chunks)
    assert all(c.character_count <= 300 for c in chunks)


def test_multi_page_document():
    """Test chunking across multiple pages in a document."""
    pages = [
        {"page_number": 1, "text_content": "Page one text content regarding regulation section 1."},
        {"page_number": 2, "text_content": "Page two text content regarding regulation section 2."},
        {"page_number": 3, "text_content": "Page three text content regarding regulation section 3."},
    ]
    chunks = chunk_document_pages(pages, document_id=5, document_version_id=1, chunk_size=500, chunk_overlap=50)

    assert len(chunks) >= 3
    page_numbers_in_chunks = [c.page_number for c in chunks]
    assert 1 in page_numbers_in_chunks
    assert 2 in page_numbers_in_chunks
    assert 3 in page_numbers_in_chunks


def test_page_boundaries_and_multi_page_provenance():
    """Test that a chunk spanning page boundaries records all source pages in metadata."""
    p1_text = "A" * 150 + " End of page 1."
    p2_text = "Start of page 2. " + "B" * 150
    pages = [
        {"page_number": 1, "text_content": p1_text},
        {"page_number": 2, "text_content": p2_text},
    ]

    chunks = chunk_document_pages(pages, document_id=7, document_version_id=1, chunk_size=400, chunk_overlap=50, combine_pages=True)

    assert len(chunks) >= 1
    spanning_chunk = [c for c in chunks if len(c.metadata["source_pages"]) > 1]
    assert len(spanning_chunk) > 0
    assert spanning_chunk[0].metadata["source_pages"] == [1, 2]
    assert spanning_chunk[0].page_number == 1


def test_chunk_overlap():
    """Test that adjacent chunks overlap correctly."""
    text = "First paragraph content. Second paragraph content. Third paragraph content. Fourth paragraph content."
    pages = [{"page_number": 1, "text_content": text}]
    chunks = chunk_document_pages(pages, document_id=1, document_version_id=1, chunk_size=60, chunk_overlap=25)

    assert len(chunks) >= 2
    chunk_0_end = chunks[0].text[-15:]
    assert any(word in chunks[1].text for word in chunk_0_end.split())


def test_empty_page():
    """Test that empty pages produce no empty chunks."""
    pages = [
        {"page_number": 1, "text_content": ""},
        {"page_number": 2, "text_content": "   "},
        {"page_number": 3, "text_content": "Valid content on page 3."},
    ]
    chunks = chunk_document_pages(pages, document_id=2, document_version_id=1)

    assert len(chunks) == 1
    assert chunks[0].page_number == 3
    assert chunks[0].text == "Valid content on page 3."


def test_whitespace_heavy_page():
    """Test normalization of whitespace-heavy pages."""
    text = "   \n\n\n  Header Title  \n\n\n  Body text here.   \n\n\n  "
    pages = [{"page_number": 1, "text_content": text}]
    chunks = chunk_document_pages(pages, document_id=3, document_version_id=1)

    assert len(chunks) == 1
    assert "Header Title\n\nBody text here." in chunks[0].text
    assert "\n\n\n" not in chunks[0].text


def test_exact_ordering():
    """Test that chunk indices are strictly sequential starting from 0."""
    pages = [
        {"page_number": 1, "text_content": "Sentence A. " * 30},
        {"page_number": 2, "text_content": "Sentence B. " * 30},
    ]
    chunks = chunk_document_pages(pages, document_id=9, document_version_id=1, chunk_size=200, chunk_overlap=40)

    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_id == f"doc_9_v_1_c_{idx}"


def test_metadata_preservation():
    """Test that document metadata is attached to every chunk object."""
    pages = [{"page_number": 1, "text_content": "Sample rule text for compliance."}]
    chunks = chunk_document_pages(
        pages,
        document_id=99,
        document_version_id=3,
        title="Attendance Policy",
        department="Computer Science",
        academic_year="2025-2026",
    )

    assert len(chunks) == 1
    meta = chunks[0].metadata
    assert meta["document_id"] == 99
    assert meta["document_version_id"] == 3
    assert meta["page_number"] == 1
    assert meta["title"] == "Attendance Policy"
    assert meta["department"] == "Computer Science"
    assert meta["academic_year"] == "2025-2026"
    assert meta["token_count"] > 0
    assert meta["character_count"] == len("Sample rule text for compliance.")


def test_deterministic_output():
    """Test that identical input and settings produce identical chunks."""
    pages = [
        {"page_number": 1, "text_content": "Deterministic rule statement 1. Deterministic rule statement 2."},
        {"page_number": 2, "text_content": "Deterministic rule statement 3. Deterministic rule statement 4."},
    ]

    run1 = chunk_document_pages(pages, document_id=12, document_version_id=1, chunk_size=80, chunk_overlap=20)
    run2 = chunk_document_pages(pages, document_id=12, document_version_id=1, chunk_size=80, chunk_overlap=20)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.chunk_id == c2.chunk_id
        assert c1.text == c2.text
        assert c1.metadata == c2.metadata


def test_configurable_chunk_size_and_overlap():
    """Test that custom chunk size and overlap parameters are respected."""
    text = "Word " * 200
    pages = [{"page_number": 1, "text_content": text}]

    small_chunks = chunk_document_pages(pages, document_id=1, document_version_id=1, chunk_size=200, chunk_overlap=50)
    large_chunks = chunk_document_pages(pages, document_id=1, document_version_id=1, chunk_size=600, chunk_overlap=100)

    assert len(small_chunks) > len(large_chunks)
    assert all(c.character_count <= 200 for c in small_chunks)
    assert all(c.character_count <= 600 for c in large_chunks)


def test_no_empty_chunks():
    """Verify no empty or whitespace-only chunks are generated."""
    text = "   Valid text sentence.   \n\n\n   Another valid sentence.   "
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 0
    assert all(len(c.strip()) > 0 for c in chunks)


def test_pdf_fixture_chunking_if_available():
    """Integration test: Verify PDF extraction and chunking if fixture exists."""
    fixture_path = Path(__file__).resolve().parent.parent.parent / "data" / "documents" / "Test_Attendance_Rules.pdf"
    if fixture_path.exists():
        import fitz  # PyMuPDF
        doc = fitz.open(str(fixture_path))
        pages = []
        for i, page in enumerate(doc, start=1):
            pages.append({"page_number": i, "text_content": page.get_text() or ""})

        chunks = chunk_document_pages(
            pages,
            document_id=500,
            document_version_id=1,
            title="Test Attendance Rules",
            department="Academic",
        )
        assert len(chunks) > 0
        assert all(c.character_count > 0 for c in chunks)
        assert all(c.metadata["document_id"] == 500 for c in chunks)
