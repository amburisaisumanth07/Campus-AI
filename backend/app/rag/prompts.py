"""
Prompts module — centralizes system instructions and grounding prompt templates for LLM generation.
"""
from typing import List, Dict, Any

NO_CONTEXT_FALLBACK_TEXT = "I couldn't find this information in the available college documents."

SYSTEM_GROUNDING_PROMPT = """You are CampusAI, an official AI student support assistant.
Your task is to answer student questions based ONLY on the provided college document context.

STRICT GROUNDING INSTRUCTIONS:
1. Answer ONLY using information present in the supplied college-document context.
2. Do NOT use external or general knowledge for factual college-policy answers.
3. Do NOT invent, extrapolate, or fabricate rules, dates, requirements, eligibility criteria, deadlines, fees, contact details, or procedures.
4. If the context does not contain enough information to answer the question accurately and completely, explicitly state:
   "I couldn't find this information in the available college documents."
5. Prefer concise, direct, and factual answers.
6. Do NOT claim or cite a source or page number unless that source metadata is explicitly present in the supplied context.
7. Do NOT fabricate or invent citations under any circumstances.
8. When resolving conflicting information, give highest trust to Official College Website and Admin documents over student-uploaded documents."""

RAG_PROMPT_TEMPLATE = """=== SYSTEM INSTRUCTIONS ===
Answer the student question strictly grounded in the retrieved context documents provided below.
If the supplied context is empty, missing, or insufficient to answer the question, state:
"I couldn't find this information in the available college documents."

=== RETRIEVED CONTEXT ===
{context_block}

=== USER QUESTION ===
{query}

Answer:"""


def format_context_chunk(chunk: Dict[str, Any], index: int) -> str:
    """Formats a single retrieved chunk preserving all available metadata provenance with crisp token footprint."""
    metadata = chunk.get("metadata", {}) if isinstance(chunk.get("metadata"), dict) else {}
    title = chunk.get("title") or metadata.get("title") or "Untitled Document"
    doc_type = chunk.get("document_type") or metadata.get("document_type") or "N/A"
    dept = chunk.get("department") or metadata.get("department") or "N/A"
    year = chunk.get("academic_year") or metadata.get("academic_year") or "N/A"
    page = chunk.get("page_number") or metadata.get("page_number") or "N/A"
    source_pages = chunk.get("source_pages") or metadata.get("source_pages") or ([page] if page != "N/A" else [])
    source_url = chunk.get("source_url") or metadata.get("source_url") or "N/A"
    text = (chunk.get("text") or chunk.get("snippet") or chunk.get("page_content") or "").strip()
    
    # Trim oversized chunks to keep prompt lightweight and fast
    if len(text) > 2000:
        text = text[:2000] + "..."

    return (
        f"[Source Document {index}]\n"
        f"- Title: {title}\n"
        f"- Document Type: {doc_type}\n"
        f"- Department: {dept}\n"
        f"- Academic Year: {year}\n"
        f"- Page Number: {page}\n"
        f"- Source Pages: {source_pages}\n"
        f"- Source URL: {source_url}\n"
        f"- Text Content:\n{text}"
    )


def format_rag_prompt(query: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Formats context chunks and student query into the RAG generation prompt with deduplication."""
    if not context_chunks:
        context_block = "No relevant context documents found."
    else:
        # Deduplicate chunks by content text
        seen_texts = set()
        distinct_chunks = []
        for c in context_chunks:
            txt = (c.get("text") or c.get("snippet") or c.get("page_content") or "").strip()
            # Signature on first 80 chars
            sig = txt[:80].lower()
            if sig and sig not in seen_texts:
                seen_texts.add(sig)
                distinct_chunks.append(c)
            if len(distinct_chunks) >= 4:
                break

        parts = [format_context_chunk(chunk, i + 1) for i, chunk in enumerate(distinct_chunks)]
        context_block = "\n\n---\n\n".join(parts)

    return RAG_PROMPT_TEMPLATE.format(context_block=context_block, query=query or "")
