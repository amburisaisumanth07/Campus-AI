# Chat API Integration & Orchestration (Milestone 10)

## Overview

The Chat API provides the primary backend HTTP endpoint connecting student authentication, conversation management, message persistence, semantic document retrieval, grounded Gemini LLM generation, and application-side source citation extraction.

---

## Endpoint Contract

### Endpoint
```http
POST /api/chat
POST /api/chat/message
```

### Headers
```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request Payload

```json
{
  "conversation_id": 25,
  "message": "What is the minimum attendance requirement?",
  "department": "CSE",
  "academic_year": "2025-26"
}
```

* **`conversation_id`** *(optional, int)*: Existing conversation ID. If omitted (`null`), a new conversation is created automatically.
* **`message` / `content`** *(required, string, 1-4000 chars)*: The student's question string.
* **`department`** *(optional, string)*: Department filter for semantic search.
* **`academic_year`** *(optional, string)*: Academic year filter for semantic search.

---

### Successful Response Payload (`200 OK`)

```json
{
  "conversation_id": 25,
  "message_id": 103,
  "answer": "Students must maintain a minimum 75% attendance in each course.",
  "grounded": true,
  "retrieval_count": 2,
  "sources": [
    {
      "doc_id": 101,
      "document_id": 101,
      "document_version_id": 1,
      "title": "Academic Regulations 2026",
      "document_type": "regulation",
      "department": "CSE",
      "academic_year": "2025-26",
      "page_number": 14,
      "source_pages": [14],
      "snippet": "Minimum attendance requirement is 75%."
    }
  ],
  "user_message": {
    "id": 102,
    "conversation_id": 25,
    "role": "user",
    "content": "What is the minimum attendance requirement?",
    "created_at": "2026-08-16T18:04:00Z"
  },
  "assistant_message": {
    "id": 103,
    "conversation_id": 25,
    "role": "assistant",
    "content": "Students must maintain a minimum 75% attendance in each course.",
    "citations": [
      {
        "doc_id": 101,
        "title": "Academic Regulations 2026",
        "page_number": 14,
        "snippet": "Minimum attendance requirement is 75%."
      }
    ],
    "created_at": "2026-08-16T18:04:01Z"
  }
}
```

---

## Authentication & Authorization Rules

1. **Bearer Token Authentication**:
   Requests must include a valid JWT access token in the `Authorization` header. Requests missing or presenting invalid tokens return `401 Unauthorized`.
2. **Strict Identity Verification**:
   The user identity is extracted strictly from the validated JWT claims (`get_current_user`). Request payloads cannot override `user_id`.
3. **Conversation Ownership**:
   When a `conversation_id` is passed, the backend queries the database and verifies `conversation.user_id == current_user.id`. Access attempts to another user's conversation ID return `404 Not Found`.

---

## No-Context & Failure Behavior

* **No-Context Fallback (`retrieval_count == 0`)**:
  If no relevant college documents match the query, the RAG pipeline short-circuits without invoking the Gemini LLM. The endpoint returns:
  ```json
  {
    "answer": "I couldn't find this information in the available college documents.",
    "grounded": false,
    "retrieval_count": 0,
    "sources": []
  }
  ```
* **Error Handling (`500` / RAG Failure)**:
  Internal exceptions (e.g. database network error or API timeout) are caught, logged internally, and return a safe, controlled fallback answer without exposing stack traces or API keys to the client.

---

## Security Review

* **Zero Identity Leakage**: User ID parameter in JSON body is ignored.
* **Input Validation**: Empty, missing, or whitespace-only query strings return `422 Unprocessable Entity`.
* **Citation Safety**: Citations are generated application-side from vector store provenance metadata (`citations.py`), guaranteeing zero Gemini citation hallucinations.
