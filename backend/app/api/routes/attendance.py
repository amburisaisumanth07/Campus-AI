"""
API router for Official MITS Student Attendance.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.services.attendance_service import (
    OfficialAttendanceService,
    AttendanceIntegrationError,
    AttendanceAuthError,
    AttendancePortalUnavailableError,
    AttendanceMalformedResponseError,
)

router = APIRouter()


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
