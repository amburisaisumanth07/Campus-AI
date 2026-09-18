"""
Unit test suite verifying exact department and faculty matching in CampusAI.
Enforces zero cross-department bleeding, canonical resolution, ambiguity prompting,
Department-Scoped Answer Contract compliance, and exact HOD attribution.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.app.core.canonical_departments import (
    CANONICAL_DEPARTMENTS,
    CANONICAL_DEPARTMENTS_BY_ID,
    resolve_canonical_department,
    detect_department_ambiguity,
)
from backend.app.rag.router import classify_query, QueryIntent

route_query = classify_query
from backend.app.services.knowledge_service import (
    resolve_faculty,
    resolve_hod,
    resolve_department,
    resolve_structured_query,
)
from backend.app.db.models import Base, Department, Faculty


# ── In-Memory Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seeded_db():
    """Create an in-memory SQLite database populated with canonical MITS records."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    # Seed canonical departments
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

    # Seed AI faculty (Dept 11) - exactly 25 official faculty from live MITS department/28
    ai_faculty = [
        Faculty(name="Dr. R. Kalpana", designation="Professor & Head", qualification="Ph.D. (Anna University)", department="AI", department_id=11, email="drkalpanar@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/80", is_active=True, is_valid=True),
        Faculty(name="Dr. Ben Sujin", designation="Professor", qualification="Ph.D. (Karunya University)", department="AI", department_id=11, email="drbensujin@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/564", is_active=True, is_valid=True),
        Faculty(name="Dr. S. Satheesh Kumar", designation="Assoc. Professor", qualification="Ph.D. (Anna University)", department="AI", department_id=11, email="drsatheeshkumars@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/743", is_active=True, is_valid=True),
        Faculty(name="Dr. K. Chokkanathan", designation="Assoc. Professor", qualification="Ph.D. (Veltech University)", department="AI", department_id=11, email="chokkanathank@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/121", is_active=True, is_valid=True),
        Faculty(name="Dr. A. Poongodai", designation="Asst. Professor", qualification="Ph.D. (Pondicherry University)", department="AI", department_id=11, email="drpoongodaia@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/557", is_active=True, is_valid=True),
        Faculty(name="Dr. Vamsi Bandi", designation="Asst. Professor", qualification="Ph.D. (Lincoln University College, Malaysia)", department="AI", department_id=11, email="drvamsib@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/122", is_active=True, is_valid=True),
        Faculty(name="Dr. Purandhar N", designation="Asst. Professor", qualification="Ph.D. (Anna University)", department="AI", department_id=11, email="drpurandharn@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/609", is_active=True, is_valid=True),
        Faculty(name="Dr. K. Hemalatha", designation="Asst. Professor", qualification="Ph.D. (SPMVV, Tirupathi)", department="AI", department_id=11, email="drhemalathak@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/418", is_active=True, is_valid=True),
        Faculty(name="Dr. R. Rampriya", designation="Asst. Professor", qualification="Ph.D. (Annamalai University )", department="AI", department_id=11, email="rampriyar@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/547", is_active=True, is_valid=True),
        Faculty(name="Dr. Y. Ravi Raju", designation="Asst. Professor", qualification="Ph.D. (Kalinga University)", department="AI", department_id=11, email="ravirajuy@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/155", is_active=True, is_valid=True),
        Faculty(name="Mr. K. Chandra Sekhar", designation="Asst. Professor", qualification="M.Tech., (Ph.D.) (GITAM University)", department="AI", department_id=11, email="kchandrasekhar@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/494", is_active=True, is_valid=True),
        Faculty(name="Mr. J. Viswanath", designation="Asst. Professor", qualification="M.E., (Ph.D) (Jain University)", department="AI", department_id=11, email="viswanathj@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/129", is_active=True, is_valid=True),
        Faculty(name="Mr. P. Raguraman", designation="Asst. Professor", qualification="M.Tech., (Ph.D) (Jain University)", department="AI", department_id=11, email="raguramanp@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/427", is_active=True, is_valid=True),
        Faculty(name="Mr. Praneel Kumar Peruru", designation="Asst. Professor", qualification="M.Tech., (Ph.D.) (JNTU Anantapur)", department="AI", department_id=11, email="praneelkumarp@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/676", is_active=True, is_valid=True),
        Faculty(name="Mr. Vasudevan M", designation="Asst. Professor", qualification="M.E., (Ph.D.) (Puducherry Technological University)", department="AI", department_id=11, email="vasudevanm@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/488", is_active=True, is_valid=True),
        Faculty(name="Mr. Kiran Palakeeti", designation="Asst. Professor", qualification="M.Tech., (Ph.D.) (Puducherry Technological University)", department="AI", department_id=11, email="kiranpalakeeti@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/497", is_active=True, is_valid=True),
        Faculty(name="Mr. Toralkar Pawan", designation="Asst. Professor", qualification="M.E., (Ph.D.) (Visvesvaraya Technological University (VTU))", department="AI", department_id=11, email="pawant@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/138", is_active=True, is_valid=True),
        Faculty(name="Mr. K. Mahammad", designation="Asst. Professor", qualification="M.Tech., (Ph.D.) (JNTU, Anantapur)", department="AI", department_id=11, email="mahammadk@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/403", is_active=True, is_valid=True),
        Faculty(name="Mrs. A. Naga Lakshmi", designation="Asst. Professor", qualification="M.Tech., (Ph.D.) (Amrita University)", department="AI", department_id=11, email="nagalakshmia@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/475", is_active=True, is_valid=True),
        Faculty(name="Mrs. A. Esther Merlin", designation="Asst. Professor", qualification="M.Tech., (Ph.D.) (Visvesvaraya Technological University)", department="AI", department_id=11, email="esthermerlina@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/659", is_active=True, is_valid=True),
        Faculty(name="Mr. Sreenath Kocharla", designation="Asst. Professor", qualification="M.Tech., (Ph.D.) (JNTU, Vijayanagaram)", department="AI", department_id=11, email="sreenathk@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/599", is_active=True, is_valid=True),
        Faculty(name="Ms. N. Mohana Priya", designation="Asst. Professor", qualification="M.Tech", department="AI", department_id=11, email="mohanapriyan@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/406", is_active=True, is_valid=True),
        Faculty(name="Mr. Surya Bahadur", designation="Asst. Professor", qualification="M.Tech.", department="AI", department_id=11, email="suryabahadur@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/722", is_active=True, is_valid=True),
        Faculty(name="Mr. D. Jaganathan", designation="Asst. Professor", qualification="M.Tech", department="AI", department_id=11, email="jaganathand@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/457", is_active=True, is_valid=True),
        Faculty(name="Mr. K. Venkata Subramanyam", designation="Asst. Professor", qualification="M.Tech.", department="AI", department_id=11, email="venkatasubramanyamk@mits.ac.in", profile_url="https://mits.ac.in/facultyprofile/1096", is_active=True, is_valid=True),
    ]
    session.add_all(ai_faculty)

    # Seed CSE faculty (Dept 1)
    cse_faculty = [
        Faculty(name="Dr. M. Sreedevi", designation="Professor & Head", qualification="Ph.D.", department="CSE", department_id=1, email="sreedevi@mits.ac.in", profile_url="https://mits.ac.in/faculty/sreedevi", is_active=True, is_valid=True),
        Faculty(name="Dr. D. J. Ashoka", designation="Professor", qualification="Ph.D.", department="CSE", department_id=1, email="ashoka@mits.ac.in", profile_url="https://mits.ac.in/faculty/ashoka", is_active=True, is_valid=True),
    ]
    session.add_all(cse_faculty)

    # Seed CSE-AIML faculty (Dept 14)
    aiml_faculty = [
        Faculty(name="Dr. S. Padma", designation="Professor & Head", qualification="Ph.D.", department="CSE-AIML", department_id=14, email="spadma@mits.ac.in", profile_url="https://mits.ac.in/faculty/padma", is_active=True, is_valid=True),
        Faculty(name="Dr. P. Kuppusamy", designation="Professor", qualification="Ph.D.", department="CSE-AIML", department_id=14, email="kuppusamy@mits.ac.in", profile_url="https://mits.ac.in/faculty/kuppusamy", is_active=True, is_valid=True),
    ]
    session.add_all(aiml_faculty)

    # Other depts HODs
    session.add_all([
        Faculty(name="Dr. Vijayakumar Natesan", designation="Professor & Head", qualification="Ph.D.", department="CIVIL", department_id=6, email="vijayakumar@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. Sanjay Kumar C. Gowre", designation="Professor & Head", qualification="Ph.D.", department="ECE", department_id=3, email="sanjaykumar@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. Manavaalan Gunasekaran", designation="Associate Professor & Head", qualification="Ph.D.", department="EEE", department_id=4, email="manavaalan@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. S. Bhaskaran", designation="Professor & Head", qualification="Ph.D.", department="MECH", department_id=5, email="bhaskaran@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. R. Varadarajan", designation="Professor & Head", qualification="Ph.D.", department="MBA", department_id=7, email="varadarajan@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. N. Naveen Kumar", designation="Professor & Head", qualification="Ph.D.", department="MCA", department_id=8, email="naveenkumar@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. S. Kusuma", designation="Professor & Head", qualification="Ph.D.", department="CSE-DS", department_id=9, email="kusuma@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. Brahm Prakash", designation="Associate Professor & Head", qualification="Ph.D.", department="CSE-CS", department_id=10, email="brahmprakash@mits.ac.in", is_active=True, is_valid=True),
        Faculty(name="Dr. K. Dinesh", designation="Associate Professor & Head", qualification="Ph.D.", department="CST", department_id=12, email="kdinesh@mits.ac.in", is_active=True, is_valid=True),
    ])

    session.commit()
    yield session
    session.close()


# ── 1. Canonical Department Resolution Tests ──────────────────────────────────

class TestCanonicalDepartmentResolution:
    def test_exact_ai_department_queries(self):
        """Verify queries for AI department resolve exclusively to AI (ID 11)."""
        ai_queries = [
            "ai department",
            "the AI department",
            "cse ai",
            "cse - ai",
            "cse (ai)",
            "cse (artificial intelligence)",
            "artificial intelligence",
            "department of artificial intelligence",
        ]
        for q in ai_queries:
            canon = resolve_canonical_department(q)
            assert canon is not None, f"Failed to resolve '{q}'"
            assert canon.code == "AI", f"Expected AI for '{q}', got {canon.code}"
            assert canon.department_id == 11

    def test_exact_cse_aiml_department_queries(self):
        """Verify queries for CSE-AIML resolve exclusively to CSE-AIML (ID 14)."""
        aiml_queries = [
            "cse aiml",
            "cse - aiml",
            "cse ai & ml",
            "cse (ai & ml)",
            "cse (ai and ml)",
            "ai and ml",
            "ai & ml",
            "artificial intelligence and machine learning",
            "department of cse (artificial intelligence & machine learning)",
        ]
        for q in aiml_queries:
            canon = resolve_canonical_department(q)
            assert canon is not None, f"Failed to resolve '{q}'"
            assert canon.code == "CSE-AIML", f"Expected CSE-AIML for '{q}', got {canon.code}"
            assert canon.department_id == 14

    def test_exact_cse_core_department_queries(self):
        """Verify queries for core CSE resolve exclusively to CSE (ID 1)."""
        cse_queries = [
            "cse",
            "cse department",
            "computer science and engineering",
            "computer science & engineering",
            "dept of cse",
        ]
        for q in cse_queries:
            canon = resolve_canonical_department(q)
            assert canon is not None, f"Failed to resolve '{q}'"
            assert canon.code == "CSE", f"Expected CSE for '{q}', got {canon.code}"
            assert canon.department_id == 1

    def test_other_canonical_departments(self):
        """Verify all other major departments resolve deterministically."""
        cases = {
            "civil engineering": "CIVIL",
            "electrical and electronics": "EEE",
            "electronics and communication": "ECE",
            "mechanical engineering": "MECH",
            "data science": "CSE-DS",
            "cyber security": "CSE-CS",
            "computer applications": "MCA",
            "management studies": "MBA",
            "basic sciences": "BSH",
            "mathematics": "BSH",
            "physics": "BSH",
            "chemistry": "BSH",
            "english": "BSH",
        }
        for query_str, expected_code in cases.items():
            canon = resolve_canonical_department(query_str)
            assert canon is not None, f"Failed to resolve '{query_str}'"
            assert canon.code == expected_code, f"Expected {expected_code} for '{query_str}', got {canon.code}"


# ── 2. Ambiguity Detection Tests ──────────────────────────────────────────────

class TestAmbiguityDetection:
    def test_isolated_ai_triggers_ambiguity(self):
        """Verify ambiguous bare query 'ai' triggers clarification between AI and CSE-AIML."""
        ambiguous_queries = [
            "faculty in ai",
            "who works in ai",
            "ai faculty",
            "show ai faculty",
        ]
        for q in ambiguous_queries:
            res = detect_department_ambiguity(q)
            assert res is not None, f"Expected ambiguity for '{q}'"
            assert res["is_ambiguous"] is True
            assert "CSE-AI" in res["clarification_question"]
            assert "CSE-AIML" in res["clarification_question"]

    def test_unambiguous_queries_do_not_trigger_ambiguity(self):
        """Verify specific queries like 'ai department' or 'ai and ml' do NOT trigger ambiguity."""
        unambiguous = [
            "show all the faculty in the AI department",
            "show all faculty in AI and ML",
            "cse ai faculty",
            "faculty in cse",
            "civil department faculty",
        ]
        for q in unambiguous:
            res = detect_department_ambiguity(q)
            assert res is None, f"Unexpected ambiguity for '{q}': {res}"


# ── 3. Query Router Integration Tests ─────────────────────────────────────────

class TestQueryRouterExactMatching:
    def test_show_all_faculty_in_ai_department(self):
        """The canonical user query must route to FACULTY_LOOKUP with pure structured knowledge."""
        routed = route_query("show all the faculty in the AI department")
        assert routed.intent == QueryIntent.FACULTY_LOOKUP
        assert routed.extracted_entities.get("department_code") == "AI"
        assert routed.requires_structured is True
        assert routed.requires_rag is False
        assert routed.is_ambiguous is False

    def test_hod_of_ai_department(self):
        """HOD query must route to ROLE_LOOKUP with role_code=HOD and department_code=AI."""
        routed = route_query("Who is the HOD of AI department?")
        assert routed.intent == QueryIntent.ROLE_LOOKUP
        assert routed.extracted_entities.get("role_code") == "HOD"
        assert routed.extracted_entities.get("department_code") == "AI"
        assert routed.requires_structured is True
        assert routed.requires_rag is False

    def test_designation_filter_professors(self):
        """Query for professors must extract designation_filter='PROFESSOR'."""
        routed = route_query("how many professors in the AI department?")
        assert routed.intent == QueryIntent.FACULTY_LOOKUP
        assert routed.extracted_entities.get("department_code") == "AI"
        assert routed.extracted_entities.get("designation_filter") == "PROFESSOR"
        assert routed.extracted_entities.get("is_count_query") is True

    def test_ambiguous_faculty_query_routing(self):
        """Ambiguous query routes with is_ambiguous=True and structured clarification question."""
        routed = route_query("faculty in ai")
        assert routed.is_ambiguous is True
        assert routed.clarification_question is not None
        assert "CSE-AI" in routed.clarification_question


# ── 4. Department Isolation & Zero-Bleed Tests ─────────────────────────────────

class TestDepartmentIsolation:
    def test_ai_department_contains_only_ai_faculty(self, seeded_db: Session):
        """
        CRITICAL TEST:
        Querying AI must return ONLY the 4 canonical AI faculty and ZERO CSE or AIML faculty.
        """
        res = resolve_faculty(seeded_db, dept_code="AI")
        assert res is not None
        assert res.get("found") is True
        text = res.get("text", "")

        # Must contain all official AI faculty
        expected_ai_faculty = [
            "Dr. R. Kalpana",
            "Dr. Ben Sujin",
            "Dr. S. Satheesh Kumar",
            "Dr. K. Chokkanathan",
            "Dr. A. Poongodai",
            "Dr. Vamsi Bandi",
            "Dr. Purandhar N",
            "Dr. K. Hemalatha",
            "Dr. R. Rampriya",
            "Dr. Y. Ravi Raju",
            "Mr. K. Chandra Sekhar",
            "Mr. J. Viswanath",
            "Mr. P. Raguraman",
            "Mr. Praneel Kumar Peruru",
            "Mr. Vasudevan M",
            "Mr. Kiran Palakeeti",
            "Mr. Toralkar Pawan",
            "Mr. K. Mahammad",
            "Mrs. A. Naga Lakshmi",
            "Mrs. A. Esther Merlin",
            "Mr. Sreenath Kocharla",
            "Ms. N. Mohana Priya",
            "Mr. Surya Bahadur",
            "Mr. D. Jaganathan",
            "Mr. K. Venkata Subramanyam",
        ]
        for name in expected_ai_faculty:
            assert name in text, f"AI faculty '{name}' missing from AI roster!"

        # Must NEVER contain faculty from CSE or CSE-AIML
        forbidden_faculty = [
            "Dr. M. Sreedevi",      # CSE HOD
            "Dr. S. Padma",         # CSE-AIML HOD
            "Dr. P. Kuppusamy",     # CSE-AIML Professor
            "Dr. D. J. Ashoka",     # CSE Professor
            "Dr. Brahm Prakash",    # CSE-CS HOD
            "Dr. S. Kusuma",        # CSE-DS HOD
        ]
        for name in forbidden_faculty:
            assert name not in text, f"CRITICAL BLEED: '{name}' incorrectly included in AI faculty roster!"

        # Must have exactly 25 total faculty
        assert res.get("total_faculty") == 25

    def test_cse_department_does_not_contain_ai_faculty(self, seeded_db: Session):
        """Querying CSE must contain Dr. M. Sreedevi and NEVER contain Dr. R. Kalpana."""
        res = resolve_faculty(seeded_db, dept_code="CSE")
        assert res is not None
        assert res.get("found") is True
        text = res.get("text", "")

        assert "Dr. M. Sreedevi" in text
        assert "Dr. R. Kalpana" not in text
        assert "Dr. S. Padma" not in text

    def test_cse_aiml_department_does_not_contain_ai_or_cse_faculty(self, seeded_db: Session):
        """Querying CSE-AIML must contain Dr. S. Padma and NEVER contain Dr. R. Kalpana or Dr. M. Sreedevi."""
        res = resolve_faculty(seeded_db, dept_code="CSE-AIML")
        assert res is not None
        assert res.get("found") is True
        text = res.get("text", "")

        assert "Dr. S. Padma" in text
        assert "Dr. R. Kalpana" not in text
        assert "Dr. M. Sreedevi" not in text

    def test_disjoint_faculty_sets_across_departments(self, seeded_db: Session):
        """The set of faculty in AI, CSE, and CSE-AIML must have ZERO overlap."""
        ai_fac_ids = set(f.id for f in seeded_db.query(Faculty).filter(Faculty.department_id == 11, Faculty.is_active == True).all())
        cse_fac_ids = set(f.id for f in seeded_db.query(Faculty).filter(Faculty.department_id == 1, Faculty.is_active == True).all())
        aiml_fac_ids = set(f.id for f in seeded_db.query(Faculty).filter(Faculty.department_id == 14, Faculty.is_active == True).all())

        assert len(ai_fac_ids & cse_fac_ids) == 0, f"Overlap between AI and CSE: {ai_fac_ids & cse_fac_ids}"
        assert len(ai_fac_ids & aiml_fac_ids) == 0, f"Overlap between AI and CSE-AIML: {ai_fac_ids & aiml_fac_ids}"
        assert len(cse_fac_ids & aiml_fac_ids) == 0, f"Overlap between CSE and CSE-AIML: {cse_fac_ids & aiml_fac_ids}"


# ── 5. Department-Scoped Answer Contract Compliance ───────────────────────────

class TestAnswerContractCompliance:
    def test_ai_faculty_contract_structure(self, seeded_db: Session):
        """Verify the exact response structure matches the Department-Scoped Answer Contract."""
        res = resolve_faculty(seeded_db, dept_code="AI")
        text = res.get("text", "")

        # 1. Department header
        assert "Department:" in text
        assert "CSE (Artificial Intelligence)" in text or "AI" in text

        # 2. HOD section
        assert "HOD:" in text
        assert "Dr. R. Kalpana" in text

        # 3. Total Faculty count
        assert "Total Faculty:\n25" in text

        # 4. Numbered faculty list
        assert "Faculty:\n1." in text
        assert "25." in text

        # 5. Official Source URL
        assert "Sources:\nhttps://mits.ac.in" in text

    def test_citation_metadata(self, seeded_db: Session):
        """Verify structured citations include exact official source URL and title."""
        res = resolve_faculty(seeded_db, dept_code="AI")
        citations = res.get("citations", [])
        assert len(citations) >= 1
        assert citations[0]["source_url"].startswith("https://mits.ac.in")
        assert citations[0]["document_type"] == "STRUCTURED_RECORD"


# ── 6. Exact HOD Attribution Tests ────────────────────────────────────────────

class TestExactHODAttribution:
    def test_ai_hod(self, seeded_db: Session):
        res = resolve_hod(seeded_db, dept_code="AI")
        assert res is not None and res.get("found") is True
        assert "Dr. R. Kalpana" in res.get("text", "")
        assert "Dr. M. Sreedevi" not in res.get("text", "")

    def test_cse_hod(self, seeded_db: Session):
        res = resolve_hod(seeded_db, dept_code="CSE")
        assert res is not None and res.get("found") is True
        assert "Dr. M. Sreedevi" in res.get("text", "")
        assert "Dr. R. Kalpana" not in res.get("text", "")

    def test_cse_aiml_hod(self, seeded_db: Session):
        res = resolve_hod(seeded_db, dept_code="CSE-AIML")
        assert res is not None and res.get("found") is True
        assert "Dr. S. Padma" in res.get("text", "")

    def test_civil_hod(self, seeded_db: Session):
        res = resolve_hod(seeded_db, dept_code="CIVIL")
        assert res is not None and res.get("found") is True
        assert "Dr. Vijayakumar Natesan" in res.get("text", "")

    def test_ece_hod(self, seeded_db: Session):
        res = resolve_hod(seeded_db, dept_code="ECE")
        assert res is not None and res.get("found") is True
        assert "Dr. Sanjay Kumar C. Gowre" in res.get("text", "")

    def test_eee_hod(self, seeded_db: Session):
        res = resolve_hod(seeded_db, dept_code="EEE")
        assert res is not None and res.get("found") is True
        assert "Dr. Manavaalan Gunasekaran" in res.get("text", "")

    def test_mech_hod(self, seeded_db: Session):
        res = resolve_hod(seeded_db, dept_code="MECH")
        assert res is not None and res.get("found") is True
        assert "Dr. S. Bhaskaran" in res.get("text", "")
