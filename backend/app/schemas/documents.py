from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from backend.app.db.models import DocumentType, DocumentStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    """Metadata sent alongside the uploaded file (multipart form fields)."""
    title: str = Field(..., min_length=1, max_length=500)
    document_type: DocumentType
    department: Optional[str] = Field(None, max_length=255)
    academic_year: Optional[str] = Field(None, max_length=20)
    version: str = Field("1.0", max_length=50)


# ── Response schemas ──────────────────────────────────────────────────────────

class DocumentVersionResponse(BaseModel):
    id: int
    version: str
    file_checksum: str
    file_size: int
    mime_type: str
    page_count: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentPageResponse(BaseModel):
    page_number: int
    text_content: Optional[str]
    char_count: int

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Public-safe document representation — no filesystem paths."""
    id: int
    title: str
    filename: str
    document_type: str
    department: Optional[str]
    academic_year: Optional[str]
    status: str
    uploaded_by_id: int
    source_type: str = "MANUAL_UPLOAD"
    source_url: Optional[str] = None
    website_source_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    active_version: Optional[DocumentVersionResponse] = None

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    """Extended response including version list and page metadata."""
    versions: List[DocumentVersionResponse] = []
    page_count: Optional[int] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: int
