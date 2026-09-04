"""
Document management API routes.

POST   /api/documents          – Admin upload PDF
GET    /api/documents          – List documents (authenticated)
GET    /api/documents/{id}     – Get document detail (authenticated)
DELETE /api/documents/{id}     – Delete document (admin only)
"""
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.api.deps import require_admin, get_current_user
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.models import Document, DocumentStatus, User
from backend.app.schemas.documents import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentVersionResponse,
    DocumentCreate,
)
from backend.app.services import document_service, file_service

router = APIRouter()


@router.post("", response_model=DocumentDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=500),
    document_type: str = Form(...),
    department: Optional[str] = Form(None),
    academic_year: Optional[str] = Form(None),
    version: str = Form("1.0"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF document (authenticated user)."""
    allowed_types = [m.strip() for m in settings.ALLOWED_MIME_TYPES.split(",")]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only PDF files are accepted. Got: {file.content_type}",
        )

    try:
        from backend.app.db.models import DocumentType as DocType
        DocType(document_type)
    except ValueError:
        from backend.app.db.models import DocumentType as DocType
        valid = [t.value for t in DocType]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid document_type. Valid values: {valid}",
        )

    metadata = DocumentCreate(
        title=title,
        document_type=document_type,
        department=department,
        academic_year=academic_year,
        version=version,
    )

    sanitized_name = file_service.sanitize_filename(file.filename or "document.pdf")

    doc = document_service.create_document_record(
        db, metadata, current_user.id, sanitized_name
    )

    storage_filename = file_service.generate_storage_filename(doc.id, version)

    try:
        saved_path, checksum, file_size = await file_service.validate_and_save_upload(
            file, storage_filename
        )
    except HTTPException:
        db.delete(doc)
        db.commit()
        raise

    existing = document_service.check_duplicate_checksum(db, checksum)
    if existing:
        saved_path.unlink(missing_ok=True)
        db.delete(doc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A document with identical content already exists (ID: {existing.id}).",
        )

    ver = document_service.create_version_record(
        db, doc, version, saved_path, checksum, file_size
    )

    document_service.set_processing(db, doc)
    try:
        document_service.process_pdf_and_store_pages(db, doc, ver, saved_path)
    except Exception as exc:
        logger.warning(f"Document {doc.id} processing/indexing failed: {exc}")

    db.refresh(doc)
    db.refresh(ver)

    return _build_detail_response(doc, ver)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents (authenticated user sees own docs; admin can see all or filter)."""
    status_enum = None
    if status_filter:
        try:
            status_enum = DocumentStatus(status_filter.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter. Valid: {[s.value for s in DocumentStatus]}",
            )

    from backend.app.db.models import Role
    target_user_id = user_id if (current_user.role == Role.ADMIN and user_id is not None) else (
        None if (current_user.role == Role.ADMIN and user_id is None) else current_user.id
    )

    items, total = document_service.get_documents(
        db, page, page_size, status_enum, user_id=target_user_id
    )
    return DocumentListResponse(
        items=[_to_response(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get document detail (owner or admin)."""
    doc = _get_or_404(db, document_id)
    from backend.app.db.models import Role
    if doc.uploaded_by_id != current_user.id and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document.",
        )
    active_ver = _active_version(doc)
    return _build_detail_response(doc, active_ver)


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and its files (owner or admin)."""
    doc = _get_or_404(db, document_id)
    from backend.app.db.models import Role
    if doc.uploaded_by_id != current_user.id and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document.",
        )
    document_service.delete_document(db, doc)
    return DocumentDeleteResponse(
        message="Document deleted successfully.", document_id=document_id
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, document_id: int) -> Document:
    doc = document_service.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
    return doc


def _active_version(doc: Document):
    for v in doc.versions:
        if v.is_active:
            return v
    return doc.versions[0] if doc.versions else None


def _to_version_response(ver) -> DocumentVersionResponse:
    return DocumentVersionResponse(
        id=ver.id,
        version=ver.version,
        file_checksum=ver.file_checksum,
        file_size=ver.file_size,
        mime_type=ver.mime_type,
        page_count=ver.page_count,
        is_active=ver.is_active,
        created_at=ver.created_at,
    )


def _to_response(doc: Document) -> DocumentResponse:
    active_ver = _active_version(doc)
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        document_type=doc.document_type.value,
        department=doc.department,
        academic_year=doc.academic_year,
        status=doc.status.value,
        uploaded_by_id=doc.uploaded_by_id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        active_version=_to_version_response(active_ver) if active_ver else None,
    )


def _build_detail_response(doc: Document, ver) -> DocumentDetailResponse:
    active_ver_resp = _to_version_response(ver) if ver else None
    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        document_type=doc.document_type.value,
        department=doc.department,
        academic_year=doc.academic_year,
        status=doc.status.value,
        uploaded_by_id=doc.uploaded_by_id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        active_version=active_ver_resp,
        versions=[_to_version_response(v) for v in doc.versions],
        page_count=ver.page_count if ver else None,
    )
