"""
Unit tests for Website Crawler, URL Validator, and HTML Processor.
"""
import pytest
from backend.app.services.crawler_service import (
    is_safe_and_valid_url,
    normalize_crawl_url,
    extract_html_content_and_links,
    infer_document_type,
)
from backend.app.db.models import DocumentType


def test_url_validation_allowed_domains():
    allowed = ["college.edu", "sub.college.edu"]

    # Valid domain & subdomains
    is_valid, msg = is_safe_and_valid_url("https://college.edu/academics", allowed)
    assert is_valid is True

    is_valid, msg = is_safe_and_valid_url("https://sub.college.edu/circulars/index.html", allowed)
    assert is_valid is True

    # Unauthorized domain
    is_valid, msg = is_safe_and_valid_url("https://evil-site.com/hack", allowed)
    assert is_valid is False
    assert "not in allowed domains" in msg


def test_url_validation_ssrf_protection():
    allowed = ["localhost", "127.0.0.1", "192.168.1.1"]

    # Block localhost
    is_valid, msg = is_safe_and_valid_url("http://localhost:8000/secret", allowed)
    assert is_valid is False
    assert "forbidden" in msg.lower() or "ssrf" in msg.lower()

    # Block private IP 127.0.0.1
    is_valid, msg = is_safe_and_valid_url("http://127.0.0.1:5000", allowed)
    assert is_valid is False

    # Block 192.168.x.x
    is_valid, msg = is_safe_and_valid_url("http://192.168.1.1/admin", allowed)
    assert is_valid is False

    # Block unsupported schemes
    is_valid, msg = is_safe_and_valid_url("file:///etc/passwd", allowed)
    assert is_valid is False
    assert "unsupported scheme" in msg.lower()

    is_valid, msg = is_safe_and_valid_url("gopher://college.edu", allowed)
    assert is_valid is False


def test_url_validation_allowed_paths():
    allowed_domains = ["college.edu"]
    allowed_paths = ["/examinations", "/academics/calendar"]

    # Allowed path
    is_valid, _ = is_safe_and_valid_url("https://college.edu/examinations/timetable.html", allowed_domains, allowed_paths)
    assert is_valid is True

    # Disallowed path
    is_valid, msg = is_safe_and_valid_url("https://college.edu/sports/events", allowed_domains, allowed_paths)
    assert is_valid is False
    assert "allowed paths" in msg.lower()


def test_normalize_crawl_url():
    url1 = "https://college.edu/about#section1"
    assert normalize_crawl_url(url1) == "https://college.edu/about"

    url2 = "https://college.edu/academics/"
    assert normalize_crawl_url(url2) == "https://college.edu/academics"

    url3 = "https://college.edu/"
    assert normalize_crawl_url(url3) == "https://college.edu/"


def test_extract_html_content_and_links():
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Campus Examination Regulations 2026</title>
        <script>console.log("ignore me");</script>
        <style>.nav { color: red; }</style>
      </head>
      <body>
        <header><nav><a href="/home">Home</a></nav></header>
        <main>
          <h1>Academic Regulations for Semester 4</h1>
          <p>Students must maintain at least 75% attendance in all courses.</p>
          <a href="/examinations/schedule.html">View Schedule</a>
          <a href="https://external-unrelated.com/ad">Ad</a>
        </main>
        <footer><p>Copyright 2026 College</p></footer>
      </body>
    </html>
    """

    data = extract_html_content_and_links(
        html_text=html,
        current_url="https://college.edu/regulations.html",
        allowed_domains=["college.edu"],
    )

    assert data["title"] == "Campus Examination Regulations 2026"
    assert "Academic Regulations for Semester 4" in data["text"]
    assert "75% attendance" in data["text"]
    # Verify script, style, nav, footer are stripped
    assert "ignore me" not in data["text"]
    assert "Copyright 2026 College" not in data["text"]
    assert len(data["content_hash"]) == 64
    # Discovered internal link
    assert "https://college.edu/examinations/schedule.html" in data["discovered_links"]
    # External link filtered out
    assert "https://external-unrelated.com/ad" not in data["discovered_links"]


def test_infer_document_type():
    assert infer_document_type("Exam Schedule May 2026", "https://college.edu/exams") == DocumentType.EXAMINATION
    assert infer_document_type("Academic Calendar 2025-2026", "https://college.edu/calendar") == DocumentType.ACADEMIC_CALENDAR
    assert infer_document_type("B.Tech B18 Regulations", "https://college.edu/regulations") == DocumentType.REGULATION
    assert infer_document_type("Attendance Shortage Notice", "https://college.edu/notice") == DocumentType.ATTENDANCE
    assert infer_document_type("Campus Placement Drive 2026", "https://college.edu/placements") == DocumentType.PLACEMENT


def test_department_sync_preserves_canonical_url(db):
    from backend.app.services.crawler_service import sync_mits_department_page
    from backend.app.db.models import Department

    sample_html = """
    <html>
      <head><title>MITS - Department of Computer Science & Engineering</title></head>
      <body>
        <h1>Department of Computer Science & Engineering</h1>
        <p>The Department of Computer Science and Engineering was established in 1998 with premier labs.</p>
      </body>
    </html>
    """
    res = sync_mits_department_page(db, "https://mits.ac.in/department/9", sample_html)
    assert res in ("added", "updated")

    dept = db.query(Department).filter(Department.code == "CSE").first()
    assert dept is not None
    assert dept.source_url == "https://mits.ac.in/department/9"
    assert "https://mits.ac.in/departments/cse" not in dept.source_url


def test_academic_calendar_sync_preserves_pdf_url(db):
    from backend.app.services.crawler_service import sync_academic_calendars_from_page
    from backend.app.db.models import AcademicCalendarEvent

    sample_html = """
    <html>
      <body>
        <div class="calendar-list">
          <a href="/public/uploads/ugc/Academic Calendar 2026-27 For B.Tech II Year I & II Semesters.pdf">
            Academic Calendar 2026-27 For B.Tech II Year I & II Semesters
          </a>
        </div>
      </body>
    </html>
    """
    count = sync_academic_calendars_from_page(db, "https://mits.ac.in/academic-calenders", sample_html)
    assert count >= 1

    ev = db.query(AcademicCalendarEvent).filter(
        AcademicCalendarEvent.event_name.ilike("%B.Tech II Year%")
    ).first()
    assert ev is not None
    assert ev.source_url == "https://mits.ac.in/academic-calenders"
    assert "public/uploads/ugc" in ev.document_url


def test_examination_sync_preserves_pdf_url(db):
    from backend.app.services.crawler_service import sync_examinations_from_page
    from backend.app.db.models import Examination

    sample_html = """
    <html>
      <body>
        <div class="exam-list">
          <a href="/public/uploads/files/Timetable_BTech_End_Sem.pdf">
            B.Tech End Semester Theory Examinations Timetable
          </a>
        </div>
      </body>
    </html>
    """
    count = sync_examinations_from_page(db, "https://mits.ac.in/university-exam", sample_html)
    assert count >= 1

    exam = db.query(Examination).filter(
        Examination.title.ilike("%End Semester%")
    ).first()
    assert exam is not None
    assert exam.source_url == "https://mits.ac.in/university-exam"
    assert "public/uploads/files" in exam.document_url

