"""
College Information and Important Verified Links API routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.db.models import CollegeInfo, ImportantLink
from backend.app.schemas.mits_entities import CollegeInfoResponse, ImportantLinkResponse

router = APIRouter()


@router.get("/info", response_model=List[CollegeInfoResponse])
def get_college_information(
    db: Session = Depends(get_db),
):
    """Retrieve verified institutional details (accreditations, vision, mission, facilities)."""
    items = db.query(CollegeInfo).filter(CollegeInfo.is_valid == True).all()
    return items


@router.get("/links", response_model=List[ImportantLinkResponse])
def get_important_links(
    db: Session = Depends(get_db),
):
    """Retrieve official verified portal links (IMS, Exam Cell, LMS, Library, Placements)."""
    items = db.query(ImportantLink).filter(ImportantLink.is_active == True, ImportantLink.is_valid == True).order_by(ImportantLink.display_order.asc()).all()
    return items
