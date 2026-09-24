"""
API router for Official MITS Student Attendance.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.core.security import decode_access_token
from backend.app.db.models import User
from backend.app.schemas.mits_entities import AttendanceTrackerResponse
from backend.app.services.attendance_service import (
    OfficialAttendanceService,
    AttendanceIntegrationError,
    AttendanceAuthError,
    AttendancePortalUnavailableError,
    AttendanceMalformedResponseError,
    get_mock_attendance_data,
)

router = APIRouter()

oauth2_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Retrieve authenticated user if valid token is provided, otherwise return None."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None


@router.get("", response_model=AttendanceTrackerResponse, summary="Get student attendance tracker data")
def get_attendance(current_user: Optional[User] = Depends(get_current_user_optional)):
    """
    Return student attendance data (mock records with Python-calculated percentages).
    If an authenticated user is present, customizes the student name while retaining standard mock roll number.
    """
    student_name = current_user.name if current_user and current_user.name else "Sai Sumanth"
    return get_mock_attendance_data(student_name=student_name, roll_number="24691A31N1")


class AttendanceCheckRequest(BaseModel):
    roll_number: str = Field(..., min_length=5, max_length=15, description="MITS student roll number (e.g. 24691A31N1)")
    password: str = Field(..., min_length=1, max_length=100, description="MITS student portal password")



@router.post("/check", summary="Check official MITS student attendance")
def check_attendance(payload: AttendanceCheckRequest):
    """
    Securely query student attendance from the official MITS student system.
    Password is used only for real-time verification and is never persisted or logged.
    """
    service = OfficialAttendanceService()
    try:
        result = service.fetch_attendance(
            roll_number=payload.roll_number,
            password=payload.password
        )
        return result
    except AttendanceAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc)
        )
    except AttendancePortalUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        )
    except AttendanceMalformedResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc)
        )
    except AttendanceIntegrationError as exc:
        raise HTTPException(
            status_code=exc.status_code if hasattr(exc, "status_code") else status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during attendance check: {str(exc)}"
        )
