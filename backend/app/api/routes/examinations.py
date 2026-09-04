"""
Examinations API routes for MITS timetables, hall tickets, results, and circulars.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.db.models import Examination
from backend.app.schemas.mits_entities import ExaminationResponse

router = APIRouter()


@router.get("", response_model=List[ExaminationResponse])
def list_examinations(
    exam_type: Optional[str] = None,
    program: Optional[str] = None,
    year: Optional[str] = None,
    semester: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve official examination notices, timetables, hall ticket circulars, and results."""
    query = db.query(Examination).filter(Examination.is_valid == True)

    if exam_type and exam_type.strip() and exam_type.lower() != "all":
        query = query.filter(Examination.exam_type == exam_type.strip().lower())
    if program and program.strip() and program.lower() != "all":
        query = query.filter(Examination.program.ilike(f"%{program.strip()}%"))
    if year and year.strip() and year.lower() != "all":
        query = query.filter(Examination.year.ilike(f"%{year.strip()}%"))
    if semester and semester.strip() and semester.lower() != "all":
        query = query.filter(Examination.semester.ilike(f"%{semester.strip()}%"))

    items = query.order_by(Examination.published_date.desc().nullslast(), Examination.created_at.desc()).offset(offset).limit(limit).all()
    return items


@router.get("/{exam_id}", response_model=ExaminationResponse)
def get_examination(
    exam_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve single examination notice details by ID."""
    item = db.query(Examination).filter(Examination.id == exam_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination record not found.")
    return item
