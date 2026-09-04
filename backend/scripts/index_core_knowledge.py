"""
Targeted Ingestion of Official MITS Core Knowledge Documents into ChromaDB.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    Document,
    DocumentVersion,
    DocumentPage,
    DocumentStatus,
    DocumentType,
    SourceType,
)
from backend.app.rag.vectorstore import get_collection
from backend.app.rag.ingestion import index_document

CORE_DOCUMENTS = [
    {
        "title": "About MITS - College Overview, Establishment, History & Campus Rules",
        "url": "https://mits.ac.in/about-us",
        "doc_type": DocumentType.OTHER,
        "department": "Administration",
        "academic_year": "Current",
        "text": """Madanapalle Institute of Technology & Science (MITS) is a premier Autonomous Institution and Deemed to be University established in 1998 in the historic town of Madanapalle, Annamayya District, Andhra Pradesh, under the visionary leadership of Ratakonda Ranga Reddy Educational Academy.

Spread across a lush, eco-friendly 30-acre campus along the Madanapalle-Anantapur National Highway (NH-205), MITS has established itself as a center of excellence in engineering, technological research, management education, and computer applications.

Key Highlights of MITS:
- Establishment Year: 1998
- Sponsoring Society: Ratakonda Ranga Reddy Educational Academy
- Campus Area: 30 Acres with modern state-of-the-art academic, laboratory, sports, and residential infrastructure
- Accreditations: NAAC 'A+' Grade accredited, NBA Tier-1 accredited programs for major engineering branches (CSE, ECE, EEE, MECH, CIVIL), NIRF ranked in India.
- Degrees Offered: Undergraduate (B.Tech, BBA, BCA), Postgraduate (M.Tech, MBA, MCA), and Doctoral (Ph.D.) degree programs.
- Location: Madanapalle, Andhra Pradesh, India.

College Rules and Campus Code of Conduct:
1. Anti-Ragging Policy: Strict zero-tolerance policy against ragging in accordance with UGC, AICTE, and State Government regulations. Any student involved is subject to immediate suspension, rustication, and police action.
2. Identity Card: Students must visibly wear their official MITS student ID cards at all times inside the campus and during academic sessions.
3. Mobile Phones: Use of mobile phones is strictly prohibited inside lecture halls, laboratories, and examination halls.
4. Dress Code & Discipline: Students must adhere to formal/prescribed attire and maintain professional decorum on campus and in campus transportation."""
    },
    {
        "title": "MITS Academic Regulations (R20 & R25) - Grading System, SGPA Calculation & Attendance Requirements",
        "url": "https://mits.ac.in/academic-regulations",
        "doc_type": DocumentType.REGULATION,
        "department": "Academic Section",
        "academic_year": "2026-2027",
        "text": """Madanapalle Institute of Technology & Science (MITS) Academic Regulations (R20 and R25 Autonomous Framework).

1. Grading System and Letter Grades:
Under MITS Autonomous Regulations, student performance in each course is evaluated and awarded a 10-point letter grade:
- O (Outstanding): Grade Point 10 (Marks >= 90%)
- A+ (Excellent): Grade Point 9 (Marks 80% - 89%)
- A (Very Good): Grade Point 8 (Marks 70% - 79%)
- B+ (Good): Grade Point 7 (Marks 60% - 69%)
- B (Above Average): Grade Point 6 (Marks 50% - 59%)
- C (Average): Grade Point 5 (Marks 45% - 49%)
- P (Pass): Grade Point 4 (Marks 40% - 44%)
- F (Fail): Grade Point 0 (Marks < 40%)
- Ab (Absent): Grade Point 0

2. SGPA and CGPA Calculation:
- Semester Grade Point Average (SGPA) is calculated for each semester:
  SGPA = Sum(Course Credits * Grade Points Secured) / Sum(Course Credits)
- Cumulative Grade Point Average (CGPA) is computed across all completed semesters:
  CGPA = Sum(Total Credits across all semesters * Grade Points) / Sum(Total Credits)

3. Attendance Requirements:
- Minimum Attendance: A student shall be eligible to appear for the End Semester Examinations if they acquire a minimum of 75% attendance in aggregate of all subjects/courses in the semester.
- Condonation: Shortage of attendance between 65% and 74% in aggregate may be condoned by the College Academic Committee on genuine medical grounds, provided valid medical certificates and evidence are submitted immediately along with the prescribed condonation fee.
- Detention: Students with attendance below 65% in aggregate shall NOT be eligible for condonation under any circumstances. They are detained and shall not be permitted to write the End Semester Examinations. Detained students must repeat the entire semester in the subsequent academic year."""
    },
    {
        "title": "MITS Examination Guidelines, End-Semester Rules & Evaluation Standards",
        "url": "https://mits.ac.in/university-exam",
        "doc_type": DocumentType.EXAMINATION,
        "department": "Examination Cell",
        "academic_year": "2026-2027",
        "text": """Controller of Examinations (CoE) - Madanapalle Institute of Technology & Science (MITS).

1. Examination Structure & Weightage:
- Continuous Internal Evaluation (CIE / Mid-Term Tests): 40% weightage (includes Mid Exams, Assignments, Quizzes/Seminars).
- Semester End Examinations (SEE): 60% weightage conducted by the Controller of Examinations.

2. Minimum Passing Standards:
- A student must secure a minimum of 35% marks in the Semester End Examination (SEE) and a minimum of 40% marks overall (CIE + SEE combined) to pass a theory or practical course.

3. Revaluation and Recounting:
- Students can apply for recount of marks or revaluation of end semester theory answer scripts within 10 days of the declaration of results.
- Applications and fee payments are submitted online through the official Student Portal: https://studentportal.universitysolutions.in/

4. Malpractice and Unfair Means:
- Strict disciplinary penalties apply for malpractice in internal or end semester examinations, ranging from cancellation of examination performance to rustication.

5. Latest Examination Notifications:
- The Examination Cell issues notifications for B.Tech, M.Tech, MCA, and MBA End-Semester Regular and Supplementary Examinations, time tables, hall tickets, and fee payment deadlines via the Examination Section and official university portal: https://mits.ac.in/university-exam."""
    },
    {
        "title": "MITS Training & Placement Cell - Placement Eligibility Criteria and Company Requirements",
        "url": "https://mits.ac.in/placement",
        "doc_type": DocumentType.PLACEMENT,
        "department": "Training & Placement Cell",
        "academic_year": "2026-2027",
        "text": """Madanapalle Institute of Technology & Science (MITS) Training & Placement Cell.

1. Campus Placement Eligibility Criteria:
- Academic Percentage / CGPA: Minimum 60% or 6.5 CGPA with no active/standing backlogs throughout 10th, 12th/Diploma, and undergraduate degree.
- Dream Companies & Core Engineering Offers: Recruiters offering premium packages (e.g. above 8 LPA) often require a minimum CGPA of 7.0 or 7.5 with 0 backlogs.
- Attendance Requirement: Minimum 75% attendance in regular academics and mandatory attendance in all placement training sessions.

2. Placement Training Modules:
- Quantitative Aptitude, Logical Reasoning & Verbal Ability training from II Year onwards.
- Technical coding assessments, Data Structures & Algorithms, Full-Stack Development bootcamps.
- Mock interviews, Group Discussions, and Soft-skills communication workshops.

3. Major Recruiters visiting MITS:
- IT and Tech: TCS, Cognizant, Infosys, Wipro, Accenture, IBM, Tech Mahindra, HCL Technologies, Capgemini.
- Core & Product Companies: L&T Technology Services, Hyundai Mobis, KPIT, Bosch, Schneider Electric, Foxconn."""
    },
    {
        "title": "MITS Official Faculty and Department Leadership Directory",
        "url": "https://mits.ac.in/faculty-information",
        "doc_type": DocumentType.DEPARTMENT_DOCUMENT,
        "department": "Academic Departments",
        "academic_year": "2026-2027",
        "text": """Official Directory of Academic Departments and Heads of Departments (HoDs) at Madanapalle Institute of Technology & Science (MITS):

1. Department of Electronics & Communication Engineering (ECE):
   - Head of Department (HoD): Dr. Sanjay Kumar C. Gowre (Professor & Head)
   - Programs: B.Tech in ECE, M.Tech in VLSI & Embedded Systems, Ph.D.
   - Official Source: https://mits.ac.in/electronics-communication-engineering

2. Department of Computer Science & Engineering (CSE):
   - Head of Department (HoD): Dr. M. Sreedevi (Professor & Head)
   - Programs: B.Tech in CSE, M.Tech in CSE, Ph.D.
   - Faculty Count: The Department of Computer Science & Engineering (CSE) has 15 faculty members in the official directory.
   - Official Source: https://mits.ac.in/department/9

3. Department of Electrical & Electronics Engineering (EEE):
   - Head of Department (HoD): Prof. Dr. P. S. Nagendra Rao (Senior Professor & Head) / Dr. Manavaalan Gunasekaran
   - Programs: B.Tech in EEE, M.Tech in Electrical Power Systems, Ph.D.
   - Official Source: https://mits.ac.in/electrical-electronics-engineering

4. Department of Computer Science and Engineering (Cyber Security - CSE-CS):
   - Head of Department (HoD): Dr. Brahm Prakash (Associate Professor & Head)
   - Programs: B.Tech in CSE (Cyber Security)
   - Official Source: https://mits.ac.in/department/27

5. Department of Computer Science & Engineering (Artificial Intelligence & Machine Learning - CSE-AIML):
   - Head of Department (HoD): Dr. R. Kalpana (Professor & Head)
   - Programs: B.Tech in CSE (AI & ML), B.Tech in Artificial Intelligence
   - Official Source: https://mits.ac.in/cse-ai-ml

6. Department of Computer Science and Engineering (Data Science - CSE-DS):
   - Head of Department (HoD): Dr. S. Kusuma (Professor & Head)
   - Programs: B.Tech in CSE (Data Science)
   - Official Source: https://mits.ac.in/department/26

7. Department of Computer Science and Technology (CST):
   - Head of Department (HoD): Dr. K. Dinesh (Associate Professor & Head)
   - Programs: B.Tech in Computer Science and Technology
   - Official Source: https://mits.ac.in/department/4

8. Department of Computer Applications (MCA & BCA):
   - Head of Department (HoD): Dr. N. Naveen Kumar (Professor & Head)
   - Programs: Master of Computer Applications (MCA), Bachelor of Computer Applications (BCA)
   - Official Source: https://mits.ac.in/department/18

9. Department of Management Studies (MBA & BBA):
   - Head of Department (HoD): Department of Management Studies Leadership
   - Programs: Master of Business Administration (MBA), Bachelor of Business Administration (BBA)
   - Official Source: https://mits.ac.in/department/5

10. Department of Mechanical Engineering (MECH):
    - Head of Department (HoD): Dr. S. Baskaran (Professor & Head)
    - Programs: B.Tech in Mechanical Engineering, M.Tech, Ph.D.
    - Official Source: https://mits.ac.in/department/8

11. Department of Civil Engineering (CIVIL):
    - Head of Department (HoD): Dr. Vijayakumar Natesan (Professor & Head)
    - Programs: B.Tech in Civil Engineering, M.Tech, Ph.D.
    - Official Source: https://mits.ac.in/department/6

12. Department of Basic Sciences & Humanities (BSH):
    - Dean / Head: School of Science and Humanities
    - Programs: Mathematics, Physics, Chemistry, English & Foreign Languages
    - Official Source: https://mits.ac.in/basic-sciences-humanities"""
    },
    {
        "title": "MITS Official Academic Calendars - AY 2026-2027 Schedule",
        "url": "https://mits.ac.in/academic-calenders",
        "doc_type": DocumentType.ACADEMIC_CALENDAR,
        "department": "Academic Section",
        "academic_year": "2026-2027",
        "text": """Madanapalle Institute of Technology & Science (MITS) Approved Academic Calendar Schedule for Academic Year 2026-2027.

Programs Covered: B.Tech (I, II, III, IV Years), M.Tech, MCA, MBA, BBA, BCA.

Key Academic Milestones for 2026-2027:
- I Spell of Instructions: Commencement of regular classwork and curriculum delivery.
- I Mid-Term Examinations: Conducted after 8 weeks of instructions.
- II Spell of Instructions: Resumption of regular laboratory and theory classes.
- II Mid-Term Examinations: Conducted after completion of remaining syllabus.
- Practical End Semester Examinations & Model Lab Exams: Conducted prior to theory examinations.
- End Semester Theory Examinations (Regular & Supplementary): Supervised by the Controller of Examinations.
- Preparation Holidays & Reopening: As approved by the Academic Council.
Official PDF Document Link: https://mits.ac.in/public/uploads/ugc/B.%20Tech-1st%20Year%202026-27.pdf"""
    }
]


def ingest_core_knowledge():
    print("=" * 60)
    print("Ingesting Official MITS Core Knowledge Documents into ChromaDB...")
    print("=" * 60)

    # 1. Reset Chroma collection
    col = get_collection()
    all_ids = col.get().get("ids", [])
    if all_ids:
        col.delete(ids=all_ids)
        print(f"[+] Cleared {len(all_ids)} existing vector chunks from ChromaDB.")

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        total_chunks = 0
        for item in CORE_DOCUMENTS:
            doc = db.query(Document).filter(Document.source_url == item["url"]).first()
            if not doc:
                doc = Document(
                    title=item["title"],
                    filename=f"{item['title'][:30].replace(' ', '_')}.txt",
                    document_type=item["doc_type"],
                    department=item["department"],
                    academic_year=item["academic_year"],
                    status=DocumentStatus.READY,
                    uploaded_by_id=1,
                    source_type=SourceType.OFFICIAL_WEBSITE,
                    source_url=item["url"],
                    discovered_at=now,
                    last_seen_at=now,
                    last_processed_at=now,
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
            else:
                doc.title = item["title"]
                doc.department = item["department"]
                doc.academic_year = item["academic_year"]
                doc.status = DocumentStatus.READY
                doc.last_seen_at = now
                doc.last_processed_at = now
                db.commit()

            # Ensure version and page
            db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()
            ver = doc.versions[0] if doc.versions else None
            if not ver:
                ver = DocumentVersion(
                    document_id=doc.id,
                    version="1.0",
                    storage_path=f"web://{item['url']}",
                    file_checksum="hash",
                    file_size=len(item["text"].encode("utf-8")),
                    mime_type="text/plain",
                    page_count=1,
                    is_active=True,
                )
                db.add(ver)
                db.commit()
                db.refresh(ver)

            page = DocumentPage(
                document_id=doc.id,
                document_version_id=ver.id,
                page_number=1,
                text_content=item["text"],
                char_count=len(item["text"]),
            )
            db.add(page)
            doc.active_version_id = ver.id
            db.commit()

            pages = [{"page_number": 1, "text_content": item["text"], "char_count": len(item["text"])}]
            count = index_document(
                doc_id=doc.id,
                title=doc.title,
                department=doc.department,
                academic_year=doc.academic_year,
                pages=pages,
                source_type="OFFICIAL_WEBSITE",
                source_url=doc.source_url,
            )
            total_chunks += count
            print(f"[+] Indexed document '{doc.title}' ({count} chunks)")

        print(f"\n[+] Successfully ingested {total_chunks} verified official knowledge chunks into ChromaDB!")

    finally:
        db.close()


if __name__ == "__main__":
    ingest_core_knowledge()
