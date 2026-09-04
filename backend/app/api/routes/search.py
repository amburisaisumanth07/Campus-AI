"""
Global Search API route across all MITS entities and documents.
"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.api.dependencies import get_db
from backend.app.db.models import (
    Announcement,
    AcademicCalendarEvent,
    Examination,
    Department,
    Placement,
    Document,
)
from backend.app.schemas.mits_entities import SearchResponse, SearchResultItem

router = APIRouter()


@router.get("", response_model=SearchResponse)
def search_all_college_info(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Unified global search across announcements, academic calendar, exams, departments, and placements."""
    query_str = f"%{q.strip()}%"
    results: List[SearchResultItem] = []

    # 1. Announcements
    announcements = db.query(Announcement).filter(
        or_(
            Announcement.title.ilike(query_str),
            Announcement.description.ilike(query_str),
            Announcement.content.ilike(query_str),
            Announcement.category.ilike(query_str),
        )
    ).limit(limit).all()

    for ann in announcements:
        results.append(
            SearchResultItem(
                id=ann.id,
                type="announcement",
                title=ann.title,
                category=ann.category,
                date=ann.published_date,
                description=ann.description or (ann.content[:150] if ann.content else None),
                source_url=ann.source_url,
                link_url=f"/announcements/{ann.id}",
            )
        )

    # 2. Examinations
    exams = db.query(Examination).filter(
        or_(
            Examination.title.ilike(query_str),
            Examination.description.ilike(query_str),
            Examination.exam_type.ilike(query_str),
            Examination.program.ilike(query_str),
        )
    ).limit(limit).all()

    for ex in exams:
        results.append(
            SearchResultItem(
                id=ex.id,
                type="examination",
                title=ex.title,
                category=ex.exam_type.title(),
                date=ex.published_date,
                description=ex.description,
                source_url=ex.source_url,
                link_url="/examinations",
            )
        )

    # 3. Academic Calendar
    events = db.query(AcademicCalendarEvent).filter(
        or_(
            AcademicCalendarEvent.event_name.ilike(query_str),
            AcademicCalendarEvent.event_description.ilike(query_str),
            AcademicCalendarEvent.program.ilike(query_str),
        )
    ).limit(limit).all()

    for ev in events:
        results.append(
            SearchResultItem(
                id=ev.id,
                type="calendar",
                title=ev.event_name,
                category=f"{ev.program} {ev.academic_year}",
                date=ev.start_date,
                description=ev.event_description,
                source_url=ev.source_url,
                link_url="/academic-calendar",
            )
        )

    # 4. Departments
    depts = db.query(Department).filter(
        or_(
            Department.name.ilike(query_str),
            Department.code.ilike(query_str),
            Department.description.ilike(query_str),
            Department.programs.ilike(query_str),
        )
    ).limit(limit).all()

    for dept in depts:
        results.append(
            SearchResultItem(
                id=dept.id,
                type="department",
                title=f"{dept.name} ({dept.code})",
                category=dept.school or "Academic Department",
                date=None,
                description=dept.description[:150] if dept.description else None,
                source_url=dept.source_url,
                link_url=f"/departments/{dept.code.lower()}",
            )
        )

    # 5. Placements
    placements = db.query(Placement).filter(
        or_(
            Placement.company.ilike(query_str),
            Placement.job_role.ilike(query_str),
            Placement.description.ilike(query_str),
        )
    ).limit(limit).all()

    for pl in placements:
        results.append(
            SearchResultItem(
                id=pl.id,
                type="placement",
                title=f"{pl.company} - {pl.job_role or 'Recruitment Drive'}",
                category=pl.package_details or "Placement Drive",
                date=pl.drive_date,
                description=pl.description,
                source_url=pl.source_url,
                link_url="/placements",
            )
        )

    return SearchResponse(
        query=q,
        total_results=len(results),
        results=results[:limit],
    )
