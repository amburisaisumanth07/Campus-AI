"""
Unit and integration tests for the CampusAI Attendance Tracker.
Covers:
1. Attendance endpoint returns 200 with proper structure.
2. Overall attendance is calculated correctly.
3. Subject percentages are correct.
4. Overall percentage uses total attended / total classes (not averaging subject percentages).
5. >=75 status ("Requirement satisfied").
6. 65-74 status ("Conditionally eligible").
7. <65 status ("Critical").
8. Bunk (classes can miss) calculation.
9. Required-class calculation.
10. Edge cases such as exactly 75%, 0 total classes, 100% attendance.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.attendance_service import (
    calculate_subject_percentage,
    calculate_overall_percentage,
    determine_attendance_status,
    calculate_classes_can_miss,
    calculate_classes_required,
    get_mock_attendance_data,
)


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. Attendance endpoint returns 200 ────────────────────────────────────────

def test_attendance_endpoint_returns_200(client):
    response = client.get("/api/attendance")
    assert response.status_code == 200
    data = response.json()
    assert "student" in data
    assert "roll_number" in data
    assert "overall" in data
    assert "required" in data
    assert "status" in data
    assert "subjects" in data
    assert isinstance(data["subjects"], list)
    assert len(data["subjects"]) == 5


# ── 2 & 3. Subject percentages and overall calculations are correct ───────────

def test_subject_percentages_are_correct():
    # DBMS: 38 / 42
    assert calculate_subject_percentage(38, 42) == 90.48
    # OS: 35 / 40
    assert calculate_subject_percentage(35, 40) == 87.5
    # AI: 31 / 38
    assert calculate_subject_percentage(31, 38) == 81.58
    # Java: 45 / 50
    assert calculate_subject_percentage(45, 50) == 90.0
    # Math: 32 / 40
    assert calculate_subject_percentage(32, 40) == 80.0


def test_overall_percentage_uses_total_attended_over_total_classes():
    subjects = [
        {"name": "DBMS", "attended": 38, "total": 42},
        {"name": "Operating Systems", "attended": 35, "total": 40},
        {"name": "Artificial Intelligence", "attended": 31, "total": 38},
        {"name": "Java", "attended": 45, "total": 50},
        {"name": "Mathematics", "attended": 32, "total": 40},
    ]
    total_attended = 38 + 35 + 31 + 45 + 32  # 181
    total_classes = 42 + 40 + 38 + 50 + 40   # 210
    expected_overall = round((total_attended / total_classes) * 100.0, 2)  # 86.19

    overall = calculate_overall_percentage(subjects)
    assert overall == expected_overall

    # Verify it does NOT equal the naive average of individual subject percentages
    individual_pcts = [calculate_subject_percentage(s["attended"], s["total"]) for s in subjects]
    naive_avg = round(sum(individual_pcts) / len(individual_pcts), 2)
    assert overall != naive_avg


def test_endpoint_overall_matches_formula(client):
    response = client.get("/api/attendance")
    assert response.status_code == 200
    data = response.json()
    subjects = data["subjects"]
    total_att = sum(s["attended"] for s in subjects)
    total_cls = sum(s["total"] for s in subjects)
    expected_overall = round((total_att / total_cls) * 100.0, 2)
    assert data["overall"] == expected_overall


# ── 5, 6, 7. Status classification ───────────────────────────────────────────

def test_status_classification_greater_or_equal_75():
    assert determine_attendance_status(75.0) == "Requirement satisfied"
    assert determine_attendance_status(86.67) == "Requirement satisfied"
    assert determine_attendance_status(100.0) == "Requirement satisfied"


def test_status_classification_65_to_74():
    assert determine_attendance_status(74.99) == "Conditionally eligible"
    assert determine_attendance_status(70.0) == "Conditionally eligible"
    assert determine_attendance_status(65.0) == "Conditionally eligible"


def test_status_classification_less_than_65():
    assert determine_attendance_status(64.99) == "Critical"
    assert determine_attendance_status(50.0) == "Critical"
    assert determine_attendance_status(0.0) == "Critical"


# ── 8. Bunk calculation (classes that can be missed) ─────────────────────────

def test_classes_can_miss_calculation():
    # Example: 38 attended out of 42 (90.48%). Required = 75%.
    # Formula: floor((100 * 38 - 75 * 42) / 75) = floor((3800 - 3150) / 75) = floor(650 / 75) = 8.
    assert calculate_classes_can_miss(38, 42, 75.0) == 8

    # Verify edge: with 8 missed, 38 / 50 = 76.0% (>= 75%).
    # With 9 missed, 38 / 51 = 74.5% (< 75%).
    assert (38 / (42 + 8)) * 100 >= 75.0
    assert (38 / (42 + 9)) * 100 < 75.0

    # Overall: 181 attended out of 210.
    # floor((18100 - 75 * 210) / 75) = floor(2350 / 75) = 31.
    assert calculate_classes_can_miss(181, 210, 75.0) == 31
    assert (181 / (210 + 31)) * 100 >= 75.0
    assert (181 / (210 + 32)) * 100 < 75.0


def test_classes_can_miss_returns_zero_when_below_required():
    # Current attendance: 60 attended out of 100 (60% < 75%).
    assert calculate_classes_can_miss(60, 100, 75.0) == 0


# ── 9. Required-class calculation (consecutive classes to reach 75%) ───────────

def test_classes_required_to_reach_75():
    # Current: 60 attended out of 100 (60% < 75%).
    # Formula: ceil((75 * 100 - 100 * 60) / (100 - 75)) = ceil((7500 - 6000) / 25) = 1500 / 25 = 60.
    assert calculate_classes_required(60, 100, 75.0) == 60
    # Verify: (60 + 60) / (100 + 60) = 120 / 160 = 75.0%.
    assert ((60 + 60) / (100 + 60)) * 100 >= 75.0
    assert ((60 + 59) / (100 + 59)) * 100 < 75.0

    # Current: 70 attended out of 100 (70%).
    # ceil((7500 - 7000) / 25) = 500 / 25 = 20.
    assert calculate_classes_required(70, 100, 75.0) == 20
    assert ((70 + 20) / (100 + 20)) * 100 >= 75.0


def test_classes_required_returns_zero_when_already_safe():
    # If already at 80% (32 / 40), 0 classes required to reach 75%.
    assert calculate_classes_required(32, 40, 75.0) == 0


# ── 10. Edge cases such as exactly 75% ────────────────────────────────────────

def test_edge_case_exactly_75_percent():
    # 75 attended out of 100 classes is exactly 75.0%.
    pct = calculate_subject_percentage(75, 100)
    assert pct == 75.0
    status = determine_attendance_status(75.0)
    assert status == "Requirement satisfied"

    # Exactly 75%: 0 classes can be missed!
    miss = calculate_classes_can_miss(75, 100, 75.0)
    assert miss == 0

    # Exactly 75%: 0 classes required to reach 75%.
    req = calculate_classes_required(75, 100, 75.0)
    assert req == 0


def test_edge_case_zero_classes_conducted():
    assert calculate_subject_percentage(0, 0) == 0.0
    assert calculate_overall_percentage([]) == 0.0
    assert calculate_classes_can_miss(0, 0, 75.0) == 0
    assert calculate_classes_required(0, 0, 75.0) == 0


def test_edge_case_100_percent():
    # 50 out of 50 attended
    assert calculate_subject_percentage(50, 50) == 100.0
    assert determine_attendance_status(100.0) == "Requirement satisfied"
    # Max miss: floor((5000 - 3750) / 75) = floor(1250 / 75) = 16.
    # 50 / (50 + 16) = 50 / 66 = 75.75% >= 75%.
    assert calculate_classes_can_miss(50, 50, 75.0) == 16
    assert calculate_classes_required(50, 50, 75.0) == 0
