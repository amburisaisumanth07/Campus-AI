"""
Unit tests for CampusAI Query Router.
Tests all 17 distinct query intents and entity extraction.
"""
import pytest
from backend.app.rag.router import classify_query, QueryIntent, extract_department, extract_person_name


def test_extract_department():
    assert extract_department("Who is the HOD of Computer Science and Engineering?") == "CSE"
    assert extract_department("Tell me about cse-aiml department") == "CSE-AIML"
    assert extract_department("Faculty members in ECE") == "ECE"
    assert extract_department("Mechanical engineering labs") == "MECH"
    assert extract_department("Civil engineering department") == "CIVIL"
    assert extract_department("Electrical and electronics") == "EEE"
    assert extract_department("MCA course details") == "MCA"
    assert extract_department("MBA programs") == "MBA"
    assert extract_department("What is the weather today?") is None


def test_extract_person_name():
    assert extract_person_name("Who is Dr. C. Kamal Basha?") == "Dr. C. Kamal Basha"
    assert extract_person_name("Tell me about Prof. K. Sreenivasulu") == "Prof. K. Sreenivasulu"
    assert extract_person_name("Contact Mr. John Doe") == "Mr. John Doe"
    assert extract_person_name("What is attendance percentage?") is None


def test_intent_person_lookup():
    q = classify_query("Who is Dr. C. Kamal Basha?")
    assert q.intent == QueryIntent.PERSON_LOOKUP
    assert q.requires_structured is True


def test_intent_role_lookup():
    q1 = classify_query("Who is the Chancellor of MITS?")
    assert q1.intent == QueryIntent.ROLE_LOOKUP
    assert q1.extracted_entities.get("role_code") == "CHANCELLOR"

    q2 = classify_query("Who is the Vice-Chancellor?")
    assert q2.intent == QueryIntent.ROLE_LOOKUP
    assert q2.extracted_entities.get("role_code") == "VICE_CHANCELLOR"

    q3 = classify_query("Who is the Registrar?")
    assert q3.intent == QueryIntent.ROLE_LOOKUP
    assert q3.extracted_entities.get("role_code") == "REGISTRAR"

    q4 = classify_query("Who is the Principal of MITS?")
    assert q4.intent == QueryIntent.ROLE_LOOKUP
    assert q4.extracted_entities.get("role_code") == "PRINCIPAL"

    q5 = classify_query("Who is the Controller of Examinations?")
    assert q5.intent == QueryIntent.ROLE_LOOKUP
    assert q5.extracted_entities.get("role_code") == "COE"

    q6 = classify_query("Who is the HOD of CSE?")
    assert q6.intent == QueryIntent.ROLE_LOOKUP
    assert q6.extracted_entities.get("role_code") == "HOD"
    assert q6.extracted_entities.get("department_code") == "CSE"


def test_intent_department_lookup():
    q = classify_query("Tell me about the department of Computer Science and Engineering")
    assert q.intent == QueryIntent.DEPARTMENT_LOOKUP
    assert q.extracted_entities.get("department_code") == "CSE"


def test_intent_faculty_lookup():
    q1 = classify_query("List all faculty in CSE department")
    assert q1.intent == QueryIntent.FACULTY_LOOKUP
    assert q1.extracted_entities.get("department_code") == "CSE"

    q2 = classify_query("Who are the professors in ECE?")
    assert q2.intent == QueryIntent.FACULTY_LOOKUP
    assert q2.extracted_entities.get("department_code") == "ECE"


def test_intent_program_lookup():
    q1 = classify_query("What B.Tech programs and degrees are offered?")
    assert q1.intent == QueryIntent.PROGRAM_LOOKUP

    q2 = classify_query("List all postgraduate programs offered")
    assert q2.intent == QueryIntent.PROGRAM_LOOKUP


def test_intent_admission():
    q1 = classify_query("How to get admission through EAPCET in MITS?")
    assert q1.intent == QueryIntent.ADMISSION
    assert q1.requires_structured is True
    assert q1.requires_rag is True

    q2 = classify_query("What is the management quota eligibility and fee structure?")
    assert q2.intent == QueryIntent.ADMISSION


def test_intent_examination():
    q1 = classify_query("What is the revaluation procedure and fee for semester exams?")
    assert q1.intent == QueryIntent.EXAMINATION
    assert q1.requires_structured is True

    q2 = classify_query("What are the malpractice rules in examinations?")
    assert q2.intent == QueryIntent.EXAMINATION


def test_intent_attendance():
    q1 = classify_query("What is the minimum attendance percentage required to write exams?")
    assert q1.intent == QueryIntent.ATTENDANCE
    assert q1.requires_structured is True
    assert q1.requires_rag is True

    q2 = classify_query("What are the condonation rules for attendance shortage?")
    assert q2.intent == QueryIntent.ATTENDANCE


def test_intent_academic_rule():
    q1 = classify_query("How is SGPA and CGPA calculated in R20 regulations?")
    assert q1.intent == QueryIntent.ACADEMIC_RULE

    q2 = classify_query("What is the grading system and pass criteria?")
    assert q2.intent == QueryIntent.ACADEMIC_RULE


def test_intent_placement():
    q1 = classify_query("What is the highest package in MITS placements?")
    assert q1.intent == QueryIntent.PLACEMENT

    q2 = classify_query("Which top recruiters visit campus for placements?")
    assert q2.intent == QueryIntent.PLACEMENT


def test_intent_facility():
    q1 = classify_query("What are the central library timings and borrowing rules?")
    assert q1.intent == QueryIntent.FACILITY
    assert q1.extracted_entities.get("facility_category") == "library"

    q2 = classify_query("What are the hostel facilities and curfew timings for students?")
    assert q2.intent == QueryIntent.FACILITY
    assert q2.extracted_entities.get("facility_category") == "hostel"

    q3 = classify_query("What are the college bus transport routes?")
    assert q3.intent == QueryIntent.FACILITY
    assert q3.extracted_entities.get("facility_category") in ("transport", "bus")


def test_intent_committee():
    q1 = classify_query("Who is on the Anti-Ragging Committee at MITS?")
    assert q1.intent == QueryIntent.COMMITTEE

    q2 = classify_query("What is the role of the Internal Complaints Committee (ICC)?")
    assert q2.intent == QueryIntent.COMMITTEE


def test_intent_history():
    q1 = classify_query("When was MITS established and founded?")
    assert q1.intent == QueryIntent.HISTORY

    q2 = classify_query("Tell me about MITS NAAC accreditation and autonomous status")
    assert q2.intent == QueryIntent.HISTORY


def test_intent_notice():
    q = classify_query("What are the recent circulars and notices published?")
    assert q.intent == QueryIntent.NOTICE


def test_intent_contact():
    q1 = classify_query("What is the contact phone number and email address for MITS?")
    assert q1.intent == QueryIntent.CONTACT

    q2 = classify_query("Where is MITS located?")
    assert q2.intent == QueryIntent.CONTACT


def test_intent_multi_source():
    q = classify_query("Who is the HOD of CSE and what programs are offered?")
    assert q.intent == QueryIntent.MULTI_SOURCE
    assert q.requires_structured is True
    assert q.requires_rag is True


def test_intent_general_rag():
    q = classify_query("Can you help me understand student culture on campus?")
    assert q.intent == QueryIntent.GENERAL_RAG
    assert q.requires_structured is False
    assert q.requires_rag is True
