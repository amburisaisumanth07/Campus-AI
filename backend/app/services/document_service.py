"""
Document management business logic.

Orchestrates:
- Creating Document + DocumentVersion records
- Triggering PDF extraction
- Persisting DocumentPage records
- Managing processing status lifecycle
- Authorization checks
- Safe deletion (file + database records)
"""
from pathlib import Path
from typing import Optional, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.db.models import Document, DocumentVersion, DocumentPage, DocumentStatus, DocumentType
from backend.app.schemas.documents import DocumentCreate
from backend.app.services.file_service import get_storage_dir
from backend.app.services.pdf_service import extract_pages


# ── Creation ──────────────────────────────────────────────────────────────────

def create_document_record(
    db: Session,
    metadata: DocumentCreate,
    uploader_id: int,
    sanitized_filename: str,
) -> Document:
    """Insert the Document row and return it."""
    doc = Document(
        title=metadata.title,
        filename=sanitized_filename,
        document_type=DocumentType(metadata.document_type),
        department=metadata.department,
        academic_year=metadata.academic_year,
        status=DocumentStatus.UPLOADED,
        uploaded_by_id=uploader_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def create_version_record(
    db: Session,
    document: Document,
    version: str,
    storage_path: Path,
    checksum: str,
    file_size: int,
) -> DocumentVersion:
    """Insert a DocumentVersion row."""
    ver = DocumentVersion(
        document_id=document.id,
        version=version,
        storage_path=str(storage_path),
        file_checksum=checksum,
        file_size=file_size,
        mime_type="application/pdf",
        is_active=True,
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)
    return ver


def set_processing(db: Session, document: Document) -> None:
    document.status = DocumentStatus.PROCESSING
    db.commit()


def process_pdf_and_store_pages(
    db: Session,
    document: Document,
    version: DocumentVersion,
    pdf_path: Path,
) -> int:
    """
    Extract pages from the PDF, persist DocumentPage rows, update version
    page_count, and mark document READY.

    Returns total page count.
    Marks document FAILED (with message) on extraction error.
    """
    try:
        pages = extract_pages(pdf_path)

        # Bulk-insert pages
        page_objects = [
            DocumentPage(
                document_id=document.id,
                document_version_id=version.id,
                page_number=p["page_number"],
                text_content=p["text_content"],
                char_count=p["char_count"],
            )
            for p in pages
        ]
        db.add_all(page_objects)

        # Update version page count
        version.page_count = len(pages)

        # Trigger RAG vector indexing
        from backend.app.rag.ingestion import index_document
        indexed_count = index_document(
            doc_id=document.id,
            title=document.title,
            department=document.department,
            academic_year=document.academic_year,
            pages=pages,
        )
        logger.info(
            f"Indexed {indexed_count} vector chunks into Chroma for document {document.id}."
        )

        # Mark document READY only when extraction and vector indexing succeed
        document.status = DocumentStatus.READY
        document.active_version_id = version.id
        document.error_message = None

        db.commit()
        logger.info(
            f"Document {document.id} processed: {len(pages)} pages extracted and indexed."
        )

        return len(pages)

    except Exception as exc:
        db.rollback()
        _mark_failed(db, document, f"Processing/indexing error: {str(exc)}")
        raise


def _mark_failed(db: Session, document: Document, error: str) -> None:
    """Mark a document as FAILED with a sanitized error message."""
    document.status = DocumentStatus.FAILED
    document.error_message = error[:500]
    db.commit()
    logger.error(f"Document {document.id} failed: {error}")


# ── Queries ───────────────────────────────────────────────────────────────────

def get_document_by_id(db: Session, document_id: int) -> Optional[Document]:
    return db.query(Document).filter(Document.id == document_id).first()


def get_documents(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[DocumentStatus] = None,
    user_id: Optional[int] = None,
) -> Tuple[List[Document], int]:
    query = db.query(Document)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    if user_id is not None:
        query = query.filter(Document.uploaded_by_id == user_id)
    total = query.count()
    items = (
        query.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def check_duplicate_checksum(db: Session, checksum: str) -> Optional[Document]:
    """Return the Document that already has this file checksum, or None."""
    ver = db.query(DocumentVersion).filter(
        DocumentVersion.file_checksum == checksum
    ).first()
    if ver:
        return get_document_by_id(db, ver.document_id)
    return None


# ── Deletion ──────────────────────────────────────────────────────────────────

def delete_document(db: Session, document: Document) -> None:
    """Delete vector store index, files from disk, then remove DB records."""
    try:
        from backend.app.rag.ingestion import remove_document_index
        remove_document_index(document.id)
    except Exception as exc:
        logger.warning(f"Vector cleanup skipped/failed for document {document.id}: {exc}")

    for version in document.versions:
        path = Path(version.storage_path)
        if path.exists():
            try:
                path.unlink()
                logger.info(f"Deleted file: {path}")
            except OSError as exc:
                logger.warning(f"Could not delete file {path}: {exc}")

    db.delete(document)
    db.commit()

