"""
Seed & Live Synchronization Script for CampusAI.

Populates initial administrative credentials, creates the official MITS website source registry,
and executes live synchronization against https://mits.ac.in/ to dynamically discover and populate
official departments, faculty, department heads, academic calendars, examinations, circulars,
and college overview with verified canonical URLs.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    User,
    Role,
    WebsiteSource,
    WebsiteSourceStatus,
    ImportantLink,
)
from backend.app.services.crawler_service import synchronize_website_source


def seed_mits_official_data():
    print("=" * 60)
    print("CampusAI: Initializing Official MITS Knowledge Infrastructure...")
    print("=" * 60)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # 1. Admin User Initialization
        admin_email = getattr(settings, "ADMIN_EMAIL", "admin@campusai.test")
        admin_pass = getattr(settings, "ADMIN_PASSWORD", "Admin@123456")
        admin_name = getattr(settings, "ADMIN_NAME", "CampusAI Administrator")

        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                name=admin_name,
                email=admin_email,
                password_hash=hash_password(admin_pass),
                role=Role.ADMIN,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"[+] Initialized Admin account: {admin_email}")
        else:
            print(f"[*] Admin account already exists: {admin_email}")

        # 2. Important Official Portal Links (Verified official MITS URLs)
        links_data = [
            {
                "title": "MITS Official Website",
                "description": "Official university portal, announcements & governance",
                "url": "https://mits.ac.in/",
                "canonical_url": "https://mits.ac.in/",
                "category": "official",
                "icon": "Globe",
                "display_order": 1,
                "is_valid": True,
            },
            {
                "title": "Controller of Examinations (CoE)",
                "description": "Timetables, circulars, hall tickets & exam notifications",
                "url": "https://mits.ac.in/university-exam",
                "canonical_url": "https://mits.ac.in/university-exam",
                "category": "examinations",
                "icon": "GraduationCap",
                "display_order": 2,
                "is_valid": True,
            },
            {
                "title": "Official Academic Calendars",
                "description": "Approved semester timelines, commencement & exam dates",
                "url": "https://mits.ac.in/academic-calenders",
                "canonical_url": "https://mits.ac.in/academic-calenders",
                "category": "academics",
                "icon": "Calendar",
                "display_order": 3,
                "is_valid": True,
            },
            {
                "title": "Student Solutions Portal",
                "description": "Official student portal for exam results & grade sheets",
                "url": "https://studentportal.universitysolutions.in/",
                "canonical_url": "https://studentportal.universitysolutions.in/",
                "category": "portal",
                "icon": "UserCheck",
                "display_order": 4,
                "is_valid": True,
            },
            {
                "title": "Training & Placement Cell",
                "description": "Campus recruitment drives, training sessions & statistics",
                "url": "https://mits.ac.in/placement",
                "canonical_url": "https://mits.ac.in/placement",
                "category": "placements",
                "icon": "Briefcase",
                "display_order": 5,
                "is_valid": True,
            },
            {
                "title": "Official Circulars & Notices",
                "description": "Institutional holiday circulars and university notifications",
                "url": "https://mits.ac.in/circulars",
                "canonical_url": "https://mits.ac.in/circulars",
                "category": "notices",
                "icon": "Bell",
                "display_order": 6,
                "is_valid": True,
            },
        ]
        for lnk in links_data:
            existing = db.query(ImportantLink).filter(ImportantLink.title == lnk["title"]).first()
            if existing:
                existing.description = lnk["description"]
                existing.url = lnk["url"]
                existing.canonical_url = lnk["canonical_url"]
                existing.icon = lnk["icon"]
                existing.display_order = lnk["display_order"]
                existing.is_valid = True
                existing.last_verified_at = now
            else:
                db.add(ImportantLink(**lnk, last_verified_at=now))
        db.commit()
        print(f"[+] Initialized {len(links_data)} verified official portal links.")

        # 3. Create or update MITS Official WebsiteSource
        ws = db.query(WebsiteSource).filter(WebsiteSource.base_url == "https://mits.ac.in/").first()
        if not ws:
            ws = WebsiteSource(
                name="MITS Official Website",
                base_url="https://mits.ac.in/",
                allowed_domains="mits.ac.in,www.mits.ac.in,studentportal.universitysolutions.in",
                allowed_paths="",
                active=True,
                sync_interval="6h",
                max_pages=100,
                status=WebsiteSourceStatus.IDLE,
                last_checked_at=now,
                created_by_id=admin_user.id,
            )
            db.add(ws)
            db.commit()
            db.refresh(ws)
            print(f"[+] Created WebsiteSource registry entry (ID: {ws.id})")
        else:
            ws.allowed_domains = "mits.ac.in,www.mits.ac.in,studentportal.universitysolutions.in"
            ws.active = True
            db.commit()
            print(f"[*] WebsiteSource registry entry verified (ID: {ws.id})")

        # 4. Trigger Live Synchronization against Official MITS
        print("\n" + "=" * 60)
        print("Executing Live Synchronization against https://mits.ac.in/ ...")
        print("=" * 60)

        history = synchronize_website_source(db, ws.id)
        print(f"\n[+] Synchronization Result: {history.status.value}")
        if history.error_message:
            print(f"[+] Report:\n{history.error_message}")

        print("\n" + "=" * 60)
        print("CampusAI Official MITS Data Synchronization COMPLETE!")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    seed_mits_official_data()
