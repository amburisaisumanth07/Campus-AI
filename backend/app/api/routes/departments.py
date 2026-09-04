"""
Departments API routes for official MITS Academic Departments.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.db.models import Department, Faculty
from backend.app.schemas.mits_entities import DepartmentResponse, FacultyResponse

router = APIRouter()


@router.get("", response_model=List[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
):
    """Retrieve all official MITS academic departments."""
    items = db.query(Department).filter(Department.is_active == True, Department.is_valid == True).order_by(Department.name.asc()).all()
    return items


DEPT_CODE_ALIASES = {
    "CSE-AI": "AI",
    "CSE(AI)": "AI",
    "AIML": "CSE-AIML",
    "CSE(AIML)": "CSE-AIML",
    "CSE-HOD": "CSE",
}


@router.get("/{dept_code_or_id}", response_model=DepartmentResponse)
def get_department(
    dept_code_or_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve department details by ID or code (e.g. 'CSE', 'ECE')."""
    if dept_code_or_id.isdigit():
        item = db.query(Department).filter(
            Department.id == int(dept_code_or_id),
            Department.is_active == True,
            Department.is_valid == True,
        ).first()
    else:
        req_code = dept_code_or_id.strip().upper()
        canonical_code = DEPT_CODE_ALIASES.get(req_code, req_code)
        item = db.query(Department).filter(
            Department.code == canonical_code,
            Department.is_active == True,
            Department.is_valid == True,
        ).first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    return item


@router.get("/{dept_code_or_id}/faculty", response_model=List[FacultyResponse])
def get_department_faculty(
    dept_code_or_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve faculty list for a specific department."""
    dept = None
    if dept_code_or_id.isdigit():
        dept = db.query(Department).filter(
            Department.id == int(dept_code_or_id),
            Department.is_active == True,
            Department.is_valid == True,
        ).first()
    else:
        req_code = dept_code_or_id.strip().upper()
        canonical_code = DEPT_CODE_ALIASES.get(req_code, req_code)
        dept = db.query(Department).filter(
            Department.code == canonical_code,
            Department.is_active == True,
            Department.is_valid == True,
        ).first()

    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    # Filter strictly by department_id and exact active status (NO substring matching)
    faculties = db.query(Faculty).filter(
        ((Faculty.department_id == dept.id) | (Faculty.department == dept.code)),
        Faculty.is_valid == True,
        Faculty.is_active == True,
    ).order_by(Faculty.name.asc()).all()

    return faculties
