"""
100-Question Institutional Knowledge Coverage Test Suite for CampusAI.

Validates that the Hybrid Structured Knowledge architecture accurately
classifies, resolves, and grounds 100 representative college-wide questions
spanning all 35 institutional domains with 100% source provenance.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import (
    Base,
    Person,
    Leadership,
    School,
    Department,
    Program,
    Faculty,
    Committee,
    CommitteeMember,
    Cell,
    CellCoordinator,
    Facility,
    Contact,
    AdmissionRule,
    AcademicRule,
    ExamRule,
    PlacementData,
    Placement,
    InstitutionHistory,
)
from backend.app.rag.router import classify_query, QueryIntent
from backend.app.services.knowledge_service import resolve_structured_query


@pytest.fixture(scope="module")
def seeded_db():
    """Create an in-memory SQLite database populated with official MITS records."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. People & Leadership
    p_chancellor = Person(name="Dr. N. Vijaya Bhaskar Choudary", title="Dr.", designation="Chancellor / Secretary & Correspondent", qualification="Ph.D.", email="correspondent@mits.ac.in")
    p_vc = Person(name="Dr. P. Ramanathan", title="Dr.", designation="Vice-Chancellor", qualification="Ph.D.", email="vc@mits.ac.in")
    p_reg = Person(name="Dr. C. Kamal Basha", title="Dr.", designation="Registrar", qualification="Ph.D.", email="registrar@mits.ac.in")
    p_principal = Person(name="Dr. C. Yuvaraj", title="Dr.", designation="Principal", qualification="Ph.D.", email="principal@mits.ac.in")
    p_coe = Person(name="Dr. K. Sreenivasulu", title="Dr.", designation="Controller of Examinations", qualification="Ph.D.", email="coe@mits.ac.in")
    p_dean_cst = Person(name="Dr. R. Kalpana", title="Dr.", designation="Dean - School of Computing", qualification="Ph.D.", email="deancst@mits.ac.in")

    # HOD People
    p_hod_cse = Person(name="Dr. D. J. Ashoka", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="csehod@mits.ac.in")
    p_hod_ece = Person(name="Dr. S. Rajasekaran", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="ecehod@mits.ac.in")
    p_hod_eee = Person(name="Dr. A. V. Pavan Kumar", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="eeehod@mits.ac.in")
    p_hod_mech = Person(name="Dr. K. Sreeramulu", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="mechhod@mits.ac.in")
    p_hod_civil = Person(name="Dr. Dipankar Roy", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="civilhod@mits.ac.in")
    p_hod_cst = Person(name="Dr. M. Sreedevi", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="csthod@mits.ac.in")
    p_hod_aiml = Person(name="Dr. P. Kuppusamy", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="aimlhod@mits.ac.in")
    p_hod_mba = Person(name="Dr. Sangeetha Roy", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="mbahod@mits.ac.in")
    p_hod_mca = Person(name="Dr. N. Naveen Kumar", title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email="mcahod@mits.ac.in")

    session.add_all([
        p_chancellor, p_vc, p_reg, p_principal, p_coe, p_dean_cst,
        p_hod_cse, p_hod_ece, p_hod_eee, p_hod_mech, p_hod_civil,
        p_hod_cst, p_hod_aiml, p_hod_mba, p_hod_mca,
    ])
    session.commit()

    # Leadership roles
    session.add_all([
        Leadership(person_id=p_chancellor.id, role_code="CHANCELLOR", role_title="Chancellor", order_index=1, is_current=True, source_url="https://mits.ac.in/governance"),
        Leadership(person_id=p_vc.id, role_code="VICE_CHANCELLOR", role_title="Vice-Chancellor", order_index=2, is_current=True, source_url="https://mits.ac.in/governance"),
        Leadership(person_id=p_reg.id, role_code="REGISTRAR", role_title="Registrar", order_index=3, is_current=True, source_url="https://mits.ac.in/governance"),
        Leadership(person_id=p_principal.id, role_code="PRINCIPAL", role_title="Principal", order_index=4, is_current=True, source_url="https://mits.ac.in/governance"),
        Leadership(person_id=p_coe.id, role_code="COE", role_title="Controller of Examinations", order_index=5, is_current=True, source_url="https://mits.ac.in/examination-cell"),
        Leadership(person_id=p_dean_cst.id, role_code="DEAN", role_title="Dean - School of Computing", order_index=6, is_current=True, source_url="https://mits.ac.in/academics"),
    ])

    # Schools
    s_comp = School(code="COMPUTING", name="School of Computing", dean_person_id=p_dean_cst.id)
    s_eng = School(code="ENGINEERING", name="School of Engineering")
    s_mgmt = School(code="MANAGEMENT", name="School of Management")
    session.add_all([s_comp, s_eng, s_mgmt])
    session.commit()

    # Departments
    d_cse = Department(code="CSE", name="Computer Science & Engineering", school="School of Computing", school_id=s_comp.id, hod_name="Dr. D. J. Ashoka", hod_person_id=p_hod_cse.id, email="csehod@mits.ac.in", phone="08571-280255", source_url="https://mits.ac.in/cse")
    d_ece = Department(code="ECE", name="Electronics & Communication Engineering", school="School of Engineering", school_id=s_eng.id, hod_name="Dr. S. Rajasekaran", hod_person_id=p_hod_ece.id, email="ecehod@mits.ac.in", phone="08571-280256", source_url="https://mits.ac.in/ece")
    d_eee = Department(code="EEE", name="Electrical & Electronics Engineering", school="School of Engineering", school_id=s_eng.id, hod_name="Dr. A. V. Pavan Kumar", hod_person_id=p_hod_eee.id, email="eeehod@mits.ac.in", source_url="https://mits.ac.in/eee")
    d_mech = Department(code="MECH", name="Mechanical Engineering", school="School of Engineering", school_id=s_eng.id, hod_name="Dr. K. Sreeramulu", hod_person_id=p_hod_mech.id, email="mechhod@mits.ac.in", source_url="https://mits.ac.in/mech")
    d_civil = Department(code="CIVIL", name="Civil Engineering", school="School of Engineering", school_id=s_eng.id, hod_name="Dr. Dipankar Roy", hod_person_id=p_hod_civil.id, email="civilhod@mits.ac.in", source_url="https://mits.ac.in/civil")
    d_cst = Department(code="CST", name="Computer Science & Technology", school="School of Computing", school_id=s_comp.id, hod_name="Dr. M. Sreedevi", hod_person_id=p_hod_cst.id, email="csthod@mits.ac.in", source_url="https://mits.ac.in/cst")
    d_aiml = Department(code="CSE-AIML", name="CSE (Artificial Intelligence & Machine Learning)", school="School of Computing", school_id=s_comp.id, hod_name="Dr. P. Kuppusamy", hod_person_id=p_hod_aiml.id, email="aimlhod@mits.ac.in", source_url="https://mits.ac.in/cse-aiml")
    d_mba = Department(code="MBA", name="Management Studies", school="School of Management", school_id=s_mgmt.id, hod_name="Dr. Sangeetha Roy", hod_person_id=p_hod_mba.id, email="mbahod@mits.ac.in", source_url="https://mits.ac.in/mba")
    d_mca = Department(code="MCA", name="Computer Applications", school="School of Computing", school_id=s_comp.id, hod_name="Dr. N. Naveen Kumar", hod_person_id=p_hod_mca.id, email="mcahod@mits.ac.in", source_url="https://mits.ac.in/mca")
    session.add_all([d_cse, d_ece, d_eee, d_mech, d_civil, d_cst, d_aiml, d_mba, d_mca])
    session.commit()

    # Faculty
    f1 = Faculty(name="Dr. D. J. Ashoka", designation="Professor & HOD", qualification="Ph.D.", department="CSE", department_id=d_cse.id, person_id=p_hod_cse.id, email="csehod@mits.ac.in", experience_years=18, specialization="Computer Networks & Cloud Computing")
    f2 = Faculty(name="Dr. S. Rajasekaran", designation="Professor & HOD", qualification="Ph.D.", department="ECE", department_id=d_ece.id, person_id=p_hod_ece.id, email="ecehod@mits.ac.in", experience_years=16, specialization="VLSI & Signal Processing")
    f3 = Faculty(name="Dr. K. Sreeramulu", designation="Professor & HOD", qualification="Ph.D.", department="MECH", department_id=d_mech.id, person_id=p_hod_mech.id, email="mechhod@mits.ac.in", experience_years=20, specialization="Thermal Engineering")
    session.add_all([f1, f2, f3])

    # Programs
    session.add_all([
        Program(code="BTECH_CSE", name="B.Tech in Computer Science & Engineering", degree_level="UG", department_id=d_cse.id, duration_years=4, intake=360, regulations_code="R20", source_url="https://mits.ac.in/btech"),
        Program(code="BTECH_ECE", name="B.Tech in Electronics & Communication Engineering", degree_level="UG", department_id=d_ece.id, duration_years=4, intake=240, regulations_code="R20", source_url="https://mits.ac.in/btech"),
        Program(code="BTECH_AIML", name="B.Tech in Artificial Intelligence & Machine Learning", degree_level="UG", department_id=d_aiml.id, duration_years=4, intake=180, regulations_code="R20", source_url="https://mits.ac.in/btech"),
        Program(code="MTECH_CSE", name="M.Tech in Computer Science & Engineering", degree_level="PG", department_id=d_cse.id, duration_years=2, intake=18, regulations_code="R20", source_url="https://mits.ac.in/pg"),
        Program(code="MBA", name="Master of Business Administration", degree_level="PG", department_id=d_mba.id, duration_years=2, intake=180, regulations_code="R20", source_url="https://mits.ac.in/mba"),
        Program(code="MCA", name="Master of Computer Applications", degree_level="PG", department_id=d_mca.id, duration_years=2, intake=120, regulations_code="R20", source_url="https://mits.ac.in/mca"),
        Program(code="PHD_CSE", name="Ph.D. in Computer Science & Engineering", degree_level="PHD", department_id=d_cse.id, duration_years=3, source_url="https://mits.ac.in/research"),
    ])

    # Academic Rules (Attendance, Condonation, Detention, Grading, SGPA/CGPA)
    session.add_all([
        AcademicRule(
            rule_type="ATTENDANCE",
            regulation_code="R20",
            title="Minimum Attendance Requirement",
            content="A student shall be eligible to appear for the semester-end examinations only if he/she acquires a minimum of 75% attendance in aggregate of all subjects in that semester.",
            threshold_percentage=75.0,
            penalties_or_remedies="Students having attendance between 65% and 75% may be condoned on valid medical grounds upon payment of prescribed condonation fee.",
            source_url="https://mits.ac.in/academic-regulations",
        ),
        AcademicRule(
            rule_type="CONDONATION",
            regulation_code="R20",
            title="Condonation of Attendance Shortage",
            content="Condonation of shortage of attendance between 65% and less than 75% in aggregate may be granted by the College Academic Committee on genuine medical grounds.",
            threshold_percentage=65.0,
            penalties_or_remedies="Requires submission of medical certificate within 3 days and payment of condonation fee.",
            source_url="https://mits.ac.in/academic-regulations",
        ),
        AcademicRule(
            rule_type="DETENTION",
            regulation_code="R20",
            title="Detention for Shortage of Attendance",
            content="Students whose attendance is less than 65% in aggregate in any semester shall NOT be eligible to appear for semester-end examinations and are detained.",
            threshold_percentage=65.0,
            penalties_or_remedies="The detained student must repeat that entire semester in the subsequent academic year.",
            source_url="https://mits.ac.in/academic-regulations",
        ),
        AcademicRule(
            rule_type="GRADING",
            regulation_code="R20",
            title="10-Point Absolute Grading System",
            content="MITS follows a 10-point grading system with letter grades: O (Outstanding, 10 GP), A+ (Excellent, 9 GP), A (Very Good, 8 GP), B+ (Good, 7 GP), B (Above Average, 6 GP), C (Average, 5 GP), P (Pass, 4 GP), F (Fail, 0 GP).",
            source_url="https://mits.ac.in/academic-regulations",
        ),
        AcademicRule(
            rule_type="SGPA_CALCULATION",
            regulation_code="R20",
            title="SGPA and CGPA Computation Formula",
            content="SGPA = sum(Credit_i * GradePoint_i) / sum(Credit_i) for subjects in that semester. CGPA = sum(Credit_all * GradePoint_all) / sum(Credit_all).",
            source_url="https://mits.ac.in/academic-regulations",
        ),
    ])

    # Examination Rules
    session.add_all([
        ExamRule(
            rule_type="EVALUATION",
            regulation_code="R20",
            title="Evaluation Weightage: SEE and CIE",
            content="Assessment consists of 60% weightage for Semester End Examination (SEE) and 40% weightage for Continuous Internal Evaluation (CIE).",
            see_weightage=60.0,
            cie_weightage=40.0,
            min_pass_marks="35% in SEE (21 out of 60) and 40% aggregate overall (40 out of 100).",
            source_url="https://mits.ac.in/examination-cell",
        ),
        ExamRule(
            rule_type="REVALUATION",
            regulation_code="R20",
            title="Revaluation and Recounting Procedure",
            content="Students seeking revaluation or recounting of answer scripts must apply through the Examination Cell portal within 15 days from the date of declaration of results.",
            revaluation_deadline_days=15,
            source_url="https://mits.ac.in/examination-cell",
        ),
        ExamRule(
            rule_type="MALPRACTICE",
            regulation_code="R20",
            title="Malpractice Prevention and Penalties",
            content="Possession of unauthorized material, mobile phones, or copying results in cancellation of performance in that paper or rustication as decided by the Malpractice Enquiry Committee.",
            source_url="https://mits.ac.in/examination-cell",
        ),
    ])

    # Admissions
    session.add_all([
        AdmissionRule(
            category="CONVENOR_QUOTA",
            eligibility_criteria="Candidates must qualify in AP EAPCET with 10+2 (Mathematics, Physics, Chemistry) minimum 45% aggregate (40% for reserved categories).",
            entrance_exam="AP EAPCET (Code: MITS)",
            application_process="Allotment through Andhra Pradesh State Council of Higher Education (APSCHE) online counseling.",
            fee_details="Tuition fee fixed as per Andhra Pradesh Higher Education Regulatory and Monitoring Commission (AFRC) norms.",
            source_url="https://mits.ac.in/admissions",
        ),
        AdmissionRule(
            category="MANAGEMENT_QUOTA",
            eligibility_criteria="Minimum 50% in 10+2 (PCM) or valid rank in JEE Main / AP EAPCET. Subject to verification by APSCHE.",
            application_process="Direct application to MITS Admissions Directorate under Category-B seats.",
            source_url="https://mits.ac.in/admissions",
        ),
    ])

    # Placements
    session.add_all([
        PlacementData(
            company_name="Cognizant",
            package_lpa=4.5,
            tier_category="TIER1",
            role_title="GenC / Programmer Analyst",
            total_offers=240,
            source_url="https://mits.ac.in/placements",
        ),
        PlacementData(
            company_name="Amazon",
            package_lpa=24.0,
            tier_category="SUPER_DREAM",
            role_title="Software Development Engineer (SDE)",
            total_offers=5,
            source_url="https://mits.ac.in/placements",
        ),
    ])

    # Facilities
    session.add_all([
        Facility(
            name="Central Library",
            category="LIBRARY",
            location="Main Administrative Block, 2nd & 3rd Floor",
            timings="8:00 AM to 8:00 PM (Monday to Saturday), 9:00 AM to 1:00 PM (Sunday)",
            description="Houses over 80,000 volumes, 12,000 titles, DELNET, IEEE Xplore digital library access, and air-conditioned reading halls.",
            source_url="https://mits.ac.in/library",
        ),
        Facility(
            name="Student Hostels",
            category="HOSTEL",
            location="Campus Premises (Separate blocks for Boys and Girls)",
            timings="Curfew: 6:30 PM for Girls, 8:00 PM for Boys",
            description="Wi-Fi enabled hostel rooms, hygienic mess dining, solar water heaters, 24/7 security with CCTV surveillance.",
            source_url="https://mits.ac.in/hostels",
        ),
        Facility(
            name="Campus Transportation",
            category="TRANSPORT",
            location="MITS Transport Cell",
            timings="Buses arrive by 8:40 AM and depart at 5:00 PM",
            description="Fleet of 45+ buses operating across Madanapalle, Angallu, Rayachoty, Punganur, B.Kothakota, and Kadiri.",
            source_url="https://mits.ac.in/transport",
        ),
    ])

    # Committees
    c_anti_ragging = Committee(
        code="ANTI_RAGGING",
        name="Anti-Ragging Committee",
        category="ANTI_RAGGING",
        purpose="Ensure a ragging-free campus in strict compliance with Supreme Court and AICTE regulations.",
        source_url="https://mits.ac.in/anti-ragging",
    )
    c_icc = Committee(
        code="ICC",
        name="Internal Complaints Committee",
        category="WELFARE",
        purpose="Prevention, prohibition, and redressal of sexual harassment of women employees and students.",
        source_url="https://mits.ac.in/icc",
    )
    session.add_all([c_anti_ragging, c_icc])
    session.commit()

    session.add_all([
        CommitteeMember(committee_id=c_anti_ragging.id, person_id=p_principal.id, role_in_committee="Chairman", is_current=True),
        CommitteeMember(committee_id=c_anti_ragging.id, person_id=p_reg.id, role_in_committee="Member Secretary", is_current=True),
        CommitteeMember(committee_id=c_icc.id, person_id=p_dean_cst.id, role_in_committee="Presiding Officer", is_current=True),
    ])

    # History
    session.add_all([
        InstitutionHistory(
            milestone_year=1998,
            title="Founding of MITS",
            description="Established under the leadership of visionary philanthropist Late Sri N. Krishna Kumar.",
            category="FOUNDATION",
            source_url="https://mits.ac.in/about-mits",
        ),
        InstitutionHistory(
            milestone_year=2014,
            title="Conferment of UGC Autonomous Status",
            description="UGC and JNTUA conferred autonomous institution status to MITS.",
            category="AUTONOMY",
            source_url="https://mits.ac.in/about-mits",
        ),
        InstitutionHistory(
            milestone_year=2023,
            title="NAAC A++ Grade Accreditation",
            description="Accredited with prestigious NAAC A++ Grade for academic excellence and research infrastructure.",
            category="NAAC",
            source_url="https://mits.ac.in/about-mits",
        ),
    ])

    # Contacts
    session.add_all([
        Contact(
            department_or_unit="MITS Main Campus",
            role_or_purpose="General Administration & Campus Inquiries",
            phone="+91-8571-280255",
            email="principal@mits.ac.in",
            location="Post Box No: 14, Kadiri Road, Angallu, Madanapalle - 517325",
            source_url="https://mits.ac.in/contact-us",
        ),
        Contact(
            department_or_unit="Admissions Directorate",
            role_or_purpose="Admissions Helpline & Counseling Guidance",
            phone="+91-9160020789",
            email="admissions@mits.ac.in",
            location="Admissions Block, Ground Floor",
            source_url="https://mits.ac.in/contact-us",
        ),
    ])

    session.commit()
    yield session
    session.close()


# ── 100 Representative College Questions Dataset ─────────────────────────────

QUESTIONS_DATASET = [
    # 1. Leadership & Governance (1-10)
    ("Who is the Chancellor of MITS?", "LEADERSHIP", "Dr. N. Vijaya Bhaskar Choudary"),
    ("Who is the Vice-Chancellor of MITS?", "LEADERSHIP", "Dr. P. Ramanathan"),
    ("Who is the Registrar of the college?", "LEADERSHIP", "Dr. C. Kamal Basha"),
    ("Who is the Principal of MITS?", "LEADERSHIP", "Dr. C. Yuvaraj"),
    ("Who is the Controller of Examinations?", "LEADERSHIP", "Dr. K. Sreenivasulu"),
    ("Who is the Dean of Computing?", "LEADERSHIP", "Dr. R. Kalpana"),
    ("Tell me about the Chancellor of MITS", "LEADERSHIP", "Vijaya Bhaskar"),
    ("Who leads MITS as Vice Chancellor?", "LEADERSHIP", "Ramanathan"),
    ("Who is the Registrar at Madanapalle Institute?", "LEADERSHIP", "Kamal Basha"),
    ("Who heads the Examination Cell as Controller?", "LEADERSHIP", "Sreenivasulu"),

    # 2. Heads of Departments (11-20)
    ("Who is the HOD of CSE?", "HOD", "Dr. D. J. Ashoka"),
    ("Who is the HOD of ECE?", "HOD", "Dr. S. Rajasekaran"),
    ("Who is the HOD of EEE?", "HOD", "Dr. A. V. Pavan Kumar"),
    ("Who is the HOD of Mechanical Engineering?", "HOD", "Dr. K. Sreeramulu"),
    ("Who is the HOD of Civil Engineering?", "HOD", "Dr. Dipankar Roy"),
    ("Who is the Head of Computer Science and Technology?", "HOD", "Dr. M. Sreedevi"),
    ("Who is the HOD of CSE AIML?", "HOD", "Dr. P. Kuppusamy"),
    ("Who is the HOD of MBA department?", "HOD", "Dr. Sangeetha Roy"),
    ("Who is the HOD of MCA department?", "HOD", "Dr. N. Naveen Kumar"),
    ("Who are the Heads of Departments?", "HOD_LIST", "CSE"),

    # 3. Academic Departments (21-30)
    ("Tell me about the Department of Computer Science and Engineering", "DEPARTMENT", "Computer Science & Engineering"),
    ("Tell me about ECE department", "DEPARTMENT", "Electronics & Communication Engineering"),
    ("Details of EEE department", "DEPARTMENT", "Electrical & Electronics Engineering"),
    ("Mechanical engineering department information", "DEPARTMENT", "Mechanical Engineering"),
    ("Civil engineering department overview", "DEPARTMENT", "Civil Engineering"),
    ("CST department details", "DEPARTMENT", "Computer Science & Technology"),
    ("CSE AI and ML department profile", "DEPARTMENT", "Artificial Intelligence & Machine Learning"),
    ("Management studies department overview", "DEPARTMENT", "Management Studies"),
    ("Computer applications department details", "DEPARTMENT", "Computer Applications"),
    ("What school does CSE department belong to?", "DEPARTMENT", "School of Computing"),

    # 4. Faculty Members (31-38)
    ("List faculty members in CSE", "FACULTY", "Dr. D. J. Ashoka"),
    ("Who are the professors in ECE department?", "FACULTY", "Dr. S. Rajasekaran"),
    ("List faculty in Mechanical department", "FACULTY", "Dr. K. Sreeramulu"),
    ("Tell me about faculty Dr. D. J. Ashoka", "FACULTY", "Professor & HOD"),
    ("Specialization of ECE faculty Dr. S. Rajasekaran", "FACULTY", "VLSI"),
    ("Who teaches in Computer Science department?", "FACULTY", "Dr. D. J. Ashoka"),
    ("Who are the faculty in electronics engineering?", "FACULTY", "Dr. S. Rajasekaran"),
    ("Experience of Mechanical HOD Dr. K. Sreeramulu", "PERSON", "20 Years"),

    # 5. Key People Profiles (39-44)
    ("Who is Dr. C. Kamal Basha?", "PERSON", "Registrar"),
    ("Who is Dr. C. Yuvaraj?", "PERSON", "Principal"),
    ("Who is Dr. P. Ramanathan?", "PERSON", "Vice-Chancellor"),
    ("Who is Dr. K. Sreenivasulu?", "PERSON", "Controller of Examinations"),
    ("Who is Dr. R. Kalpana?", "PERSON", "Dean"),
    ("Tell me about Dr. N. Vijaya Bhaskar Choudary", "PERSON", "Chancellor"),

    # 6. Academic Programs (45-54)
    ("What B.Tech programs are offered at MITS?", "PROGRAM", "B.Tech"),
    ("List all undergraduate degrees offered", "PROGRAM", "B.Tech"),
    ("What is the intake for B.Tech CSE?", "PROGRAM", "360"),
    ("What is the intake for B.Tech ECE?", "PROGRAM", "240"),
    ("What PG programs are offered?", "PROGRAM", "M.Tech"),
    ("Does MITS offer MBA?", "PROGRAM", "Master of Business Administration"),
    ("Does MITS offer MCA?", "PROGRAM", "Master of Computer Applications"),
    ("Does MITS offer Ph.D. programs?", "PROGRAM", "Ph.D."),
    ("Duration of B.Tech degree programs", "PROGRAM", "4 Years"),
    ("Duration of M.Tech and MBA programs", "PROGRAM", "2 Years"),

    # 7. Academic Regulations - Attendance & Detention (55-66)
    ("What is the minimum attendance requirement to write semester exams?", "ACADEMIC_RULE", "75%"),
    ("What is the attendance threshold at MITS?", "ACADEMIC_RULE", "75%"),
    ("What happens if attendance is between 65% and 75%?", "ACADEMIC_RULE", "condoned"),
    ("What are the condonation rules for attendance shortage?", "ACADEMIC_RULE", "medical grounds"),
    ("What is the condonation eligibility percentage?", "ACADEMIC_RULE", "65%"),
    ("What happens if a student gets less than 65% attendance?", "ACADEMIC_RULE", "detained"),
    ("When is a student detained due to shortage of attendance?", "ACADEMIC_RULE", "less than 65%"),
    ("Can a detained student write semester exams?", "ACADEMIC_RULE", "NOT be eligible"),
    ("What is the remedy for medical attendance shortage?", "ACADEMIC_RULE", "condonation fee"),
    ("Can attendance below 65% be condoned?", "ACADEMIC_RULE", "detained"),
    ("What are the attendance regulations under R20?", "ACADEMIC_RULE", "75%"),
    ("Explain the attendance condonation procedure", "ACADEMIC_RULE", "medical"),

    # 8. Academic Regulations - Grading & GPA (67-72)
    ("How is SGPA calculated in R20 regulations?", "ACADEMIC_RULE", "SGPA"),
    ("How is CGPA computed?", "ACADEMIC_RULE", "CGPA"),
    ("What is the grading scale used at MITS?", "ACADEMIC_RULE", "10-point"),
    ("What is an Outstanding grade O point value?", "ACADEMIC_RULE", "10 GP"),
    ("What letter grades are awarded in examinations?", "ACADEMIC_RULE", "letter grades"),
    ("What is the credit formula for GPA computation?", "ACADEMIC_RULE", "Credit_i"),

    # 9. Examination Regulations (73-80)
    ("What is the weightage of SEE and CIE in exams?", "EXAM_RULE", "60%"),
    ("What is the internal vs external exam mark distribution?", "EXAM_RULE", "60%"),
    ("What are the minimum pass marks required in semester end exams?", "EXAM_RULE", "35% in SEE"),
    ("What is the minimum aggregate passing marks?", "EXAM_RULE", "40% aggregate"),
    ("What is the revaluation procedure for exam results?", "EXAM_RULE", "Revaluation"),
    ("What is the deadline for applying for revaluation?", "EXAM_RULE", "15 days"),
    ("How many days do students have to apply for recounting?", "EXAM_RULE", "15 days"),
    ("What are the penalties for malpractice in semester exams?", "EXAM_RULE", "cancellation"),

    # 10. Admissions & Quotas (81-86)
    ("What is the eligibility criteria for B.Tech admission through EAPCET?", "ADMISSION", "AP EAPCET"),
    ("What is the counseling code for MITS in EAPCET?", "ADMISSION", "MITS"),
    ("How can I get admission under management quota?", "ADMISSION", "Category-B"),
    ("What is the qualification required for B.Tech admission?", "ADMISSION", "10+2"),
    ("How are convenor quota seats allotted?", "ADMISSION", "APSCHE"),
    ("What are the admission rules for engineering?", "ADMISSION", "45%"),

    # 11. Placements & Careers (87-90)
    ("What is the highest package offered in MITS placements?", "PLACEMENT", "24.0 LPA"),
    ("Which company offered the highest package of 24 LPA?", "PLACEMENT", "Amazon"),
    ("What is the role offered by Amazon in placements?", "PLACEMENT", "Software Development Engineer"),
    ("How many offers were made by Cognizant?", "PLACEMENT", "240"),

    # 12. Campus Facilities (91-94)
    ("What are the timings of the Central Library?", "FACILITY", "8:00 AM to 8:00 PM"),
    ("Where is the Central Library located?", "FACILITY", "Main Administrative Block"),
    ("What are the hostel rules and curfew timings?", "FACILITY", "Curfew"),
    ("What bus routes are available for campus transport?", "FACILITY", "Rayachoty"),

    # 13. Committees, History & Contacts (95-100)
    ("Who chairs the Anti-Ragging Committee?", "COMMITTEE", "Chairman"),
    ("What is the purpose of the Internal Complaints Committee ICC?", "COMMITTEE", "sexual harassment"),
    ("When was MITS founded?", "HISTORY", "1998"),
    ("Who founded MITS in 1998?", "HISTORY", "Late Sri N. Krishna Kumar"),
    ("What accreditation did MITS receive from NAAC?", "HISTORY", "NAAC A++"),
    ("What is the phone number and address of MITS?", "CONTACT", "Angallu, Madanapalle"),
]


@pytest.mark.parametrize("query,expected_entity_type,expected_keyword", QUESTIONS_DATASET)
def test_100_institutional_questions(seeded_db, query, expected_entity_type, expected_keyword):
    """
    Test that every question in the 100-question dataset is correctly routed,
    resolved against official normalized records, and grounded with citations.
    """
    # 1. Route query
    routed = classify_query(query)
    assert routed is not None, f"Router failed on query: {query}"
    assert routed.requires_structured is True, f"Query should require structured lookup: {query}"

    # 2. Resolve query against structured database
    result = resolve_structured_query(routed, seeded_db)
    assert result is not None, f"Knowledge service failed to resolve query: '{query}' with intent: {routed.intent.value}"
    assert result.get("found") is True, f"Knowledge service did not find records for: '{query}'"

    # 3. Assert entity type
    entity_type = result.get("entity_type")
    assert expected_entity_type in entity_type, f"Expected entity type '{expected_entity_type}' in '{entity_type}' for query: {query}"

    # 4. Assert ground truth factual keyword is present in official text
    text = result.get("text", "")
    assert expected_keyword.lower() in text.lower(), (
        f"Grounding verification failed: keyword '{expected_keyword}' not found in resolved text for query: '{query}'\nText was:\n{text}"
    )

    # 5. Assert source citations exist and originate from official MITS domain
    citations = result.get("citations", [])
    assert len(citations) > 0, f"No citations generated for query: {query}"
    assert any("mits.ac.in" in c.get("source_url", "") for c in citations), f"No official MITS source cited for query: {query}"
