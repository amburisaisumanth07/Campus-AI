"""
Announcements API routes for MITS Official Notices & Circulars.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.db.models import Announcement
from backend.app.schemas.mits_entities import AnnouncementResponse

router = APIRouter()


@router.get("", response_model=List[AnnouncementResponse])
def list_announcements(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve latest official MITS announcements, notices, and circulars."""
    query = db.query(Announcement).filter(Announcement.is_valid == True)
    if category and category.strip() and category.lower() != "all":
        query = query.filter(Announcement.category.ilike(category.strip()))
    
    items = query.order_by(Announcement.published_date.desc().nullslast(), Announcement.created_at.desc()).offset(offset).limit(limit).all()
    return items


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve single official announcement details by ID."""
    item = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found.")
    return item
