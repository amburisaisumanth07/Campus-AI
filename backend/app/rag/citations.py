"""
Citation & Source Provenance Module for CampusAI RAG Pipeline.

Constructs reliable, deterministic source citations from retrieved document metadata
independently of LLM generation.
Fulfills Milestone 9 requirements.
"""

from typing import List, Dict, Any, Optional, Tuple


def parse_int_field(val: Any) -> Optional[int]:
    """
    Safely parse integer metadata field.
    Returns None if value is None, empty string, or cannot be converted to int.
    Never invents a default integer if missing.
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        try:
            return int(val)
        except (ValueError, OverflowError):
            return None
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        try:
            return int(val_str)
        except ValueError:
            return None
    return None


def parse_str_field(val: Any) -> Optional[str]:
    """
    Safely parse string metadata field.
    Returns None if value is None, empty string, or non-string placeholder.
    Never invents fallback titles or text.
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    return val_str


def parse_source_pages(source_pages_raw: Any, page_number: Optional[int] = None) -> List[int]:
    """
    Parse source_pages metadata from string ("14, 15"), list ([14, 15]), or integer.
    Returns sorted, deduplicated list of page integers.
    If no source_pages metadata exists, returns [page_number] if page_number is valid, else [].
    """
    parsed: List[int] = []

    if isinstance(source_pages_raw, list):
        for item in source_pages_raw:
            p_int = parse_int_field(item)
            if p_int is not None:
                parsed.append(p_int)
    elif isinstance(source_pages_raw, str) and source_pages_raw.strip():
        for part in source_pages_raw.split(","):
            p_int = parse_int_field(part)
            if p_int is not None:
                parsed.append(p_int)
    elif isinstance(source_pages_raw, (int, float)):
        p_int = parse_int_field(source_pages_raw)
        if p_int is not None:
            parsed.append(p_int)

    if parsed:
        return sorted(list(set(parsed)))

    if page_number is not None:
        return [page_number]

    return []


def build_citation(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a structured, normalized citation dictionary from a retrieved chunk.
    Does not invent missing metadata fields.
    """
    meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}

    # Extract metadata checking chunk root first, then nested metadata dict
    doc_id = parse_int_field(chunk.get("document_id"))
    if doc_id is None:
        doc_id = parse_int_field(chunk.get("doc_id"))
    if doc_id is None:
        doc_id = parse_int_field(meta.get("document_id"))
    if doc_id is None:
        doc_id = parse_int_field(meta.get("doc_id"))

    doc_ver_id = parse_int_field(chunk.get("document_version_id"))
    if doc_ver_id is None:
        doc_ver_id = parse_int_field(meta.get("document_version_id"))

    title = parse_str_field(chunk.get("title"))
    if title is None:
        title = parse_str_field(meta.get("title"))

    doc_type = parse_str_field(chunk.get("document_type"))
    if doc_type is None:
        doc_type = parse_str_field(meta.get("document_type"))

    department = parse_str_field(chunk.get("department"))
    if department is None:
        department = parse_str_field(meta.get("department"))

    academic_year = parse_str_field(chunk.get("academic_year"))
    if academic_year is None:
        academic_year = parse_str_field(meta.get("academic_year"))

    page_num = parse_int_field(chunk.get("page_number"))
    if page_num is None:
        page_num = parse_int_field(meta.get("page_number"))

    source_pages_raw = chunk.get("source_pages") or meta.get("source_pages")
    source_pages = parse_source_pages(source_pages_raw, page_number=page_num)

    # Snippet text extraction
    snippet = parse_str_field(chunk.get("snippet"))
    if snippet is None:
        snippet = parse_str_field(chunk.get("text"))
    if snippet is None:
        snippet = parse_str_field(meta.get("snippet"))
    if snippet is None:
        snippet = parse_str_field(meta.get("text"))

    source_type = parse_str_field(chunk.get("source_type"))
    if source_type is None:
        source_type = parse_str_field(meta.get("source_type"))

    source_url = parse_str_field(chunk.get("source_url"))
    if source_url is None:
        source_url = parse_str_field(meta.get("source_url"))

    return {
        "doc_id": doc_id,
        "document_id": doc_id,
        "document_version_id": doc_ver_id,
        "title": title,
        "document_type": doc_type,
        "department": department,
        "academic_year": academic_year,
        "page_number": page_num,
        "source_pages": source_pages,
        "snippet": snippet,
        "source_type": source_type,
        "source_url": source_url,
    }


def get_deduplication_key(citation: Dict[str, Any]) -> Tuple[Any, Any, Tuple[Any, ...]]:
    """
    Compute deduplication key for a citation based on:
    document_id + document_version_id + page(s)
    """
    doc_id = citation.get("document_id")
    doc_ver_id = citation.get("document_version_id")

    source_pages = citation.get("source_pages")
    if source_pages and isinstance(source_pages, list):
        pages_key = tuple(sorted(source_pages))
    elif citation.get("page_number") is not None:
        pages_key = (citation.get("page_number"),)
    else:
        pages_key = (None,)

    return (doc_id, doc_ver_id, pages_key)


def deduplicate_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate citations sharing (document_id + document_version_id + page(s))
    while preserving original relevance ordering.
    """
    seen = set()
    deduped: List[Dict[str, Any]] = []

    for cit in citations:
        key = get_deduplication_key(cit)
        if key not in seen:
            seen.add(key)
            deduped.append(cit)

    return deduped


def build_citations_from_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build deduplicated, relevance-ordered citations from a list of retrieved chunks.
    Preserves original rank ordering of input chunks.
    """
    if not chunks:
        return []

    raw_citations = [build_citation(chunk) for chunk in chunks]
    return deduplicate_citations(raw_citations)
