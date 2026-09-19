"""
Regression and verification tests for CampusAI Faculty Freshness, Stale-Data Protection,
Current vs Historical Disambiguation, and Department Isolation.
"""
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Base, Department, Faculty, Person
from backend.app.core.canonical_departments import CANONICAL_DEPARTMENTS, CANONICAL_DEPARTMENTS_BY_ID
from backend.app.rag.router import classify_query, QueryIntent
from backend.app.services.knowledge_service import resolve_faculty, resolve_hod
from backend.app.rag.pipeline import run_pipeline


@pytest.fixture
def mem_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed departments
    dept_map = {}
    for code, cd in CANONICAL_DEPARTMENTS.items():
        dept = Department(
            id=cd.department_id,
            name=cd.official_name,
            code=cd.code,
            school=cd.school,
            hod_name=cd.hod_name,
            hod_designation=cd.hod_designation,
            source_url=cd.official_url,
            is_active=True,
            is_valid=True,
        )
        session.add(dept)
        dept_map[cd.department_id] = dept

    session.flush()

    # Seed verified faculty for CSE (42 active, 1 inactive), AI (25 active), CSE-AIML (25 active)
    # CSE HOD + 41 faculty
    session.add(Faculty(name="Dr. M. Sreedevi", designation="Professor & Head", department="CSE", department_id=1, is_active=True, is_valid=True))
    for i in range(2, 43):
        session.add(Faculty(name=f"CSE Faculty Member {i}", designation="Assistant Professor", department="CSE", department_id=1, is_active=True, is_valid=True))
    # Inactive/historical CSE faculty
    session.add(Faculty(name="Dr. Former Professor", designation="Former Professor", department="CSE", department_id=1, is_active=False, is_valid=True))

    # AI HOD + 24 faculty
    session.add(Faculty(name="Dr. R. Kalpana", designation="Professor & Head", department="AI", department_id=11, is_active=True, is_valid=True))
    for i in range(2, 26):
        session.add(Faculty(name=f"AI Faculty Member {i}", designation="Assistant Professor", department="AI", department_id=11, is_active=True, is_valid=True))

    # CSE-AIML HOD + 24 faculty
    session.add(Faculty(name="Dr. S. Padma", designation="Professor & Head", department="CSE-AIML", department_id=14, is_active=True, is_valid=True))
    for i in range(2, 26):
        session.add(Faculty(name=f"AIML Faculty Member {i}", designation="Assistant Professor", department="CSE-AIML", department_id=14, is_active=True, is_valid=True))

    # ECE HOD + 28 faculty (29 total)
    session.add(Faculty(name="Dr. Sanjay Kumar C. Gowre", designation="Professor & Head", department="ECE", department_id=3, is_active=True, is_valid=True))
    for i in range(2, 30):
        session.add(Faculty(name=f"ECE Faculty Member {i}", designation="Assistant Professor", department="ECE", department_id=3, is_active=True, is_valid=True))

    session.commit()
    yield session
    session.close()


class TestFacultyQueryClassification:
    def test_current_faculty_natural_language_queries(self):
        """Natural variations of current faculty questions map to FACULTY_LOOKUP with is_historical=False."""
        q1 = classify_query("Who is currently working in CSE?")
        assert q1.intent == QueryIntent.FACULTY_LOOKUP
        assert q1.extracted_entities.get("department_code") == "CSE"
        assert q1.is_historical is False

        q2 = classify_query("Show the current faculty of CSE-AIML")
        assert q2.intent == QueryIntent.FACULTY_LOOKUP
        assert q2.extracted_entities.get("department_code") == "CSE-AIML"
        assert q2.is_historical is False

        q3 = classify_query("Show all faculty members currently in ECE")
        assert q3.intent == QueryIntent.FACULTY_LOOKUP
        assert q3.extracted_entities.get("department_code") == "ECE"
        assert q3.is_historical is False

        q4 = classify_query("Who works in mechanical engineering?")
        assert q4.intent == QueryIntent.FACULTY_LOOKUP
        assert q4.extracted_entities.get("department_code") == "MECH"
        assert q4.is_historical is False

    def test_historical_faculty_queries(self):
        """Historical faculty queries are flagged with is_historical=True."""
        q1 = classify_query("Who were the faculty earlier?")
        assert q1.intent == QueryIntent.FACULTY_LOOKUP
        assert q1.is_historical is True

        q2 = classify_query("Show historical faculty information for CSE")
        assert q2.intent == QueryIntent.FACULTY_LOOKUP
        assert q2.is_historical is True
        assert q2.extracted_entities.get("department_code") == "CSE"

    def test_current_vs_historical_hod_queries(self):
        """Distinguishes current HOD queries from historical ones."""
        curr = classify_query("Who is the current HOD of CSE?")
        assert curr.intent == QueryIntent.ROLE_LOOKUP
        assert curr.extracted_entities.get("role_code") == "HOD"
        assert curr.extracted_entities.get("department_code") == "CSE"
        assert curr.is_historical is False

        hist = classify_query("Who was the previous HOD of CSE?")
        assert hist.intent == QueryIntent.ROLE_LOOKUP
        assert hist.extracted_entities.get("role_code") == "HOD"
        assert hist.extracted_entities.get("department_code") == "CSE"
        assert hist.is_historical is True

        hist_year = classify_query("Who was the HOD in 2023 for ECE?")
        assert hist_year.intent == QueryIntent.ROLE_LOOKUP
        assert hist_year.is_historical is True


class TestFacultyRosterAndFreshness:
    def test_current_cse_faculty_count_and_status(self, mem_db: Session):
        """Current CSE faculty query returns exactly 42 active faculty and excludes inactive."""
        res = resolve_faculty(mem_db, dept_code="CSE", is_historical=False)
        assert res is not None
        assert res.get("found") is True
        assert res.get("total_faculty") == 42
        text = res.get("text", "")
        assert "Total Faculty:\n42" in text
        assert "Current official source" in text
        assert "Dr. M. Sreedevi" in text
        # Inactive faculty must NOT be in current active roster
        assert "Dr. Former Professor" not in text

    def test_historical_cse_faculty_returns_inactive_only(self, mem_db: Session):
        """Historical faculty query returns inactive/former faculty and labels status as Historical."""
        res = resolve_faculty(mem_db, dept_code="CSE", is_historical=True)
        assert res is not None
        assert res.get("found") is True
        text = res.get("text", "")
        assert "Historical records" in text
        assert "Dr. Former Professor" in text
        assert "CSE Faculty Member 2" not in text

    def test_current_hod_compact_source_display(self, mem_db: Session):
        """Current HOD query displays the required compact source format."""
        res = resolve_hod(mem_db, dept_code="CSE", is_historical=False)
        assert res is not None
        text = res.get("text", "")
        assert "Current HOD:\nDr. M. Sreedevi" in text
        assert "Source:\nOfficial MITS CSE Department" in text
        assert "Status:\nCurrent official source" in text

    def test_historical_hod_display(self, mem_db: Session):
        """Historical HOD query indicates historical inquiry and archives."""
        res = resolve_hod(mem_db, dept_code="CSE", is_historical=True)
        assert res is not None
        text = res.get("text", "")
        assert "Historical record" in text
        assert "Past administrative records" in text


class TestDepartmentIsolationRegression:
    def test_zero_contamination_between_departments(self, mem_db: Session):
        """CSE, AI, and CSE-AIML rosters must not contain members from one another."""
        cse_res = resolve_faculty(mem_db, dept_code="CSE")
        ai_res = resolve_faculty(mem_db, dept_code="AI")
        aiml_res = resolve_faculty(mem_db, dept_code="CSE-AIML")

        assert "Dr. M. Sreedevi" in cse_res["text"]
        assert "Dr. R. Kalpana" not in cse_res["text"]
        assert "Dr. S. Padma" not in cse_res["text"]

        assert "Dr. R. Kalpana" in ai_res["text"]
        assert "Dr. M. Sreedevi" not in ai_res["text"]
        assert "Dr. S. Padma" not in ai_res["text"]

        assert "Dr. S. Padma" in aiml_res["text"]
        assert "Dr. M. Sreedevi" not in aiml_res["text"]
        assert "Dr. R. Kalpana" not in aiml_res["text"]


class TestNonFacultyKnowledgeIntegrity:
    def test_academic_and_grading_rules_unaffected(self):
        """Verify non-faculty queries remain untouched and route to their respective intents."""
        q_gpa = classify_query("How is SGPA and CGPA calculated in R20 regulation?")
        assert q_gpa.intent == QueryIntent.ACADEMIC_RULE

        q_att = classify_query("What is the attendance condonation criteria?")
        assert q_att.intent == QueryIntent.ATTENDANCE

        q_exam = classify_query("What is the supplementary examination fee and revaluation rule?")
        assert q_exam.intent == QueryIntent.EXAMINATION
