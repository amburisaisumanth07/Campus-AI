"""
Placements API routes for MITS Training & Placement drives and recruiters.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.db.models import Placement
from backend.app.schemas.mits_entities import PlacementResponse

router = APIRouter()


@router.get("", response_model=List[PlacementResponse])
def list_placements(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve verified MITS campus placement drives and recruiter alerts."""
    items = db.query(Placement).filter(Placement.is_valid == True).order_by(Placement.drive_date.desc().nullslast(), Placement.created_at.desc()).offset(offset).limit(limit).all()
    return items


@router.get("/{placement_id}", response_model=PlacementResponse)
def get_placement(
    placement_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve single placement drive details by ID."""
    item = db.query(Placement).filter(Placement.id == placement_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placement record not found.")
    return item
