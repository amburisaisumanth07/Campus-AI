"""
Structured Knowledge Service for CampusAI.

Provides normalized database query resolvers and formatted prompt context blocks
with complete source provenance across all 35 institutional categories.
"""
from datetime import datetime, timezone
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, not_, func

from backend.app.core.logging import logger
from backend.app.core.canonical_departments import (
    CANONICAL_DEPARTMENTS,
    CANONICAL_DEPARTMENTS_BY_ID,
    CanonicalDepartment,
    resolve_canonical_department,
)
from backend.app.db.models import (
    Person,
    Leadership,
    RoleRecord,
    School,
    Department,
    Program,
    Faculty,
    FacultyDepartment,
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
from backend.app.rag.router import RoutedQuery, QueryIntent, extract_department


OFFICIAL_MITS_BASE_URL = "https://mits.ac.in"


def _make_citation(
    title: str,
    source_url: Optional[str],
    category: str = "Institutional Record",
    page_number: int = 1,
) -> Dict[str, Any]:
    return {
        "title": title or "Official MITS Institutional Record",
        "source_url": source_url or OFFICIAL_MITS_BASE_URL,
        "page_number": page_number,
        "source_pages": [page_number],
        "category": category,
        "document_type": "STRUCTURED_RECORD",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "confidence": 1.0,
    }


# ── Resolvers ─────────────────────────────────────────────────────────────────

def resolve_leadership(
    db: Session,
    role_code: Optional[str] = None,
    is_current: bool = True,
) -> Optional[Dict[str, Any]]:
    """Resolve college-wide leadership (Chancellor, VC, Registrar, Principal, Deans, etc.)."""
    query = db.query(Leadership).join(Person).options(joinedload(Leadership.person))
    if is_current:
        query = query.filter(Leadership.is_current == True)  # noqa: E712

    if role_code:
        # Match role code
        code_upper = role_code.strip().upper()
        if code_upper in ("VC", "VICE-CHANCELLOR"):
            code_upper = "VICE_CHANCELLOR"
        query = query.filter(Leadership.role_code == code_upper)

    leaders = query.order_by(Leadership.order_index, Leadership.id).all()
    if not leaders:
        return None

    lines = [
        "=== OFFICIAL MITS LEADERSHIP DIRECTORY ===",
        f"Status: Verified Current ({datetime.now(timezone.utc).strftime('%Y-%m')})",
        f"Source: {OFFICIAL_MITS_BASE_URL}/governance",
        "",
    ]
    citations = []
    for lead in leaders:
        p = lead.person
        title_str = f"{p.title} " if p.title else ""
        qual_str = f", {p.qualification}" if p.qualification else ""
        lines.append(f"• Role: {lead.role_title} ({lead.role_code})")
        lines.append(f"  Name: {title_str}{p.name}{qual_str}")
        if p.email:
            lines.append(f"  Email: {p.email}")
        if p.phone:
            lines.append(f"  Phone: {p.phone}")
        if lead.term_start:
            lines.append(f"  Tenure: {lead.term_start} to {lead.term_end or 'Present'}")
        if lead.source_url:
            lines.append(f"  Source: {lead.source_url}")
        lines.append("")

        citations.append(
            _make_citation(
                title=f"MITS Leadership: {lead.role_title} - {p.name}",
                source_url=lead.source_url or f"{OFFICIAL_MITS_BASE_URL}/governance",
                category="Governance",
            )
        )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": f"LEADERSHIP_{role_code.upper()}" if role_code else "LEADERSHIP",
        "found": True,
    }


def resolve_department(
    db: Session,
    code_or_name: str,
) -> Optional[Dict[str, Any]]:
    """Resolve department details including HOD, school, programs, and contact."""
    canon = resolve_canonical_department(code_or_name)
    dept = None
    if canon:
        dept = db.query(Department).filter(
            or_(
                Department.id == canon.department_id,
                Department.code == canon.code,
            )
        ).first()

    if not dept:
        code_upper = code_or_name.strip().upper()
        dept = db.query(Department).filter(
            or_(
                Department.code == code_upper,
                Department.name.ilike(f"%{code_or_name.strip()}%"),
            )
        ).first()

    if not dept and not canon:
        return None

    official_name = canon.official_name if canon else dept.name
    official_code = canon.code if canon else dept.code
    school_name = canon.school if canon else (dept.school or "N/A")
    official_url = canon.official_url if canon else (dept.source_url or f"{OFFICIAL_MITS_BASE_URL}/{dept.code.lower()}")
    hod_name = canon.hod_name if canon else (dept.hod_name or dept.hod if dept else "N/A")
    hod_desig = canon.hod_designation if canon else (dept.hod_designation if dept else "Head of Department")

    lines = [
        f"=== OFFICIAL MITS DEPARTMENT RECORD: {official_name} ({official_code}) ===",
        f"Department: {official_name}",
        f"Department Code: {official_code}",
        f"School: {school_name}",
        f"Head of Department (HOD): {hod_name}",
        f"HOD Designation: {hod_desig}",
    ]
    if dept and dept.description:
        lines.append(f"Overview: {dept.description}")

    if dept and dept.email:
        lines.append(f"Department Email: {dept.email}")
    if dept and dept.phone:
        lines.append(f"Contact Phone: {dept.phone}")

    # Programs offered
    dept_id = canon.department_id if canon else (dept.id if dept else None)
    if dept_id:
        programs = db.query(Program).filter(
            Program.department_id == dept_id,
            Program.is_active == True,  # noqa: E712
        ).all()
        if programs:
            lines.append("")
            lines.append("Programs Offered:")
            for prg in programs:
                intake_str = f" (Intake: {prg.intake})" if prg.intake else ""
                lines.append(f"  • [{prg.degree_level}] {prg.name} - {prg.duration_years} Years{intake_str}")

    lines.append("")
    lines.append(f"Official Department URL: {official_url}")

    citations = [
        _make_citation(
            title=f"MITS Department of {official_name} ({official_code})",
            source_url=official_url,
            category="Department Information",
        )
    ]

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "DEPARTMENT",
        "entity_name": official_name,
        "found": True,
    }


def resolve_hod(
    db: Session,
    dept_code: Optional[str] = None,
    is_historical: bool = False,
) -> Optional[Dict[str, Any]]:
    """Resolve Head of Department (HOD) for a given department or list all HODs."""
    if dept_code:
        canon = resolve_canonical_department(dept_code)
        dept = None
        if canon:
            dept = db.query(Department).filter(
                or_(
                    Department.id == canon.department_id,
                    Department.code == canon.code,
                )
            ).first()

        if not dept:
            code_upper = dept_code.strip().upper()
            dept = db.query(Department).filter(
                or_(
                    Department.code == code_upper,
                    Department.name.ilike(f"%{dept_code.strip()}%"),
                )
            ).first()

        if not dept and not canon:
            return None

        official_name = canon.official_name if canon else (dept.name if dept else dept_code)
        official_code = canon.code if canon else (dept.code if dept else dept_code)
        hod_name = canon.hod_name if canon else (dept.hod_name or dept.hod if dept else "N/A")
        hod_desig = canon.hod_designation if canon else (dept.hod_designation if dept else "Head of Department")
        official_url = canon.source_url if canon else f"{OFFICIAL_MITS_BASE_URL}/departmentheads"

        if is_historical:
            lines = [
                f"Department:\n{official_name} ({official_code})" if official_code else f"Department:\n{official_name}",
                f"\nHistorical HOD Information:",
                f"Past administrative records for the Department of {official_name} are archived in institutional history. The current official HOD administering the department is {hod_name} ({hod_desig}).",
                f"\nStatus:\nHistorical record",
                f"\nSource:\nOfficial MITS {official_code} Department",
                f"Official Source: {official_url}",
            ]
        else:
            lines = [
                f"Department:\n{official_name} ({official_code})" if official_code else f"Department:\n{official_name}",
                f"\nCurrent HOD:\n{hod_name}",
                f"\nDesignation:\n{hod_desig}",
            ]
            fac = None
            if dept and dept.hod_id:
                fac = db.query(Faculty).filter(Faculty.id == dept.hod_id, Faculty.is_active == True).first()
            if not fac and dept:
                fac = db.query(Faculty).filter(
                    Faculty.department_id == dept.id,
                    Faculty.name.ilike(f"%{hod_name.split()[-1]}%"),
                    Faculty.is_active == True,
                ).first()

            if fac:
                if fac.qualification:
                    lines.append(f"Qualification: {fac.qualification}")
                if fac.email:
                    lines.append(f"Email: {fac.email}")
                if fac.phone:
                    lines.append(f"Phone: {fac.phone}")
                if fac.profile_url:
                    lines.append(f"Profile: {fac.profile_url}")
            elif dept and dept.email:
                lines.append(f"Email: {dept.email}")

            lines.append(f"\nSource:\nOfficial MITS {official_code} Department")
            lines.append("\nStatus:\nCurrent official source")
            lines.append(f"Official Source: {official_url}")

        citations = [
            _make_citation(
                title=f"Head of Department - {official_name} ({official_code})",
                source_url=official_url,
                category="Department Heads",
            )
        ]
        return {
            "text": "\n".join(lines).strip(),
            "citations": citations,
            "entity_type": "HOD",
            "entity_name": hod_name,
            "found": True,
        }

    # All HODs - list canonical 14 department heads from official MITS records
    lines = [
        "=== OFFICIAL MITS HEADS OF DEPARTMENTS (HODs) ===",
        f"Source: {OFFICIAL_MITS_BASE_URL}/departmentheads",
        "Status: Current official source",
        "",
    ]
    citations = [
        _make_citation(
            title="MITS Heads of Departments Directory",
            source_url=f"{OFFICIAL_MITS_BASE_URL}/departmentheads",
            category="Department Heads",
        )
    ]
    for code, c_dept in CANONICAL_DEPARTMENTS.items():
        if code == "BSH":
            lines.append(f"• Basic Sciences & Humanities (BSH):")
            for div, h_info in c_dept.division_heads.items():
                lines.append(f"    - {div}: {h_info}")
        else:
            lines.append(f"• {c_dept.code} ({c_dept.official_name}): {c_dept.hod_name} ({c_dept.hod_designation})")

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "HOD_LIST",
        "found": True,
    }


def resolve_faculty(
    db: Session,
    dept_code: Optional[str] = None,
    person_name: Optional[str] = None,
    designation_filter: Optional[str] = None,
    is_count_query: bool = False,
    limit: Optional[int] = None,
    is_historical: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Resolve faculty members by department or specific name using exact SQL queries only.
    Never uses semantic similarity search. Returns 100% complete faculty rosters.
    Follows the Department-Scoped Answer Contract.
    """
    if is_historical:
        query = db.query(Faculty).filter(Faculty.is_active == False)
    else:
        query = db.query(Faculty).filter(Faculty.is_active == True, Faculty.is_valid == True)  # noqa: E712

    canon_dept: Optional[CanonicalDepartment] = None
    dept_obj: Optional[Department] = None

    if dept_code:
        canon_dept = resolve_canonical_department(dept_code)
        if not canon_dept and dept_code.upper() in CANONICAL_DEPARTMENTS:
            canon_dept = CANONICAL_DEPARTMENTS[dept_code.upper()]

        if canon_dept:
            dept_obj = db.query(Department).filter(
                or_(
                    Department.id == canon_dept.department_id,
                    Department.code == canon_dept.code,
                )
            ).first()
            # STRICT SQL: filter only on the exact canonical department_id
            query = query.filter(Faculty.department_id == canon_dept.department_id)
        else:
            # Fallback by code or exact department name
            dept_obj = db.query(Department).filter(
                or_(
                    Department.code == dept_code.strip().upper(),
                    Department.name == dept_code.strip(),
                )
            ).first()
            if dept_obj:
                query = query.filter(Faculty.department_id == dept_obj.id)
            else:
                return {
                    "text": f"The official MITS data currently contains no department matching '{dept_code}'.",
                    "citations": [],
                    "entity_type": "FACULTY",
                    "found": False,
                }

    if person_name:
        clean_name = re.sub(r"^(Dr\.?|Prof\.?|Mr\.?|Mrs\.?|Ms\.?)\s+", "", person_name.strip(), flags=re.IGNORECASE)
        query = query.filter(Faculty.name.ilike(f"%{clean_name}%"))

    # Handle designation filters (professors, assistant professors, associate professors)
    if designation_filter == "PROFESSOR":
        query = query.filter(
            and_(
                Faculty.designation.ilike("%professor%"),
                not_(Faculty.designation.ilike("%assistant%")),
                not_(Faculty.designation.ilike("%asst%")),
                not_(Faculty.designation.ilike("%associate%")),
                not_(Faculty.designation.ilike("%assoc%")),
            )
        )
    elif designation_filter == "ASSISTANT_PROFESSOR":
        query = query.filter(
            or_(
                Faculty.designation.ilike("%assistant professor%"),
                Faculty.designation.ilike("%asst%professor%"),
                Faculty.designation.ilike("%sr. assistant professor%"),
                Faculty.designation.ilike("%senior assistant professor%"),
            )
        )
    elif designation_filter == "ASSOCIATE_PROFESSOR":
        query = query.filter(
            or_(
                Faculty.designation.ilike("%associate professor%"),
                Faculty.designation.ilike("%assoc%professor%"),
            )
        )

    # Order faculty logically by designation prestige, then name
    faculty_list = query.order_by(Faculty.designation, Faculty.name).all()

    # Department-Scoped Answer Contract
    dept_name = canon_dept.official_name if canon_dept else (dept_obj.name if dept_obj else "MITS Academic Department")
    dept_code_str = canon_dept.code if canon_dept else (dept_obj.code if dept_obj else "")
    hod_name = canon_dept.hod_name if canon_dept else (dept_obj.hod_name or dept_obj.hod if dept_obj else "N/A")
    source_url = canon_dept.official_url if canon_dept else (dept_obj.source_url if dept_obj else f"{OFFICIAL_MITS_BASE_URL}/faculty-information")

    status_label = "Historical records" if is_historical else "Current official source"

    if not faculty_list:
        msg = (
            f"The official MITS archive currently contains no inactive historical faculty records for this department ({dept_name})."
            if is_historical
            else f"The official MITS data currently contains no faculty records for this department ({dept_name})."
        )
        return {
            "text": msg,
            "citations": [
                _make_citation(
                    title=f"MITS Official Faculty Directory - {dept_name}",
                    source_url=source_url,
                    category="Faculty",
                )
            ],
            "entity_type": "FACULTY",
            "found": True,
        }

    lines = [
        f"Department:\n{dept_name} ({dept_code_str})" if dept_code_str else f"Department:\n{dept_name}",
        f"\nCurrent HOD:\n{hod_name}",
        f"\nTotal Faculty:\n{len(faculty_list)}",
        f"\nStatus:\n{status_label}",
        "\nFaculty:",
    ]

    for idx, f in enumerate(faculty_list, 1):
        qual_str = f" ({f.qualification})" if f.qualification else ""
        spec_str = f" | Specialization: {f.specialization}" if f.specialization else ""
        email_str = f" | Email: {f.email}" if f.email else ""
        profile_str = f" | Profile: {f.profile_url}" if f.profile_url else ""
        lines.append(f"{idx}. {f.name} - {f.designation or 'Faculty Member'}{qual_str}{spec_str}{email_str}{profile_str}")

    lines.append(f"\nSource:\nOfficial MITS {dept_code_str or dept_name} Department")
    lines.append(f"\nSources:\n{source_url}")

    citations = [
        _make_citation(
            title=f"MITS Faculty Directory - {dept_name}",
            source_url=source_url,
            category="Faculty",
        )
    ]

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "FACULTY",
        "total_faculty": len(faculty_list),
        "found": True,
    }


def resolve_person(
    db: Session,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Resolve person record across leadership, faculty, and committees."""
    clean_name = re.sub(r"^(Dr\.?|Prof\.?|Mr\.?|Mrs\.?|Ms\.?)\s+", "", name.strip(), flags=re.IGNORECASE)
    person = db.query(Person).filter(
        or_(
            Person.name.ilike(f"%{clean_name}%"),
            Person.email.ilike(f"%{clean_name}%"),
        )
    ).first()

    if not person:
        # Fallback to Faculty table
        faculty = db.query(Faculty).filter(Faculty.name.ilike(f"%{clean_name}%")).first()
        if faculty:
            return resolve_faculty(db, person_name=faculty.name)
        return None

    title_str = f"{person.title} " if person.title else ""
    qual_str = f", {person.qualification}" if person.qualification else ""
    lines = [
        f"=== OFFICIAL MITS PERSON PROFILE: {title_str}{person.name}{qual_str} ===",
    ]
    if person.designation:
        lines.append(f"Designation: {person.designation}")
    if person.email:
        lines.append(f"Email: {person.email}")
    if person.phone:
        lines.append(f"Phone: {person.phone}")
    if person.bio:
        lines.append(f"Bio/Background: {person.bio}")

    # Leadership roles
    roles = db.query(Leadership).filter(
        Leadership.person_id == person.id,
        Leadership.is_current == True,  # noqa: E712
    ).all()
    if roles:
        lines.append("Leadership Roles:")
        for r in roles:
            lines.append(f"  • {r.role_title} ({r.role_code})")

    # Faculty details
    fac = db.query(Faculty).filter(
        or_(
            Faculty.person_id == person.id,
            Faculty.name == person.name,
        )
    ).first()
    if fac:
        if fac.department:
            lines.append(f"Academic Department: {fac.department}")
        if fac.experience_years:
            lines.append(f"Teaching Experience: {fac.experience_years} Years")
        if fac.specialization:
            lines.append(f"Specialization: {fac.specialization}")

    # Committees
    memberships = db.query(CommitteeMember).join(Committee).filter(
        CommitteeMember.person_id == person.id,
        CommitteeMember.is_current == True,  # noqa: E712
    ).all()
    if memberships:
        lines.append("Committee Appointments:")
        for m in memberships:
            lines.append(f"  • {m.committee.name}: {m.role_in_committee}")

    source_url = person.profile_url or person.source_url or OFFICIAL_MITS_BASE_URL
    lines.append(f"Official Profile URL: {source_url}")

    citations = [
        _make_citation(
            title=f"MITS Person Profile: {person.name}",
            source_url=source_url,
            category="Directory",
        )
    ]

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "PERSON",
        "entity_name": person.name,
        "found": True,
    }


def resolve_programs(
    db: Session,
    dept_code: Optional[str] = None,
    degree_level: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve educational programs (B.Tech, M.Tech, MBA, MCA, Ph.D.)."""
    query = db.query(Program).filter(Program.is_active == True)  # noqa: E712

    if dept_code:
        code_upper = dept_code.strip().upper()
        dept = db.query(Department).filter(Department.code == code_upper).first()
        if dept:
            query = query.filter(Program.department_id == dept.id)

    if degree_level:
        query = query.filter(Program.degree_level == degree_level.strip().upper())

    programs = query.order_by(Program.degree_level, Program.name).all()
    if not programs:
        return None

    lines = [
        "=== OFFICIAL MITS ACADEMIC PROGRAMS ===",
        f"Total Programs: {len(programs)}",
        "",
    ]
    citations = []
    for prg in programs:
        dept_str = f" | Dept: {prg.department_rel.code}" if prg.department_rel else ""
        intake_str = f" | Intake: {prg.intake}" if prg.intake else ""
        reg_str = f" | Regulation: {prg.regulations_code}" if prg.regulations_code else ""
        lines.append(f"• [{prg.degree_level}] {prg.name} ({prg.code})")
        lines.append(f"  Duration: {prg.duration_years} Years{dept_str}{intake_str}{reg_str}")
        if prg.eligibility:
            lines.append(f"  Eligibility: {prg.eligibility}")
        lines.append("")

        if len(citations) < 4:
            citations.append(
                _make_citation(
                    title=f"MITS Program: {prg.name} ({prg.code})",
                    source_url=prg.source_url or f"{OFFICIAL_MITS_BASE_URL}/programs",
                    category="Academic Programs",
                )
            )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "PROGRAM",
        "found": True,
    }


def resolve_academic_rules(
    db: Session,
    rule_type: Optional[str] = None,
    regulation_code: str = "R20",
) -> Optional[Dict[str, Any]]:
    """
    Resolve academic rules (Attendance 75%, Condonation 65-75%, Detention, Grading, SGPA/CGPA).
    """
    query = db.query(AcademicRule).filter(AcademicRule.is_current == True)  # noqa: E712

    if rule_type:
        rt_upper = rule_type.strip().upper()
        if rt_upper in ("ATTENDANCE", "CONDONATION", "DETENTION"):
            query = query.filter(AcademicRule.rule_type.in_(["ATTENDANCE", "CONDONATION", "DETENTION"]))
        elif rt_upper in ("SGPA_CALCULATION", "CGPA_CALCULATION", "GPA"):
            query = query.filter(AcademicRule.rule_type.in_(["SGPA_CALCULATION", "CGPA_CALCULATION"]))
        else:
            query = query.filter(AcademicRule.rule_type == rt_upper)

    rules = query.order_by(AcademicRule.id).all()
    if not rules:
        return None

    lines = [
        f"=== OFFICIAL MITS ACADEMIC REGULATIONS ({regulation_code}) ===",
        f"Authority: MITS Autonomous Academic Council / Regulations Handbook",
        "",
    ]
    citations = []
    for r in rules:
        lines.append(f"• Rule Type: {r.rule_type} — {r.title}")
        if r.threshold_percentage is not None:
            lines.append(f"  Threshold Requirement: {r.threshold_percentage}%")
        lines.append(f"  Rule Policy: {r.content}")
        if r.penalties_or_remedies:
            lines.append(f"  Remedy/Consequences: {r.penalties_or_remedies}")
        if r.source_url:
            lines.append(f"  Official Source: {r.source_url}")
        lines.append("")

        citations.append(
            _make_citation(
                title=f"MITS Academic Regulation: {r.title}",
                source_url=r.source_url or f"{OFFICIAL_MITS_BASE_URL}/academic-regulations",
                category="Academic Rules",
            )
        )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "ACADEMIC_RULE",
        "found": True,
    }


def resolve_exam_rules(
    db: Session,
    rule_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve examination rules (SEE/CIE weightage, Revaluation, Recounting, Malpractice)."""
    query = db.query(ExamRule).filter(ExamRule.is_current == True)  # noqa: E712

    if rule_type:
        query = query.filter(ExamRule.rule_type == rule_type.strip().upper())

    rules = query.order_by(ExamRule.id).all()
    if not rules:
        return None

    lines = [
        "=== OFFICIAL MITS EXAMINATION CELL REGULATIONS ===",
        "Authority: Controller of Examinations (CoE), MITS Autonomous",
        "",
    ]
    citations = []
    for r in rules:
        lines.append(f"• Policy: {r.title} ({r.rule_type})")
        if r.see_weightage is not None and r.cie_weightage is not None:
            lines.append(f"  Weightage: Semester End Exam (SEE) = {r.see_weightage}%, Continuous Internal Eval (CIE) = {r.cie_weightage}%")
        if r.min_pass_marks:
            lines.append(f"  Minimum Pass Marks: {r.min_pass_marks}")
        if r.revaluation_deadline_days:
            lines.append(f"  Revaluation Deadline: Within {r.revaluation_deadline_days} days of result publication")
        lines.append(f"  Details: {r.content}")
        if r.source_url:
            lines.append(f"  Source: {r.source_url}")
        lines.append("")

        citations.append(
            _make_citation(
                title=f"MITS Examination Cell: {r.title}",
                source_url=r.source_url or f"{OFFICIAL_MITS_BASE_URL}/examination-cell",
                category="Examination Rules",
            )
        )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "EXAM_RULE",
        "found": True,
    }


def resolve_facilities(
    db: Session,
    category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve student campus facilities (Library, Hostel, Transport, Sports, Medical, Canteen)."""
    query = db.query(Facility).filter(Facility.is_active == True)  # noqa: E712

    if category:
        cat_upper = category.strip().upper()
        query = query.filter(
            or_(
                Facility.category == cat_upper,
                Facility.name.ilike(f"%{category.strip()}%"),
            )
        )

    facilities = query.order_by(Facility.category, Facility.name).all()
    if not facilities:
        return None

    lines = [
        "=== OFFICIAL MITS CAMPUS FACILITIES ===",
        f"Total Facilities Listed: {len(facilities)}",
        "",
    ]
    citations = []
    for fac in facilities:
        lines.append(f"• Facility: {fac.name} [{fac.category}]")
        if fac.location:
            lines.append(f"  Location: {fac.location}")
        if fac.timings:
            lines.append(f"  Operating Timings: {fac.timings}")
        if fac.description:
            lines.append(f"  Details: {fac.description}")
        if fac.rules:
            lines.append(f"  Rules & Policies: {fac.rules}")
        if fac.source_url:
            lines.append(f"  Official Source: {fac.source_url}")
        lines.append("")

        citations.append(
            _make_citation(
                title=f"MITS Campus Facility: {fac.name}",
                source_url=fac.source_url or f"{OFFICIAL_MITS_BASE_URL}/facilities",
                category="Campus Facilities",
            )
        )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "FACILITY",
        "found": True,
    }


def resolve_committees(
    db: Session,
    keyword: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve statutory and student welfare committees (Academic Council, Anti-Ragging, ICC, Grievance)."""
    query = db.query(Committee).filter(Committee.is_active == True)  # noqa: E712

    if keyword:
        kw = keyword.strip()
        query = query.filter(
            or_(
                Committee.code.ilike(f"%{kw}%"),
                Committee.name.ilike(f"%{kw}%"),
                Committee.category.ilike(f"%{kw}%"),
            )
        )

    committees = query.order_by(Committee.category, Committee.name).all()
    if not committees:
        return None

    lines = [
        "=== OFFICIAL MITS STATUTORY COMMITTEES & COUNCILS ===",
        "",
    ]
    citations = []
    for com in committees:
        lines.append(f"• Committee: {com.name} ({com.code}) [{com.category}]")
        if com.purpose:
            lines.append(f"  Mandate/Purpose: {com.purpose}")
        if com.meeting_frequency:
            lines.append(f"  Meeting Frequency: {com.meeting_frequency}")

        # Members
        members = db.query(CommitteeMember).join(Person).filter(
            CommitteeMember.committee_id == com.id,
            CommitteeMember.is_current == True,  # noqa: E712
        ).order_by(CommitteeMember.order_index).all()

        if members:
            lines.append("  Key Committee Members:")
            for m in members:
                title_str = f"{m.person.title} " if m.person.title else ""
                lines.append(f"    - {m.role_in_committee}: {title_str}{m.person.name} ({m.person.designation or 'Faculty'})")

        if com.source_url:
            lines.append(f"  Official Source: {com.source_url}")
        lines.append("")

        citations.append(
            _make_citation(
                title=f"MITS Committee: {com.name}",
                source_url=com.source_url or f"{OFFICIAL_MITS_BASE_URL}/committees",
                category="Committees & Governance",
            )
        )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "COMMITTEE",
        "found": True,
    }


def resolve_cells(
    db: Session,
    keyword: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve student cells (NSS, NCC, Innovation, Placement Cell, Women Empowerment)."""
    query = db.query(Cell).filter(Cell.is_active == True)  # noqa: E712

    if keyword:
        kw = keyword.strip()
        query = query.filter(
            or_(
                Cell.code.ilike(f"%{kw}%"),
                Cell.name.ilike(f"%{kw}%"),
            )
        )

    cells = query.all()
    if not cells:
        return None

    lines = [
        "=== OFFICIAL MITS STUDENT CELLS & ACTIVITIES ===",
        "",
    ]
    citations = []
    for c in cells:
        lines.append(f"• Cell: {c.name} ({c.code}) [{c.category}]")
        if c.description:
            lines.append(f"  Description: {c.description}")

        coords = db.query(CellCoordinator).join(Person).filter(
            CellCoordinator.cell_id == c.id,
            CellCoordinator.is_current == True,  # noqa: E712
        ).all()
        if coords:
            lines.append("  Coordinators:")
            for co in coords:
                lines.append(f"    - {co.role}: {co.person.name}")

        if c.source_url:
            lines.append(f"  Source: {c.source_url}")
        lines.append("")

        citations.append(
            _make_citation(
                title=f"MITS Student Cell: {c.name}",
                source_url=c.source_url or f"{OFFICIAL_MITS_BASE_URL}/cells",
                category="Student Support",
            )
        )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "CELL",
        "found": True,
    }


def resolve_admissions(
    db: Session,
    category: Optional[str] = None,
    entrance_exam: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve admission rules, eligibility, entrance exams (EAPCET/ICET), and quota criteria."""
    query = db.query(AdmissionRule)

    if category:
        query = query.filter(AdmissionRule.category == category.strip().upper())
    if entrance_exam:
        query = query.filter(AdmissionRule.entrance_exam.ilike(f"%{entrance_exam.strip()}%"))

    rules = query.all()
    if not rules:
        return None

    lines = [
        "=== OFFICIAL MITS ADMISSION INFORMATION ===",
        "Source: MITS Admissions Directorate",
        "",
    ]
    citations = []
    for adm in rules:
        prg_name = adm.program.name if adm.program else "College-Wide / General"
        lines.append(f"• Admission Category: {adm.category} ({prg_name})")
        if adm.entrance_exam:
            lines.append(f"  Entrance Examination: {adm.entrance_exam}")
        lines.append(f"  Eligibility Criteria: {adm.eligibility_criteria}")
        if adm.application_process:
            lines.append(f"  Application Procedure: {adm.application_process}")
        if adm.fee_details:
            lines.append(f"  Fee Structure: {adm.fee_details}")
        if adm.scholarship_info:
            lines.append(f"  Scholarship & Concessions: {adm.scholarship_info}")
        if adm.source_url:
            lines.append(f"  Source: {adm.source_url}")
        lines.append("")

        citations.append(
            _make_citation(
                title=f"MITS Admission Rules - {adm.category}",
                source_url=adm.source_url or f"{OFFICIAL_MITS_BASE_URL}/admissions",
                category="Admissions",
            )
        )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "ADMISSION",
        "found": True,
    }


def resolve_placements(
    db: Session,
    company_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve placement records, recruiters, highest/average packages."""
    query = db.query(PlacementData)
    if company_name:
        query = query.filter(PlacementData.company_name.ilike(f"%{company_name.strip()}%"))

    records = query.order_by(PlacementData.package_lpa.desc().nullslast()).limit(20).all()
    if not records:
        # Fallback to general Placement table
        p_query = db.query(Placement).filter(Placement.is_valid == True)  # noqa: E712
        if company_name:
            p_query = p_query.filter(Placement.company.ilike(f"%{company_name.strip()}%"))
        general_placements = p_query.limit(20).all()
        if not general_placements:
            return None

        lines = [
            "=== OFFICIAL MITS PLACEMENTS & RECRUITMENT DRIVES ===",
            "",
        ]
        citations = []
        for gp in general_placements:
            lines.append(f"• Company: {gp.company}")
            if gp.job_role:
                lines.append(f"  Role: {gp.job_role}")
            if gp.package_details:
                lines.append(f"  Package: {gp.package_details}")
            if gp.eligibility:
                lines.append(f"  Eligibility: {gp.eligibility}")
            lines.append("")

            if len(citations) < 3:
                citations.append(
                    _make_citation(
                        title=f"MITS Placement Drive: {gp.company}",
                        source_url=gp.source_url or f"{OFFICIAL_MITS_BASE_URL}/placements",
                        category="Placements",
                    )
                )
        return {
            "text": "\n".join(lines).strip(),
            "citations": citations,
            "entity_type": "PLACEMENT",
            "found": True,
        }

    lines = [
        "=== OFFICIAL MITS PLACEMENT RECORDS & STATISTICS ===",
        f"Authority: MITS Training & Placement Cell",
        "",
    ]
    citations = []
    for pd in records:
        pkg_str = f" | Package: {pd.package_lpa} LPA" if pd.package_lpa else ""
        tier_str = f" [{pd.tier_category}]" if pd.tier_category else ""
        lines.append(f"• Recruiter: {pd.company_name}{tier_str}{pkg_str}")
        if pd.role_title:
            lines.append(f"  Role: {pd.role_title}")
        if pd.eligibility_cgpa:
            lines.append(f"  Eligibility: Minimum {pd.eligibility_cgpa} CGPA")
        if pd.eligible_branches:
            lines.append(f"  Eligible Branches: {pd.eligible_branches}")
        if pd.total_offers:
            lines.append(f"  Total Offers: {pd.total_offers}")
        lines.append("")

        if len(citations) < 3:
            citations.append(
                _make_citation(
                    title=f"MITS Placement Statistics - {pd.company_name}",
                    source_url=pd.source_url or f"{OFFICIAL_MITS_BASE_URL}/placements",
                    category="Placements",
                )
            )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "PLACEMENT",
        "found": True,
    }


def resolve_history(
    db: Session,
) -> Optional[Dict[str, Any]]:
    """Resolve institution establishment history, milestones, and accreditations."""
    milestones = db.query(InstitutionHistory).order_by(InstitutionHistory.milestone_year).all()
    if not milestones:
        return None

    lines = [
        "=== OFFICIAL MITS INSTITUTIONAL HISTORY & MILESTONES ===",
        "Institution: Madanapalle Institute of Technology & Science (MITS)",
        "",
    ]
    citations = []
    for m in milestones:
        lines.append(f"• Year {m.milestone_year}: {m.title} [{m.category}]")
        lines.append(f"  {m.description}")
        lines.append("")

        if len(citations) < 3:
            citations.append(
                _make_citation(
                    title=f"MITS Institutional Milestone ({m.milestone_year}): {m.title}",
                    source_url=m.source_url or f"{OFFICIAL_MITS_BASE_URL}/about-mits",
                    category="Institution History",
                )
            )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "HISTORY",
        "found": True,
    }


def resolve_contacts(
    db: Session,
    dept_or_unit: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve official contacts, emergency phone numbers, and administrative unit emails."""
    query = db.query(Contact)
    if dept_or_unit:
        query = query.filter(
            or_(
                Contact.department_or_unit.ilike(f"%{dept_or_unit.strip()}%"),
                Contact.role_or_purpose.ilike(f"%{dept_or_unit.strip()}%"),
            )
        )

    contacts = query.limit(20).all()
    if not contacts:
        return None

    lines = [
        "=== OFFICIAL MITS CONTACT DIRECTORY ===",
        "",
    ]
    citations = []
    for c in contacts:
        lines.append(f"• {c.department_or_unit} — {c.role_or_purpose}")
        if c.phone:
            lines.append(f"  Phone: {c.phone}")
        if c.email:
            lines.append(f"  Email: {c.email}")
        if c.location:
            lines.append(f"  Location: {c.location}")
        lines.append("")

        if len(citations) < 3:
            citations.append(
                _make_citation(
                    title=f"MITS Contact: {c.department_or_unit}",
                    source_url=c.source_url or f"{OFFICIAL_MITS_BASE_URL}/contact-us",
                    category="Contact Information",
                )
            )

    return {
        "text": "\n".join(lines).strip(),
        "citations": citations,
        "entity_type": "CONTACT",
        "found": True,
    }


# ── Unified Query Resolver ───────────────────────────────────────────────────

def resolve_structured_query(
    routed_query: RoutedQuery,
    db: Session,
) -> Optional[Dict[str, Any]]:
    """
    Main dispatch method: takes a RoutedQuery and queries the normalized
    PostgreSQL tables based on the classified intent and extracted entities.
    """
    intent = routed_query.intent
    entities = routed_query.extracted_entities or {}
    query_text = routed_query.cleaned_query

    logger.info(f"[KNOWLEDGE_SERVICE] Dispatching intent '{intent.value}' with entities: {entities}")

    if routed_query.is_ambiguous and routed_query.clarification_question:
        return {
            "text": routed_query.clarification_question,
            "citations": [
                _make_citation(
                    title="MITS Academic Departments Directory",
                    source_url=f"{OFFICIAL_MITS_BASE_URL}/departments",
                    category="Department Directory",
                )
            ],
            "entity_type": "CLARIFICATION",
            "is_ambiguous": True,
            "found": True,
        }

    try:
        is_historical = getattr(routed_query, "is_historical", False) or entities.get("is_historical", False)

        if intent == QueryIntent.ROLE_LOOKUP:
            role_code = entities.get("role_code")
            if role_code == "HOD":
                dept_code = entities.get("department_code")
                return resolve_hod(db, dept_code=dept_code, is_historical=is_historical)
            return resolve_leadership(db, role_code=role_code)

        elif intent == QueryIntent.DEPARTMENT_LOOKUP:
            dept_code = entities.get("department_code") or query_text
            return resolve_department(db, code_or_name=dept_code)

        elif intent == QueryIntent.FACULTY_LOOKUP:
            dept_code = entities.get("department_code")
            person_name = entities.get("person_name")
            designation_filter = entities.get("designation_filter")
            is_count_query = entities.get("is_count_query", False)
            return resolve_faculty(
                db,
                dept_code=dept_code,
                person_name=person_name,
                designation_filter=designation_filter,
                is_count_query=is_count_query,
                is_historical=is_historical,
            )

        elif intent == QueryIntent.PERSON_LOOKUP:
            person_name = entities.get("person_name") or query_text
            return resolve_person(db, name=person_name)

        elif intent == QueryIntent.PROGRAM_LOOKUP:
            dept_code = entities.get("department_code")
            degree_level = None
            q_lower = query_text.lower()
            if "b.tech" in q_lower or "btech" in q_lower or "undergraduate" in q_lower or "ug" in q_lower:
                degree_level = "UG"
            elif "m.tech" in q_lower or "mtech" in q_lower or "postgraduate" in q_lower or "pg" in q_lower:
                degree_level = "PG"
            elif "ph.d" in q_lower or "phd" in q_lower:
                degree_level = "PHD"
            elif "mba" in q_lower:
                dept_code = "MBA"
            elif "mca" in q_lower:
                dept_code = "MCA"
            return resolve_programs(db, dept_code=dept_code, degree_level=degree_level)

        elif intent == QueryIntent.ATTENDANCE:
            return resolve_academic_rules(db, rule_type="ATTENDANCE")

        elif intent == QueryIntent.ACADEMIC_RULE:
            q_lower = query_text.lower()
            rule_type = None
            if "grading" in q_lower or "grade" in q_lower:
                rule_type = "GRADING"
            elif "promotion" in q_lower:
                rule_type = "PROMOTION"
            elif "detention" in q_lower or "detained" in q_lower:
                rule_type = "DETENTION"
            elif "sgpa" in q_lower or "cgpa" in q_lower or "gpa" in q_lower:
                rule_type = "SGPA_CALCULATION"
            return resolve_academic_rules(db, rule_type=rule_type)

        elif intent == QueryIntent.EXAMINATION:
            q_lower = query_text.lower()
            rule_type = None
            if "revaluation" in q_lower or "recounting" in q_lower:
                rule_type = "REVALUATION"
            elif "malpractice" in q_lower:
                rule_type = "MALPRACTICE"
            elif "supplementary" in q_lower:
                rule_type = "SUPPLEMENTARY"
            elif "see" in q_lower or "cie" in q_lower or "weightage" in q_lower or "pass mark" in q_lower or "passing mark" in q_lower or "aggregate" in q_lower:
                rule_type = "EVALUATION"
            return resolve_exam_rules(db, rule_type=rule_type)

        elif intent == QueryIntent.ADMISSION:
            return resolve_admissions(db)

        elif intent == QueryIntent.PLACEMENT:
            return resolve_placements(db)

        elif intent == QueryIntent.FACILITY:
            cat = entities.get("facility_category")
            return resolve_facilities(db, category=cat)

        elif intent == QueryIntent.COMMITTEE:
            kw = entities.get("committee_keyword")
            res = resolve_committees(db, keyword=kw)
            if not res:
                res = resolve_cells(db, keyword=kw)
            return res

        elif intent == QueryIntent.HISTORY:
            return resolve_history(db)

        elif intent == QueryIntent.CONTACT:
            dept = entities.get("department_code")
            return resolve_contacts(db, dept_or_unit=dept)

        elif intent == QueryIntent.MULTI_SOURCE:
            # Query asks about HOD + courses/curriculum
            dept_code = entities.get("department_code")
            if dept_code:
                return resolve_department(db, code_or_name=dept_code)

    except Exception as exc:
        logger.error(f"[KNOWLEDGE_SERVICE] Error resolving structured query: {exc}", exc_info=True)
        return None

    return None
