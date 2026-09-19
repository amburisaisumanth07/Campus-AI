"""
Dedicated HOD verification test for all 13 Canonical MITS Departments.
Verifies that knowledge_service.resolve_hod returns the current official HOD from
https://mits.ac.in/departmentheads for every canonical department.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.models import Base, Department, Faculty
from backend.app.services.knowledge_service import resolve_hod
from backend.app.core.canonical_departments import CANONICAL_DEPARTMENTS

EXPECTED_HOD_PAIRS = [
    ("CSE", "Dr. M. Sreedevi"),
    ("AI", "Dr. R. Kalpana"),
    ("CSE-DS", "Dr. S. Kusuma"),
    ("CSE-CS", "Dr. Brahm Prakash"),
    ("CSE-AIML", "Dr. S. Padma"),
    ("MCA", "Dr. N. Naveen Kumar"),
    ("ECE", "Dr. Sanjay Kumar C. Gowre"),
    ("EEE", "Dr. Manavaalan Gunasekaran"),
    ("MECH", "Dr. S. Bhaskaran"),
    ("CIVIL", "Dr. Vijayakumar Natesan"),
    ("MBA", "Dr. Bhanu Sree Reddy"),
    ("CST", "Dr. K. Dinesh"),
    ("BSH", "Dr. R. Saravana"),
]


@pytest.fixture(scope="module")
def seeded_db():
    """Create in-memory SQLite database populated with canonical MITS records."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    for canon in CANONICAL_DEPARTMENTS.values():
        dept = Department(
            id=canon.department_id,
            code=canon.code,
            name=canon.official_name,
            school=canon.school,
            hod=canon.hod_name,
            hod_name=canon.hod_name,
            hod_designation=canon.hod_designation,
            source_url=canon.source_url,
            is_active=True,
            is_valid=True,
        )
        session.add(dept)

    session.commit()
    yield session
    session.close()
    engine.dispose()


class TestLiveHODVerification:
    @pytest.mark.parametrize("dept_code,expected_hod", EXPECTED_HOD_PAIRS)
    def test_each_department_resolves_to_current_official_hod(self, seeded_db, dept_code, expected_hod):
        res = resolve_hod(seeded_db, dept_code=dept_code, is_historical=False)
        assert res is not None, f"Failed to resolve HOD for {dept_code}"
        assert res.get("found") is True, f"HOD not found for {dept_code}"

        text = res.get("text", "")
        assert expected_hod in text, f"Expected {expected_hod} in response text for {dept_code}, got:\n{text}"
        assert "Status:\nCurrent official source" in text
        assert "https://mits.ac.in" in text

    def test_all_hods_list_contains_all_13_official_heads(self, seeded_db):
        res = resolve_hod(seeded_db, dept_code=None, is_historical=False)
        assert res is not None
        assert res.get("found") is True
        text = res.get("text", "")

        for dept_code, expected_hod in EXPECTED_HOD_PAIRS:
            assert expected_hod in text, f"List of all HODs missing {expected_hod} for {dept_code}"
