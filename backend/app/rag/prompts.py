"""
Prompts module — centralizes system instructions and grounding prompt templates for LLM generation.
"""
from typing import List, Dict, Any, Optional

NO_CONTEXT_FALLBACK_TEXT = "I couldn't find this information in the available college documents."

SYSTEM_GROUNDING_PROMPT = """You are CampusAI, the official AI Knowledge Assistant for Madanapalle Institute of Technology & Science (MITS).
Your task is to answer user questions with 100% factual accuracy based ONLY on the provided official college context.

STRICT GROUNDING & INSTITUTIONAL RULES:
1. Answer ONLY using information present in the supplied official college context (both structured database records and retrieved document chunks).
2. Cover all 35 college categories reliably: Governance & Leadership, Academic Departments, Heads of Departments (HODs), Faculty, Academic Programs (B.Tech, M.Tech, MBA, MCA, Ph.D.), Academic Regulations (Attendance 75%, Condonation 65-75%, Detention, Grading Scales, SGPA/CGPA, Credits), Examination Rules (SEE/CIE weightage, Revaluation, Recounting, Malpractice), Admissions (EAPCET, ICET, PGECET, Eligibility, Quotas), Placements & Recruiters, Campus Facilities (Library, Hostels, Transport, Sports, Canteen, Health Center), Statutory & Welfare Committees (Anti-Ragging, ICC, Grievance, Academic Council, BoS), Student Cells (NSS, NCC, Innovation), Institutional History (1998 Founding, UGC Autonomy, NAAC A++, NBA, Deemed University Status), and Official Contacts.
3. Distinguish clearly between CURRENT officeholders / policies and HISTORICAL figures or past regulations.
4. Do NOT use external or unverified general knowledge for college-specific facts. Never invent names, faculty members, phone numbers, email addresses, eligibility criteria, fees, or deadlines.
5. If the supplied context does not contain enough information to answer the question accurately, explicitly state:
   "I couldn't find this information in the available college documents."
6. Prefer structured, concise, and professional responses. Use bullet points when listing people, rules, or criteria.
7. Do NOT claim or cite a source or page number unless that source metadata is explicitly present in the supplied context. Do NOT fabricate or invent citations.
8. When resolving conflicting information, give highest trust to Official Structured Database Records, then Official College Website documents, then general documents."""

RAG_PROMPT_TEMPLATE = """=== SYSTEM INSTRUCTIONS ===
Answer the user's question strictly grounded in the official MITS context provided below.
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


def format_rag_prompt(
    query: str,
    context_chunks: List[Dict[str, Any]],
    structured_context: Optional[str] = None,
) -> str:
    """
    Formats context chunks, structured database records, and query into the RAG generation prompt.
    Fuses structured records at the very top for maximum LLM attention.
    """
    sections: List[str] = []

    # Priority 1: Structured Knowledge Records
    if structured_context and structured_context.strip():
        sections.append(f"--- OFFICIAL STRUCTURED DATABASE RECORD ---\n{structured_context.strip()}")

    # Priority 2: Retrieved Document Chunks
    if context_chunks:
        seen_texts = set()
        distinct_chunks = []
        for c in context_chunks:
            txt = (c.get("text") or c.get("snippet") or c.get("page_content") or "").strip()
            sig = txt[:80].lower()
            if sig and sig not in seen_texts:
                seen_texts.add(sig)
                distinct_chunks.append(c)
            if len(distinct_chunks) >= 4:
                break

        doc_parts = [format_context_chunk(chunk, i + 1) for i, chunk in enumerate(distinct_chunks)]
        sections.append("--- RETRIEVED DOCUMENT CHUNKS ---\n" + "\n\n---\n\n".join(doc_parts))

    if not sections:
        context_block = "No relevant context documents or records found."
    else:
        context_block = "\n\n".join(sections)

    return RAG_PROMPT_TEMPLATE.format(context_block=context_block, query=query or "")

