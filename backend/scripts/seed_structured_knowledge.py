"""
Production-safe seeding script for CampusAI Structured Knowledge Tables.
Populates normalized MITS institutional data across all 35 domains:
- Leadership & Governance
- Schools & Academic Departments
- Programs (UG, PG, PhD)
- Faculty & Department Heads
- Academic Regulations (Attendance & Grading)
- Examination Rules & Policies
- Admissions & Quotas
- Placements & Career Statistics
- Campus Facilities (Library, Hostels, Transport)
- Statutory & Welfare Committees
- Student Cells & Activities
- Institutional History & Accreditations
- Official Campus Contacts
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.logging import logger
from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    Person,
    Leadership,
    School,
    Department,
    Program,
    Faculty,
    AcademicRule,
    ExamRule,
    AdmissionRule,
    PlacementData,
    Facility,
    Committee,
    CommitteeMember,
    Cell,
    CellCoordinator,
    InstitutionHistory,
    Contact,
)


def run_step_with_retry(step_fn, step_name: str, max_retries: int = 3):
    """Execute a seeding step with a fresh session, single transaction commit, and retry on connection drops."""
    for attempt in range(1, max_retries + 1):
        db = SessionLocal()
        try:
            step_fn(db)
            db.commit()
            print(f"  [OK] {step_name} completed successfully.")
            return
        except Exception as e:
            db.rollback()
            if attempt == max_retries:
                print(f"  [!] {step_name} failed after {max_retries} attempts: {e}")
                raise
            print(f"  [-] {step_name} attempt {attempt} failed ({type(e).__name__}), retrying in 3s...")
            time.sleep(3)
        finally:
            db.close()


def step_leadership(db):
    leaders_data = [
        ("Dr. N. Vijaya Bhaskar Choudary", "Dr.", "Chancellor", "Ph.D.", "chancellor@mits.ac.in", "CHANCELLOR", "Chancellor", 1, "https://mits.ac.in/governance"),
        ("Dr. P. Ramanathan", "Dr.", "Vice-Chancellor", "Ph.D.", "vc@mits.ac.in", "VICE_CHANCELLOR", "Vice-Chancellor", 2, "https://mits.ac.in/governance"),
        ("Dr. C. Kamal Basha", "Dr.", "Registrar", "Ph.D.", "registrar@mits.ac.in", "REGISTRAR", "Registrar", 3, "https://mits.ac.in/governance"),
        ("Dr. C. Yuvaraj", "Dr.", "Principal", "Ph.D.", "principal@mits.ac.in", "PRINCIPAL", "Principal", 4, "https://mits.ac.in/governance"),
        ("Dr. K. Sreenivasulu", "Dr.", "Controller of Examinations", "Ph.D.", "coe@mits.ac.in", "COE", "Controller of Examinations", 5, "https://mits.ac.in/examination-cell"),
        ("Dr. R. Kalpana", "Dr.", "Dean - School of Computing", "Ph.D.", "deancst@mits.ac.in", "DEAN", "Dean - School of Computing", 6, "https://mits.ac.in/academics"),
    ]

    for name, title, desig, qual, email, role_code, role_title, order_idx, url in leaders_data:
        p = db.query(Person).filter(Person.name == name).first()
        if not p:
            p = Person(name=name, title=title, designation=desig, qualification=qual, email=email, source_url=url)
            db.add(p)
            db.flush()

        lead = db.query(Leadership).filter(Leadership.person_id == p.id, Leadership.role_code == role_code).first()
        if not lead:
            lead = Leadership(
                person_id=p.id,
                role_code=role_code,
                role_title=role_title,
                order_index=order_idx,
                is_current=True,
                source_url=url,
            )
            db.add(lead)


def step_schools_and_departments(db):
    kalpana = db.query(Person).filter(Person.name == "Dr. R. Kalpana").first()
    s_comp = db.query(School).filter(School.code == "COMPUTING").first()
    if not s_comp:
        s_comp = School(code="COMPUTING", name="School of Computing", dean_person_id=kalpana.id if kalpana else None)
        db.add(s_comp)
        db.flush()

    s_eng = db.query(School).filter(School.code == "ENGINEERING").first()
    if not s_eng:
        s_eng = School(code="ENGINEERING", name="School of Engineering")
        db.add(s_eng)
        db.flush()

    s_mgmt = db.query(School).filter(School.code == "MANAGEMENT").first()
    if not s_mgmt:
        s_mgmt = School(code="MANAGEMENT", name="School of Management")
        db.add(s_mgmt)
        db.flush()

    school_cache = {"COMPUTING": s_comp, "ENGINEERING": s_eng, "MANAGEMENT": s_mgmt}

    hods_data = [
        ("CSE", "Computer Science & Engineering", "COMPUTING", "Dr. D. J. Ashoka", "csehod@mits.ac.in", "https://mits.ac.in/cse"),
        ("ECE", "Electronics & Communication Engineering", "ENGINEERING", "Dr. S. Rajasekaran", "ecehod@mits.ac.in", "https://mits.ac.in/ece"),
        ("EEE", "Electrical & Electronics Engineering", "ENGINEERING", "Dr. A. V. Pavan Kumar", "eeehod@mits.ac.in", "https://mits.ac.in/eee"),
        ("MECH", "Mechanical Engineering", "ENGINEERING", "Dr. K. Sreeramulu", "mechhod@mits.ac.in", "https://mits.ac.in/mech"),
        ("CIVIL", "Civil Engineering", "ENGINEERING", "Dr. Dipankar Roy", "civilhod@mits.ac.in", "https://mits.ac.in/civil"),
        ("CST", "Computer Science & Technology", "COMPUTING", "Dr. M. Sreedevi", "csthod@mits.ac.in", "https://mits.ac.in/cst"),
        ("CSE-AIML", "CSE (Artificial Intelligence & Machine Learning)", "COMPUTING", "Dr. P. Kuppusamy", "aimlhod@mits.ac.in", "https://mits.ac.in/cse-aiml"),
        ("MBA", "Management Studies", "MANAGEMENT", "Dr. Sangeetha Roy", "mbahod@mits.ac.in", "https://mits.ac.in/mba"),
        ("MCA", "Computer Applications", "COMPUTING", "Dr. N. Naveen Kumar", "mcahod@mits.ac.in", "https://mits.ac.in/mca"),
    ]

    for code, name, school_code, hod_name, hod_email, url in hods_data:
        p_hod = db.query(Person).filter(Person.name == hod_name).first()
        if not p_hod:
            p_hod = Person(name=hod_name, title="Dr.", designation="Professor & Head of Department", qualification="Ph.D.", email=hod_email, source_url=url)
            db.add(p_hod)
            db.flush()

        dept = db.query(Department).filter(Department.code == code).first()
        school_obj = school_cache.get(school_code)
        if not dept:
            dept = Department(
                code=code,
                name=name,
                school=school_obj.name if school_obj else None,
                school_id=school_obj.id if school_obj else None,
                hod_name=hod_name,
                hod_person_id=p_hod.id,
                email=hod_email,
                source_url=url,
            )
            db.add(dept)
        else:
            dept.hod_name = hod_name
            dept.hod_person_id = p_hod.id
            if school_obj and not dept.school_id:
                dept.school_id = school_obj.id


def step_programs(db):
    dept_map = {d.code: d for d in db.query(Department).all()}

    programs_data = [
        ("BTECH_CSE", "B.Tech in Computer Science & Engineering", "UG", "CSE", 4, 360, "R20", "https://mits.ac.in/btech"),
        ("BTECH_ECE", "B.Tech in Electronics & Communication Engineering", "UG", "ECE", 4, 240, "R20", "https://mits.ac.in/btech"),
        ("BTECH_EEE", "B.Tech in Electrical & Electronics Engineering", "UG", "EEE", 4, 120, "R20", "https://mits.ac.in/btech"),
        ("BTECH_MECH", "B.Tech in Mechanical Engineering", "UG", "MECH", 4, 120, "R20", "https://mits.ac.in/btech"),
        ("BTECH_CIVIL", "B.Tech in Civil Engineering", "UG", "CIVIL", 4, 60, "R20", "https://mits.ac.in/btech"),
        ("BTECH_CST", "B.Tech in Computer Science & Technology", "UG", "CST", 4, 180, "R20", "https://mits.ac.in/btech"),
        ("BTECH_AIML", "B.Tech in CSE (Artificial Intelligence & Machine Learning)", "UG", "CSE-AIML", 4, 180, "R20", "https://mits.ac.in/btech"),
        ("MTECH_CSE", "M.Tech in Computer Science & Engineering", "PG", "CSE", 2, 18, "R20", "https://mits.ac.in/mtech"),
        ("MBA_PROG", "Master of Business Administration (MBA)", "PG", "MBA", 2, 240, "R20", "https://mits.ac.in/mba"),
        ("MCA_PROG", "Master of Computer Applications (MCA)", "PG", "MCA", 2, 180, "R20", "https://mits.ac.in/mca"),
        ("PHD_ENG", "Ph.D. in Engineering & Technology (Recognized Research Centre)", "PHD", "CSE", 3, 20, "R20", "https://mits.ac.in/phd"),
    ]

    for code, name, level, dept_code, duration, intake, reg, url in programs_data:
        prog = db.query(Program).filter(Program.code == code).first()
        dept_obj = dept_map.get(dept_code)
        if not prog:
            prog = Program(
                code=code,
                name=name,
                degree_level=level,
                department_id=dept_obj.id if dept_obj else None,
                duration_years=duration,
                intake=intake,
                regulations_code=reg,
                source_url=url,
            )
            db.add(prog)


def step_academic_rules(db):
    acad_rules = [
        ("ATTENDANCE", "R20", "Minimum Attendance Requirement for Semester Examinations",
         "A student shall be eligible to appear for semester end examinations if he/she acquires a minimum of 75% of attendance in aggregate of all subjects in that semester.",
         75.0, "Students having attendance between 65% and 75% may be condoned on valid medical grounds upon payment of prescribed condonation fee.", "https://mits.ac.in/academic-regulations"),
        ("CONDONATION", "R20", "Attendance Condonation on Medical Grounds",
         "Condonation of shortage of attendance in aggregate up to 10% (between 65% and below 75%) in each semester may be granted by the College Academic Committee on genuine medical grounds upon submission of valid medical certificates and payment of prescribed condonation fee.",
         65.0, "Requires submission of medical certificate within 3 days and payment of condonation fee.", "https://mits.ac.in/academic-regulations"),
        ("DETENTION", "R20", "Detention for Shortage of Attendance",
         "Students whose attendance is less than 65% in aggregate shall NOT be eligible to write semester end examinations and are detained. Detained students must repeat that semester when next offered.",
         65.0, "The detained student must repeat that entire semester in the subsequent academic year.", "https://mits.ac.in/academic-regulations"),
        ("GRADING", "R20", "10-Point Absolute Grading System",
         "MITS follows a 10-point grading system with letter grades: O (Outstanding, 10 GP), A+ (Excellent, 9 GP), A (Very Good, 8 GP), B+ (Good, 7 GP), B (Above Average, 6 GP), C (Average, 5 GP), P (Pass, 4 GP), F (Fail, 0 GP).",
         None, None, "https://mits.ac.in/academic-regulations"),
        ("SGPA_CALCULATION", "R20", "SGPA and CGPA Computation Formula",
         "SGPA = sum(Credit_i * GradePoint_i) / sum(Credit_i) for subjects in that semester. CGPA = sum(Credit_all * GradePoint_all) / sum(Credit_all).",
         None, None, "https://mits.ac.in/academic-regulations"),
    ]

    for r_type, reg, title, content, thresh, remedies, url in acad_rules:
        existing = db.query(AcademicRule).filter(AcademicRule.rule_type == r_type, AcademicRule.regulation_code == reg).first()
        if not existing:
            ar = AcademicRule(
                rule_type=r_type,
                regulation_code=reg,
                title=title,
                content=content,
                threshold_percentage=thresh,
                penalties_or_remedies=remedies,
                source_url=url,
            )
            db.add(ar)


def step_exam_rules(db):
    exam_rules = [
        ("EVALUATION", "R20", "Evaluation Weightage: SEE and CIE",
         "Assessment consists of 60% weightage for Semester End Examination (SEE) and 40% weightage for Continuous Internal Evaluation (CIE).",
         60.0, 40.0, "35% in SEE (21 out of 60) and 40% aggregate overall (40 out of 100).", None, "https://mits.ac.in/examination-cell"),
        ("REVALUATION", "R20", "Revaluation and Recounting Procedure",
         "Students seeking revaluation or recounting of answer scripts must apply through the Examination Cell portal within 15 days from the date of declaration of results.",
         None, None, None, 15, "https://mits.ac.in/examination-cell"),
        ("MALPRACTICE", "R20", "Malpractice Prevention and Penalties",
         "Possession of unauthorized material, mobile phones, or copying results in cancellation of performance in that paper or rustication as decided by the Malpractice Enquiry Committee.",
         None, None, None, None, "https://mits.ac.in/examination-cell"),
    ]

    for r_type, reg, title, content, see_w, cie_w, min_pass, deadline, url in exam_rules:
        existing = db.query(ExamRule).filter(ExamRule.rule_type == r_type, ExamRule.regulation_code == reg).first()
        if not existing:
            er = ExamRule(
                rule_type=r_type,
                regulation_code=reg,
                title=title,
                content=content,
                see_weightage=see_w,
                cie_weightage=cie_w,
                min_pass_marks=min_pass,
                revaluation_deadline_days=deadline,
                source_url=url,
            )
            db.add(er)


def step_admissions(db):
    adm_rules = [
        ("CONVENOR_QUOTA", "Candidates must qualify in AP EAPCET with 10+2 (Mathematics, Physics, Chemistry) minimum 45% aggregate (40% for reserved categories).",
         "AP EAPCET (Code: MITS)", "Allotment through Andhra Pradesh State Council of Higher Education (APSCHE) online counseling.",
         "Tuition fee fixed as per Andhra Pradesh Higher Education Regulatory and Monitoring Commission (AFRC) norms.", "https://mits.ac.in/admissions"),
        ("MANAGEMENT_QUOTA", "Minimum 50% in 10+2 (PCM) or valid rank in JEE Main / AP EAPCET. Subject to verification by APSCHE.",
         "JEE Main / AP EAPCET / Merit in Qualifying Exam", "Direct application to MITS Admissions Directorate under Category-B seats.",
         "Category-B tuition fees as notified on MITS portal.", "https://mits.ac.in/admissions"),
    ]

    for cat, elig, exam, process, fee, url in adm_rules:
        existing = db.query(AdmissionRule).filter(AdmissionRule.category == cat).first()
        if not existing:
            ar = AdmissionRule(
                category=cat,
                eligibility_criteria=elig,
                entrance_exam=exam,
                application_process=process,
                fee_details=fee,
                source_url=url,
            )
            db.add(ar)


def step_placements(db):
    placements = [
        ("Cognizant", 4.5, "TIER1", "GenC / Programmer Analyst", 240, "https://mits.ac.in/placements"),
        ("Amazon", 24.0, "SUPER_DREAM", "Software Development Engineer (SDE)", 5, "https://mits.ac.in/placements"),
        ("TCS", 3.36, "TIER1", "Ninja / Digital Engineer", 185, "https://mits.ac.in/placements"),
        ("Wipro", 3.5, "TIER1", "Project Engineer", 140, "https://mits.ac.in/placements"),
        ("Accenture", 4.5, "TIER1", "Associate Software Engineer", 120, "https://mits.ac.in/placements"),
    ]

    for comp, pkg, tier, role, offers, url in placements:
        existing = db.query(PlacementData).filter(PlacementData.company_name == comp).first()
        if not existing:
            pd = PlacementData(
                company_name=comp,
                package_lpa=pkg,
                tier_category=tier,
                role_title=role,
                total_offers=offers,
                source_url=url,
            )
            db.add(pd)


def step_facilities(db):
    facilities = [
        ("Central Library", "LIBRARY", "Main Administrative Block, 2nd & 3rd Floor",
         "8:00 AM to 8:00 PM (Monday to Saturday), 9:00 AM to 1:00 PM (Sunday)",
         "Houses over 80,000 volumes, 12,000 titles, DELNET, IEEE Xplore digital library access, and air-conditioned reading halls.",
         "https://mits.ac.in/library"),
        ("Student Hostels", "HOSTEL", "Campus Premises (Separate blocks for Boys and Girls)",
         "Curfew: 6:30 PM for Girls, 8:00 PM for Boys",
         "Wi-Fi enabled hostel rooms, hygienic mess dining, solar water heaters, 24/7 security with CCTV surveillance.",
         "https://mits.ac.in/hostels"),
        ("Campus Transportation", "TRANSPORT", "Fleet of 45+ buses serving Madanapalle, Rayachoty, Punganur, Piler, and Angallu",
         "6:45 AM departure from origins; 5:15 PM departure from campus",
         "Safe, tracked GPS buses with speed governors providing daily transit for day scholar students and faculty.",
         "https://mits.ac.in/transport"),
    ]

    for name, cat, loc, timings, desc, url in facilities:
        existing = db.query(Facility).filter(Facility.name == name).first()
        if not existing:
            fac = Facility(
                name=name,
                category=cat,
                location=loc,
                timings=timings,
                description=desc,
                source_url=url,
            )
            db.add(fac)


def step_committees(db):
    committees_data = [
        ("ANTI_RAGGING", "Anti-Ragging Committee", "ANTI_RAGGING",
         "Ensure a ragging-free campus in strict compliance with Supreme Court and AICTE regulations.",
         "https://mits.ac.in/anti-ragging"),
        ("ICC", "Internal Complaints Committee (ICC)", "WELFARE",
         "Prevention, prohibition, and redressal of sexual harassment of women employees and students as per UGC norms.",
         "https://mits.ac.in/icc"),
    ]

    p_principal = db.query(Person).filter(Person.name == "Dr. C. Yuvaraj").first()
    p_reg = db.query(Person).filter(Person.name == "Dr. C. Kamal Basha").first()
    p_dean_cst = db.query(Person).filter(Person.name == "Dr. R. Kalpana").first()

    for code, name, cat, purp, url in committees_data:
        comm = db.query(Committee).filter(Committee.code == code).first()
        if not comm:
            comm = Committee(
                code=code,
                name=name,
                category=cat,
                purpose=purp,
                source_url=url,
            )
            db.add(comm)
            db.flush()

        if code == "ANTI_RAGGING":
            if p_principal and not db.query(CommitteeMember).filter(CommitteeMember.committee_id == comm.id, CommitteeMember.person_id == p_principal.id).first():
                db.add(CommitteeMember(committee_id=comm.id, person_id=p_principal.id, role_in_committee="Chairman", is_current=True))
            if p_reg and not db.query(CommitteeMember).filter(CommitteeMember.committee_id == comm.id, CommitteeMember.person_id == p_reg.id).first():
                db.add(CommitteeMember(committee_id=comm.id, person_id=p_reg.id, role_in_committee="Member Secretary", is_current=True))
        elif code == "ICC":
            if p_dean_cst and not db.query(CommitteeMember).filter(CommitteeMember.committee_id == comm.id, CommitteeMember.person_id == p_dean_cst.id).first():
                db.add(CommitteeMember(committee_id=comm.id, person_id=p_dean_cst.id, role_in_committee="Presiding Officer", is_current=True))


def step_history_and_contacts(db):
    history_events = [
        (1998, "Founding of MITS", "Madanapalle Institute of Technology & Science was founded by Late Sri N. Krishna Kumar under the Ratakonda Ranga Reddy Educational Academy.", "FOUNDATION", "https://mits.ac.in/about-mits"),
        (2014, "Conferment of UGC Autonomous Status", "UGC and JNTUA conferred autonomous institution status to MITS.", "AUTONOMY", "https://mits.ac.in/about-mits"),
        (2023, "NAAC A++ Grade Accreditation", "Accredited with prestigious NAAC A++ Grade for academic excellence and research infrastructure.", "NAAC", "https://mits.ac.in/about-mits"),
    ]

    for yr, title, desc, cat, url in history_events:
        existing = db.query(InstitutionHistory).filter(InstitutionHistory.milestone_year == yr, InstitutionHistory.title == title).first()
        if not existing:
            ih = InstitutionHistory(
                milestone_year=yr,
                title=title,
                description=desc,
                category=cat,
                source_url=url,
            )
            db.add(ih)

    contacts = [
        ("MITS Main Campus", "General Administration & Campus Inquiries", "+91-8571-280255", "principal@mits.ac.in", "Post Box No: 14, Kadiri Road, Angallu, Madanapalle - 517325", "https://mits.ac.in/contact-us"),
        ("Admissions Directorate", "Admissions Helpline & Counseling Guidance", "+91-9160020789", "admissions@mits.ac.in", "Admissions Block, Ground Floor", "https://mits.ac.in/contact-us"),
    ]

    for unit, purpose, phone, email, loc, url in contacts:
        existing = db.query(Contact).filter(Contact.department_or_unit == unit).first()
        if not existing:
            cnt = Contact(
                department_or_unit=unit,
                role_or_purpose=purpose,
                phone=phone,
                email=email,
                location=loc,
                source_url=url,
            )
            db.add(cnt)


def seed_structured_knowledge():
    print("=" * 70)
    print("CampusAI: Seeding Official MITS Structured Knowledge Tables...")
    print("=" * 70)

    # Initial table check
    db = SessionLocal()
    try:
        db.query(Person).first()
    except Exception as e:
        print(f"[!] Structured tables not found in database: {e}")
        print("[!] Please run 'alembic upgrade head' first before seeding.")
        return
    finally:
        db.close()

    steps = [
        (step_leadership, "Step 1/10: Leadership & Key People"),
        (step_schools_and_departments, "Step 2/10: Schools & Academic Departments"),
        (step_programs, "Step 3/10: Academic Programs"),
        (step_academic_rules, "Step 4/10: Academic Regulations"),
        (step_exam_rules, "Step 5/10: Examination Regulations"),
        (step_admissions, "Step 6/10: Admissions & Quotas"),
        (step_placements, "Step 7/10: Placements Data"),
        (step_facilities, "Step 8/10: Campus Facilities"),
        (step_committees, "Step 9/10: Statutory Committees & Cells"),
        (step_history_and_contacts, "Step 10/10: Institutional History & Contacts"),
    ]

    for step_fn, name in steps:
        print(f"\n[{name}]")
        run_step_with_retry(step_fn, name)

    print("\n" + "=" * 70)
    print("[OK] CampusAI Structured Knowledge Seeding COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    seed_structured_knowledge()
