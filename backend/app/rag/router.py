"""
Intelligent Query Router for CampusAI.

Classifies user queries into 17 distinct intents to drive the hybrid
Structured Knowledge (SQL) + Semantic RAG architecture.
"""
from dataclasses import dataclass, field
import enum
import re
from typing import Dict, Any, Optional, List


class QueryIntent(str, enum.Enum):
    PERSON_LOOKUP = "PERSON_LOOKUP"
    ROLE_LOOKUP = "ROLE_LOOKUP"
    DEPARTMENT_LOOKUP = "DEPARTMENT_LOOKUP"
    FACULTY_LOOKUP = "FACULTY_LOOKUP"
    PROGRAM_LOOKUP = "PROGRAM_LOOKUP"
    ADMISSION = "ADMISSION"
    EXAMINATION = "EXAMINATION"
    ATTENDANCE = "ATTENDANCE"
    ACADEMIC_RULE = "ACADEMIC_RULE"
    PLACEMENT = "PLACEMENT"
    FACILITY = "FACILITY"
    COMMITTEE = "COMMITTEE"
    HISTORY = "HISTORY"
    NOTICE = "NOTICE"
    CONTACT = "CONTACT"
    MULTI_SOURCE = "MULTI_SOURCE"
    GENERAL_RAG = "GENERAL_RAG"


@dataclass
class RoutedQuery:
    original_query: str
    cleaned_query: str
    intent: QueryIntent
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    requires_structured: bool = True
    requires_rag: bool = False
    metadata_filters: Optional[Dict[str, Any]] = None


# Known department code synonyms and mapping
DEPT_SYNONYMS = {
    "cse": "CSE",
    "computer science": "CSE",
    "computer science & engineering": "CSE",
    "computer science and engineering": "CSE",
    "cse-aiml": "CSE-AIML",
    "cse ai & ml": "CSE-AIML",
    "cse aiml": "CSE-AIML",
    "ai & ml": "CSE-AIML",
    "ai and ml": "CSE-AIML",
    "ai": "AI",
    "artificial intelligence": "AI",
    "cse-ds": "CSE-DS",
    "cse ds": "CSE-DS",
    "data science": "CSE-DS",
    "cse-cs": "CSE-CS",
    "cse cs": "CSE-CS",
    "cyber security": "CSE-CS",
    "cybersecurity": "CSE-CS",
    "cst": "CST",
    "computer science & technology": "CST",
    "computer science and technology": "CST",
    "ece": "ECE",
    "electronics": "ECE",
    "electronics & communication": "ECE",
    "electronics and communication": "ECE",
    "eee": "EEE",
    "electrical": "EEE",
    "electrical & electronics": "EEE",
    "electrical and electronics": "EEE",
    "mech": "MECH",
    "mechanical": "MECH",
    "mechanical engineering": "MECH",
    "civil": "CIVIL",
    "civil engineering": "CIVIL",
    "mca": "MCA",
    "computer applications": "MCA",
    "bca": "MCA",
    "mba": "MBA",
    "management": "MBA",
    "management studies": "MBA",
    "bsh": "BSH",
    "humanities": "BSH",
    "basic sciences": "BSH",
    "basic science": "BSH",
}

# Known executive roles
# Known executive roles (compound roles first to prevent prefix mis-matches)
ROLE_PATTERNS = [
    (r"\b(pro[- ]?chancellor)\b", "PRO_CHANCELLOR"),
    (r"\b(vice[- ]?chancellor|vc)\b", "VICE_CHANCELLOR"),
    (r"(?<!pro[-\s])(?<!vice[-\s])\b(chancellor)\b", "CHANCELLOR"),
    (r"\b(executive director|ed)\b", "EXECUTIVE_DIRECTOR"),
    (r"\b(additional registrar)\b", "ADDITIONAL_REGISTRAR"),
    (r"\b(registrar)\b", "REGISTRAR"),
    (r"\b(controller of examinations?|coe|controller|heads? (the )?examination cell)\b", "COE"),
    (r"\b(ombudsperson|ombudsman)\b", "OMBUDSPERSON"),
    (r"\b(vice[- ]?principals?)\b", "VICE_PRINCIPAL"),
    (r"(?<!vice[-\s])\b(principal)\b", "PRINCIPAL"),
    (r"\b(dean)\b", "DEAN"),
    (r"\b(founder|late sri n\.? krishna kumar)\b", "FOUNDER"),
    (r"\b(president)\b", "PRESIDENT"),
]

# Facility keywords
FACILITY_KEYWORDS = [
    "library", "hostel", "transport", "bus", "buses", "sports", "canteen",
    "cafeteria", "mess", "gym", "medical", "health centre", "health center",
    "counselling", "dispensary"
]

# Committee regex patterns
COMMITTEE_PATTERNS = [
    (r"\b(academic council)\b", "academic council"),
    (r"\b(board of studies|bos)\b", "board of studies"),
    (r"\b(executive council)\b", "executive council"),
    (r"\b(governing body)\b", "governing body"),
    (r"\b(anti[- ]?ragging)\b", "anti-ragging"),
    (r"\b(internal complaints|icc)\b", "icc"),
    (r"\b(grievance|redressal)\b", "grievance"),
    (r"\b(women empowerment)\b", "women empowerment"),
    (r"\b(edc|nss|ncc|innovation cell|r&d cell)\b", "cell"),
]


def extract_department(text: str) -> Optional[str]:
    """Extract canonical department code from query text."""
    lower = text.lower()
    # Check multi-word synonyms first for maximal substring matching
    sorted_synonyms = sorted(DEPT_SYNONYMS.keys(), key=lambda x: -len(x))
    for syn in sorted_synonyms:
        pattern = r"\b" + re.escape(syn) + r"\b"
        if re.search(pattern, lower):
            return DEPT_SYNONYMS[syn]
    return None


def extract_person_name(text: str) -> Optional[str]:
    """Extract candidate person name if prefixed by Dr./Prof./Mr./Mrs."""
    m = re.search(r"\b(Dr\.?|Prof\.?|Mr\.?|Mrs\.?|Ms\.?)\s+([A-Z][a-zA-Z\.]*(?:\s+[A-Z][a-zA-Z\.]*)*)", text)
    if m:
        return m.group(0).strip()
    return None


def classify_query(query: str) -> RoutedQuery:
    """
    Intelligently classify user query into 17 distinct intents with extracted entities.
    """
    cleaned = " ".join(query.strip().split())
    lower = cleaned.lower()

    entities: Dict[str, Any] = {}
    dept = extract_department(cleaned)
    if dept:
        entities["department_code"] = dept

    person = extract_person_name(cleaned)
    if person:
        entities["person_name"] = person

    # 1. Check MULTI_SOURCE (asks about HOD/person AND program/rules/labs)
    has_hod_keyword = bool(re.search(r"\b(hods?|heads? of (the )?departments?|head of [a-z\s]+|head of)\b", lower))
    if dept and ("head" in lower or "hod" in lower):
        has_hod_keyword = True

    has_curriculum_or_rules = bool(re.search(r"\b(programs?|courses?|regulations?|rules?|labs?|syllabus)\b", lower))
    if has_hod_keyword and has_curriculum_or_rules and dept:
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.MULTI_SOURCE,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 2. Check ATTENDANCE specifically (must take precedence over generic academic rules)
    if re.search(r"\b(attendance|condonation|shortage of attendance|detention|detained)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.ATTENDANCE,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
            metadata_filters={"category": "attendance"},
        )

    # 3. Check ROLE_LOOKUP (e.g. Chancellor, VC, Registrar, Principal, CoE)
    for pattern, role_code in ROLE_PATTERNS:
        if re.search(pattern, lower):
            entities["role_code"] = role_code
            return RoutedQuery(
                original_query=query,
                cleaned_query=cleaned,
                intent=QueryIntent.ROLE_LOOKUP,
                extracted_entities=entities,
                requires_structured=True,
                requires_rag=False,
            )

    # 4. Check HOD (Head of Department) Lookup
    # If a specific person name is present and asking for their details/experience/profile, route to PERSON_LOOKUP instead
    if has_hod_keyword and not (person and re.search(r"\b(experience|profile|qualification|bio|about|details)\b", lower)):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.ROLE_LOOKUP,
            extracted_entities=dict(role_code="HOD", **entities),
            requires_structured=True,
            requires_rag=False,
        )

    # 5. Check FACULTY_LOOKUP (e.g. list faculty, faculty members, professors, who teaches)
    if re.search(r"\b(faculty|professors?|lecturers?|teachers?|teaches|faculty list|list (of )?faculty|all faculty)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.FACULTY_LOOKUP,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=False,
        )

    # 6. Check PERSON_LOOKUP (query has named person or asks "Who is Dr...")
    if person or re.search(r"\bwho is\b", lower):
        if person:
            return RoutedQuery(
                original_query=query,
                cleaned_query=cleaned,
                intent=QueryIntent.PERSON_LOOKUP,
                extracted_entities=entities,
                requires_structured=True,
                requires_rag=False,
            )

    # 6b. Check Academic Grading / GPA rules before general exam rules (takes precedence over generic "examinations")
    if re.search(r"\b(sgpa|cgpa|grad\w*|grading system|grading scale|grade points?|letter grades?)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.ACADEMIC_RULE,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 7. Check EXAMINATION (SEE/CIE, revaluation, recounting, malpractice, pass marks)
    if re.search(r"\b(examinations?|exams?|hall tickets?|time ?tables?|revaluation|recounting|supplementary|mid[- ]?term|see|cie|pass marks?|passing marks?)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.EXAMINATION,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 8. Check ADMISSION (EAPCET, ICET, PGECET, quotas, eligibility for admission)
    if re.search(r"\b(admission|admissions|how to apply|entrance exam|eapcet|icet|pgecet|management quota|convenor quota|category[- ]?[ab]|lateral entry|seats? allotted)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.ADMISSION,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 9. Check PROGRAM_LOOKUP (programs, degrees, courses offered, B.Tech, M.Tech, MBA, MCA, PhD, offer ...)
    if re.search(r"\b(programs?|degrees?|courses? offered|programs? offered|specializations?|undergraduate|postgraduate|ph\.?d|b\.?tech|m\.?tech|intake|offer (mba|mca|b\.?tech|m\.?tech|degree|course|program))\b", lower) and not re.search(r"\b(exam\w*|admiss\w*|attend\w*)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.PROGRAM_LOOKUP,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=False,
        )

    # 10. Check DEPARTMENT_LOOKUP
    if re.search(r"\b(department|dept|school of)\b", lower) and dept:
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.DEPARTMENT_LOOKUP,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=False,
        )

    # 11. Check ACADEMIC_RULE (SGPA, CGPA, grading scale, credits, pass criteria)
    if re.search(r"\b(sgpa|cgpa|grad\w*|grading system|grading scale|pass criteria|credits?|regulations?|r20|r25)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.ACADEMIC_RULE,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 12. Check PLACEMENT
    if re.search(r"\b(placements?|recruiters?|companies|packages?|lpa|highest package|average package|internships?|placement cell|training and placement|offers?|offers made)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.PLACEMENT,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 13. Check FACILITY
    for kw in FACILITY_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", lower):
            entities["facility_category"] = kw
            return RoutedQuery(
                original_query=query,
                cleaned_query=cleaned,
                intent=QueryIntent.FACILITY,
                extracted_entities=entities,
                requires_structured=True,
                requires_rag=True,
            )

    # 14. Check COMMITTEE
    for pat, kw in COMMITTEE_PATTERNS:
        if re.search(pat, lower):
            entities["committee_keyword"] = kw
            return RoutedQuery(
                original_query=query,
                cleaned_query=cleaned,
                intent=QueryIntent.COMMITTEE,
                extracted_entities=entities,
                requires_structured=True,
                requires_rag=True,
            )

    # 15. Check HISTORY (founding, history, accreditation, NIRF, deemed university)
    if re.search(r"\b(history|established|establishment|founded|founder|when was mits|about mits|milestones|accreditation|naac|nba|nirf|deemed to be university)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.HISTORY,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 16. Check NOTICE (circulars, notices, events)
    if re.search(r"\b(notices?|circulars?|announcements?|workshops?|conferences?|events?)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.NOTICE,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=True,
        )

    # 17. Check CONTACT (phone, email, address, location, pincode)
    if re.search(r"\b(contact|phone numbers?|telephone|email address(es)?|address|location|where is|reach mits|emergency)\b", lower):
        return RoutedQuery(
            original_query=query,
            cleaned_query=cleaned,
            intent=QueryIntent.CONTACT,
            extracted_entities=entities,
            requires_structured=True,
            requires_rag=False,
        )

    # Default Fallback: GENERAL_RAG
    return RoutedQuery(
        original_query=query,
        cleaned_query=cleaned,
        intent=QueryIntent.GENERAL_RAG,
        extracted_entities=entities,
        requires_structured=False,
        requires_rag=True,
    )
