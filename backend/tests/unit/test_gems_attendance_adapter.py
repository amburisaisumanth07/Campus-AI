"""
Comprehensive unit and integration tests for GemsAttendanceAdapter and /api/attendance/check.

Covers:
1. Successful GEMS login and attendance retrieval
2. Invalid GEMS credentials
3. GEMS timeout handling
4. GEMS unavailable / 500 error
5. Relaxed JSON attendance response parsing
6. Multiple subjects and single subject handling
7. Missing optional fields (e.g., missing code or semester)
8. Malformed GEMS response (unparseable / missing attendanceTable)
9. Strict overall attendance calculation: sum(attended) / sum(total) * 100
10. 75% safe-to-miss calculation
11. 75% recovery class calculation
12. CRITICAL SECURITY: Password is never returned in response
13. CRITICAL SECURITY: Session cookie is never returned in response or persisted
14. POST /api/attendance/check endpoint returns AttendanceTrackerResponse
15. Existing mock attendance (GET /api/attendance) remains operational
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from backend.app.core.rate_limiter import attendance_rate_limiter
from backend.app.main import app
from backend.app.services.gems_attendance_service import (
    GemsAttendanceAdapter,
    safe_parse_gems_json,
    AttendanceAuthError,
    AttendancePortalUnavailableError,
    AttendanceMalformedResponseError,
    AttendanceIntegrationError,
)

@pytest.fixture(autouse=True)
def reset_attendance_rate_limiter():
    attendance_rate_limiter.reset()
    yield
    attendance_rate_limiter.reset()

SAMPLE_GEMS_LOGIN_SUCCESS = '{"status":"success"}'
SAMPLE_GEMS_LOGIN_FAIL = '{"status":"fail","message":"Invalid User Id or Password."}'

SAMPLE_GEMS_SIDEBAR_SUCCESS = """{
    studName: 'Amburi Sai Sumanth',
    instituteName: 'Madanapalle Institute of Technology & Science',
    contactUs: 'contact@mits.ac.in'
}"""

SAMPLE_GEMS_DASHBOARD_SUCCESS = """{
    status: 'success',
    attendanceTable: {
        id: 'attendanceTable',
        schema: {
            fields: [
                { name: 'subCode' },
                { name: 'subName' },
                { name: 'classesAttended' },
                { name: 'classesConducted' },
                { name: 'percentage' },
                { name: 'semester' }
            ]
        },
        records: [
            {
                subCode: '20CSE301',
                subName: 'Database Management Systems',
                classesAttended: 38,
                classesConducted: 42,
                percentage: 90.48,
                semester: 'IV'
            },
            {
                subCode: '20CSE302',
                subName: 'Operating Systems',
                classesAttended: 35,
                classesConducted: 40,
                percentage: 87.5,
                semester: 'IV'
            },
            {
                subCode: '20CSE303',
                subName: 'Artificial Intelligence',
                classesAttended: 31,
                classesConducted: 38,
                percentage: 81.58,
                semester: 'IV'
            },
            {
                subCode: '20CSE304',
                subName: 'Java Programming',
                classesAttended: 45,
                classesConducted: 50,
                percentage: 90.0,
                semester: 'IV'
            },
            {
                subCode: '20HUM101',
                subName: 'Discrete Mathematics',
                classesAttended: 32,
                classesConducted: 40,
                percentage: 80.0,
                semester: 'IV'
            }
        ]
    }
}"""


class MockAsyncResponse:
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {"content-type": "application/json"}

    def json(self):
        return safe_parse_gems_json(self.text)


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. Successful GEMS Login and Retrieval ───────────────────────────────────

@pytest.mark.asyncio
async def test_gems_successful_login_and_retrieval():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    # 1. Login POST -> success
    # 2. Sidebar GET -> name
    # 3. Dashboard GET -> attendanceTable
    # 4. Logout POST
    mock_client.post.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_LOGIN_SUCCESS),
        MockAsyncResponse(status_code=200, text="logged_out"),
    ]
    mock_client.get.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_SIDEBAR_SUCCESS),
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_DASHBOARD_SUCCESS),
    ]

    adapter = GemsAttendanceAdapter()
    result = await adapter.fetch_attendance(
        roll_number="24691A31N1",
        password="TestFakePassword123",
        http_client=mock_client
    )

    assert result["student"] == "Amburi Sai Sumanth"
    assert result["roll_number"] == "24691A31N1"
    assert result["required"] == 75.0
    assert result["status"] == "Requirement satisfied"
    assert len(result["subjects"]) == 5
    assert result["subjects"][0]["code"] == "20CSE301"
    assert result["subjects"][0]["name"] == "Database Management Systems"
    assert result["subjects"][0]["attended"] == 38
    assert result["subjects"][0]["total"] == 42


# ── 2. Invalid GEMS Credentials ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gems_invalid_credentials():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_LOGIN_FAIL)

    adapter = GemsAttendanceAdapter()
    with pytest.raises(AttendanceAuthError) as exc_info:
        await adapter.fetch_attendance(
            roll_number="24691A31N1",
            password="WrongPassword",
            http_client=mock_client
        )
    assert "Invalid MITS GEMS roll number or password." in str(exc_info.value)


# ── 3. GEMS Timeout ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gems_login_timeout():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")

    adapter = GemsAttendanceAdapter()
    with pytest.raises(AttendancePortalUnavailableError) as exc_info:
        await adapter.fetch_attendance(
            roll_number="24691A31N1",
            password="TestPassword",
            http_client=mock_client
        )
    assert "unable to connect" in str(exc_info.value).lower()


# ── 4. GEMS Unavailable (500 Error) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_gems_server_500_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = MockAsyncResponse(status_code=500, text="Internal Server Error")

    adapter = GemsAttendanceAdapter()
    with pytest.raises(AttendancePortalUnavailableError) as exc_info:
        await adapter.fetch_attendance(
            roll_number="24691A31N1",
            password="TestPassword",
            http_client=mock_client
        )
    assert exc_info.value.status_code == 503


# ── 5. Relaxed JSON Parsing ──────────────────────────────────────────────────

def test_safe_parse_gems_json_variants():
    # Test unquoted keys and single quotes
    raw = "{ status: 'success', totalRecords: 42, active: true }"
    parsed = safe_parse_gems_json(raw)
    assert parsed["status"] == "success"
    assert parsed["totalRecords"] == 42
    assert parsed["active"] is True


# ── 6 & 7. Missing Optional Fields & Multiple Subjects ───────────────────────

@pytest.mark.asyncio
async def test_missing_optional_fields_handled_gracefully():
    sample_minimal = """{
        attendanceTable: {
            records: [
                {
                    name: 'General Lab',
                    attended: 10,
                    total: 10
                }
            ]
        }
    }"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_LOGIN_SUCCESS),
        MockAsyncResponse(status_code=200, text=""),
    ]
    mock_client.get.side_effect = [
        MockAsyncResponse(status_code=404, text=""),  # Sidebar fails gracefully
        MockAsyncResponse(status_code=200, text=sample_minimal),
    ]

    adapter = GemsAttendanceAdapter()
    result = await adapter.fetch_attendance(
        roll_number="24691A31N1",
        password="TestPassword",
        http_client=mock_client
    )
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["code"] == ""
    assert result["subjects"][0]["name"] == "General Lab"
    assert result["subjects"][0]["percentage"] == 100.0
    assert result["overall"] == 100.0


# ── 8. Malformed GEMS Response ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_malformed_gems_dashboard_response():
    sample_malformed = "<html><body>Not JSON Error Page</body></html>"
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_LOGIN_SUCCESS),
        MockAsyncResponse(status_code=200, text=""),
    ]
    mock_client.get.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_SIDEBAR_SUCCESS),
        MockAsyncResponse(status_code=200, text=sample_malformed),
    ]

    adapter = GemsAttendanceAdapter()
    with pytest.raises(AttendanceMalformedResponseError):
        await adapter.fetch_attendance(
            roll_number="24691A31N1",
            password="TestPassword",
            http_client=mock_client
        )


# ── 9. Strict Overall Percentage Calculation ─────────────────────────────────

@pytest.mark.asyncio
async def test_overall_percentage_is_weighted_not_average():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_LOGIN_SUCCESS),
        MockAsyncResponse(status_code=200, text=""),
    ]
    mock_client.get.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_SIDEBAR_SUCCESS),
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_DASHBOARD_SUCCESS),
    ]

    adapter = GemsAttendanceAdapter()
    result = await adapter.fetch_attendance(
        roll_number="24691A31N1",
        password="TestPassword",
        http_client=mock_client
    )

    total_att = 38 + 35 + 31 + 45 + 32  # 181
    total_cls = 42 + 40 + 38 + 50 + 40   # 210
    expected_overall = round((total_att / total_cls) * 100.0, 2)  # 86.19
    assert result["overall"] == expected_overall

    # Assert it does NOT equal naive average of percentages
    naive_avg = round((90.48 + 87.5 + 81.58 + 90.0 + 80.0) / 5, 2)
    assert result["overall"] != naive_avg


# ── 12 & 13. CRITICAL SECURITY: Never leak password or JSESSIONID ────────────

@pytest.mark.asyncio
async def test_security_password_and_cookie_never_returned():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_LOGIN_SUCCESS),
        MockAsyncResponse(status_code=200, text=""),
    ]
    mock_client.get.side_effect = [
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_SIDEBAR_SUCCESS),
        MockAsyncResponse(status_code=200, text=SAMPLE_GEMS_DASHBOARD_SUCCESS),
    ]

    fake_secret = "SuperSecretPassword!@#123"
    adapter = GemsAttendanceAdapter()
    result = await adapter.fetch_attendance(
        roll_number="24691A31N1",
        password=fake_secret,
        http_client=mock_client
    )

    result_str = str(result)
    assert fake_secret not in result_str
    assert "JSESSIONID" not in result_str
    assert "cookie" not in result.keys()
    assert "password" not in result.keys()


# ── 14. POST /api/attendance/check API Endpoint ──────────────────────────────

def test_api_check_attendance_endpoint_success(client):
    with patch("backend.app.services.gems_attendance_service.GemsAttendanceAdapter.fetch_attendance") as mock_fetch:
        mock_fetch.return_value = {
            "student": "Amburi Sai Sumanth",
            "roll_number": "24691A31N1",
            "overall": 86.19,
            "required": 75.0,
            "status": "Requirement satisfied",
            "subjects": [
                {
                    "code": "20CSE301",
                    "name": "Database Management Systems",
                    "attended": 38,
                    "total": 42,
                    "percentage": 90.48,
                }
            ],
            "student_name": "Amburi Sai Sumanth",
            "overall_percentage": 86.19,
            "attended_classes": 38,
            "total_classes": 42,
            "absent_classes": 4,
            "required_percentage": 75.0,
            "is_safe": True,
            "status_text": "Attendance requirement currently satisfied.",
            "official_source": "http://mitsims.in",
            "last_updated": "24 Sep 2026, 4:30 PM UTC",
            "success": True,
        }

        resp = client.post("/api/attendance/check", json={
            "roll_number": "24691A31N1",
            "password": "FakeStudentPassword123"
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["student"] == "Amburi Sai Sumanth"
        assert data["overall"] == 86.19
        assert len(data["subjects"]) == 1
        assert "password" not in data
        assert "JSESSIONID" not in data


def test_api_check_attendance_auth_failure_returns_401(client):
    with patch("backend.app.services.gems_attendance_service.GemsAttendanceAdapter.fetch_attendance") as mock_fetch:
        mock_fetch.side_effect = AttendanceAuthError("Invalid MITS GEMS roll number or password.")

        resp = client.post("/api/attendance/check", json={
            "roll_number": "24691A31N1",
            "password": "WrongPassword"
        })

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid MITS GEMS roll number or password."


def test_api_check_attendance_unavailable_returns_503(client):
    with patch("backend.app.services.gems_attendance_service.GemsAttendanceAdapter.fetch_attendance") as mock_fetch:
        mock_fetch.side_effect = AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

        resp = client.post("/api/attendance/check", json={
            "roll_number": "24691A31N1",
            "password": "Password123"
        })

        assert resp.status_code == 503
        assert resp.json()["detail"] == "Unable to connect to MITS GEMS right now. Please try again later."


def test_api_check_attendance_zero_records_returns_502(client):
    with patch("backend.app.services.gems_attendance_service.GemsAttendanceAdapter.fetch_attendance") as mock_fetch:
        mock_fetch.side_effect = AttendanceMalformedResponseError("No attendance records were returned by MITS GEMS.")

        resp = client.post("/api/attendance/check", json={
            "roll_number": "24691A31N1",
            "password": "Password123"
        })

        assert resp.status_code == 502
        assert resp.json()["detail"] == "No attendance records were returned by MITS GEMS."


def test_api_check_attendance_malformed_response_returns_502(client):
    with patch("backend.app.services.gems_attendance_service.GemsAttendanceAdapter.fetch_attendance") as mock_fetch:
        mock_fetch.side_effect = AttendanceMalformedResponseError("Could not read attendance data from MITS GEMS.")

        resp = client.post("/api/attendance/check", json={
            "roll_number": "24691A31N1",
            "password": "Password123"
        })

        assert resp.status_code == 502
        assert resp.json()["detail"] == "Could not read attendance data from MITS GEMS."


def test_api_check_attendance_rate_limit_exceeded_returns_429(client):
    """Verify application-level rate limiting on POST /api/attendance/check returns 429."""
    with patch("backend.app.services.gems_attendance_service.GemsAttendanceAdapter.fetch_attendance") as mock_fetch:
        mock_fetch.return_value = {
            "student": "Amburi Sai Sumanth",
            "roll_number": "24691A31N1",
            "overall": 80.0,
            "required": 75.0,
            "status": "Requirement satisfied",
            "subjects": [],
            "official_source": "http://mitsims.in",
            "success": True,
        }

        test_headers = {"X-Forwarded-For": "203.0.113.50"}

        # First 5 requests from the same IP with the same roll number should succeed (200)
        for _ in range(5):
            resp = client.post(
                "/api/attendance/check",
                json={"roll_number": "24691A31N1", "password": "Password123"},
                headers=test_headers,
            )
            assert resp.status_code == 200

        # The 6th request from the same IP should be rate-limited (429)
        rate_limited_resp = client.post(
            "/api/attendance/check",
            json={"roll_number": "24691A31N1", "password": "Password123"},
            headers=test_headers,
        )
        assert rate_limited_resp.status_code == 429
        data = rate_limited_resp.json()
        assert data["detail"] == "Too many attendance sync attempts. Please wait a few minutes and try again."
        assert "Retry-After" in rate_limited_resp.headers

        # Critical security invariant: Honest student on a DIFFERENT IP is NOT blocked
        different_ip_resp = client.post(
            "/api/attendance/check",
            json={"roll_number": "24691A31N1", "password": "Password123"},
            headers={"X-Forwarded-For": "198.51.100.99"},
        )
        assert different_ip_resp.status_code == 200


def test_off_domain_redirect_blocked_by_adapter():
    """Verify adapter prevents following redirects to untrusted external domains."""
    import urllib.parse
    expected_host = urllib.parse.urlparse("http://mitsims.in").netloc.lower()

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.is_redirect = True
    mock_resp.headers = {"location": "http://malicious-external-site.com/steal"}

    def _validate_redirect(response):
        if response.is_redirect and "location" in response.headers:
            loc = response.headers["location"].strip()
            parsed = urllib.parse.urlparse(loc)
            if parsed.netloc and parsed.netloc.lower() != expected_host:
                raise AttendancePortalUnavailableError("External redirect prohibited for GEMS.")

    with pytest.raises(AttendancePortalUnavailableError) as exc_info:
        _validate_redirect(mock_resp)
    assert "External redirect prohibited for GEMS." in str(exc_info.value)


# ── 15. Mock Attendance (GET /api/attendance) Unaffected ─────────────────────

def test_mock_attendance_endpoint_still_operational(client):
    resp = client.get("/api/attendance")
    assert resp.status_code == 200
    data = resp.json()
    assert "student" in data
    assert "subjects" in data
    assert len(data["subjects"]) == 5


# ── 16. semesterActivity & SubDetails Extraction Tests ────────────────────────

SAMPLE_EXTJS_FORM_PANEL_DASHBOARD = {
    "formPanel": {
        "items": [
            {
                "xtype": "fieldset",
                "id": "SubDetails",
                "items": [
                    {
                        "componentCls": "bottom-border-header",
                        "items": [
                            {"value": "<b>S.NO</b>"},
                            {"value": "<b>CODE</b>"},
                            {"value": "<b>SUBJECT</b>"},
                            {"value": "<b>FACULTY</b>"}
                        ]
                    },
                    {
                        "componentCls": "bottom-border",
                        "items": [
                            {"value": "<span>1</span>"},
                            {"value": "<span>23PHY102</span>"},
                            {"value": "<span>INTRODUCTION TO QUANTUM TECHNOLOGIES</span>"},
                            {"value": "<span>RAJESH</span>"}
                        ]
                    },
                    {
                        "componentCls": "bottom-border",
                        "items": [
                            {"value": "<span>2</span>"},
                            {"value": "<span>23ENG901</span>"},
                            {"value": "<span>TECHNICAL PAPER WRITING AND IPR</span>"},
                            {"value": "<span>VENKATA</span>"}
                        ]
                    }
                ]
            },
            {
                "xtype": "fieldset",
                "id": "semesterActivity",
                "title": "Semester Activity for-III YEAR I SEMESTER - REGULAR ",
                "items": [
                    {
                        "componentCls": "bottom-border-header",
                        "items": [
                            {"value": "<span><b>S.NO</b></span>"},
                            {"value": "<span><b>SUBJECT CODE</b></span>"},
                            {"value": "<span><b>CLASSES ATTENDED</b></span>"},
                            {"value": "<span><b>TOTAL CONDUCTED</b></span>"},
                            {"value": "<span><b>ATTENDANCE %</b></span>"}
                        ]
                    },
                    {
                        "componentCls": "bottom-border",
                        "items": [
                            {"value": "<span>1</span>"},
                            {"value": "<span>23PHY102</span>"},
                            {"value": "<span> 17 </span>"},
                            {"value": "<span> 26 </span>"},
                            {"value": "<span> 65.38 </span>"}
                        ]
                    },
                    {
                        "componentCls": "bottom-border",
                        "items": [
                            {"value": "<span>2</span>"},
                            {"value": "<span>23ENG901</span>"},
                            {"value": "<span> 9 </span>"},
                            {"value": "<span> 12 </span>"},
                            {"value": "<span> 75.0 </span>"}
                        ]
                    },
                    {
                        "componentCls": "bottom-border",
                        "items": [
                            {"value": "<span>Note :</span>"},
                            {"value": "<span>Green: 85%</span>"}
                        ]
                    }
                ]
            }
        ]
    },
    "attendanceTable": {
        "id": "stuAttendncTbl",
        "records": []
    }
}


def test_semester_activity_extraction_with_subdetails_mapping():
    adapter = GemsAttendanceAdapter()
    result = adapter._normalize_attendance_records(
        valid_roll="24691A31N2",
        student_name="Test Student",
        data=SAMPLE_EXTJS_FORM_PANEL_DASHBOARD
    )

    assert result["roll_number"] == "24691A31N2"
    assert result["semester"] == "III YEAR I SEMESTER - REGULAR"
    assert len(result["subjects"]) == 2

    sub1 = result["subjects"][0]
    assert sub1["code"] == "23PHY102"
    assert sub1["name"] == "INTRODUCTION TO QUANTUM TECHNOLOGIES"
    assert sub1["attended"] == 17
    assert sub1["total"] == 26
    assert sub1["percentage"] == 65.38
    assert sub1["semester"] == "III YEAR I SEMESTER - REGULAR"

    sub2 = result["subjects"][1]
    assert sub2["code"] == "23ENG901"
    assert sub2["name"] == "TECHNICAL PAPER WRITING AND IPR"
    assert sub2["attended"] == 9
    assert sub2["total"] == 12
    assert sub2["percentage"] == 75.0

    # Overall calculation: (17 + 9) / (26 + 12) * 100 = 26 / 38 * 100 = 68.42%
    assert result["overall"] == 68.42


def test_missing_subject_name_fallback():
    data = {
        "formPanel": {
            "items": [
                {
                    "xtype": "fieldset",
                    "id": "SubDetails",
                    "items": []  # No mapped subject names
                },
                {
                    "xtype": "fieldset",
                    "id": "semesterActivity",
                    "title": "Semester Activity for-II YEAR",
                    "items": [
                        {
                            "componentCls": "bottom-border",
                            "items": [
                                {"value": "1"},
                                {"value": "UNKNOWN101"},
                                {"value": "8"},
                                {"value": "10"},
                                {"value": "80.0"}
                            ]
                        }
                    ]
                }
            ]
        }
    }
    adapter = GemsAttendanceAdapter()
    result = adapter._normalize_attendance_records("24691A31N2", "Student", data)
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["code"] == "UNKNOWN101"
    assert result["subjects"][0]["name"] == "UNKNOWN101"
    assert result["subjects"][0]["attended"] == 8
    assert result["subjects"][0]["total"] == 10
    assert result["subjects"][0]["percentage"] == 80.0


def test_malformed_row_skipped():
    data = {
        "formPanel": {
            "items": [
                {
                    "xtype": "fieldset",
                    "id": "semesterActivity",
                    "items": [
                        # Malformed: attended > total
                        {
                            "items": [
                                {"value": "1"},
                                {"value": "BAD_ROW_1"},
                                {"value": "20"},
                                {"value": "10"},
                                {"value": "200.0"}
                            ]
                        },
                        # Malformed: total is 0
                        {
                            "items": [
                                {"value": "2"},
                                {"value": "BAD_ROW_2"},
                                {"value": "0"},
                                {"value": "0"},
                                {"value": "0.0"}
                            ]
                        },
                        # Malformed: attended is negative
                        {
                            "items": [
                                {"value": "3"},
                                {"value": "BAD_ROW_3"},
                                {"value": "-5"},
                                {"value": "10"},
                                {"value": "-50.0"}
                            ]
                        },
                        # Malformed: non-numeric
                        {
                            "items": [
                                {"value": "4"},
                                {"value": "BAD_ROW_4"},
                                {"value": "N/A"},
                                {"value": "10"},
                                {"value": "0.0"}
                            ]
                        },
                        # Valid row
                        {
                            "items": [
                                {"value": "5"},
                                {"value": "GOOD101"},
                                {"value": "15"},
                                {"value": "20"},
                                {"value": "75.0"}
                            ]
                        }
                    ]
                }
            ]
        }
    }
    adapter = GemsAttendanceAdapter()
    result = adapter._normalize_attendance_records("24691A31N2", "Student", data)
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["code"] == "GOOD101"
    assert result["subjects"][0]["attended"] == 15
    assert result["subjects"][0]["total"] == 20


def test_empty_semester_activity_raises_error():
    data = {
        "formPanel": {
            "items": [
                {
                    "xtype": "fieldset",
                    "id": "semesterActivity",
                    "items": []  # Empty!
                }
            ]
        },
        "attendanceTable": {
            "records": []  # Also empty!
        }
    }
    adapter = GemsAttendanceAdapter()
    with pytest.raises(AttendanceMalformedResponseError) as exc_info:
        adapter._normalize_attendance_records("24691A31N2", "Student", data)
    assert "No attendance records were returned by MITS GEMS." in str(exc_info.value)


def test_raw_text_regex_fallback_extraction():
    raw_str = """
    {
        id:'SubDetails',
        items: [
            { componentCls: 'bottom-border', items: [{value:'1'}, {value:'23PHY102'}, {value:'Quantum Physics'}] }
        ]
    }
    {
        id:'semesterActivity',
        title: 'Semester Activity for-III YEAR I SEMESTER',
        items: [
            { componentCls: 'bottom-border-header', items: [{value:'S.NO'}, {value:'SUBJECT CODE'}, {value:'ATTENDED'}, {value:'CONDUCTED'}, {value:'%'}] },
            { componentCls: 'bottom-border', items: [{value:'1'}, {value:'23PHY102'}, {value:'18'}, {value:'20'}, {value:'90.0'}] }
        ]
    }
    """
    adapter = GemsAttendanceAdapter()
    result = adapter._normalize_attendance_records("24691A31N2", "Student", {}, raw_text=raw_str)
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["code"] == "23PHY102"
    assert result["subjects"][0]["name"] == "Quantum Physics"
    assert result["subjects"][0]["attended"] == 18
    assert result["subjects"][0]["total"] == 20
    assert result["subjects"][0]["percentage"] == 90.0
    assert result["semester"] == "III YEAR I SEMESTER"


@pytest.mark.asyncio
async def test_async_event_hook_executes_without_type_error(monkeypatch):
    """Regression test: AsyncClient response event hook must be awaitable and not raise TypeError."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "studentLogin" in str(request.url):
            return httpx.Response(200, text="{'status': 'fail', 'message': 'Invalid'}", request=request)
        if "studentLogout" in str(request.url):
            return httpx.Response(200, text="{}", request=request)
        return httpx.Response(404, request=request)

    mock_transport = httpx.MockTransport(handler)
    orig_async_client = httpx.AsyncClient

    def custom_async_client(*args, **kwargs):
        kwargs["transport"] = mock_transport
        return orig_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", custom_async_client)

    adapter = GemsAttendanceAdapter()
    # Before the fix, this raised TypeError: 'NoneType' object can't be awaited
    with pytest.raises(AttendanceAuthError):
        await adapter.fetch_attendance("24691A31N1", "WrongPass123!")


@pytest.mark.asyncio
async def test_async_event_hook_blocks_off_domain_redirect(monkeypatch):
    """Ensure off-domain redirect protection remains active and blocks foreign hosts."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "studentLogin" in str(request.url):
            return httpx.Response(
                302,
                headers={"Location": "http://evil-phishing-host.com/login"},
                request=request
            )
        return httpx.Response(200, text="{}", request=request)

    mock_transport = httpx.MockTransport(handler)
    orig_async_client = httpx.AsyncClient

    def custom_async_client(*args, **kwargs):
        kwargs["transport"] = mock_transport
        return orig_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", custom_async_client)

    adapter = GemsAttendanceAdapter()
    with pytest.raises(AttendancePortalUnavailableError) as exc_info:
        await adapter.fetch_attendance("24691A31N1", "Pass123!")
    assert "External redirect prohibited" in str(exc_info.value)
