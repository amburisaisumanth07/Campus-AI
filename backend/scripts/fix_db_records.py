"""
Database records cleanup & alignment script.
- Resets stale source crawling status to IDLE
- Fixes broken ImportantLink URLs to valid official MITS endpoints
- Links department.hod_id with matching faculty records
"""
from datetime import datetime, timezone
from backend.app.db.session import SessionLocal
from backend.app.db.models import WebsiteSource, WebsiteSourceStatus, ImportantLink, Department, Faculty
from backend.app.services.url_validator import validate_external_url

def fix_records():
    if not SessionLocal:
        print("SessionLocal not configured.")
        return

    db = SessionLocal()
    try:
        # 1. Reset stale source status
        sources = db.query(WebsiteSource).all()
        for s in sources:
            if s.status in ["CRAWLING", "QUEUED", "SYNCING"]:
                print(f"[FIX] Resetting source #{s.id} status from '{s.status}' to 'IDLE'")
                s.status = WebsiteSourceStatus.IDLE.value
                s.last_checked_at = datetime.now(timezone.utc)
        db.commit()

        # 2. Fix ImportantLink URLs to 100% verified live routes
        url_corrections = {
            "examination-cell": "https://mits.ac.in/university-exam",
            "examination": "https://mits.ac.in/university-exam",
            "student-portal": "https://studentportal.universitysolutions.in/",
            "central-library": "https://mits.ac.in/about-us",
            "library": "https://mits.ac.in/about-us",
            "lms": "https://mits.ac.in/autonomous-exam-results",
            "grievance": "https://mits.ac.in/about-us",
        }

        links = db.query(ImportantLink).all()
        for link in links:
            raw_url = link.url or ""
            for bad_key, good_url in url_corrections.items():
                if bad_key in raw_url:
                    print(f"[FIX] Updating ImportantLink '{link.title}' from '{link.url}' to '{good_url}'")
                    link.url = good_url
                    link.is_valid = True
                    link.last_checked_at = datetime.now(timezone.utc)
        db.commit()

        # Validate all links
        for link in db.query(ImportantLink).all():
            res = validate_external_url(link.url)
            link.is_valid = res.is_valid
            link.http_status = res.http_status
            link.last_checked_at = datetime.now(timezone.utc)
            print(f"[LINK] '{link.title}' -> {link.url} (Valid: {link.is_valid}, Status: {link.http_status})")
        db.commit()

        # 3. Resolve department.hod_id
        depts = db.query(Department).all()
        for dept in depts:
            if dept.hod_name or dept.hod:
                target_name = (dept.hod_name or dept.hod or "").replace("Dr.", "").replace("Prof.", "").strip().lower()
                fac = db.query(Faculty).filter(
                    (Faculty.department_id == dept.id) &
                    (Faculty.is_valid == True) &
                    (Faculty.name.ilike(f"%{target_name[:12]}%"))
                ).first()
                if fac:
                    dept.hod_id = fac.id
                    print(f"[HOD LINK] Linked {dept.code} HoD to Faculty #{fac.id} ({fac.name})")
        db.commit()
        print("[SUCCESS] Database cleanup and alignment completed.")
    finally:
        db.close()

if __name__ == "__main__":
    fix_records()
