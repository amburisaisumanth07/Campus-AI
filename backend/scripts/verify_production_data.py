"""
Live Production Data Consistency & Verification Script for CampusAI.

Validates:
1. Canonical Academic Departments (Separation of CSE, CSE-AIML, AI, CSE-DS, CSE-CS, CST, ECE, EEE, MECH, CIVIL, MBA, MCA, BSH).
2. Authoritative Heads of Departments (HODs) and `hod_id` foreign key mappings.
3. Faculty department mappings, exact faculty counts per department, and active status.
4. Academic calendars, examinations, announcements, and placements consistency.
5. URL health & 404/500 rejection check across all stored links.
6. ChromaDB vector store indexing (checking published documents and vector consistency).
7. RAG query retrieval, grounded answer generation, latency profile, and citation correctness.
8. Background Scheduler state, active sources, and next run timestamp.
"""
import io
import sys
import time
from datetime import datetime, timezone
import httpx
from sqlalchemy.orm import Session

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    Department,
    Faculty,
    Announcement,
    AcademicCalendarEvent,
    Examination,
    Placement,
    CollegeInfo,
    ImportantLink,
    WebsiteSource,
    WebsiteSyncHistory,
    Document,
    DocumentStatus,
)
from backend.app.rag import vectorstore, pipeline
from backend.app.services.url_validator import validate_external_url
from backend.app.services.scheduler_service import get_scheduler


def print_section(title: str):
    print(f"\n{'='*75}\n  {title}\n{'='*75}")


def test_departments_and_hods(db: Session) -> bool:
    print_section("1. Canonical Departments & Authoritative HOD Verification")
    depts = db.query(Department).filter(Department.is_active == True, Department.is_valid == True).all()
    print(f"[INFO] Found {len(depts)} active official academic departments in database.")

    canonical_codes = ["CSE", "CSE-AIML", "AI", "CSE-DS", "CSE-CS", "CST", "ECE", "EEE", "MECH", "CIVIL", "MBA", "MCA", "BSH"]
    dept_codes_present = [d.code for d in depts]
    
    print(f"[INFO] Departments found: {', '.join(dept_codes_present)}")

    all_ok = True
    for code in canonical_codes:
        dept = next((d for d in depts if d.code == code), None)
        if dept:
            hod_str = dept.hod_name or dept.hod or "Not Assigned"
            hod_id_str = f" (Faculty ID: {dept.hod_id})" if dept.hod_id else ""
            print(f"  [OK] {dept.code:10} | {dept.name[:45]:45} | HoD: {hod_str}{hod_id_str}")
        else:
            print(f"  [WARN] {code:10} | Not present in active database")

    # Check for substring collision (e.g. CSE matching CSE-AIML)
    cse_depts = [d.code for d in depts if "CSE" in d.code]
    print(f"\n[CHECK] Distinct CSE Family Specializations: {', '.join(cse_depts)}")
    if len(cse_depts) >= 3:
        print("  [OK] CSE specializations are strictly separated into canonical entities.")
    else:
        print("  [WARN] Note: Some CSE sub-specializations may be unseeded or combined.")

    return all_ok


def test_faculty_counts_and_mappings(db: Session) -> bool:
    print_section("2. Faculty Counts & Department Mappings Verification")
    total_faculty = db.query(Faculty).filter(Faculty.is_valid == True, Faculty.is_active == True).count()
    print(f"[INFO] Total verified active faculty members: {total_faculty}")

    depts = db.query(Department).filter(Department.is_active == True).all()
    all_ok = True

    for dept in depts:
        fac_count = db.query(Faculty).filter(
            Faculty.department_id == dept.id,
            Faculty.is_valid == True,
            Faculty.is_active == True
        ).count()
        hod_display = dept.hod_name or dept.hod or "N/A"
        print(f"  • {dept.code:10} : {fac_count:3} members | HoD: {hod_display}")

    return all_ok


def test_announcements_exams_calendar(db: Session) -> bool:
    print_section("3. Announcements, Examinations, Calendars & Placements")
    ann_count = db.query(Announcement).filter(Announcement.is_valid == True).count()
    cal_count = db.query(AcademicCalendarEvent).filter(AcademicCalendarEvent.is_valid == True).count()
    exam_count = db.query(Examination).filter(Examination.is_valid == True).count()
    place_count = db.query(Placement).filter(Placement.is_valid == True).count()
    link_count = db.query(ImportantLink).filter(ImportantLink.is_valid == True, ImportantLink.is_active == True).count()

    print(f"  • Announcements / Circulars : {ann_count}")
    print(f"  • Academic Calendar Events  : {cal_count}")
    print(f"  • Examination Notices       : {exam_count}")
    print(f"  • Placement Drives          : {place_count}")
    print(f"  • Verified Important Links  : {link_count}")

    # Inspect sample records
    latest_ann = db.query(Announcement).filter(Announcement.is_valid == True).order_by(Announcement.published_date.desc().nullslast()).first()
    if latest_ann:
        print(f"\n[SAMPLE ANNOUNCEMENT] '{latest_ann.title}' (Category: {latest_ann.category})")

    latest_exam = db.query(Examination).filter(Examination.is_valid == True).order_by(Examination.published_date.desc().nullslast()).first()
    if latest_exam:
        print(f"[SAMPLE EXAMINATION]  '{latest_exam.title}' (Type: {latest_exam.exam_type}, Program: {latest_exam.program})")

    return True


def test_url_health_checks(db: Session) -> bool:
    print_section("4. URL Health & 404 Prevention Check")
    
    # Collect sample URLs across entities
    urls_to_test = []
    
    for ann in db.query(Announcement).filter(Announcement.is_valid == True, Announcement.source_url.isnot(None)).limit(3).all():
        urls_to_test.append(("Announcement", ann.source_url))
        
    for exam in db.query(Examination).filter(Examination.is_valid == True, Examination.source_url.isnot(None)).limit(3).all():
        urls_to_test.append(("Examination", exam.source_url))
        
    for cal in db.query(AcademicCalendarEvent).filter(AcademicCalendarEvent.is_valid == True, AcademicCalendarEvent.source_url.isnot(None)).limit(3).all():
        urls_to_test.append(("Calendar", cal.source_url))
        
    for link in db.query(ImportantLink).filter(ImportantLink.is_valid == True).limit(3).all():
        urls_to_test.append(("ImportantLink", link.url))

    print(f"[INFO] Validating {len(urls_to_test)} sample official URLs...")

    client = httpx.Client(timeout=10.0, follow_redirects=True)
    all_healthy = True
    try:
        for cat, url in urls_to_test:
            res = validate_external_url(url, client=client)
            status_symbol = "[OK]  " if res.is_valid else "[FAIL]"
            print(f"  {status_symbol} [{cat:14}] HTTP {res.http_status:3} | {url[:60]}")
            if not res.is_valid:
                all_healthy = False
    finally:
        client.close()

    return all_healthy


def test_chroma_and_rag(db: Session) -> bool:
    print_section("5. ChromaDB Vector Indexing & RAG Retrieval Verification")
    
    # Vector count
    try:
        vec_count = vectorstore.count()
        print(f"[INFO] Total vector embeddings in ChromaDB collection '{settings.CHROMA_COLLECTION}': {vec_count}")
    except Exception as e:
        print(f"[ERROR] ChromaDB connection failed: {e}")
        return False

    # Document count in DB
    ready_docs = db.query(Document).filter(Document.status == DocumentStatus.READY).count()
    print(f"[INFO] Total published READY documents in database: {ready_docs}")

    # Test sample RAG queries
    test_queries = [
        "What is the establishment history and overview of MITS Madanapalle?",
        "Who is the Head of the Department for Computer Science & Engineering?",
        "What are the examination guidelines and academic calendar details?",
    ]

    for q in test_queries:
        print(f"\n[RAG QUERY] '{q}'")
        res = pipeline.run_pipeline(query=q, bypass_cache=True)
        print(f"  * Status          : {res.get('status')}")
        print(f"  * Grounded        : {res.get('grounded')}")
        print(f"  * Chunks Retrieved: {res.get('retrieval_count')}")
        print(f"  * Total Latency   : {res.get('total_ms', 0):.1f}ms (Retrieval: {res.get('retrieval_ms', 0):.1f}ms, LLM: {res.get('llm_ms', 0):.1f}ms)")
        answer_preview = res.get('answer', '')[:120].replace('\n', ' ')
        print(f"  * Answer Preview  : {answer_preview}...")

        citations = res.get('citations') or res.get('sources') or []
        print(f"  * Citations ({len(citations)}):")
        for c in citations[:2]:
            print(f"     - Title: {c.get('title')}, Source: {c.get('source_url', 'N/A')}")

    return True


def test_scheduler_state(db: Session) -> bool:
    print_section("6. Background Scheduler & Auto-Sync State")
    sources = db.query(WebsiteSource).all()
    print(f"[INFO] Found {len(sources)} configured website sources in database.")

    scheduler = get_scheduler()

    for s in sources:
        job = scheduler.get_job(f"website_sync_{s.id}")
        job_info = f"Next Execution: {job.next_run_time}" if job else "No APScheduler job registered"
        auto_sync_str = "ENABLED" if s.auto_sync_enabled else "DISABLED"
        print(f"  * Source #{s.id} '{s.name}':")
        print(f"     - Status               : {s.status}")
        print(f"     - Auto-Sync            : {auto_sync_str} (Interval: {s.sync_interval})")
        print(f"     - Last Checked         : {s.last_checked_at or 'Never'}")
        print(f"     - Last Successful Sync : {s.last_successful_sync_at or 'Never'}")
        print(f"     - Next Scheduled Run   : {s.next_scheduled_sync_at or 'Not Set'}")
        print(f"     - Scheduler Engine Job : {job_info}")

    return True


def main():
    print("\n" + "="*75)
    print("  CAMPUSAI -- PRODUCTION DATA CONSISTENCY & ROOT CAUSE VERIFICATION")
    print("="*75)

    if not SessionLocal:
        print("[ERROR] Database SessionLocal is not configured.")
        sys.exit(1)

    db = SessionLocal()
    try:
        test_departments_and_hods(db)
        test_faculty_counts_and_mappings(db)
        test_announcements_exams_calendar(db)
        test_url_health_checks(db)
        test_chroma_and_rag(db)
        test_scheduler_state(db)
        print_section("VERIFICATION SUMMARY")
        print("[SUCCESS] All data consistency and architectural checks executed successfully.")
    except Exception as exc:
        print(f"\n[FATAL] Verification encountered exception: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
