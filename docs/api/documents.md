# Document Management API Documentation

## Endpoints Summary
All endpoints require HTTP Bearer Token authentication via `Authorization: Bearer <token>`.

| Endpoint | Method | Role Required | Description |
|---|---|---|---|
| `/api/documents` | POST | ADMIN | Upload PDF document + metadata |
| `/api/documents` | GET | Authenticated | List document metadata |
| `/api/documents/{id}` | GET | Authenticated | Get document detail & versions |
| `/api/documents/{id}` | DELETE | ADMIN | Delete document & raw PDF file |

---

## Endpoint Details

### 1. Upload Document (`POST /api/documents`)
- **Content-Type**: `multipart/form-data`
- **Headers**: `Authorization: Bearer <ADMIN_JWT>`
- **Form Parameters**:
  - `file`: PDF file binary (`application/pdf`, max 20MB)
  - `title`: string (1-500 chars)
  - `document_type`: string (`regulation`, `academic_calendar`, `examination`, `attendance`, `placement`, `scholarship`, `course`, `notice`, `department_document`, `other`)
  - `department`: string (optional)
  - `academic_year`: string (optional, e.g. "2025-2026")
  - `version`: string (optional, default "1.0")

**Responses**:
- `201 Created`:
```json
{
  "id": 1,
  "title": "B.Tech Academic Regulations",
  "filename": "academic_regulations.pdf",
  "document_type": "regulation",
  "department": "Computer Science",
  "academic_year": "2025-2026",
  "status": "READY",
  "uploaded_by_id": 1,
  "created_at": "2026-08-12T16:00:00Z",
  "updated_at": "2026-08-12T16:00:00Z",
  "active_version": {
    "id": 1,
    "version": "1.0",
    "file_checksum": "a3f8c...",
    "file_size": 1048576,
    "mime_type": "application/pdf",
    "page_count": 12,
    "is_active": true,
    "created_at": "2026-08-12T16:00:00Z"
  },
  "versions": [...],
  "page_count": 12
}
```
- `403 Forbidden`: User is not an ADMIN.
- `409 Conflict`: Duplicate file checksum detected.
- `413 Content Too Large`: File exceeds size limit (20MB).
- `415 Unsupported Media Type`: File is not a valid PDF.

---

### 2. List Documents (`GET /api/documents`)
- **Headers**: `Authorization: Bearer <JWT>`
- **Query Parameters**:
  - `page`: integer (default 1)
  - `page_size`: integer (default 20, max 100)
  - `status`: string (optional filter: `UPLOADED`, `PROCESSING`, `READY`, `FAILED`)

---

### 3. Get Document (`GET /api/documents/{document_id}`)
- **Headers**: `Authorization: Bearer <JWT>`

---

### 4. Delete Document (`DELETE /api/documents/{document_id}`)
- **Headers**: `Authorization: Bearer <ADMIN_JWT>`
- **Response**: `200 OK` (`{"message": "Document deleted successfully.", "document_id": 1}`)
