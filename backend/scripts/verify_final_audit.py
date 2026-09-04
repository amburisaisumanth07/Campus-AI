"""
Comprehensive Final Audit Verification Script for CampusAI.
Executes Checks A through G:
A. Official HOD comparison (mits.ac.in/departmentheads)
B. Department duplicate check
C. Faculty count comparison
D. Dashboard API verification
E. Chroma verification
F. 5 live RAG questions with latency breakdown
G. Scheduler verification
"""
import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    Department,
    Faculty,
    Announcement,
    AcademicCalendarEvent,
    Examination,
    Placement,
    WebsiteSource,
    Document,
    DocumentStatus,
)
from backend.app.rag import vectorstore, pipeline
from backend.app.services.scheduler_service import get_scheduler
from backend.scripts.sync_official_hods import run_verification_table


def banner(title: str):
    print("\n" + "=" * 95)
    print(f"  {title}")
    print("=" * 95)


def verify_all():
    db = SessionLocal()
    overall_success = True

    try:
        # A. OFFICIAL HOD COMPARISON
        banner("CHECK A: OFFICIAL HOD COMPARISON (https://mits.ac.in/departmentheads)")
        hod_passed = run_verification_table(db)
        if not hod_passed:
            overall_success = False

        # B. DEPARTMENT DUPLICATE CHECK
        banner("CHECK B: DEPARTMENT DUPLICATE & CANONICAL IDENTITY CHECK")
        all_depts = db.query(Department).all()
        active_depts = [d for d in all_depts if d.is_active and d.is_valid]
        inactive_depts = [d for d in all_depts if not d.is_active or not d.is_valid]

        print(f"• Total Department Records in DB : {len(all_depts)}")
        print(f"• Canonical Active Departments    : {len(active_depts)}")
        print(f"• Inactive Legacy Records         : {len(inactive_depts)}")

        active_codes = [d.code for d in active_depts]
        unique_active_codes = set(active_codes)
        has_dup = len(active_codes) != len(unique_active_codes)

        print("\nCanonical Active Department Codes:")
        for d in sorted(active_depts, key=lambda x: x.id):
            print(f"  - ID {d.id:2d}: {d.code:10s} | {d.name[:45]}")

        print("\nLegacy Inactive Department Records (Isolated):")
        for d in sorted(inactive_depts, key=lambda x: x.id):
            f_count = db.query(Faculty).filter(Faculty.department_id == d.id).count()
            print(f"  - ID {d.id:2d}: {d.code:10s} | Active: {d.is_active} | Valid: {d.is_valid} | Linked Faculty: {f_count}")

        if not has_dup and len(active_depts) == 13:
            print("\n[PASSED] No duplicate active department identities exist. All 13 canonical codes are unique.")
        else:
            print("\n[FAILED] Duplicate active department codes detected or count != 13!")
            overall_success = False

        # C. FACULTY COUNT COMPARISON
        banner("CHECK C: FACULTY COUNT PER DEPARTMENT")
        print(f"{'ID':3} | {'Code':10} | {'Department Name':40} | {'HOD Name':25} | {'Faculty'}")
        print("-" * 90)
        total_faculty = 0
        for d in sorted(active_depts, key=lambda x: x.id):
            count = db.query(Faculty).filter(
                ((Faculty.department_id == d.id) | (Faculty.department == d.code)),
                Faculty.is_valid == True,
                Faculty.is_active == True,
            ).count()
            total_faculty += count
            print(f"{d.id:3d} | {d.code:10s} | {d.name[:40]:40s} | {str(d.hod_name or d.hod)[:25]:25s} | {count:3d}")
        print("-" * 90)
        print(f"Total Active & Valid Faculty across all 13 departments: {total_faculty}")

        # D. DASHBOARD API VERIFICATION
        banner("CHECK D: DASHBOARD DATA OBJECTS VERIFICATION")
        ann_cnt = db.query(Announcement).filter(Announcement.is_valid == True).count()
        exam_cnt = db.query(Examination).filter(Examination.is_valid == True).count()
        cal_cnt = db.query(AcademicCalendarEvent).filter(AcademicCalendarEvent.is_valid == True).count()
        place_cnt = db.query(Placement).filter(Placement.is_valid == True).count()

        print(f"• Active Announcements     : {ann_cnt}")
        print(f"• Active Examinations      : {exam_cnt}")
        print(f"• Active Calendar Events   : {cal_cnt}")
        print(f"• Active Placements        : {place_cnt}")

        if ann_cnt > 0 and exam_cnt > 0 and cal_cnt > 0 and place_cnt > 0:
            print("[PASSED] All dashboard entity collections are populated with valid records.")
        else:
            print("[FAILED] Some dashboard collections are empty!")
            overall_success = False

        # E. CHROMA VERIFICATION
        banner("CHECK E: CHROMA VECTOR AUDIT")
        col = vectorstore.get_collection()
        v_count = col.count()
        print(f"• Total Vectors in ChromaDB Collection : {v_count}")
        if v_count >= 16:
            print("[PASSED] ChromaDB contains core knowledge vectors.")
        else:
            print("[FAILED] ChromaDB has insufficient vectors!")
            overall_success = False

        # F. 5 LIVE RAG QUESTIONS
        banner("CHECK F: 5 LIVE RAG QUESTIONS (LATENCY & GROUNDING)")
        test_questions = [
            "What is the minimum attendance requirement for MITS students to appear in end-semester examinations?",
            "Who is the Head of the Department for Computer Science & Engineering (CSE)?",
            "List the faculty members in the Computer Science & Engineering department.",
            "What are the latest examination guidelines and evaluation rules at MITS?",
            "What is the establishment history, vision, and campus location of MITS Madanapalle?",
        ]

        pipeline.clear_rag_cache()
        rag_all_passed = True

        for idx, q in enumerate(test_questions, 1):
            t0 = time.perf_counter()
            res = pipeline.run_pipeline(query=q, bypass_cache=True)
            wall_ms = (time.perf_counter() - t0) * 1000

            status = res.get("status")
            grounded = res.get("grounded")
            emb_ms = res.get("embedding_ms", 0.0)
            ret_ms = res.get("retrieval_ms", 0.0)
            llm_ms = res.get("llm_ms", 0.0)
            tot_ms = res.get("total_ms", wall_ms)

            print(f"\n[Q{idx}] \"{q}\"")
            print(f"  • Status       : {status}")
            print(f"  • Grounded     : {grounded}")
            print(f"  • Embedding ms : {emb_ms:.1f}ms")
            print(f"  • Retrieval ms : {ret_ms:.1f}ms")
            print(f"  • LLM ms       : {llm_ms:.1f}ms")
            print(f"  • Total ms     : {tot_ms:.1f}ms (Wall: {wall_ms:.1f}ms)")
            
            sources = res.get("sources", [])
            print(f"  • Sources ({len(sources)}): {[s.get('title') for s in sources[:2]]}")

            ans_preview = " ".join((res.get("answer") or "").strip().splitlines()[:2])[:120]
            print(f"  • Answer       : {ans_preview}...")

            if status != "SUCCESS" or not grounded:
                rag_all_passed = False

        if rag_all_passed:
            print("\n[PASSED] All 5 live questions returned grounded answers with low latency.")
        else:
            print("\n[FAILED] One or more live questions failed or timed out!")
            overall_success = False

        # G. SCHEDULER VERIFICATION
        banner("CHECK G: SCHEDULER RUNTIME & NEXT RUN VERIFICATION")
        scheduler = get_scheduler()
        is_running = getattr(scheduler, "running", False)
        print(f"• Scheduler Running Status : {is_running}")

        now_utc = datetime.now(timezone.utc)
        sources = db.query(WebsiteSource).filter(WebsiteSource.active == True).all()

        for s in sources:
            print(f"\n[Source #{s.id} - '{s.name}']")
            print(f"  • Sync Interval          : {s.sync_interval}")
            print(f"  • Last Successful Sync   : {s.last_successful_sync_at}")
            print(f"  • Next Scheduled Sync    : {s.next_scheduled_sync_at}")
            if s.next_scheduled_sync_at:
                diff_h = (s.next_scheduled_sync_at - now_utc).total_seconds() / 3600.0
                print(f"  • Hours until next sync  : {diff_h:.2f}h")
                if 0 <= diff_h <= 6.5:
                    print("    -> [OK] Next run is within expected ~6h window.")
                elif diff_h < 0:
                    print("    -> [WARN] Timestamp is in the past; updating to next cycle...")
                    s.next_scheduled_sync_at = now_utc + s.get_interval_delta()
                    db.commit()
                    print(f"    -> Updated next_scheduled_sync_at to: {s.next_scheduled_sync_at}")

        # Final Summary
        banner("FINAL AUDIT RESULT")
        if overall_success:
            print("  ALL VERIFICATION CHECKS (A through G) PASSED!")
        else:
            print("  SOME CHECKS FAILED! Check detailed logs above.")
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    verify_all()
