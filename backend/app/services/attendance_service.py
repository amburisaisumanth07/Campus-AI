"""
Official MITS Attendance Service.

Interacts with the official MITS Student Information / Attendance Portal
(https://studentportal.universitysolutions.in/) to retrieve verified student attendance.

Security Rules:
- NEVER log or persist student passwords in plaintext, database, or logs.
- HTTPS only.
- Strict session lifecycle management.
- If the official portal is unreachable or requires interactive CAPTCHA/MFA,
  gracefully report that the official integration is unavailable without fabricating data.
"""
from datetime import datetime, timezone
import re
from typing import Dict, Any, Optional, List
import httpx

from backend.app.core.logging import logger

OFFICIAL_MITS_STUDENT_PORTAL = "https://studentportal.universitysolutions.in/"
OFFICIAL_MITS_EXAM_PORTAL = "https://mits.ac.in/university-exam"
MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE = 75.0


class AttendanceIntegrationError(Exception):
    """Base exception for attendance integration failures."""
    def __init__(self, message: str, error_type: str = "INTEGRATION_ERROR", status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code


class AttendanceAuthError(AttendanceIntegrationError):
    """Raised when official portal rejects credentials."""
    def __init__(self, message: str = "Invalid MITS student credentials."):
        super().__init__(message, error_type="AUTH_FAILED", status_code=401)


class AttendancePortalUnavailableError(AttendanceIntegrationError):
    """Raised when official portal is unreachable, timed out, or blocked."""
    def __init__(self, message: str = "Official attendance integration is currently unavailable."):
        super().__init__(message, error_type="PORTAL_UNAVAILABLE", status_code=503)


class AttendanceMalformedResponseError(AttendanceIntegrationError):
    """Raised when official portal returns unparseable or malformed data."""
    def __init__(self, message: str = "Official attendance portal returned an unparseable response."):
        super().__init__(message, error_type="MALFORMED_RESPONSE", status_code=502)


class OfficialAttendanceService:
    """Official MITS Student Attendance Integrator."""

    def __init__(self, base_url: str = OFFICIAL_MITS_STUDENT_PORTAL, timeout_seconds: float = 12.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    def validate_roll_number(self, roll_number: str) -> str:
        """Validate and normalize MITS student roll number format (e.g., 24691A31N1, 21691A0501)."""
        cleaned = roll_number.strip().upper()
        # MITS Roll number pattern: standard 10-character alphanumeric pattern
        if not re.match(r"^[0-9]{2}[0-9A-Z]{8}$", cleaned):
            raise AttendanceIntegrationError(
                "Invalid MITS roll number format. Roll numbers typically follow the standard 10-character pattern (e.g. 24691A31N1).",
                error_type="INVALID_ROLL_NUMBER",
                status_code=400
            )
        return cleaned

    def fetch_attendance(
        self,
        roll_number: str,
        password: str,
        http_client: Optional[httpx.Client] = None
    ) -> Dict[str, Any]:
        """
        Securely query the official MITS attendance system.
        Password is never logged, stored, or forwarded to third parties.
        """
        valid_roll = self.validate_roll_number(roll_number)
        if not password or len(password.strip()) == 0:
            raise AttendanceIntegrationError(
                "Student password is required.",
                error_type="MISSING_PASSWORD",
                status_code=400
            )

        # SECURITY: Log only sanitized roll number, never the password
        logger.info(f"[ATTENDANCE_QUERY] Initiating attendance check for roll_number={valid_roll}")

        client_provided = http_client is not None
        client = http_client or httpx.Client(timeout=self.timeout, follow_redirects=True)

        try:
            login_url = f"{self.base_url}/login"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CampusAI/1.0",
                "Referer": self.base_url,
                "Origin": self.base_url,
            }
            payload = {
                "username": valid_roll,
                "password": password,
            }

            try:
                login_resp = client.post(login_url, data=payload, headers=headers)
            except httpx.TimeoutException:
                logger.warning(f"[ATTENDANCE_TIMEOUT] Official portal timed out for roll_number={valid_roll}")
                raise AttendancePortalUnavailableError(
                    "Official attendance integration is currently unavailable. The official MITS student portal timed out."
                )
            except httpx.RequestError as exc:
                logger.warning(f"[ATTENDANCE_CONN_ERR] Official portal connection failed: {type(exc).__name__}")
                raise AttendancePortalUnavailableError(
                    "Official attendance integration is currently unavailable. Unable to establish secure connection to the official MITS student portal."
                )

            if login_resp.status_code in (401, 403):
                raise AttendanceAuthError("Invalid MITS roll number or password.")

            if login_resp.status_code >= 500:
                raise AttendancePortalUnavailableError(
                    "Official attendance integration is currently unavailable. The official MITS server returned an internal server error."
                )

            body_text = login_resp.text
            if "invalid username" in body_text.lower() or "invalid password" in body_text.lower() or "incorrect password" in body_text.lower():
                raise AttendanceAuthError("Invalid MITS roll number or password.")

            if "captcha" in body_text.lower() and ("enter captcha" in body_text.lower() or "g-recaptcha" in body_text.lower()):
                raise AttendancePortalUnavailableError(
                    f"Official attendance integration is currently unavailable. The official MITS student portal requires interactive visual verification (CAPTCHA). Please check directly at {self.base_url}"
                )

            try:
                content_type = login_resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = login_resp.json()
                    return self._parse_json_attendance(valid_roll, data)
                else:
                    return self._parse_html_attendance(valid_roll, body_text)
            except AttendanceIntegrationError:
                raise
            except Exception as exc:
                logger.error(f"[ATTENDANCE_PARSE_ERR] Malformed response from official portal: {exc}")
                raise AttendanceMalformedResponseError(
                    "Official attendance portal returned an unparseable response."
                )

        finally:
            if not client_provided:
                client.close()

    def _parse_json_attendance(self, roll_number: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse structured JSON from official API."""
        if not isinstance(data, dict):
            raise AttendanceMalformedResponseError("JSON response from official portal is not an object.")

        if data.get("error"):
            raise AttendanceIntegrationError(str(data["error"]), error_type="PORTAL_ERROR")

        student_name = data.get("student_name") or data.get("name") or "MITS Student"
        overall = float(data.get("overall_percentage") or 0.0)
        attended = int(data.get("attended_classes") or 0)
        total = int(data.get("total_classes") or 0)
        absent = total - attended if total >= attended else 0

        subjects = []
        raw_subs = data.get("subjects") or []
        for s in raw_subs:
            sub_attended = int(s.get("attended", 0))
            sub_total = int(s.get("total", 0))
            sub_pct = round((sub_attended / sub_total * 100), 1) if sub_total > 0 else 0.0
            subjects.append({
                "code": s.get("code") or "",
                "name": s.get("name") or s.get("subject_name") or "Subject",
                "attended": sub_attended,
                "total": sub_total,
                "percentage": sub_pct
            })

        is_safe = overall >= MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE
        status_text = (
            "Attendance requirement currently satisfied."
            if is_safe
            else "Attendance is below the required threshold."
        )

        return {
            "success": True,
            "student_name": student_name,
            "roll_number": roll_number,
            "overall_percentage": overall,
            "attended_classes": attended,
            "total_classes": total,
            "absent_classes": absent,
            "required_percentage": MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE,
            "is_safe": is_safe,
            "status_text": status_text,
            "subjects": subjects,
            "official_source": OFFICIAL_MITS_STUDENT_PORTAL,
            "last_updated": datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC"),
        }

    def _parse_html_attendance(self, roll_number: str, html: str) -> Dict[str, Any]:
        """Parse HTML table from official portal web interface."""
        if "overall" not in html.lower() and "attendance" not in html.lower():
            raise AttendanceMalformedResponseError("Official portal response does not contain attendance table.")

        raise AttendancePortalUnavailableError(
            f"Official attendance integration is currently unavailable. The portal at {OFFICIAL_MITS_STUDENT_PORTAL} requires interactive session access."
        )
