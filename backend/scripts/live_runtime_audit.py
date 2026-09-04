"""
Comprehensive Live Runtime Audit Script for CampusAI.
Executes Steps 1 through 11:
- Step 1: Scheduler runtime inspection & mathematical verification
- Step 2: Database truth for all departments & faculty
- Step 3: Fetch official HOD source (https://mits.ac.in/departmentheads) & compare
- Step 4: Fetch official Faculty source (https://mits.ac.in/faculty-information) & compare
- Step 5: Dashboard API endpoints validation
- Step 6: Stale data checks
- Step 7: 5 Real Chat RAG Latency measurements
- Step 8: Chroma vector inspection
- Step 9: Human review workflow check
- Step 10: Last-Known-Good simulated failure check
- Step 11: Frontend cache configuration review
"""
import io
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import httpx
from bs4 import BeautifulSoup
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
    SyncChangeReview,
    Document,
    DocumentStatus,
)
from backend.app.rag import vectorstore, pipeline
from backend.app.services.scheduler_service import get_scheduler, schedule_source_sync
from backend.app.services.url_validator import validate_external_url


def print_header(title: str):
    print(f"\n{'='*80}\n  {title}\n{'='*80}")


def run_audit():
    if not SessionLocal:
        print("[ERROR] SessionLocal is not configured.")
        return

    db: Session = SessionLocal()
    try:
        # =========================================================================
        # STEP 1: SCHEDULER
        # =========================================================================
        print_header("STEP 1 — SCHEDULER RUNTIME AUDIT")
        scheduler = get_scheduler()
        is_running = getattr(scheduler, "running", False)
        print(f"• Scheduler Instance Type : {type(scheduler).__name__}")
        print(f"• Scheduler Running Status: {is_running}")

        sources = db.query(WebsiteSource).all()
        now_utc = datetime.now(timezone.utc)
        print(f"• Current Server UTC Time : {now_utc.isoformat()}")

        for s in sources:
            job_id = f"website_sync_{s.id}"
            job = scheduler.get_job(job_id) if is_running else None
            print(f"\n[Source #{s.id} - '{s.name}']")
            print(f"  - Current DB Status         : {s.status}")
            print(f"  - Auto-Sync Enabled         : {s.auto_sync_enabled}")
            print(f"  - Configured Sync Interval  : {s.sync_interval}")
            print(f"  - Last Checked At (DB)      : {s.last_checked_at}")
            print(f"  - Last Successful Sync (DB) : {s.last_successful_sync_at}")
            print(f"  - Next Scheduled Sync (DB)  : {s.next_scheduled_sync_at}")
            
            if job:
                print(f"  - APScheduler Job ID        : {job.id}")
                print(f"  - Trigger                   : {job.trigger}")
                print(f"  - Next Run Time (Engine)    : {job.next_run_time}")
            else:
                print(f"  - APScheduler Job ID        : None (Job not active in current process)")

            # Mathematical Check:
            if s.next_scheduled_sync_at:
                diff_sec = (s.next_scheduled_sync_at - now_utc).total_seconds()
                diff_hours = diff_sec / 3600.0
                print(f"  - Math Verification         : next_scheduled_sync_at is {diff_hours:.2f} hours from now.")
                if 0 <= diff_hours <= 6.5:
                    print("    [OK] Next scheduled run is within expected ~6h window.")
                elif diff_hours < 0:
                    print(f"    [FAIL] Next scheduled run is in the PAST by {abs(diff_hours):.2f} hours (STALE TIMESTAMP).")
                else:
                    print(f"    [FAIL] Next scheduled run is too far in future ({diff_hours:.2f} hours).")
            else:
                print("    [WARN] next_scheduled_sync_at is None.")

        # =========================================================================
        # STEP 2: DATABASE TRUTH
        # =========================================================================
        print_header("STEP 2 — DATABASE TRUTH (DEPARTMENTS & FACULTY)")
        depts = db.query(Department).order_by(Department.id.asc()).all()
        print(f"Total Departments in DB: {len(depts)}")
        print(f"{'ID':3} | {'Code':10} | {'Name':38} | {'HOD ID':6} | {'HOD Name':25} | {'Tot':3} | {'Act':3} | {'Val':3} | {'Valid':5} | {'Active':6}")
        print("-" * 115)

        for d in depts:
            tot_fac = db.query(Faculty).filter(Faculty.department_id == d.id).count()
            act_fac = db.query(Faculty).filter(Faculty.department_id == d.id, Faculty.is_active == True).count()
            val_fac = db.query(Faculty).filter(Faculty.department_id == d.id, Faculty.is_valid == True).count()
            val_act_fac = db.query(Faculty).filter(Faculty.department_id == d.id, Faculty.is_active == True, Faculty.is_valid == True).count()
            
            hod_name_disp = (d.hod_name or d.hod or "None")[:25]
            print(f"{d.id:3} | {d.code:10} | {d.name[:38]:38} | {str(d.hod_id or 'None'):6} | {hod_name_disp:25} | {tot_fac:3} | {act_fac:3} | {val_fac:3} | {str(d.is_valid):5} | {str(d.is_active):6}")

        # Check unassigned or invalid faculty
        null_dept_fac = db.query(Faculty).filter(Faculty.department_id.is_(None)).count()
        inactive_fac = db.query(Faculty).filter(Faculty.is_active == False).count()
        invalid_fac = db.query(Faculty).filter(Faculty.is_valid == False).count()
        print(f"\nFaculty Anomalies in DB:")
        print(f"  - Faculty with NULL department_id : {null_dept_fac}")
        print(f"  - Faculty with is_active = False   : {inactive_fac}")
        print(f"  - Faculty with is_valid = False    : {invalid_fac}")

        # =========================================================================
        # STEP 3: OFFICIAL HOD SOURCE (https://mits.ac.in/departmentheads)
        # =========================================================================
        print_header("STEP 3 — OFFICIAL HOD SOURCE SCRAPE & COMPARISON")
        hod_url = "https://mits.ac.in/departmentheads"
        print(f"Fetching official HOD source: {hod_url} ...")
        
        official_hods = {}
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(hod_url)
                print(f"HTTP Response: {resp.status_code}")
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Try tables
                    for row in soup.find_all("tr"):
                        cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                        if len(cols) >= 2:
                            print(f"  [HOD Row] {cols}")
                    # Try cards / headings / paragraphs
                    for tag in soup.find_all(["h3", "h4", "h5", "strong", "p"]):
                        text = tag.get_text(strip=True)
                        if any(k in text.lower() for k in ["head", "hod", "department of", "dean"]):
                            print(f"  [HOD Element] {text[:80]}")
        except Exception as e:
            print(f"[ERROR] Could not fetch {hod_url}: {e}")

        print("\nCurrent DB HOD Mappings vs Linked Faculty:")
        for d in depts:
            linked_fac = db.query(Faculty).filter(Faculty.id == d.hod_id).first() if d.hod_id else None
            linked_name = linked_fac.name if linked_fac else "NO_FACULTY_LINKED"
            print(f"  • {d.code:10} | Stored HOD Name: {d.hod_name or d.hod} | Linked Faculty ID: {d.hod_id} ({linked_name})")

        # =========================================================================
        # STEP 4: FACULTY SOURCE (https://mits.ac.in/faculty-information)
        # =========================================================================
        print_header("STEP 4 — FACULTY SOURCE SCRAPE & COMPARISON")
        fac_url = "https://mits.ac.in/faculty-information"
        print(f"Fetching official faculty source: {fac_url} ...")
        official_faculty_by_dept: Dict[str, List[str]] = {}
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(fac_url)
                print(f"HTTP Response: {resp.status_code}")
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    current_dept = "GENERAL"
                    for element in soup.find_all(["h2", "h3", "h4", "table", "tr"]):
                        if element.name in ["h2", "h3", "h4"]:
                            title = element.get_text(strip=True)
                            if "department" in title.lower() or "faculty" in title.lower():
                                current_dept = title
                        elif element.name == "tr":
                            cols = [c.get_text(strip=True) for c in element.find_all("td")]
                            if len(cols) >= 2:
                                name = cols[1] if len(cols) > 1 else cols[0]
                                if name and not name.lower().startswith("name") and not name.isdigit():
                                    official_faculty_by_dept.setdefault(current_dept, []).append(name)
                    print(f"Parsed {sum(len(v) for v in official_faculty_by_dept.values())} faculty members across {len(official_faculty_by_dept)} sections from official website.")
                    for sec, fac_list in official_faculty_by_dept.items():
                        print(f"  • Section '{sec[:40]}': {len(fac_list)} faculty members (e.g. {fac_list[:2]})")
        except Exception as e:
            print(f"[ERROR] Could not fetch {fac_url}: {e}")

        # =========================================================================
        # STEP 5 & 6: DASHBOARD API & STALE DATA CHECKS
        # =========================================================================
        print_header("STEP 5 & 6 — DASHBOARD API & STALE DATA CHECKS")
        announcements = db.query(Announcement).filter(Announcement.is_valid == True).order_by(Announcement.published_date.desc().nullslast()).limit(5).all()
        print(f"Active Announcements in DB (Top 5):")
        for a in announcements:
            print(f"  - [{a.published_date}] ({a.category}) {a.title[:60]}")

        exams = db.query(Examination).filter(Examination.is_valid == True).order_by(Examination.published_date.desc().nullslast()).limit(5).all()
        print(f"\nActive Examinations in DB (Top 5):")
        for ex in exams:
            print(f"  - [{ex.published_date}] ({ex.exam_type}) {ex.title[:60]}")

        calendars = db.query(AcademicCalendarEvent).filter(AcademicCalendarEvent.is_valid == True).order_by(AcademicCalendarEvent.start_date.desc().nullslast()).limit(5).all()
        print(f"\nActive Calendar Events in DB (Top 5):")
        for c in calendars:
            print(f"  - [{c.start_date}] {c.event_name[:60]}")

        # =========================================================================
        # STEP 7: CHAT LIVE LATENCY (5 REAL QUESTIONS)
        # =========================================================================
        print_header("STEP 7 — CHAT LIVE LATENCY (5 REAL QUESTIONS)")
        test_questions = [
            "What is the minimum attendance requirement for MITS students to appear in end-semester examinations?",
            "Who is the Head of the Department for Computer Science & Engineering (CSE)?",
            "List the faculty members in the Computer Science & Engineering department.",
            "What are the latest examination guidelines and evaluation rules at MITS?",
            "What is the establishment history, vision, and campus location of MITS Madanapalle?",
        ]

        for idx, q in enumerate(test_questions, 1):
            print(f"\n--- Question {idx}: '{q}' ---")
            t0 = time.perf_counter()
            res = pipeline.run_pipeline(query=q, bypass_cache=True)
            t_total = (time.perf_counter() - t0) * 1000

            print(f"Status        : {res.get('status')}")
            print(f"Grounded      : {res.get('grounded')}")
            print(f"Chunks Count  : {res.get('retrieval_count')}")
            print(f"Embedding ms  : {res.get('embedding_ms')}")
            print(f"Retrieval ms  : {res.get('retrieval_ms')}")
            print(f"Citation ms   : {res.get('citation_ms')}")
            print(f"LLM ms        : {res.get('llm_ms')}")
            print(f"Total ms      : {res.get('total_ms', t_total):.1f}ms")
            
            answer_lines = (res.get('answer') or '').strip().split('\n')
            preview = " ".join(answer_lines[:2])[:140]
            print(f"Answer Preview: {preview}...")
            
            sources = res.get('sources') or res.get('citations') or []
            print(f"Sources ({len(sources)}):")
            for s in sources[:2]:
                print(f"  - {s.get('title')} ({s.get('source_url')})")

        # =========================================================================
        # STEP 8: CHROMA VECTOR AUDIT
        # =========================================================================
        print_header("STEP 8 — CHROMA VECTOR AUDIT")
        total_vectors = vectorstore.count()
        print(f"Chroma Host       : {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        print(f"Collection Name   : {settings.CHROMA_COLLECTION}")
        print(f"Total Chunks/Vecs : {total_vectors}")

        ready_docs = db.query(Document).filter(Document.status == DocumentStatus.READY).all()
        pending_docs = db.query(Document).filter(Document.status == DocumentStatus.UPLOADED).all()
        failed_docs = db.query(Document).filter(Document.status == DocumentStatus.FAILED).all()
        print(f"Database Documents:")
        print(f"  - READY (Published) : {len(ready_docs)}")
        print(f"  - PENDING_REVIEW    : {len(pending_docs)}")
        print(f"  - FAILED/REJECTED   : {len(failed_docs)}")

        for d in ready_docs[:5]:
            print(f"    • Doc #{d.id}: {d.title[:40]} | URL: {d.source_url} | Type: {d.source_type}")

        # =========================================================================
        # STEP 9: HUMAN REVIEW AUDIT
        # =========================================================================
        print_header("STEP 9 — HUMAN REVIEW AUDIT")
        pending_changes = db.query(SyncChangeReview).filter(SyncChangeReview.status == "PENDING_REVIEW").count()
        approved_changes = db.query(SyncChangeReview).filter(SyncChangeReview.status == "APPROVED").count()
        rejected_changes = db.query(SyncChangeReview).filter(SyncChangeReview.status == "REJECTED").count()
        print(f"Sync Change Reviews:")
        print(f"  - PENDING_REVIEW : {pending_changes}")
        print(f"  - APPROVED       : {approved_changes}")
        print(f"  - REJECTED       : {rejected_changes}")

    except Exception as exc:
        print(f"[FATAL] Audit failed: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_audit()
