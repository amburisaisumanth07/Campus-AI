"""
API router for Official MITS Student Attendance.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.core.rate_limiter import attendance_rate_limiter, get_client_ip
from backend.app.core.security import decode_access_token
from backend.app.db.models import User
from backend.app.schemas.mits_entities import AttendanceTrackerResponse
from backend.app.services.attendance_service import (
    AttendanceIntegrationError,
    AttendanceAuthError,
    AttendancePortalUnavailableError,
    AttendanceMalformedResponseError,
    get_mock_attendance_data,
)
from backend.app.services.gems_attendance_service import GemsAttendanceAdapter

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
    roll_number: str = Field(..., min_length=2, max_length=20, description="MITS student roll number (e.g. 24691A31N1)")
    password: str = Field(..., min_length=1, max_length=100, description="MITS student portal password")



@router.post("/check", response_model=AttendanceTrackerResponse, summary="Check official MITS student attendance")
async def check_attendance(
    payload: AttendanceCheckRequest,
    request: Request,
):
    """
    Securely query student attendance from the official MITS student system (GEMS).
    Password is used only for real-time verification and is never persisted or logged.
    Protected by application-level rate limiting against brute-force attempts.
    """
    client_ip = get_client_ip(request)
    attendance_rate_limiter.check(client_ip=client_ip, roll_number=payload.roll_number)

    adapter = GemsAttendanceAdapter()
    try:
        result = await adapter.fetch_attendance(
            roll_number=payload.roll_number,
            password=payload.password
        )
        return result
    except AttendanceAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MITS GEMS roll number or password."
        )
    except AttendancePortalUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to connect to MITS GEMS right now. Please try again later."
        )
    except AttendanceMalformedResponseError as exc:
        msg = str(exc).lower()
        if "no attendance records" in msg or "returned no" in msg:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No attendance records were returned by MITS GEMS."
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not read attendance data from MITS GEMS."
        )
    except AttendanceIntegrationError as exc:
        err_type = getattr(exc, "error_type", "")
        if err_type in ("INVALID_ROLL_NUMBER", "MISSING_PASSWORD", "MISSING_ROLL_NUMBER"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not read attendance data from MITS GEMS."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not read attendance data from MITS GEMS."
        )
