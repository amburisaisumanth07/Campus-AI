"""
Integration tests for PDF page extraction and processing lifecycle.
"""
import io
from pathlib import Path

from backend.app.services.pdf_service import extract_pages, get_page_count
from backend.app.services.file_service import sanitize_filename, generate_storage_filename

TEST_PDF_PATH = Path(__file__).parent.parent / "fixtures" / "test_document.pdf"


def _get_pdf_bytes() -> bytes:
    if TEST_PDF_PATH.exists():
        return TEST_PDF_PATH.read_bytes()
    return (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length 44>>\nstream\nBT /F1 12 Tf 50 700 Td (Test Page) Tj ET\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n9\n%%EOF"
    )


def test_pdf_page_count():
    """Verify the fixture PDF reports the correct page count."""
    if not TEST_PDF_PATH.exists():
        import pytest
        pytest.skip("Test PDF not found")
    count = get_page_count(TEST_PDF_PATH)
    assert count == 2, f"Expected 2 pages, got {count}"


def test_page_numbers_are_one_based():
    """Page numbers must start at 1 for accurate citation."""
    if not TEST_PDF_PATH.exists():
        import pytest
        pytest.skip("Test PDF not found")
    pages = extract_pages(TEST_PDF_PATH)
    assert len(pages) >= 1
    assert pages[0]["page_number"] == 1


def test_all_pages_have_required_fields():
    """Each extracted page must have page_number, text_content, and char_count."""
    if not TEST_PDF_PATH.exists():
        import pytest
        pytest.skip("Test PDF not found")
    pages = extract_pages(TEST_PDF_PATH)
    for page in pages:
        assert "page_number" in page
        assert "text_content" in page
        assert "char_count" in page
        assert isinstance(page["page_number"], int)
        assert isinstance(page["char_count"], int)
        assert page["char_count"] == len(page["text_content"] or "")


def test_pages_have_sequential_numbers():
    """Pages must be returned in sequential order."""
    if not TEST_PDF_PATH.exists():
        import pytest
        pytest.skip("Test PDF not found")
    pages = extract_pages(TEST_PDF_PATH)
    numbers = [p["page_number"] for p in pages]
    assert numbers == list(range(1, len(pages) + 1))


def test_invalid_pdf_raises_value_error():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"This is not a PDF at all")
        tmp = Path(f.name)
    try:
        import pytest
        with pytest.raises((ValueError, RuntimeError)):
            extract_pages(tmp)
    finally:
        tmp.unlink(missing_ok=True)


# ── File service unit tests ───────────────────────────────────────────────────

def test_sanitize_filename_strips_path_traversal():
    result = sanitize_filename("../../../etc/passwd.pdf")
    assert ".." not in result
    assert "/" not in result
    assert "\\" not in result


def test_sanitize_filename_adds_pdf_extension():
    result = sanitize_filename("document_without_extension")
    assert result.endswith(".pdf")


def test_sanitize_filename_replaces_special_chars():
    result = sanitize_filename("my document (v1) <test>.pdf")
    for bad in ["(", ")", "<", ">", " "]:
        assert bad not in result


def test_sanitize_filename_empty_input():
    result = sanitize_filename("")
    assert result.endswith(".pdf")
    assert len(result) > 0


def test_storage_filename_is_uuid_based():
    name = generate_storage_filename(42, "1.0")
    assert name.startswith("doc_42_")
    assert name.endswith(".pdf")
    # Contains UUID hex (32 chars)
    import re
    assert re.search(r"[0-9a-f]{32}", name)


def test_storage_filename_no_path_separators():
    name = generate_storage_filename(1, "../../evil/path")
    assert "/" not in name
    assert "\\" not in name
