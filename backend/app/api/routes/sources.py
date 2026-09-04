"""
Admin Data Sources & Website Synchronization API routes.

Provides endpoints for managing website sources, viewing sync histories,
and triggering manual crawl and synchronization tasks.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.api.deps import require_admin
from backend.app.db.models import (
    User,
    WebsiteSource,
    WebsiteSyncHistory,
    WebsiteSourceStatus,
    Document,
    SyncChangeReview,
)
from backend.app.schemas.sources import (
    WebsiteSourceCreate,
    WebsiteSourceUpdate,
    WebsiteSourceResponse,
    WebsiteSyncHistoryResponse,
    SyncTriggerResponse,
    SourceStatusResponse,
    SyncChangeReviewResponse,
)
from backend.app.services import crawler_service, scheduler_service
from backend.app.services.crawler_service import is_safe_and_valid_url
from backend.app.rag.ingestion import remove_document_index

router = APIRouter()


def _to_source_response(src: WebsiteSource, db: Session) -> WebsiteSourceResponse:
    doc_count = db.query(Document).filter(Document.website_source_id == src.id).count()
    pending_count = (
        db.query(SyncChangeReview)
        .filter(SyncChangeReview.source_id == src.id, SyncChangeReview.status == "PENDING_REVIEW")
        .count()
    )
    return WebsiteSourceResponse(
        id=src.id,
        name=src.name,
        base_url=src.base_url,
        allowed_domains=src.allowed_domains,
        allowed_paths=src.allowed_paths,
        active=src.active,
        auto_sync_enabled=getattr(src, "auto_sync_enabled", True),
        sync_interval=src.sync_interval,
        max_pages=src.max_pages,
        last_checked_at=src.last_checked_at,
        last_successful_sync_at=src.last_successful_sync_at,
        next_scheduled_sync_at=getattr(src, "next_scheduled_sync_at", None),
        status=src.status.value if hasattr(src.status, "value") else str(src.status),
        last_error=src.last_error,
        created_by_id=src.created_by_id,
        document_count=doc_count,
        pending_review_count=pending_count,
        created_at=src.created_at,
        updated_at=src.updated_at,
    )


# ── 1. List Sources ───────────────────────────────────────────────────────────

@router.get("", response_model=List[WebsiteSourceResponse])
def list_website_sources(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all configured website knowledge sources (Admin only)."""
    sources = db.query(WebsiteSource).order_by(WebsiteSource.created_at.desc()).all()
    return [_to_source_response(s, db) for s in sources]


# ── 2. Create Source ──────────────────────────────────────────────────────────

@router.post("", response_model=WebsiteSourceResponse, status_code=status.HTTP_201_CREATED)
def create_website_source(
    payload: WebsiteSourceCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new website knowledge source (Admin only)."""
    allowed_domains = [d.strip() for d in payload.allowed_domains.split(",") if d.strip()]
    allowed_paths = [p.strip() for p in payload.allowed_paths.split(",")] if payload.allowed_paths else None

    # Validate Base URL
    is_safe, error_msg = is_safe_and_valid_url(payload.base_url, allowed_domains, allowed_paths)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid or unsafe base_url: {error_msg}",
        )

    # Check for duplicate base_url
    existing = db.query(WebsiteSource).filter(WebsiteSource.base_url == payload.base_url.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A website source with base URL '{payload.base_url}' already exists (ID: {existing.id}).",
        )

    source = WebsiteSource(
        name=payload.name.strip(),
        base_url=payload.base_url.strip(),
        allowed_domains=",".join(allowed_domains),
        allowed_paths=",".join(allowed_paths) if allowed_paths else None,
        active=payload.active,
        sync_interval=payload.sync_interval,
        max_pages=payload.max_pages,
        status=WebsiteSourceStatus.IDLE,
        created_by_id=admin.id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # Schedule background job if active
    if source.active:
        scheduler_service.schedule_source_sync(source)

    return _to_source_response(source, db)


# ── 3. Get Source Details ─────────────────────────────────────────────────────

@router.get("/{source_id}", response_model=WebsiteSourceResponse)
def get_website_source(
    source_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve details for a single website source (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")
    return _to_source_response(source, db)


# ── 4. Update Source ──────────────────────────────────────────────────────────

@router.put("/{source_id}", response_model=WebsiteSourceResponse)
def update_website_source(
    source_id: int,
    payload: WebsiteSourceUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update website source settings (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    if payload.base_url is not None or payload.allowed_domains is not None:
        new_base = payload.base_url.strip() if payload.base_url else source.base_url
        new_domains_str = payload.allowed_domains if payload.allowed_domains is not None else source.allowed_domains
        new_domains = [d.strip() for d in new_domains_str.split(",") if d.strip()]
        new_paths_str = payload.allowed_paths if payload.allowed_paths is not None else source.allowed_paths
        new_paths = [p.strip() for p in new_paths_str.split(",")] if new_paths_str else None

        is_safe, error_msg = is_safe_and_valid_url(new_base, new_domains, new_paths)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Updated URL/Domain configuration is invalid: {error_msg}",
            )

    if payload.name is not None:
        source.name = payload.name.strip()
    if payload.base_url is not None:
        source.base_url = payload.base_url.strip()
    if payload.allowed_domains is not None:
        source.allowed_domains = ",".join([d.strip() for d in payload.allowed_domains.split(",") if d.strip()])
    if payload.allowed_paths is not None:
        source.allowed_paths = ",".join([p.strip() for p in payload.allowed_paths.split(",") if p.strip()]) if payload.allowed_paths else None
    if payload.active is not None:
        source.active = payload.active
    if payload.sync_interval is not None:
        source.sync_interval = payload.sync_interval
    if payload.max_pages is not None:
        source.max_pages = payload.max_pages

    db.commit()
    db.refresh(source)

    # Reschedule job
    scheduler_service.schedule_source_sync(source)

    return _to_source_response(source, db)


# ── 5. Delete Source ──────────────────────────────────────────────────────────

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_website_source(
    source_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a website source and clean up all synced documents and vector embeddings (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    # Remove scheduler job
    scheduler_service.remove_source_sync(source.id)

    # Clean up associated documents from vector store and DB
    synced_docs = db.query(Document).filter(Document.website_source_id == source.id).all()
    for doc in synced_docs:
        try:
            remove_document_index(doc.id)
        except Exception:
            pass
        db.delete(doc)

    db.delete(source)
    db.commit()


# ── 6. Trigger Sync Now ───────────────────────────────────────────────────────

def _run_background_sync(source_id: int):
    """Background execution runner for manual sync trigger."""
    from backend.app.db.session import SessionLocal
    if SessionLocal:
        db = SessionLocal()
        try:
            crawler_service.synchronize_website_source(db, source_id)
        except Exception:
            pass
        finally:
            db.close()


@router.post("/{source_id}/sync", response_model=SyncTriggerResponse)
def trigger_website_sync(
    source_id: int,
    background_tasks: BackgroundTasks,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger immediate manual synchronization for a website source (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    if source.status == WebsiteSourceStatus.SYNCING:
        return SyncTriggerResponse(
            message="Synchronization is already running for this source.",
            source_id=source.id,
            status="SYNCING",
        )

    # Queue background crawl task
    background_tasks.add_task(_run_background_sync, source.id)

    return SyncTriggerResponse(
        message=f"Synchronization started for source '{source.name}'.",
        source_id=source.id,
        status="IN_PROGRESS",
    )


# ── 7. Get Sync History ───────────────────────────────────────────────────────

@router.get("/{source_id}/sync-history", response_model=List[WebsiteSyncHistoryResponse])
def get_website_sync_history(
    source_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve execution history for a website source (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    items = (
        db.query(WebsiteSyncHistory)
        .filter(WebsiteSyncHistory.source_id == source.id)
        .order_by(WebsiteSyncHistory.started_at.desc())
        .limit(50)
        .all()
    )
    return [
        WebsiteSyncHistoryResponse(
            id=h.id,
            source_id=h.source_id,
            started_at=h.started_at,
            completed_at=h.completed_at,
            status=h.status.value if hasattr(h.status, "value") else str(h.status),
            documents_discovered=h.documents_discovered,
            documents_added=h.documents_added,
            documents_updated=h.documents_updated,
            documents_unchanged=h.documents_unchanged,
            documents_failed=h.documents_failed,
            error_message=h.error_message,
        )
        for h in items
    ]


# ── 8. Get Live Status ────────────────────────────────────────────────────────

@router.get("/{source_id}/status", response_model=SourceStatusResponse)
def get_source_live_status(
    source_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get live status and latest sync history for a website source (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    doc_count = db.query(Document).filter(Document.website_source_id == source.id).count()
    latest_hist = (
        db.query(WebsiteSyncHistory)
        .filter(WebsiteSyncHistory.source_id == source.id)
        .order_by(WebsiteSyncHistory.started_at.desc())
        .first()
    )

    latest_resp = None
    if latest_hist:
        latest_resp = WebsiteSyncHistoryResponse(
            id=latest_hist.id,
            source_id=latest_hist.source_id,
            started_at=latest_hist.started_at,
            completed_at=latest_hist.completed_at,
            status=latest_hist.status.value if hasattr(latest_hist.status, "value") else str(latest_hist.status),
            documents_discovered=latest_hist.documents_discovered,
            documents_added=latest_hist.documents_added,
            documents_updated=latest_hist.documents_updated,
            documents_unchanged=latest_hist.documents_unchanged,
            documents_failed=latest_hist.documents_failed,
            error_message=latest_hist.error_message,
        )

    pending_count = (
        db.query(SyncChangeReview)
        .filter(SyncChangeReview.source_id == source.id, SyncChangeReview.status == "PENDING_REVIEW")
        .count()
    )

    return SourceStatusResponse(
        source_id=source.id,
        name=source.name,
        status=source.status.value if hasattr(source.status, "value") else str(source.status),
        last_checked_at=source.last_checked_at,
        last_successful_sync_at=source.last_successful_sync_at,
        next_scheduled_sync_at=getattr(source, "next_scheduled_sync_at", None),
        total_documents=doc_count,
        pending_review_count=pending_count,
        latest_history=latest_resp,
    )


# ── 9. Pause & Resume Automatic Sync ──────────────────────────────────────────

@router.post("/{source_id}/pause", response_model=WebsiteSourceResponse)
def pause_source_sync(
    source_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Pause automatic background synchronization for a source (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    scheduler_service.pause_source_sync(source.id, db)
    db.refresh(source)
    return _to_source_response(source, db)


@router.post("/{source_id}/resume", response_model=WebsiteSourceResponse)
def resume_source_sync(
    source_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Resume automatic background synchronization for a source (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    scheduler_service.resume_source_sync(source.id, db)
    db.refresh(source)
    return _to_source_response(source, db)


# ── 10. Human-in-the-Loop Change Review Endpoints ──────────────────────────────

@router.get("/{source_id}/changes", response_model=List[SyncChangeReviewResponse])
def get_source_changes(
    source_id: int,
    status_filter: Optional[str] = None,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List discovered changes awaiting or having undergone human review (Admin only)."""
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    query = db.query(SyncChangeReview).filter(SyncChangeReview.source_id == source.id)
    if status_filter:
        query = query.filter(SyncChangeReview.status == status_filter.strip().upper())
    changes = query.order_by(SyncChangeReview.created_at.desc()).limit(100).all()

    return [
        SyncChangeReviewResponse(
            id=c.id,
            source_id=c.source_id,
            history_id=c.history_id,
            url=c.url,
            title=c.title,
            entity_type=c.entity_type,
            change_type=c.change_type,
            status=c.status,
            previous_content=c.previous_content,
            new_content=c.new_content,
            content_hash=c.content_hash,
            http_status=c.http_status,
            error_reason=c.error_reason,
            reviewed_at=c.reviewed_at,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in changes
    ]


@router.post("/{source_id}/changes/{change_id}/approve", response_model=SyncChangeReviewResponse)
def approve_change(
    source_id: int,
    change_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve a discovered change and index it into the knowledge base (Admin only)."""
    from datetime import datetime, timezone
    from backend.app.rag.ingestion import index_document, remove_document_index
    from backend.app.rag.pipeline import invalidate_rag_cache
    from backend.app.db.models import DocumentStatus

    change = db.query(SyncChangeReview).filter(
        SyncChangeReview.id == change_id,
        SyncChangeReview.source_id == source_id,
    ).first()
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change review record not found.")

    change.status = "APPROVED"
    change.reviewed_by_id = admin.id
    change.reviewed_at = datetime.now(timezone.utc)

    # Publish Document and index into ChromaDB if entity_type is document
    if change.entity_type == "document":
        doc = db.query(Document).filter(
            Document.website_source_id == source_id,
            Document.source_url == change.url,
        ).first()
        if doc:
            if change.change_type in ("NEW", "UPDATED"):
                doc.status = DocumentStatus.READY
                try:
                    remove_document_index(doc.id)
                except Exception:
                    pass
                pages = [
                    {"page_number": p.page_number, "text_content": p.text_content or "", "char_count": p.char_count}
                    for p in doc.pages
                ]
                if pages:
                    index_document(
                        doc_id=doc.id,
                        title=doc.title,
                        department=doc.department,
                        academic_year=doc.academic_year,
                        pages=pages,
                        source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
                        source_url=doc.source_url,
                    )
            elif change.change_type == "REMOVED":
                doc.status = DocumentStatus.FAILED
                try:
                    remove_document_index(doc.id)
                except Exception:
                    pass

    db.commit()
    db.refresh(change)
    invalidate_rag_cache()

    return SyncChangeReviewResponse(
        id=change.id,
        source_id=change.source_id,
        history_id=change.history_id,
        url=change.url,
        title=change.title,
        entity_type=change.entity_type,
        change_type=change.change_type,
        status=change.status,
        previous_content=change.previous_content,
        new_content=change.new_content,
        content_hash=change.content_hash,
        http_status=change.http_status,
        error_reason=change.error_reason,
        reviewed_at=change.reviewed_at,
        created_at=change.created_at,
        updated_at=change.updated_at,
    )


@router.post("/{source_id}/changes/{change_id}/reject", response_model=SyncChangeReviewResponse)
def reject_change(
    source_id: int,
    change_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reject a discovered change, discarding it from publication (Admin only)."""
    from datetime import datetime, timezone
    from backend.app.rag.ingestion import remove_document_index
    from backend.app.db.models import DocumentStatus

    change = db.query(SyncChangeReview).filter(
        SyncChangeReview.id == change_id,
        SyncChangeReview.source_id == source_id,
    ).first()
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change review record not found.")

    change.status = "REJECTED"
    change.reviewed_by_id = admin.id
    change.reviewed_at = datetime.now(timezone.utc)

    # Ensure rejected document is not in Chroma vector index
    if change.entity_type == "document":
        doc = db.query(Document).filter(
            Document.website_source_id == source_id,
            Document.source_url == change.url,
        ).first()
        if doc and doc.status != DocumentStatus.READY:
            try:
                remove_document_index(doc.id)
            except Exception:
                pass

    db.commit()
    db.refresh(change)

    return SyncChangeReviewResponse(
        id=change.id,
        source_id=change.source_id,
        history_id=change.history_id,
        url=change.url,
        title=change.title,
        entity_type=change.entity_type,
        change_type=change.change_type,
        status=change.status,
        previous_content=change.previous_content,
        new_content=change.new_content,
        content_hash=change.content_hash,
        http_status=change.http_status,
        error_reason=change.error_reason,
        reviewed_at=change.reviewed_at,
        created_at=change.created_at,
        updated_at=change.updated_at,
    )


@router.post("/{source_id}/changes/approve-all")
def approve_all_changes(
    source_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve all pending changes for a website source and index them into ChromaDB (Admin only)."""
    from datetime import datetime, timezone
    from backend.app.rag.ingestion import index_document, remove_document_index
    from backend.app.rag.pipeline import invalidate_rag_cache
    from backend.app.db.models import DocumentStatus

    pending = db.query(SyncChangeReview).filter(
        SyncChangeReview.source_id == source_id,
        SyncChangeReview.status == "PENDING_REVIEW",
    ).all()

    now = datetime.now(timezone.utc)
    for c in pending:
        c.status = "APPROVED"
        c.reviewed_by_id = admin.id
        c.reviewed_at = now

        if c.entity_type == "document":
            doc = db.query(Document).filter(
                Document.website_source_id == source_id,
                Document.source_url == c.url,
            ).first()
            if doc:
                if c.change_type in ("NEW", "UPDATED"):
                    doc.status = DocumentStatus.READY
                    try:
                        remove_document_index(doc.id)
                    except Exception:
                        pass
                    pages = [
                        {"page_number": p.page_number, "text_content": p.text_content or "", "char_count": p.char_count}
                        for p in doc.pages
                    ]
                    if pages:
                        index_document(
                            doc_id=doc.id,
                            title=doc.title,
                            department=doc.department,
                            academic_year=doc.academic_year,
                            pages=pages,
                            source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
                            source_url=doc.source_url,
                        )
                elif c.change_type == "REMOVED":
                    doc.status = DocumentStatus.FAILED
                    try:
                        remove_document_index(doc.id)
                    except Exception:
                        pass

    db.commit()
    invalidate_rag_cache()
    return {"message": f"Successfully approved and published {len(pending)} pending change(s).", "approved_count": len(pending)}
