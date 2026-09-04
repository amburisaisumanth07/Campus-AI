"""
Academic Calendar API routes for official MITS calendar events and schedules.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.db.models import AcademicCalendarEvent
from backend.app.schemas.mits_entities import AcademicCalendarResponse

router = APIRouter()


@router.get("", response_model=List[AcademicCalendarResponse])
def list_calendar_events(
    academic_year: Optional[str] = None,
    program: Optional[str] = None,
    year: Optional[str] = None,
    semester: Optional[str] = None,
    upcoming_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve official MITS academic calendar events and milestones."""
    query = db.query(AcademicCalendarEvent).filter(AcademicCalendarEvent.is_valid == True)

    if academic_year and academic_year.strip() and academic_year.lower() != "all":
        query = query.filter(AcademicCalendarEvent.academic_year == academic_year.strip())
    if program and program.strip() and program.lower() != "all":
        query = query.filter(AcademicCalendarEvent.program.ilike(f"%{program.strip()}%"))
    if year and year.strip() and year.lower() != "all":
        query = query.filter(AcademicCalendarEvent.year.ilike(f"%{year.strip()}%"))
    if semester and semester.strip() and semester.lower() != "all":
        query = query.filter(AcademicCalendarEvent.semester.ilike(f"%{semester.strip()}%"))

    if upcoming_only:
        now = datetime.now(timezone.utc)
        query = query.filter((AcademicCalendarEvent.end_date >= now) | (AcademicCalendarEvent.start_date >= now))

    items = query.order_by(AcademicCalendarEvent.start_date.asc().nullslast()).offset(offset).limit(limit).all()
    return items


@router.get("/{event_id}", response_model=AcademicCalendarResponse)
def get_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve single academic calendar event details by ID."""
    item = db.query(AcademicCalendarEvent).filter(AcademicCalendarEvent.id == event_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found.")
    return item
