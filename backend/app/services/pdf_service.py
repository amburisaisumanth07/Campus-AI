"""
PDF text extraction service using pdfplumber.

Design principles:
- Extract text page-by-page (page numbers are preserved as-is for future citation accuracy)
- Never combine pages into a single blob
- Return a structured list of page dicts suitable for database insertion
- Handle malformed/encrypted PDFs gracefully
"""
from pathlib import Path
from typing import List, Dict, Any

import pdfplumber

from backend.app.core.logging import logger


def extract_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text from every page of the PDF at pdf_path.

    Returns a list of dicts, one per page, with keys:
        page_number  int   1-based
        text_content str   extracted text (may be empty for image-only pages)
        char_count   int   len(text_content)

    Raises ValueError if the file cannot be opened as a PDF.
    Raises RuntimeError on unrecoverable extraction errors.
    """
    if not pdf_path.exists():
        raise ValueError(f"PDF file not found: {pdf_path}")

    pages: List[Dict[str, Any]] = []

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            total = len(pdf.pages)
            logger.info(f"Extracting {total} pages from {pdf_path.name}")

            for page in pdf.pages:
                page_number = page.page_number  # 1-based in pdfplumber
                try:
                    text = page.extract_text() or ""
                except Exception as exc:
                    logger.warning(
                        f"Page {page_number} extraction error ({pdf_path.name}): {exc}"
                    )
                    text = ""

                pages.append(
                    {
                        "page_number": page_number,
                        "text_content": text,
                        "char_count": len(text),
                    }
                )

    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as exc:
        raise ValueError(f"Invalid or corrupted PDF: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc

    return pages


def get_page_count(pdf_path: Path) -> int:
    """Return the number of pages in a PDF without extracting text."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return len(pdf.pages)
    except Exception as exc:
        raise ValueError(f"Cannot read page count: {exc}") from exc
