"""
MITS Official Source Adapters for CampusAI.

Modular data adapters implementing the discover -> fetch -> parse -> normalize -> validate -> save
pattern for official Madanapalle Institute of Technology & Science (MITS) web sources and documents.
Strictly preserves canonical URLs without inventing or fabricating synthetic paths.
"""
from datetime import datetime, timezone
import hashlib
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.db.models import (
    Announcement,
    AcademicCalendarEvent,
    Examination,
    Department,
    Faculty,
    Placement,
    CollegeInfo,
    ImportantLink,
    Person,
    Leadership,
    RoleRecord,
    School,
    Program,
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
    InstitutionHistory,
)
from backend.app.services.url_validator import normalize_external_url, validate_external_url

CRAWLER_USER_AGENT = "CampusAICrawler/1.0 (+https://mits.ac.in/bot)"
DEFAULT_TIMEOUT = 15.0


def compute_content_hash(fields: List[Any]) -> str:
    """Generate deterministic SHA-256 hash across string representations of fields."""
    raw = "|".join(str(f or "").strip() for f in fields)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class BaseMITSAdapter:
    """Base class for all MITS official source adapters."""

    def __init__(self, base_url: str = "https://mits.ac.in/"):
        self.base_url = base_url

    def fetch(self, url: str) -> str:
        headers = {"User-Agent": CRAWLER_USER_AGENT}
        with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    def validate_record(self, record: Dict[str, Any], required_fields: List[str]) -> bool:
        for field in required_fields:
            if not record.get(field):
                return False
        return True


class MITSAnnouncementAdapter(BaseMITSAdapter):
    """Adapter for official MITS notices, circulars, and announcements."""

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        title = str(raw_item.get("title", "")).strip()
        description = str(raw_item.get("description", "")).strip() or None
        content = str(raw_item.get("content", "")).strip() or description
        category = str(raw_item.get("category", "General")).strip() or "General"
        
        raw_source_url = raw_item.get("source_url") or "https://mits.ac.in/circulars"
        source_url = normalize_external_url(raw_source_url, self.base_url)
        
        raw_doc_url = raw_item.get("document_url")
        document_url = normalize_external_url(raw_doc_url, self.base_url) if raw_doc_url else None
        
        source_name = raw_item.get("source_name") or "MITS Official Portal"
        is_valid = raw_item.get("is_valid", True)
        http_status = raw_item.get("http_status", 200)
        error_reason = raw_item.get("error_reason")

        published_date = raw_item.get("published_date")
        if isinstance(published_date, str):
            try:
                published_date = datetime.fromisoformat(published_date)
            except Exception:
                published_date = datetime.now(timezone.utc)
        elif not isinstance(published_date, datetime):
            published_date = datetime.now(timezone.utc)

        content_hash = compute_content_hash([title, category, str(published_date.date() if published_date else ""), source_url, document_url or ""])

        return {
            "title": title,
            "description": description,
            "content": content,
            "category": category,
            "published_date": published_date,
            "source_url": source_url,
            "canonical_url": source_url,
            "document_url": document_url,
            "source_name": source_name,
            "content_hash": content_hash,
            "http_status": http_status,
            "is_valid": is_valid,
            "error_reason": error_reason,
            "last_verified_at": datetime.now(timezone.utc),
        }

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            data = self.normalize(raw)
            if not self.validate_record(data, ["title", "source_url"]):
                continue

            existing = db.query(Announcement).filter(
                (Announcement.content_hash == data["content_hash"]) |
                (Announcement.title == data["title"])
            ).first()

            if existing:
                existing.description = data["description"]
                existing.content = data["content"]
                existing.category = data["category"]
                existing.source_url = data["source_url"]
                existing.canonical_url = data["canonical_url"]
                existing.document_url = data["document_url"]
                existing.http_status = data["http_status"]
                existing.is_valid = data["is_valid"]
                existing.error_reason = data["error_reason"]
                existing.last_verified_at = data["last_verified_at"]
                db.commit()
            else:
                ann = Announcement(**data)
                db.add(ann)
                db.commit()
                count += 1
        return count


class MITSCalendarAdapter(BaseMITSAdapter):
    """Adapter for official MITS Academic Calendars."""

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        event_name = str(raw_item.get("event_name", "")).strip()
        academic_year = str(raw_item.get("academic_year", "2026-2027")).strip()
        program = str(raw_item.get("program", "B.Tech")).strip()
        year = str(raw_item.get("year", "")).strip() or None
        semester = str(raw_item.get("semester", "")).strip() or None
        event_description = str(raw_item.get("event_description", "")).strip() or None
        
        raw_source_url = raw_item.get("source_url") or "https://mits.ac.in/academic-calenders"
        source_url = normalize_external_url(raw_source_url, self.base_url)
        
        raw_doc_url = raw_item.get("document_url")
        document_url = normalize_external_url(raw_doc_url, self.base_url) if raw_doc_url else None
        
        source_name = raw_item.get("source_name") or "MITS Academic Section"
        is_valid = raw_item.get("is_valid", True)
        http_status = raw_item.get("http_status", 200)
        error_reason = raw_item.get("error_reason")

        start_date = raw_item.get("start_date")
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date)
            except Exception:
                start_date = None

        end_date = raw_item.get("end_date")
        if isinstance(end_date, str):
            try:
                end_date = datetime.fromisoformat(end_date)
            except Exception:
                end_date = None

        content_hash = compute_content_hash([event_name, academic_year, program, year or "", semester or "", str(start_date), document_url or ""])

        return {
            "academic_year": academic_year,
            "program": program,
            "year": year,
            "semester": semester,
            "event_name": event_name,
            "event_description": event_description,
            "start_date": start_date,
            "end_date": end_date,
            "source_url": source_url,
            "canonical_url": source_url,
            "document_url": document_url,
            "source_name": source_name,
            "content_hash": content_hash,
            "http_status": http_status,
            "is_valid": is_valid,
            "error_reason": error_reason,
            "last_verified_at": datetime.now(timezone.utc),
        }

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            data = self.normalize(raw)
            if not self.validate_record(data, ["event_name", "academic_year"]):
                continue

            existing = db.query(AcademicCalendarEvent).filter(
                (AcademicCalendarEvent.content_hash == data["content_hash"]) |
                ((AcademicCalendarEvent.event_name == data["event_name"]) & (AcademicCalendarEvent.academic_year == data["academic_year"]))
            ).first()

            if existing:
                existing.event_description = data["event_description"]
                existing.start_date = data["start_date"]
                existing.end_date = data["end_date"]
                existing.source_url = data["source_url"]
                existing.canonical_url = data["canonical_url"]
                existing.document_url = data["document_url"]
                existing.http_status = data["http_status"]
                existing.is_valid = data["is_valid"]
                existing.error_reason = data["error_reason"]
                existing.last_verified_at = data["last_verified_at"]
                db.commit()
            else:
                ev = AcademicCalendarEvent(**data)
                db.add(ev)
                db.commit()
                count += 1
        return count


class MITSExamAdapter(BaseMITSAdapter):
    """Adapter for official MITS Examinations (notifications, timetables, results, hall tickets)."""

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        title = str(raw_item.get("title", "")).strip()
        exam_type = str(raw_item.get("exam_type", "notification")).strip().lower()
        program = str(raw_item.get("program", "B.Tech")).strip()
        year = str(raw_item.get("year", "")).strip() or None
        semester = str(raw_item.get("semester", "")).strip() or None
        description = str(raw_item.get("description", "")).strip() or None
        
        raw_source_url = raw_item.get("source_url") or "https://mits.ac.in/university-exam"
        source_url = normalize_external_url(raw_source_url, self.base_url)
        
        raw_doc_url = raw_item.get("document_url")
        document_url = normalize_external_url(raw_doc_url, self.base_url) if raw_doc_url else None
        
        source_name = raw_item.get("source_name") or "MITS Examination Cell"
        is_valid = raw_item.get("is_valid", True)
        http_status = raw_item.get("http_status", 200)
        error_reason = raw_item.get("error_reason")

        published_date = raw_item.get("published_date")
        if isinstance(published_date, str):
            try:
                published_date = datetime.fromisoformat(published_date)
            except Exception:
                published_date = datetime.now(timezone.utc)
        elif not isinstance(published_date, datetime):
            published_date = datetime.now(timezone.utc)

        exam_date = raw_item.get("exam_date")
        if isinstance(exam_date, str):
            try:
                exam_date = datetime.fromisoformat(exam_date)
            except Exception:
                exam_date = None

        content_hash = compute_content_hash([title, exam_type, program, year or "", semester or "", str(published_date.date() if published_date else ""), document_url or ""])

        return {
            "title": title,
            "exam_type": exam_type,
            "program": program,
            "year": year,
            "semester": semester,
            "published_date": published_date,
            "exam_date": exam_date,
            "description": description,
            "source_url": source_url,
            "canonical_url": source_url,
            "document_url": document_url,
            "source_name": source_name,
            "content_hash": content_hash,
            "http_status": http_status,
            "is_valid": is_valid,
            "error_reason": error_reason,
            "last_verified_at": datetime.now(timezone.utc),
        }

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            data = self.normalize(raw)
            if not self.validate_record(data, ["title", "exam_type"]):
                continue

            existing = db.query(Examination).filter(
                (Examination.content_hash == data["content_hash"]) |
                (Examination.title == data["title"])
            ).first()

            if existing:
                existing.description = data["description"]
                existing.source_url = data["source_url"]
                existing.canonical_url = data["canonical_url"]
                existing.document_url = data["document_url"]
                existing.exam_date = data["exam_date"]
                existing.http_status = data["http_status"]
                existing.is_valid = data["is_valid"]
                existing.error_reason = data["error_reason"]
                existing.last_verified_at = data["last_verified_at"]
                db.commit()
            else:
                ex = Examination(**data)
                db.add(ex)
                db.commit()
                count += 1
        return count


class MITSDepartmentAdapter(BaseMITSAdapter):
    """Adapter for official MITS Academic Departments."""

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        code = str(raw_item.get("code", "")).strip().upper()
        name = str(raw_item.get("name", "")).strip()
        school = str(raw_item.get("school", "")).strip() or None
        description = str(raw_item.get("description", "")).strip() or None
        hod = str(raw_item.get("hod", "")).strip() or None
        hod_name = str(raw_item.get("hod_name", "")).strip() or hod
        hod_designation = str(raw_item.get("hod_designation", "")).strip() or None
        hod_profile_url = str(raw_item.get("hod_profile_url", "")).strip() or None
        hod_source_url = str(raw_item.get("hod_source_url", "")).strip() or None
        phone = str(raw_item.get("phone", "")).strip() or None
        email = str(raw_item.get("email", "")).strip() or None
        faculty = raw_item.get("faculty")
        programs = raw_item.get("programs")
        courses = raw_item.get("courses")
        
        raw_source_url = raw_item.get("source_url") or "https://mits.ac.in/"
        source_url = normalize_external_url(raw_source_url, self.base_url)
        
        is_valid = raw_item.get("is_valid", True)
        http_status = raw_item.get("http_status", 200)
        error_reason = raw_item.get("error_reason")
        is_active = raw_item.get("is_active", True)
        source_hash = compute_content_hash([code, name, school or "", description or "", hod_name or "", source_url])

        return {
            "code": code,
            "name": name,
            "school": school,
            "description": description,
            "hod": hod_name or hod,
            "hod_name": hod_name,
            "hod_designation": hod_designation,
            "hod_profile_url": hod_profile_url,
            "hod_source_url": hod_source_url or source_url,
            "hod_verified_at": datetime.now(timezone.utc),
            "phone": phone,
            "email": email,
            "faculty": str(faculty) if faculty else None,
            "programs": str(programs) if programs else None,
            "courses": str(courses) if courses else None,
            "source_url": source_url,
            "canonical_url": source_url,
            "source_hash": source_hash,
            "http_status": http_status,
            "is_valid": is_valid,
            "error_reason": error_reason,
            "is_active": is_active,
            "last_verified_at": datetime.now(timezone.utc),
        }

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            data = self.normalize(raw)
            if not self.validate_record(data, ["code", "name"]):
                continue

            existing = db.query(Department).filter(Department.code == data["code"]).first()
            dept_obj = None
            if existing:
                existing.name = data["name"]
                existing.school = data["school"]
                existing.description = data["description"]
                existing.hod = data["hod"]
                existing.hod_name = data["hod_name"]
                if data["hod_designation"]:
                    existing.hod_designation = data["hod_designation"]
                if data["hod_profile_url"]:
                    existing.hod_profile_url = data["hod_profile_url"]
                if data["phone"]:
                    existing.phone = data["phone"]
                if data["email"]:
                    existing.email = data["email"]
                if data["faculty"]:
                    existing.faculty = data["faculty"]
                if data["programs"]:
                    existing.programs = data["programs"]
                if data["courses"]:
                    existing.courses = data["courses"]
                existing.source_url = data["source_url"]
                existing.canonical_url = data["canonical_url"]
                existing.source_hash = data["source_hash"]
                existing.http_status = data["http_status"]
                existing.is_valid = data["is_valid"]
                existing.error_reason = data["error_reason"]
                existing.is_active = data["is_active"]
                existing.last_verified_at = data["last_verified_at"]
                dept_obj = existing
                db.commit()
            else:
                dept = Department(**data)
                db.add(dept)
                db.commit()
                db.refresh(dept)
                dept_obj = dept
                count += 1

            # Resolve hod_id if hod_name is present
            if dept_obj and dept_obj.hod_name:
                clean_hod = dept_obj.hod_name.replace("Dr.", "").replace("Prof.", "").strip().lower()
                fac = db.query(Faculty).filter(
                    (Faculty.department_id == dept_obj.id) &
                    (Faculty.is_valid == True) &
                    (Faculty.name.ilike(f"%{clean_hod[:15]}%"))
                ).first()
                if fac:
                    dept_obj.hod_id = fac.id
                    db.commit()

        return count


CANONICAL_DEPT_CODE_MAP = {
    "CSE": "CSE",
    "COMPUTER SCIENCE & ENGINEERING": "CSE",
    "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING": "CSE",
    "CSE-AIML": "CSE-AIML",
    "CSE(AIML)": "CSE-AIML",
    "CSE (AI&ML)": "CSE-AIML",
    "CSE (AIML)": "CSE-AIML",
    "CSE-AI-ML": "CSE-AIML",
    "AI & ML": "CSE-AIML",
    "ARTIFICIAL INTELLIGENCE & MACHINE LEARNING": "CSE-AIML",
    "CSE-DS": "CSE-DS",
    "CSE(DS)": "CSE-DS",
    "DATA SCIENCE": "CSE-DS",
    "CSE-CS": "CSE-CS",
    "CSE(CS)": "CSE-CS",
    "CYBER SECURITY": "CSE-CS",
    "AI": "AI",
    "CSE-AI": "AI",
    "CSE (AI)": "AI",
    "CSE (ARTIFICIAL INTELLIGENCE)": "AI",
    "ARTIFICIAL INTELLIGENCE": "AI",
    "CST": "CST",
    "COMPUTER SCIENCE AND TECHNOLOGY": "CST",
    "ECE": "ECE",
    "ELECTRONICS & COMMUNICATION ENGINEERING": "ECE",
    "ELECTRONICS AND COMMUNICATION ENGINEERING": "ECE",
    "EEE": "EEE",
    "ELECTRICAL & ELECTRONICS ENGINEERING": "EEE",
    "ELECTRICAL AND ELECTRONICS ENGINEERING": "EEE",
    "MECH": "MECH",
    "MECHANICAL ENGINEERING": "MECH",
    "ME": "MECH",
    "CIVIL": "CIVIL",
    "CIVIL ENGINEERING": "CIVIL",
    "CE": "CIVIL",
    "CSE - AI": "AI",
    "CSE - AI AND ML": "CSE-AIML",
    "CSE - CS": "CSE-CS",
    "CSE - DS": "CSE-DS",
    "CHEMISTRY": "BSH",
    "ENGLISH & FL": "BSH",
    "MATHEMATICS": "BSH",
    "PHYSICS": "BSH",
    "MBA": "MBA",
    "MANAGEMENT STUDIES": "MBA",
    "MCA": "MCA",
    "COMPUTER APPLICATIONS": "MCA",
    "BSH": "BSH",
    "BASIC SCIENCES & HUMANITIES": "BSH",
    "HUMANITIES": "BSH",
}


def resolve_canonical_department_id(db: Session, dept_str: Optional[str]) -> Optional[int]:
    """Map raw faculty department string to exact Department primary key without substring ambiguity."""
    if not dept_str:
        return None
    raw = dept_str.strip().upper()
    code = CANONICAL_DEPT_CODE_MAP.get(raw, raw)
    dept = db.query(Department).filter(
        (Department.code == code) |
        (Department.code == raw)
    ).first()
    return dept.id if dept else None


class MITSFacultyAdapter(BaseMITSAdapter):
    """Adapter for official MITS University Faculty Members."""

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        name = str(raw_item.get("name", "")).strip()
        designation = str(raw_item.get("designation", "")).strip() or None
        qualification = str(raw_item.get("qualification", "")).strip() or None
        department = str(raw_item.get("department", "")).strip() or None
        email = str(raw_item.get("email", "")).strip() or None
        phone = str(raw_item.get("phone", "")).strip() or None
        
        raw_prof_url = raw_item.get("profile_url")
        profile_url = normalize_external_url(raw_prof_url, self.base_url) if raw_prof_url else None
        
        raw_source_url = raw_item.get("source_url") or "https://mits.ac.in/faculty-information"
        source_url = normalize_external_url(raw_source_url, self.base_url)
        
        is_valid = raw_item.get("is_valid", True)
        content_hash = compute_content_hash([name, designation or "", qualification or "", department or "", profile_url or ""])

        return {
            "name": name,
            "designation": designation,
            "qualification": qualification,
            "department": department,
            "email": email,
            "phone": phone,
            "profile_url": profile_url,
            "source_url": source_url,
            "canonical_url": source_url,
            "is_valid": is_valid,
            "content_hash": content_hash,
            "last_verified_at": datetime.now(timezone.utc),
        }

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            data = self.normalize(raw)
            if not self.validate_record(data, ["name"]):
                continue

            dept_id = resolve_canonical_department_id(db, data.get("department"))
            data["department_id"] = dept_id

            data["is_active"] = True

            existing = db.query(Faculty).filter(
                (Faculty.content_hash == data["content_hash"]) |
                ((Faculty.name == data["name"]) & (Faculty.department == data["department"]))
            ).first()

            fac_obj = None
            if existing:
                existing.designation = data["designation"]
                existing.qualification = data["qualification"]
                existing.profile_url = data["profile_url"]
                existing.source_url = data["source_url"]
                existing.canonical_url = data["canonical_url"]
                existing.is_valid = data["is_valid"]
                existing.is_active = True
                existing.last_verified_at = data["last_verified_at"]
                if dept_id:
                    existing.department_id = dept_id
                fac_obj = existing
                db.commit()
            else:
                fac = Faculty(**data)
                db.add(fac)
                db.commit()
                db.refresh(fac)
                fac_obj = fac
                count += 1

            # Note: HOD assignments are strictly authoritative and handled solely by
            # sync_mits_departmentheads_from_page from https://mits.ac.in/departmentheads.
            # Never infer or overwrite HOD from faculty designations.
        return count


class MITSPlacementAdapter(BaseMITSAdapter):
    """Adapter for official MITS Training & Placement records."""

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        company = str(raw_item.get("company", "")).strip()
        job_role = str(raw_item.get("job_role", "")).strip() or None
        package_details = str(raw_item.get("package_details", "")).strip() or None
        eligibility = str(raw_item.get("eligibility", "")).strip() or None
        description = str(raw_item.get("description", "")).strip() or None
        
        raw_source_url = raw_item.get("source_url") or "https://mits.ac.in/placement"
        source_url = normalize_external_url(raw_source_url, self.base_url)
        
        raw_doc_url = raw_item.get("document_url")
        document_url = normalize_external_url(raw_doc_url, self.base_url) if raw_doc_url else None
        is_valid = raw_item.get("is_valid", True)

        drive_date = raw_item.get("drive_date")
        if isinstance(drive_date, str):
            try:
                drive_date = datetime.fromisoformat(drive_date)
            except Exception:
                drive_date = None

        return {
            "company": company,
            "job_role": job_role,
            "package_details": package_details,
            "eligibility": eligibility,
            "description": description,
            "drive_date": drive_date,
            "source_url": source_url,
            "canonical_url": source_url,
            "document_url": document_url,
            "is_valid": is_valid,
            "last_verified_at": datetime.now(timezone.utc),
        }

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            data = self.normalize(raw)
            if not self.validate_record(data, ["company"]):
                continue

            existing = db.query(Placement).filter(
                (Placement.company == data["company"]) &
                (Placement.job_role == data["job_role"])
            ).first()

            if existing:
                existing.package_details = data["package_details"]
                existing.eligibility = data["eligibility"]
                existing.description = data["description"]
                existing.drive_date = data["drive_date"]
                existing.source_url = data["source_url"]
                existing.canonical_url = data["canonical_url"]
                existing.document_url = data["document_url"]
                existing.is_valid = data["is_valid"]
                existing.last_verified_at = data["last_verified_at"]
                db.commit()
            else:
                pl = Placement(**data)
                db.add(pl)
                db.commit()
                count += 1
        return count


# ── Structured Knowledge Adapters ─────────────────────────────────────────────

class MITSLeadershipAdapter(BaseMITSAdapter):
    """Adapter for official MITS Chancellor, Vice-Chancellor, Registrar, Deans, etc."""

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            name = str(raw.get("name", "")).strip()
            role_code = str(raw.get("role_code", "")).strip().upper()
            role_title = str(raw.get("role_title", "")).strip() or role_code
            if not name or not role_code:
                continue

            # Resolve or create Person
            person = db.query(Person).filter(Person.name == name).first()
            if not person:
                person = Person(
                    name=name,
                    title=raw.get("title"),
                    designation=raw.get("designation") or role_title,
                    qualification=raw.get("qualification"),
                    email=raw.get("email"),
                    phone=raw.get("phone"),
                    profile_url=raw.get("profile_url"),
                    source_url=raw.get("source_url"),
                )
                db.add(person)
                db.commit()
                db.refresh(person)

            # Resolve or update Leadership record
            existing_lead = db.query(Leadership).filter(
                (Leadership.person_id == person.id) &
                (Leadership.role_code == role_code)
            ).first()

            if existing_lead:
                existing_lead.role_title = role_title
                existing_lead.is_current = raw.get("is_current", True)
                existing_lead.order_index = raw.get("order_index", 0)
                existing_lead.term_start = raw.get("term_start")
                existing_lead.term_end = raw.get("term_end")
                existing_lead.source_url = raw.get("source_url")
                existing_lead.source_title = raw.get("source_title")
                db.commit()
            else:
                lead = Leadership(
                    person_id=person.id,
                    role_code=role_code,
                    role_title=role_title,
                    order_index=raw.get("order_index", 0),
                    is_current=raw.get("is_current", True),
                    term_start=raw.get("term_start"),
                    term_end=raw.get("term_end"),
                    source_url=raw.get("source_url"),
                    source_title=raw.get("source_title"),
                )
                db.add(lead)
                db.commit()
                count += 1
        return count


class MITSProgramAdapter(BaseMITSAdapter):
    """Adapter for official MITS Degree Programs (B.Tech, M.Tech, MBA, MCA, Ph.D.)."""

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            code = str(raw.get("code", "")).strip().upper()
            name = str(raw.get("name", "")).strip()
            degree_level = str(raw.get("degree_level", "UG")).strip().upper()
            if not code or not name:
                continue

            dept_id = raw.get("department_id")
            if not dept_id and raw.get("department_code"):
                dept = db.query(Department).filter(Department.code == raw["department_code"].strip().upper()).first()
                if dept:
                    dept_id = dept.id

            existing = db.query(Program).filter(Program.code == code).first()
            if existing:
                existing.name = name
                existing.degree_level = degree_level
                if dept_id:
                    existing.department_id = dept_id
                existing.duration_years = raw.get("duration_years", existing.duration_years)
                existing.eligibility = raw.get("eligibility", existing.eligibility)
                existing.intake = raw.get("intake", existing.intake)
                existing.regulations_code = raw.get("regulations_code", existing.regulations_code)
                existing.source_url = raw.get("source_url", existing.source_url)
                db.commit()
            else:
                prg = Program(
                    code=code,
                    name=name,
                    degree_level=degree_level,
                    department_id=dept_id,
                    duration_years=raw.get("duration_years", 4),
                    eligibility=raw.get("eligibility"),
                    intake=raw.get("intake"),
                    regulations_code=raw.get("regulations_code", "R20"),
                    source_url=raw.get("source_url"),
                )
                db.add(prg)
                db.commit()
                count += 1
        return count


class MITSFacilityAdapter(BaseMITSAdapter):
    """Adapter for official MITS Student Facilities (Library, Hostel, Sports, etc.)."""

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            name = str(raw.get("name", "")).strip()
            category = str(raw.get("category", "GENERAL")).strip().upper()
            if not name:
                continue

            existing = db.query(Facility).filter(Facility.name == name).first()
            if existing:
                existing.category = category
                existing.description = raw.get("description", existing.description)
                existing.location = raw.get("location", existing.location)
                existing.timings = raw.get("timings", existing.timings)
                existing.rules = raw.get("rules", existing.rules)
                existing.source_url = raw.get("source_url", existing.source_url)
                db.commit()
            else:
                fac = Facility(
                    name=name,
                    category=category,
                    description=raw.get("description"),
                    location=raw.get("location"),
                    timings=raw.get("timings"),
                    rules=raw.get("rules"),
                    source_url=raw.get("source_url"),
                )
                db.add(fac)
                db.commit()
                count += 1
        return count


class MITSAcademicRuleAdapter(BaseMITSAdapter):
    """Adapter for official MITS Academic Regulations (Attendance 75%, Condonation, Grading)."""

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            rule_type = str(raw.get("rule_type", "")).strip().upper()
            title = str(raw.get("title", "")).strip()
            content = str(raw.get("content", "")).strip()
            reg_code = str(raw.get("regulation_code", "R20")).strip()
            if not rule_type or not title or not content:
                continue

            existing = db.query(AcademicRule).filter(
                (AcademicRule.rule_type == rule_type) &
                (AcademicRule.regulation_code == reg_code)
            ).first()

            if existing:
                existing.title = title
                existing.content = content
                existing.threshold_percentage = raw.get("threshold_percentage", existing.threshold_percentage)
                existing.penalties_or_remedies = raw.get("penalties_or_remedies", existing.penalties_or_remedies)
                existing.source_url = raw.get("source_url", existing.source_url)
                db.commit()
            else:
                rule = AcademicRule(
                    rule_type=rule_type,
                    regulation_code=reg_code,
                    title=title,
                    content=content,
                    threshold_percentage=raw.get("threshold_percentage"),
                    penalties_or_remedies=raw.get("penalties_or_remedies"),
                    source_url=raw.get("source_url"),
                )
                db.add(rule)
                db.commit()
                count += 1
        return count


class MITSExamRuleAdapter(BaseMITSAdapter):
    """Adapter for official MITS Examination Cell rules (SEE/CIE weightage, Revaluation)."""

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            rule_type = str(raw.get("rule_type", "")).strip().upper()
            title = str(raw.get("title", "")).strip()
            content = str(raw.get("content", "")).strip()
            if not rule_type or not title or not content:
                continue

            existing = db.query(ExamRule).filter(
                (ExamRule.rule_type == rule_type) &
                (ExamRule.title == title)
            ).first()

            if existing:
                existing.content = content
                existing.see_weightage = raw.get("see_weightage", existing.see_weightage)
                existing.cie_weightage = raw.get("cie_weightage", existing.cie_weightage)
                existing.min_pass_marks = raw.get("min_pass_marks", existing.min_pass_marks)
                existing.revaluation_deadline_days = raw.get("revaluation_deadline_days", existing.revaluation_deadline_days)
                existing.source_url = raw.get("source_url", existing.source_url)
                db.commit()
            else:
                rule = ExamRule(
                    rule_type=rule_type,
                    regulation_code=raw.get("regulation_code", "R20"),
                    title=title,
                    content=content,
                    see_weightage=raw.get("see_weightage"),
                    cie_weightage=raw.get("cie_weightage"),
                    min_pass_marks=raw.get("min_pass_marks"),
                    revaluation_deadline_days=raw.get("revaluation_deadline_days"),
                    source_url=raw.get("source_url"),
                )
                db.add(rule)
                db.commit()
                count += 1
        return count


class MITSHistoryAdapter(BaseMITSAdapter):
    """Adapter for official MITS Milestones & Accreditations (1998, UGC Autonomy, NAAC A++)."""

    def save(self, db: Session, items: List[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            year = int(raw.get("milestone_year", 0))
            title = str(raw.get("title", "")).strip()
            description = str(raw.get("description", "")).strip()
            if not year or not title:
                continue

            existing = db.query(InstitutionHistory).filter(
                (InstitutionHistory.milestone_year == year) &
                (InstitutionHistory.title == title)
            ).first()

            if existing:
                existing.description = description
                existing.category = raw.get("category", existing.category)
                existing.source_url = raw.get("source_url", existing.source_url)
                db.commit()
            else:
                hist = InstitutionHistory(
                    milestone_year=year,
                    title=title,
                    description=description,
                    category=raw.get("category", "MILESTONE"),
                    source_url=raw.get("source_url"),
                )
                db.add(hist)
                db.commit()
                count += 1
        return count

