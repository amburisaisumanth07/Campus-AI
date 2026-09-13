"""
Admin Coverage API Route for CampusAI.

Provides live coverage breakdown across all 35 institutional categories:
Governance, Leadership, Departments, Faculty, Programs, Academic Rules,
Examinations, Admissions, Placements, Facilities, Committees, and History.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.api.dependencies import get_db
from backend.app.api.deps import get_current_user
from backend.app.core.logging import logger
from backend.app.db.models import (
    User,
    Person,
    Leadership,
    School,
    Department,
    Program,
    Faculty,
    Committee,
    Cell,
    Facility,
    Contact,
    AdmissionRule,
    AcademicRule,
    ExamRule,
    PlacementData,
    Placement,
    InstitutionHistory,
    Announcement,
)

router = APIRouter()


def _safe_count(db: Session, model_cls, filter_expr=None) -> int:
    """Safely count records in a model, returning 0 if table/column does not exist yet."""
    try:
        q = db.query(func.count(model_cls.id))
        if filter_expr is not None:
            q = q.filter(filter_expr)
        return int(q.scalar() or 0)
    except Exception as exc:
        db.rollback()
        logger.debug(f"Count failed for {model_cls.__tablename__}: {exc}")
        return 0


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
def get_institutional_coverage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns live knowledge coverage statistics across all 35 institutional categories.
    """
    categories: List[Dict[str, Any]] = [
        # 1. Governance & Leadership
        {
            "id": 1,
            "category": "Governance & Leadership",
            "model": "Leadership",
            "count": _safe_count(db, Leadership),
            "source_url": "https://mits.ac.in/governance",
            "coverage_area": "Chancellor, Vice-Chancellor, Registrar, Deans, Governing Body",
        },
        # 2. Key People Directory
        {
            "id": 2,
            "category": "Key Institutional People",
            "model": "Person",
            "count": _safe_count(db, Person),
            "source_url": "https://mits.ac.in/faculty-information",
            "coverage_area": "Profiles, qualifications, emails, phone numbers of officials",
        },
        # 3. Schools & Academic Structure
        {
            "id": 3,
            "category": "Schools & Academic Structure",
            "model": "School",
            "count": _safe_count(db, School),
            "source_url": "https://mits.ac.in/academics",
            "coverage_area": "Computing, Engineering, Management, Science & Humanities",
        },
        # 4. Academic Departments
        {
            "id": 4,
            "category": "Academic Departments",
            "model": "Department",
            "count": _safe_count(db, Department),
            "source_url": "https://mits.ac.in/departmentheads",
            "coverage_area": "All 10+ engineering, computing, and management departments",
        },
        # 5. Heads of Departments (HODs)
        {
            "id": 5,
            "category": "Heads of Departments (HODs)",
            "model": "Department",
            "count": _safe_count(db, Department, Department.hod_name.isnot(None)),
            "source_url": "https://mits.ac.in/departmentheads",
            "coverage_area": "Authoritative departmental leadership assignments",
        },
        # 6. Faculty Directory
        {
            "id": 6,
            "category": "Faculty Directory",
            "model": "Faculty",
            "count": _safe_count(db, Faculty),
            "source_url": "https://mits.ac.in/faculty-information",
            "coverage_area": "Teaching professors, associate/assistant professors",
        },
        # 7. Undergraduate Programs (B.Tech)
        {
            "id": 7,
            "category": "Undergraduate Programs (UG)",
            "model": "Program",
            "count": _safe_count(db, Program, Program.degree_level == "UG"),
            "source_url": "https://mits.ac.in/btech",
            "coverage_area": "B.Tech in CSE, AI, Data Science, Cyber Security, ECE, EEE, Mech, Civil",
        },
        # 8. Postgraduate Programs (M.Tech, MBA, MCA)
        {
            "id": 8,
            "category": "Postgraduate Programs (PG)",
            "model": "Program",
            "count": _safe_count(db, Program, Program.degree_level == "PG"),
            "source_url": "https://mits.ac.in/pg",
            "coverage_area": "M.Tech, MBA, MCA program details and intake",
        },
        # 9. Doctoral Programs (Ph.D.)
        {
            "id": 9,
            "category": "Doctoral Research Programs (Ph.D.)",
            "model": "Program",
            "count": _safe_count(db, Program, Program.degree_level == "PHD"),
            "source_url": "https://mits.ac.in/research",
            "coverage_area": "Ph.D. specializations, research centers, supervisors",
        },
        # 10. Academic Regulations - Attendance
        {
            "id": 10,
            "category": "Academic Regulations - Attendance",
            "model": "AcademicRule",
            "count": _safe_count(db, AcademicRule, AcademicRule.rule_type == "ATTENDANCE"),
            "source_url": "https://mits.ac.in/academic-regulations",
            "coverage_area": "75% mandatory attendance threshold and tracking",
        },
        # 11. Academic Regulations - Condonation
        {
            "id": 11,
            "category": "Academic Regulations - Condonation",
            "model": "AcademicRule",
            "count": _safe_count(db, AcademicRule, AcademicRule.rule_type == "CONDONATION"),
            "source_url": "https://mits.ac.in/academic-regulations",
            "coverage_area": "65% to 75% medical condonation rules and fees",
        },
        # 12. Academic Regulations - Detention
        {
            "id": 12,
            "category": "Academic Regulations - Detention",
            "model": "AcademicRule",
            "count": _safe_count(db, AcademicRule, AcademicRule.rule_type == "DETENTION"),
            "source_url": "https://mits.ac.in/academic-regulations",
            "coverage_area": "Below 65% semester detention and repeat rules",
        },
        # 13. Academic Regulations - Grading Scale
        {
            "id": 13,
            "category": "Academic Regulations - Grading Scale",
            "model": "AcademicRule",
            "count": _safe_count(db, AcademicRule, AcademicRule.rule_type == "GRADING"),
            "source_url": "https://mits.ac.in/academic-regulations",
            "coverage_area": "10-point grade scale, letter grades (O, A+, A, B+, B, C, F)",
        },
        # 14. Academic Regulations - SGPA / CGPA
        {
            "id": 14,
            "category": "Academic Regulations - SGPA / CGPA",
            "model": "AcademicRule",
            "count": _safe_count(db, AcademicRule, AcademicRule.rule_type.in_(["SGPA_CALCULATION", "CGPA_CALCULATION"])),
            "source_url": "https://mits.ac.in/academic-regulations",
            "coverage_area": "Credit calculation, GPA formulae, classification of degree",
        },
        # 15. Examination Rules - Evaluation & Passing
        {
            "id": 15,
            "category": "Examination Rules - Evaluation & Passing",
            "model": "ExamRule",
            "count": _safe_count(db, ExamRule, ExamRule.rule_type == "EVALUATION"),
            "source_url": "https://mits.ac.in/examination-cell",
            "coverage_area": "SEE/CIE weightage, internal assessment, minimum pass marks",
        },
        # 16. Examination Rules - Revaluation & Recounting
        {
            "id": 16,
            "category": "Examination Rules - Revaluation & Recounting",
            "model": "ExamRule",
            "count": _safe_count(db, ExamRule, ExamRule.rule_type.in_(["REVALUATION", "RECOUNTING"])),
            "source_url": "https://mits.ac.in/examination-cell",
            "coverage_area": "Revaluation fee, deadlines, and grade challenge procedure",
        },
        # 17. Examination Rules - Malpractice
        {
            "id": 17,
            "category": "Examination Rules - Malpractice",
            "model": "ExamRule",
            "count": _safe_count(db, ExamRule, ExamRule.rule_type == "MALPRACTICE"),
            "source_url": "https://mits.ac.in/examination-cell",
            "coverage_area": "Penalties, expulsion, disciplinary committee procedures",
        },
        # 18. Admissions - Convenor Quota (EAPCET)
        {
            "id": 18,
            "category": "Admissions - Convenor Quota (EAPCET)",
            "model": "AdmissionRule",
            "count": _safe_count(db, AdmissionRule, AdmissionRule.category == "CONVENOR_QUOTA"),
            "source_url": "https://mits.ac.in/admissions",
            "coverage_area": "State counseling, EAPCET / ICET code MITS, rank cutoffs",
        },
        # 19. Admissions - Management Quota
        {
            "id": 19,
            "category": "Admissions - Management Quota (Category B)",
            "model": "AdmissionRule",
            "count": _safe_count(db, AdmissionRule, AdmissionRule.category == "MANAGEMENT_QUOTA"),
            "source_url": "https://mits.ac.in/admissions",
            "coverage_area": "Category B admission procedure, merit list, fee guidelines",
        },
        # 20. Admissions - Lateral Entry
        {
            "id": 20,
            "category": "Admissions - Lateral Entry (ECET)",
            "model": "AdmissionRule",
            "count": _safe_count(db, AdmissionRule, AdmissionRule.category == "LATERAL_ENTRY"),
            "source_url": "https://mits.ac.in/admissions",
            "coverage_area": "Direct entry into 2nd year B.Tech for diploma holders",
        },
        # 21. Admissions - International / NRI
        {
            "id": 21,
            "category": "Admissions - NRI / International",
            "model": "AdmissionRule",
            "count": _safe_count(db, AdmissionRule, AdmissionRule.category == "NRI_INTERNATIONAL"),
            "source_url": "https://mits.ac.in/admissions",
            "coverage_area": "Foreign national admissions, passport verification, equivalence",
        },
        # 22. Placements - Recruiter Statistics
        {
            "id": 22,
            "category": "Placements - Recruiter Statistics",
            "model": "PlacementData",
            "count": _safe_count(db, PlacementData),
            "source_url": "https://mits.ac.in/placements",
            "coverage_area": "Top recruiters, highest package (LPA), average package, total offers",
        },
        # 23. Placements - Active Drives & Opportunities
        {
            "id": 23,
            "category": "Placements - Drives & Notifications",
            "model": "Placement",
            "count": _safe_count(db, Placement),
            "source_url": "https://mits.ac.in/placements",
            "coverage_area": "Campus recruitment drive dates, eligibility criteria, CTC packages",
        },
        # 24. Facilities - Central Library
        {
            "id": 24,
            "category": "Facilities - Central Library",
            "model": "Facility",
            "count": _safe_count(db, Facility, Facility.category == "LIBRARY"),
            "source_url": "https://mits.ac.in/library",
            "coverage_area": "Operating hours, e-resources, DELNET, book borrowing rules",
        },
        # 25. Facilities - Student Hostels
        {
            "id": 25,
            "category": "Facilities - Student Hostels",
            "model": "Facility",
            "count": _safe_count(db, Facility, Facility.category == "HOSTEL"),
            "source_url": "https://mits.ac.in/hostels",
            "coverage_area": "Boys and girls hostels, curfew timings, mess facilities, wardens",
        },
        # 26. Facilities - Transportation & Bus Routes
        {
            "id": 26,
            "category": "Facilities - Transportation",
            "model": "Facility",
            "count": _safe_count(db, Facility, Facility.category == "TRANSPORT"),
            "source_url": "https://mits.ac.in/transport",
            "coverage_area": "College bus routes across Madanapalle, Angallu, Rayachoty, Punganur",
        },
        # 27. Facilities - Sports & Gymnasium
        {
            "id": 27,
            "category": "Facilities - Sports & Gymnasium",
            "model": "Facility",
            "count": _safe_count(db, Facility, Facility.category == "SPORTS"),
            "source_url": "https://mits.ac.in/sports",
            "coverage_area": "Indoor and outdoor sports facilities, gym timings, tournaments",
        },
        # 28. Facilities - Medical & Health Center
        {
            "id": 28,
            "category": "Facilities - Medical & Health Center",
            "model": "Facility",
            "count": _safe_count(db, Facility, Facility.category == "MEDICAL"),
            "source_url": "https://mits.ac.in/health-center",
            "coverage_area": "Campus dispensary, resident doctor, ambulance, first aid",
        },
        # 29. Facilities - Canteen & Cafeteria
        {
            "id": 29,
            "category": "Facilities - Canteen & Cafeteria",
            "model": "Facility",
            "count": _safe_count(db, Facility, Facility.category == "CANTEEN"),
            "source_url": "https://mits.ac.in/campus-life",
            "coverage_area": "Student dining, hygienic food stalls, operating hours",
        },
        # 30. Statutory Committees - Academic Council & BoS
        {
            "id": 30,
            "category": "Committees - Academic Council & BoS",
            "model": "Committee",
            "count": _safe_count(db, Committee, Committee.category == "ACADEMIC"),
            "source_url": "https://mits.ac.in/governance",
            "coverage_area": "Board of Studies (BoS), Academic Council curriculum approvals",
        },
        # 31. Welfare Committees - Anti-Ragging & ICC
        {
            "id": 31,
            "category": "Committees - Anti-Ragging & ICC",
            "model": "Committee",
            "count": _safe_count(db, Committee, Committee.category.in_(["ANTI_RAGGING", "WELFARE", "GRIEVANCE"])),
            "source_url": "https://mits.ac.in/anti-ragging",
            "coverage_area": "Anti-Ragging Squad, Internal Complaints Committee (ICC), Grievance Redressal",
        },
        # 32. Student Support Cells - NSS, NCC, Innovation
        {
            "id": 32,
            "category": "Student Support Cells (NSS, NCC, Innovation)",
            "model": "Cell",
            "count": _safe_count(db, Cell),
            "source_url": "https://mits.ac.in/cells",
            "coverage_area": "NSS unit, NCC wing, Innovation & Incubation Cell (IIC), Women Empowerment",
        },
        # 33. Institutional History & Accreditations
        {
            "id": 33,
            "category": "Institutional History & Milestones",
            "model": "InstitutionHistory",
            "count": _safe_count(db, InstitutionHistory),
            "source_url": "https://mits.ac.in/about-mits",
            "coverage_area": "1998 Founding, UGC Autonomy 2014, NAAC A++, NBA, Deemed to be University",
        },
        # 34. Official Institutional Contacts
        {
            "id": 34,
            "category": "Official Directory & Contacts",
            "model": "Contact",
            "count": _safe_count(db, Contact),
            "source_url": "https://mits.ac.in/contact-us",
            "coverage_area": "Emergency phone numbers, department helplines, administrative emails",
        },
        # 35. Official College Announcements
        {
            "id": 35,
            "category": "Official Circulars & Notices",
            "model": "Announcement",
            "count": _safe_count(db, Announcement),
            "source_url": "https://mits.ac.in/circulars",
            "coverage_area": "Active college notifications, exam notices, holiday announcements",
        },
    ]

    total_categories = len(categories)
    covered_categories = sum(1 for c in categories if c["count"] > 0)
    coverage_percentage = round((covered_categories / total_categories) * 100, 1)
    total_records = sum(c["count"] for c in categories)

    return {
        "total_categories": total_categories,
        "covered_categories": covered_categories,
        "coverage_percentage": coverage_percentage,
        "total_records": total_records,
        "categories": categories,
    }
