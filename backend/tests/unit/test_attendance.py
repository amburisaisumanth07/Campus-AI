"""
Unit tests for the Official MITS Student Attendance Integration.
Verifies all error modes, security invariants, and successful attendance parsing:
- official authentication failure
- invalid credentials
- timeout
- official server unavailable
- malformed attendance response
- successful authentication
- successful attendance retrieval
- password never logged
- password never persisted
"""
import pytest
import httpx
from unittest.mock import MagicMock, patch
import logging

from backend.app.services.attendance_service import (
    OfficialAttendanceService,
    AttendanceIntegrationError,
    AttendanceAuthError,
    AttendancePortalUnavailableError,
    AttendanceMalformedResponseError,
    MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE,
)


class MockResponse:
    def __init__(self, status_code=200, text="", json_data=None, headers=None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self.headers = headers or {"content-type": "application/json"}

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise ValueError("No JSON data")


def test_invalid_roll_number_format():
    svc = OfficialAttendanceService()
    with pytest.raises(AttendanceIntegrationError) as exc_info:
        svc.fetch_attendance(roll_number="123", password="validpassword")
    assert exc_info.value.error_type == "INVALID_ROLL_NUMBER"
    assert exc_info.value.status_code == 400


def test_missing_password():
    svc = OfficialAttendanceService()
    with pytest.raises(AttendanceIntegrationError) as exc_info:
        svc.fetch_attendance(roll_number="24691A31N1", password="")
    assert exc_info.value.error_type == "MISSING_PASSWORD"
    assert exc_info.value.status_code == 400


def test_official_auth_failure_status_code():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(status_code=401, text="Unauthorized")

    svc = OfficialAttendanceService()
    with pytest.raises(AttendanceAuthError) as exc_info:
        svc.fetch_attendance(roll_number="24691A31N1", password="WrongPassword", http_client=mock_client)
    assert exc_info.value.status_code == 401
    assert "Invalid MITS" in str(exc_info.value)


def test_invalid_credentials_in_body_text():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(status_code=200, text="<html><body>Invalid username or password</body></html>")

    svc = OfficialAttendanceService()
    with pytest.raises(AttendanceAuthError) as exc_info:
        svc.fetch_attendance(roll_number="24691A31N1", password="WrongPassword", http_client=mock_client)
    assert exc_info.value.status_code == 401


def test_official_server_timeout():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.TimeoutException("Read timed out")

    svc = OfficialAttendanceService()
    with pytest.raises(AttendancePortalUnavailableError) as exc_info:
        svc.fetch_attendance(roll_number="24691A31N1", password="Password123", http_client=mock_client)
    assert exc_info.value.status_code == 503
    assert "timed out" in str(exc_info.value)


def test_official_server_unavailable_status_500():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(status_code=503, text="Service Unavailable")

    svc = OfficialAttendanceService()
    with pytest.raises(AttendancePortalUnavailableError) as exc_info:
        svc.fetch_attendance(roll_number="24691A31N1", password="Password123", http_client=mock_client)
    assert exc_info.value.status_code == 503
    assert "unavailable" in str(exc_info.value).lower()


def test_official_server_connection_failure():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("Failed to resolve host")

    svc = OfficialAttendanceService()
    with pytest.raises(AttendancePortalUnavailableError) as exc_info:
        svc.fetch_attendance(roll_number="24691A31N1", password="Password123", http_client=mock_client)
    assert exc_info.value.status_code == 503


def test_malformed_attendance_response_invalid_json():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        json_data=["not", "a", "dictionary"]
    )

    svc = OfficialAttendanceService()
    with pytest.raises(AttendanceMalformedResponseError) as exc_info:
        svc.fetch_attendance(roll_number="24691A31N1", password="Password123", http_client=mock_client)
    assert exc_info.value.status_code == 502


def test_successful_attendance_retrieval_and_threshold_verification():
    mock_data = {
        "student_name": "Amburi Sai Sumanth",
        "overall_percentage": 82.5,
        "attended_classes": 165,
        "total_classes": 200,
        "subjects": [
            {"code": "20CS101", "name": "DBMS", "attended": 38, "total": 42},
            {"code": "20CS102", "name": "Operating Systems", "attended": 35, "total": 40},
            {"code": "20CS103", "name": "Artificial Intelligence", "attended": 31, "total": 38}
        ]
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        json_data=mock_data
    )

    svc = OfficialAttendanceService()
    result = svc.fetch_attendance(roll_number="24691A31N1", password="SecretPassword123", http_client=mock_client)

    assert result["success"] is True
    assert result["student_name"] == "Amburi Sai Sumanth"
    assert result["roll_number"] == "24691A31N1"
    assert result["overall_percentage"] == 82.5
    assert result["attended_classes"] == 165
    assert result["total_classes"] == 200
    assert result["absent_classes"] == 35
    assert result["required_percentage"] == MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE
    assert result["is_safe"] is True
    assert "satisfied" in result["status_text"].lower()
    assert len(result["subjects"]) == 3
    assert result["subjects"][0]["percentage"] == 90.5


def test_attendance_below_required_threshold():
    mock_data = {
        "student_name": "Test Student",
        "overall_percentage": 68.0,
        "attended_classes": 68,
        "total_classes": 100,
        "subjects": [
            {"code": "20CS101", "name": "Mathematics", "attended": 25, "total": 40}
        ]
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        json_data=mock_data
    )

    svc = OfficialAttendanceService()
    result = svc.fetch_attendance(roll_number="24691A31N1", password="SecretPassword123", http_client=mock_client)

    assert result["overall_percentage"] == 68.0
    assert result["is_safe"] is False
    assert "below" in result["status_text"].lower()


def test_password_never_logged(caplog):
    caplog.set_level(logging.INFO)
    sensitive_pwd = "SuperSecretStudentPassword@999"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(status_code=401, text="Unauthorized")

    svc = OfficialAttendanceService()
    try:
        svc.fetch_attendance(roll_number="24691A31N1", password=sensitive_pwd, http_client=mock_client)
    except Exception:
        pass

    # Invariant: the password string must NEVER appear in any log output
    log_text = caplog.text
    assert sensitive_pwd not in log_text
    assert "24691A31N1" in log_text  # Roll number is allowed in audit log


def test_password_never_persisted():
    sensitive_pwd = "TopSecretStudentPassword!123"
    mock_data = {
        "student_name": "Test Student",
        "overall_percentage": 85.0,
        "attended_classes": 85,
        "total_classes": 100,
        "subjects": []
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MockResponse(
        status_code=200,
        headers={"content-type": "application/json"},
        json_data=mock_data
    )

    svc = OfficialAttendanceService()
    result = svc.fetch_attendance(roll_number="24691A31N1", password=sensitive_pwd, http_client=mock_client)

    # Invariant 1: password is never saved in service instance attributes
    for key, value in svc.__dict__.items():
        assert sensitive_pwd not in str(value)
        assert sensitive_pwd not in str(key)

    # Invariant 2: password is never present in returned dictionary keys or values
    assert sensitive_pwd not in str(result)

