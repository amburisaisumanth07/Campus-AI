# Grounded LLM Generation Documentation

## Overview

The Grounded LLM Generation module (Milestone 8) generates strictly factual, document-grounded answers for student queries using retrieved context chunks from official campus documents. It utilizes the official Google GenAI SDK (`google-genai`) with Gemini models (`gemini-2.5-flash`).

## Architecture & Control Flow

```
Student Question + Metadata Filters (department, academic_year)
    ↓
retrieval.py (Retrieves & filters vector embeddings from ChromaDB)
    ↓
retrieved context chunks (with metadata provenance)
    ↓
pipeline.py (Short-circuit check: empty context -> return fallback without LLM call)
    ↓ (if context chunks exist)
prompts.py (Formats structured grounding prompt: SYSTEM, CONTEXT, QUESTION)
    ↓
llm.py (Calls Gemini API via google-genai SDK at temperature=0.0)
    ↓
Structured Pipeline Result (answer, grounded status, source metadata, retrieval count)
```

## Prompt Structure & Section Separation

The generation prompt explicitly separates three key sections:

1. **`=== SYSTEM INSTRUCTIONS ===`**:
   - Answer strictly using ONLY information present in the supplied context.
   - Do NOT use external or general knowledge for factual college-policy answers.
   - Do NOT invent rules, dates, requirements, eligibility criteria, deadlines, fees, or procedures.
   - If context is insufficient, explicitly output:
     `"I couldn't find this information in the available college documents."`
   - Prefer concise, direct answers.
   - Do NOT claim or cite a source/page unless that source metadata is explicitly present.
   - Do NOT fabricate or invent citations.

2. **`=== RETRIEVED CONTEXT ===`**:
   - Each retrieved chunk is rendered with its full metadata provenance:
     - `Title`
     - `Document Type`
     - `Department`
     - `Academic Year`
     - `Page Number`
     - `Source Pages`
     - `Text Content`

3. **`=== USER QUESTION ===`**:
   - The verbatim student query string.

## Hallucination Control Strategy

- **Zero-Temperature Execution (`GEMINI_TEMPERATURE = 0.0`)**: Ensures deterministic, low-variance generation focused strictly on provided context tokens.
- **Strict Grounding Rules**: The system prompt instructs Gemini to reject speculative questions or external facts not backed by the provided context chunks.
- **Explicit Fallback Response**: Standardized message across the system:
  `"I couldn't find this information in the available college documents."`

## No-Context Short-Circuiting Behavior

To prevent unnecessary API calls and potential hallucinations on out-of-domain questions:
- If `retrieval.py` returns no sufficiently relevant context chunks (`retrieval_count == 0`), `pipeline.py` **short-circuits immediately without calling Gemini**.
- The pipeline returns `grounded = False`, `sources = []`, `retrieval_count = 0`, and the standardized fallback answer string.

## Error Handling Strategy

- **Missing API Key (`GEMINI_API_KEY`)**: Checked before initializing `genai.Client`. Raises `ValueError`.
- **Gemini API Failures / Network Timeouts**: Caught in `llm.py` and logged. Pipeline returns a friendly fallback answer to the user without exposing raw internal stack traces.
- **Empty / Malformed LLM Responses**: Validates that `response.text` is non-empty before returning.

## Citation Strategy & Deferral to Milestone 9

- **Milestone 8 Scope**: Returns raw, structured source metadata (`doc_id`, `title`, `page_number`, `source_pages`, `department`, `academic_year`, `document_type`, `snippet`, `text`) alongside the generated answer text.
- **Deferral Reason**: User-facing citation rendering, interactive UI chips, page jumping, and inline citation numbers are reserved for **Milestone 9** (Citation Rendering & Source Provenance UI). Milestone 8 focuses exclusively on backend grounded generation, response structure stability, and provenance preservation.
