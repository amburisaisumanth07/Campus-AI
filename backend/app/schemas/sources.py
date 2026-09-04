"""
Pydantic schemas for Website Sources and Synchronization History.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class WebsiteSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    base_url: str = Field(..., min_length=1, max_length=1000)
    allowed_domains: str = Field(..., min_length=1, max_length=1000)
    allowed_paths: Optional[str] = Field(None, max_length=1000)
    active: bool = True
    sync_interval: str = Field("6h", pattern="^(1h|6h|12h|24h)$")
    max_pages: int = Field(50, ge=1, le=500)


class WebsiteSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    base_url: Optional[str] = Field(None, min_length=1, max_length=1000)
    allowed_domains: Optional[str] = Field(None, min_length=1, max_length=1000)
    allowed_paths: Optional[str] = Field(None, max_length=1000)
    active: Optional[bool] = None
    sync_interval: Optional[str] = Field(None, pattern="^(1h|6h|12h|24h)$")
    max_pages: Optional[int] = Field(None, ge=1, le=500)


# ── Response schemas ──────────────────────────────────────────────────────────

class WebsiteSyncHistoryResponse(BaseModel):
    id: int
    source_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    documents_discovered: int
    documents_added: int
    documents_updated: int
    documents_unchanged: int
    documents_failed: int
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class WebsiteSourceResponse(BaseModel):
    id: int
    name: str
    base_url: str
    allowed_domains: str
    allowed_paths: Optional[str] = None
    active: bool
    auto_sync_enabled: bool = True
    sync_interval: str
    max_pages: int
    last_checked_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    next_scheduled_sync_at: Optional[datetime] = None
    status: str
    last_error: Optional[str] = None
    created_by_id: int
    document_count: int = 0
    pending_review_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncTriggerResponse(BaseModel):
    message: str
    source_id: int
    history_id: Optional[int] = None
    status: str


class SourceStatusResponse(BaseModel):
    source_id: int
    name: str
    status: str
    last_checked_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    next_scheduled_sync_at: Optional[datetime] = None
    total_documents: int = 0
    pending_review_count: int = 0
    latest_history: Optional[WebsiteSyncHistoryResponse] = None


class SyncChangeReviewResponse(BaseModel):
    id: int
    source_id: int
    history_id: Optional[int] = None
    url: str
    title: str
    entity_type: str
    change_type: str
    status: str
    previous_content: Optional[str] = None
    new_content: Optional[str] = None
    content_hash: Optional[str] = None
    http_status: Optional[int] = 200
    error_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

