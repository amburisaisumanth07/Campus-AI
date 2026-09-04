"""
Document Chunking Module for CampusAI RAG Pipeline.

Splits page-level document text into deterministic, retrieval-friendly chunks
while preserving original page numbers and metadata.
"""

from dataclasses import dataclass, field
import re
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: int
    document_version_id: int
    page_number: int
    text: str
    chunk_index: int
    character_count: int
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk object to a standard dictionary structure."""
        return {
            "chunk_id": self.chunk_id,
            "id": self.chunk_id,
            "document_id": self.document_id,
            "document_version_id": self.document_version_id,
            "page_number": self.page_number,
            "text": self.text,
            "chunk_index": self.chunk_index,
            "character_count": self.character_count,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


def normalize_text(text: str) -> str:
    """
    Normalize text artifacts while preserving meaningful paragraph boundaries.
    Strips null bytes, non-printable control characters, trailing line spaces,
    and collapses 3+ consecutive newlines to 2 newlines.
    """
    if not text:
        return ""
    # Strip null bytes and non-printable control characters (except newline, tab)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # Strip leading/trailing spaces from each line
    lines = [line.strip() for line in text.splitlines()]
    # Collapse multiple consecutive empty lines to a single empty line
    result_lines: List[str] = []
    for line in lines:
        if line == "" and result_lines and result_lines[-1] == "":
            continue
        result_lines.append(line)
    return "\n".join(result_lines).strip()


def chunk_text(
    text: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None
) -> List[str]:
    """
    Sentence and word boundary-aware sliding window chunker for plain text strings.
    Guarantees deterministic, non-empty chunks with the requested overlap.
    """
    normalized = normalize_text(text)
    if not normalized:
        return []

    c_size = chunk_size if chunk_size is not None else settings.RAG_CHUNK_SIZE
    c_overlap = overlap if overlap is not None else settings.RAG_CHUNK_OVERLAP
    c_overlap = min(c_overlap, max(0, c_size - 1))

    if len(normalized) <= c_size:
        return [normalized]

    chunks: List[str] = []
    start = 0
    total_len = len(normalized)

    while start < total_len:
        end = start + c_size

        if end < total_len:
            search_window_start = max(start + 1, end - int(c_size * 0.25))
            boundary_idx = -1

            sentence_match = list(re.finditer(r"[.!?](\s|\n)", normalized[search_window_start:end]))
            if sentence_match:
                last_m = sentence_match[-1]
                boundary_idx = search_window_start + last_m.start() + 1
            else:
                space_match = list(re.finditer(r"\s", normalized[search_window_start:end]))
                if space_match:
                    last_m = space_match[-1]
                    boundary_idx = search_window_start + last_m.start() + 1

            if boundary_idx > start:
                end = boundary_idx

        chunk_str = normalized[start:end].strip()
        if chunk_str:
            chunks.append(chunk_str)

        if end >= total_len:
            break

        next_start = end - c_overlap
        start = max(start + 1, next_start)

    return chunks


def chunk_document_pages(
    pages: List[Dict[str, Any]],
    document_id: int,
    document_version_id: int,
    title: Optional[str] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    combine_pages: bool = False,
    source_type: Optional[str] = None,
    source_url: Optional[str] = None,
) -> List[DocumentChunk]:
    """
    Process page-level document dictionaries into structured DocumentChunk objects.
    Preserves exact source page provenance.

    Input pages format:
        [{"page_number": int, "text_content": str}, ...]
    """
    c_size = chunk_size if chunk_size is not None else settings.RAG_CHUNK_SIZE
    c_overlap = chunk_overlap if chunk_overlap is not None else settings.RAG_CHUNK_OVERLAP
    c_overlap = min(c_overlap, max(0, c_size - 1))

    sorted_pages = sorted(pages, key=lambda p: p.get("page_number", 1))

    if not combine_pages:
        # Per-page chunking (default)
        chunks: List[DocumentChunk] = []
        global_chunk_index = 0

        for page in sorted_pages:
            page_num = page.get("page_number", 1)
            raw_content = page.get("text_content") or ""
            norm_content = normalize_text(raw_content)

            if not norm_content:
                continue

            text_chunks = chunk_text(norm_content, chunk_size=c_size, overlap=c_overlap)
            for text_str in text_chunks:
                chunk_id = f"doc_{document_id}_v_{document_version_id}_c_{global_chunk_index}"
                token_count = len(text_str.split())

                meta = {
                    "document_id": document_id,
                    "doc_id": document_id,
                    "document_version_id": document_version_id,
                    "page_number": page_num,
                    "source_pages": [page_num],
                    "chunk_index": global_chunk_index,
                    "character_count": len(text_str),
                    "token_count": token_count,
                    "title": title or "",
                    "department": department or "",
                    "academic_year": academic_year or "",
                    "source_type": source_type or "",
                    "source_url": source_url or "",
                }

                doc_chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_version_id=document_version_id,
                    page_number=page_num,
                    text=text_str,
                    chunk_index=global_chunk_index,
                    character_count=len(text_str),
                    token_count=token_count,
                    metadata=meta,
                )
                chunks.append(doc_chunk)
                global_chunk_index += 1

        return chunks

    # Continuous cross-page chunking (combine_pages=True)
    full_text_chars: List[str] = []
    char_page_map: List[int] = []

    for page in sorted_pages:
        page_num = page.get("page_number", 1)
        raw_content = page.get("text_content") or ""
        norm_content = normalize_text(raw_content)

        if not norm_content:
            continue

        if full_text_chars:
            full_text_chars.extend(["\n", "\n"])
            char_page_map.extend([page_num, page_num])

        for char in norm_content:
            full_text_chars.append(char)
            char_page_map.append(page_num)

    full_text = "".join(full_text_chars)
    total_len = len(full_text)

    if total_len == 0:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < total_len:
        end = start + c_size

        if end < total_len:
            search_window_start = max(start + 1, end - int(c_size * 0.25))
            boundary_idx = -1

            sentence_match = list(re.finditer(r"[.!?](\s|\n)", full_text[search_window_start:end]))
            if sentence_match:
                last_m = sentence_match[-1]
                boundary_idx = search_window_start + last_m.start() + 1
            else:
                space_match = list(re.finditer(r"\s", full_text[search_window_start:end]))
                if space_match:
                    last_m = space_match[-1]
                    boundary_idx = search_window_start + last_m.start() + 1

            if boundary_idx > start:
                end = boundary_idx

        raw_chunk_slice = full_text[start:end]
        raw_pages_slice = char_page_map[start:end]

        l_strip = len(raw_chunk_slice) - len(raw_chunk_slice.lstrip())
        r_strip = len(raw_chunk_slice) - len(raw_chunk_slice.rstrip())

        trimmed_text = raw_chunk_slice.strip()

        if trimmed_text:
            trimmed_pages_slice = raw_pages_slice[l_strip: len(raw_pages_slice) - r_strip]
            if not trimmed_pages_slice:
                trimmed_pages_slice = raw_pages_slice

            source_pages = sorted(list(dict.fromkeys(trimmed_pages_slice)))
            primary_page = source_pages[0] if source_pages else 1

            chunk_id = f"doc_{document_id}_v_{document_version_id}_c_{chunk_index}"
            token_count = len(trimmed_text.split())

            meta = {
                "document_id": document_id,
                "doc_id": document_id,
                "document_version_id": document_version_id,
                "page_number": primary_page,
                "source_pages": source_pages,
                "chunk_index": chunk_index,
                "character_count": len(trimmed_text),
                "token_count": token_count,
                "title": title or "",
                "department": department or "",
                "academic_year": academic_year or "",
                "source_type": source_type or "",
                "source_url": source_url or "",
            }

            doc_chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                document_version_id=document_version_id,
                page_number=primary_page,
                text=trimmed_text,
                chunk_index=chunk_index,
                character_count=len(trimmed_text),
                token_count=token_count,
                metadata=meta,
            )
            chunks.append(doc_chunk)
            chunk_index += 1

        if end >= total_len:
            break

        next_start = end - c_overlap
        start = max(start + 1, next_start)

    return chunks


def create_chunks_from_pages(
    doc_id: int,
    title: str,
    department: Optional[str],
    academic_year: Optional[str],
    pages: List[Dict[str, Any]],
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
    source_type: Optional[str] = None,
    source_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Backwards-compatible helper returning dictionary representations of chunks.
    """
    chunks = chunk_document_pages(
        pages=pages,
        document_id=doc_id,
        document_version_id=1,
        title=title,
        department=department,
        academic_year=academic_year,
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        source_type=source_type,
        source_url=source_url,
    )
    return [c.to_dict() for c in chunks]
