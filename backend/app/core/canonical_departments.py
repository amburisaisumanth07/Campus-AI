"""
Canonical Department Registry & Entity Resolution for CampusAI.

Authoritative source of truth for all MITS Academic Departments,
disjoint alias mappings, and deterministic entity resolution.
Strictly based on official MITS institutional records:
- https://mits.ac.in/departmentheads
- https://mits.ac.in/departments
"""
from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple, Any


@dataclass(frozen=True)
class CanonicalDepartment:
    department_id: int
    code: str
    official_name: str
    normalized_name: str
    school: str
    school_code: str
    hod_name: str
    hod_designation: str
    official_url: str
    source_url: str
    aliases: List[str] = field(default_factory=list)
    division_heads: Dict[str, str] = field(default_factory=dict)


# Authoritative MITS Academic Departments (Active)
CANONICAL_DEPARTMENTS: Dict[str, CanonicalDepartment] = {
    "CSE": CanonicalDepartment(
        department_id=1,
        code="CSE",
        official_name="Department of Computer Science & Engineering",
        normalized_name="computer science and engineering",
        school="School of Computing",
        school_code="COMPUTING",
        hod_name="Dr. M. Sreedevi",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/department/9",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "cse",
            "computer science",
            "computer science and engineering",
            "computer science & engineering",
            "dept of cse",
            "cse dept",
            "cse department",
        ],
    ),
    "ECE": CanonicalDepartment(
        department_id=3,
        code="ECE",
        official_name="Department of Electronics & Communication Engineering",
        normalized_name="electronics and communication engineering",
        school="School of Engineering",
        school_code="ENGINEERING",
        hod_name="Dr. Sanjay Kumar C. Gowre",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/electronics-communication-engineering",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "ece",
            "electronics",
            "electronics & communication engineering",
            "electronics and communication engineering",
            "electronics & communication",
            "electronics and communication",
            "dept of ece",
            "ece dept",
            "ece department",
        ],
    ),
    "EEE": CanonicalDepartment(
        department_id=4,
        code="EEE",
        official_name="Department of Electrical & Electronics Engineering",
        normalized_name="electrical and electronics engineering",
        school="School of Engineering",
        school_code="ENGINEERING",
        hod_name="Dr. Manavaalan Gunasekaran",
        hod_designation="Associate Professor & Head",
        official_url="https://mits.ac.in/electrical-electronics-engineering",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "eee",
            "electrical",
            "electrical & electronics engineering",
            "electrical and electronics engineering",
            "electrical & electronics",
            "electrical and electronics",
            "dept of eee",
            "eee dept",
            "eee department",
        ],
    ),
    "MECH": CanonicalDepartment(
        department_id=5,
        code="MECH",
        official_name="Department of Mechanical Engineering",
        normalized_name="mechanical engineering",
        school="School of Engineering",
        school_code="ENGINEERING",
        hod_name="Dr. S. Bhaskaran",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/department/8",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "mech",
            "mechanical",
            "mechanical engineering",
            "dept of mechanical engineering",
            "mech dept",
            "mech department",
        ],
    ),
    "CIVIL": CanonicalDepartment(
        department_id=6,
        code="CIVIL",
        official_name="Department of Civil Engineering",
        normalized_name="civil engineering",
        school="School of Engineering",
        school_code="ENGINEERING",
        hod_name="Dr. Vijayakumar Natesan",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/department/6",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "civil",
            "civil engineering",
            "dept of civil engineering",
            "civil dept",
            "civil department",
        ],
    ),
    "MBA": CanonicalDepartment(
        department_id=7,
        code="MBA",
        official_name="Department of Management Studies (BBA & MBA)",
        normalized_name="management studies",
        school="School of Management",
        school_code="MANAGEMENT",
        hod_name="Dr. R. Varadarajan",
        hod_designation="Professor & Head - Management Studies",
        official_url="https://mits.ac.in/department/5",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "mba",
            "bba",
            "bba & mba",
            "management studies",
            "department of management studies",
            "management department",
            "mba dept",
            "mba department",
        ],
    ),
    "MCA": CanonicalDepartment(
        department_id=8,
        code="MCA",
        official_name="Department of Computer Applications (BCA & MCA)",
        normalized_name="computer applications",
        school="School of Computing",
        school_code="COMPUTING",
        hod_name="Dr. N. Naveen Kumar",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/department/18",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "mca",
            "bca",
            "bca & mca",
            "computer applications",
            "dept of computer applications",
            "mca dept",
            "mca department",
        ],
    ),
    "CSE-DS": CanonicalDepartment(
        department_id=9,
        code="CSE-DS",
        official_name="Department of Computer Science and Engineering (Data Science)",
        normalized_name="cse data science",
        school="School of Computing",
        school_code="COMPUTING",
        hod_name="Dr. S. Kusuma",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/department/26",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "cse-ds",
            "cse ds",
            "data science",
            "data science department",
            "cse data science",
            "cse (data science)",
            "cse - data science",
            "dept of cse data science",
        ],
    ),
    "CSE-CS": CanonicalDepartment(
        department_id=10,
        code="CSE-CS",
        official_name="Department of Computer Science and Engineering (Cyber Security)",
        normalized_name="cse cyber security",
        school="School of Computing",
        school_code="COMPUTING",
        hod_name="Dr. Brahm Prakash",
        hod_designation="Associate Professor & Head",
        official_url="https://mits.ac.in/department/27",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "cse-cs",
            "cse cs",
            "cyber security",
            "cybersecurity",
            "cyber security department",
            "cse cyber security",
            "cse (cyber security)",
            "cse - cyber security",
            "dept of cse cyber security",
        ],
    ),
    "AI": CanonicalDepartment(
        department_id=11,
        code="AI",
        official_name="Department of Computer Science & Engineering (Artificial Intelligence)",
        normalized_name="cse artificial intelligence",
        school="School of AI & ML",
        school_code="AI_ML",
        hod_name="Dr. R. Kalpana",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/department/28",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "cse-ai",
            "cse ai",
            "cse - ai",
            "cse (ai)",
            "cse (artificial intelligence)",
            "cse - artificial intelligence",
            "artificial intelligence",
            "artificial intelligence department",
            "ai department",
            "the ai department",
            "department of ai",
            "department of artificial intelligence",
            "ai dept",
            "cse ai dept",
            "cse ai department",
        ],
    ),
    "CST": CanonicalDepartment(
        department_id=12,
        code="CST",
        official_name="Department of Computer Science and Technology (CST)",
        normalized_name="computer science and technology",
        school="School of Computing",
        school_code="COMPUTING",
        hod_name="Dr. K. Dinesh",
        hod_designation="Associate Professor & Head",
        official_url="https://mits.ac.in/department/4",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "cst",
            "computer science and technology",
            "computer science & technology",
            "dept of cst",
            "cst dept",
            "cst department",
        ],
    ),
    "CSE-AIML": CanonicalDepartment(
        department_id=14,
        code="CSE-AIML",
        official_name="Department of Computer Science & Engineering (Artificial Intelligence & Machine Learning)",
        normalized_name="cse artificial intelligence and machine learning",
        school="School of AI & ML",
        school_code="AI_ML",
        hod_name="Dr. S. Padma",
        hod_designation="Professor & Head",
        official_url="https://mits.ac.in/cse-ai-ml",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "cse-aiml",
            "cse aiml",
            "cse - aiml",
            "cse ai & ml",
            "cse ai and ml",
            "cse - ai & ml",
            "cse - ai and ml",
            "cse (ai & ml)",
            "cse (ai and ml)",
            "ai & ml",
            "ai and ml",
            "aiml",
            "ai & ml department",
            "ai and ml department",
            "aiml department",
            "cse (artificial intelligence & machine learning)",
            "cse (artificial intelligence and machine learning)",
            "cse - artificial intelligence & machine learning",
            "cse - artificial intelligence and machine learning",
            "artificial intelligence & machine learning",
            "artificial intelligence and machine learning",
        ],
    ),
    "BSH": CanonicalDepartment(
        department_id=15,
        code="BSH",
        official_name="Department of Basic Sciences & Humanities",
        normalized_name="basic sciences and humanities",
        school="School of Science & Humanities",
        school_code="SCIENCE_HUMANITIES",
        hod_name="Dr. R. Saravana (Maths) / Dr. Jagadeesh Babu Bellam (Physics) / Dr. Renjith Bhaskaran (Chemistry) / Dr. Sudhakar Beedam (English)",
        hod_designation="Heads of Divisions",
        official_url="https://mits.ac.in/basic-sciences-humanities",
        source_url="https://mits.ac.in/departmentheads",
        aliases=[
            "bsh",
            "basic sciences",
            "basic science",
            "basic sciences & humanities",
            "basic sciences and humanities",
            "humanities",
            "science & humanities",
            "science and humanities",
            "mathematics",
            "maths",
            "physics",
            "chemistry",
            "english",
            "english & foreign languages",
            "english and foreign languages",
        ],
        division_heads={
            "Mathematics": "Dr. R. Saravana (Head I/c)",
            "Physics": "Dr. Jagadeesh Babu Bellam (Head I/c)",
            "Chemistry": "Dr. Renjith Bhaskaran (Head)",
            "English & Foreign Languages": "Dr. Sudhakar Beedam (Head I/c)",
        },
    ),
}

# Lookup map by ID
CANONICAL_DEPARTMENTS_BY_ID: Dict[int, CanonicalDepartment] = {
    dept.department_id: dept for dept in CANONICAL_DEPARTMENTS.values()
}


def normalize_text_for_matching(text: str) -> str:
    """Normalize text by replacing punctuation (except &) with space and standardizing whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s&]", " ", text.lower())).strip()


# Compile sorted alias list (longer normalized aliases first to ensure greedy specific matching)
_ALIAS_LOOKUP: List[Tuple[re.Pattern, str, int]] = []
for code, dept in CANONICAL_DEPARTMENTS.items():
    for alias in dept.aliases:
        norm_alias = normalize_text_for_matching(alias)
        if not norm_alias:
            continue
        pattern = re.compile(r"\b" + re.escape(norm_alias) + r"\b", re.IGNORECASE)
        _ALIAS_LOOKUP.append((pattern, code, len(norm_alias)))

_ALIAS_LOOKUP.sort(key=lambda item: -item[2])


def resolve_canonical_department(query_text: str) -> Optional[CanonicalDepartment]:
    """
    Deterministically resolve a query string to a single canonical department.
    Uses strict, longest-alias-first pattern matching.
    """
    if not query_text:
        return None

    cleaned = normalize_text_for_matching(query_text)
    if not cleaned:
        return None

    for pattern, code, _ in _ALIAS_LOOKUP:
        if pattern.search(cleaned):
            return CANONICAL_DEPARTMENTS[code]

    return None


def detect_department_ambiguity(query_text: str) -> Optional[Dict[str, Any]]:
    """
    Detect if a query has ambiguous intent between multiple distinct official departments.
    For instance: 'show all faculty in AI' without specifying AI vs AI&ML.
    
    If the query explicitly specifies:
    - 'AI and ML' or 'AIML' -> Disambiguated to CSE-AIML.
    - 'Artificial Intelligence' (without ML) or 'CSE AI' or 'AI department' -> Disambiguated to AI.
    
    Returns a dict with clarification question if truly ambiguous, else None.
    """
    lower = query_text.lower().strip()
    
    # Standalone "ai" with generic tokens (e.g. "who works in ai", "show ai faculty", "ai faculty")
    # without specifying "ml", "machine learning", or specific department qualifiers.
    is_standalone_ai = bool(re.search(r"\b(faculty\s+(in|of)\s+ai|show\s+ai\s+faculty|ai\s+faculty|who\s+works\s+in\s+ai)\b", lower))
    has_ml = bool(re.search(r"\b(ml|machine learning|and ml|& ml)\b", lower))
    has_dept_qualifier = bool(re.search(r"\b(ai\s+department|department\s+of\s+ai|cse[- ]?ai)\b", lower))

    # If the user says "show AI faculty" or "faculty in AI" without "department" and without "ML"
    if is_standalone_ai and not has_ml and not has_dept_qualifier:
        return {
            "is_ambiguous": True,
            "clarification_question": (
                "Which department do you mean?\n"
                "1. Department of Computer Science & Engineering (Artificial Intelligence) [CSE-AI]\n"
                "2. Department of Computer Science & Engineering (Artificial Intelligence & Machine Learning) [CSE-AIML]"
            ),
            "candidate_departments": [
                CANONICAL_DEPARTMENTS["AI"],
                CANONICAL_DEPARTMENTS["CSE-AIML"],
            ],
        }

    return None
