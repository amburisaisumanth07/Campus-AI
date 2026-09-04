"""
Unit tests for MITS entity adapters, dynamic faculty/HOD synchronization, and calendar extraction.
"""
import pytest
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Department,
    Faculty,
    AcademicCalendarEvent,
    Examination,
    Announcement,
    CollegeInfo,
)
from backend.app.services.mits_adapters import (
    MITSDepartmentAdapter,
    MITSFacultyAdapter,
    MITSCalendarAdapter,
    MITSExamAdapter,
    MITSAnnouncementAdapter,
)
from backend.app.services.crawler_service import (
    sync_mits_faculty_from_page,
    sync_mits_department_page,
    sync_academic_calendars_from_page,
)

SAMPLE_FACULTY_HTML = """
<html>
<body>
  <table>
    <tr><th>S.No</th><th>Name of Faculty</th><th>Qualification</th><th>Designation</th><th>Department</th><th>Profile</th></tr>
    <tr>
      <td>1</td>
      <td>Dr. Sanjay Kumar C. Gowre</td>
      <td>Ph.D.</td>
      <td>Professor & Head of the Department</td>
      <td>ECE</td>
      <td><a href="/faculty/sanjay-kumar">View Profile</a></td>
    </tr>
    <tr>
      <td>2</td>
      <td>Dr. Manavaalan Gunasekaran</td>
      <td>Ph.D.</td>
      <td>Associate Professor & Head of the Department</td>
      <td>EEE</td>
      <td><a href="/faculty/manavaalan">View Profile</a></td>
    </tr>
    <tr>
      <td>3</td>
      <td>Dr. Brahm Prakash</td>
      <td>Ph.D.</td>
      <td>Associate Professor & HoD</td>
      <td>CSE - CS</td>
      <td><a href="/faculty/brahm-prakash">View Profile</a></td>
    </tr>
  </table>
</body>
</html>
"""

SAMPLE_CALENDAR_HTML = """
<html>
<body>
  <div class="calendar-list">
    <a href="/public/uploads/ugc/B.Tech-1st%20Year%202026-27.pdf">Academic Calendar for B.Tech I Year 2026-27</a>
    <a href="/public/uploads/ugc/MCA-1st%20Year%202026-27.pdf">Academic Calendar for MCA I Year 2026-27</a>
  </div>
</body>
</html>
"""


def test_sync_faculty_and_hod_extraction(db: Session):
    count, hod_map = sync_mits_faculty_from_page(db, "https://mits.ac.in/faculty-information", SAMPLE_FACULTY_HTML)
    assert count == 3
    assert "ECE" in hod_map
    assert hod_map["ECE"]["hod_name"] == "Dr. Sanjay Kumar C. Gowre"
    assert "EEE" in hod_map
    assert hod_map["EEE"]["hod_name"] == "Dr. Manavaalan Gunasekaran"
    assert "CSE - CS" in hod_map
    assert hod_map["CSE - CS"]["hod_name"] == "Dr. Brahm Prakash"

    # Verify saved in DB
    facs = db.query(Faculty).all()
    assert len(facs) == 3
    ece_fac = db.query(Faculty).filter(Faculty.name.contains("Sanjay Kumar")).first()
    assert ece_fac is not None
    assert ece_fac.department == "ECE"


def test_sync_department_with_hod_map(db: Session):
    dept_html = """
    <html>
      <head><title>Department of Electronics & Communication Engineering - MITS</title></head>
      <body>
        <h1>Department of Electronics & Communication Engineering</h1>
        <p>The Department of Electronics and Communication Engineering at MITS offers premier B.Tech and M.Tech degree programs accredited by NBA Tier-1.</p>
      </body>
    </html>
    """
    hod_map = {
        "ECE": {
            "hod_name": "Dr. Sanjay Kumar C. Gowre",
            "hod_designation": "Professor & Head of the Department",
            "qualification": "Ph.D.",
            "hod_profile_url": "https://mits.ac.in/faculty/sanjay-kumar",
        }
    }

    res = sync_mits_department_page(db, "https://mits.ac.in/electronics-communication-engineering", dept_html, hod_map=hod_map)
    assert res in ("added", "updated")

    dept = db.query(Department).filter(Department.code == "ECE").first()
    assert dept is not None
    assert dept.name == "Department of Electronics & Communication Engineering"
    assert dept.hod == "Dr. Sanjay Kumar C. Gowre"
    assert dept.hod_name == "Dr. Sanjay Kumar C. Gowre"
    assert dept.hod_designation == "Professor & Head of the Department"
    assert dept.is_valid is True


def test_calendar_adapter_normalization():
    adapter = MITSCalendarAdapter()
    raw = {
        "academic_year": "2026-2027",
        "program": "B.Tech",
        "year": "I Year",
        "semester": "I & II Semesters",
        "event_name": "Commencement of Classwork",
        "document_url": "https://mits.ac.in/public/uploads/ugc/B.Tech-1st%20Year.pdf",
    }
    normalized = adapter.normalize(raw)
    assert normalized["academic_year"] == "2026-2027"
    assert normalized["canonical_url"].startswith("https://mits.ac.in")
    assert normalized["is_valid"] is True
    assert normalized["content_hash"] is not None
