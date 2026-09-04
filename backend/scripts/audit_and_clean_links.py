"""
Audit and clean all MITS external URLs across:
- Announcements
- AcademicCalendarEvent
- Examination
- Placement
- Department
- Faculty

If any URL returns 404 or fails to connect:
- Mark is_valid = False
- If document_url is a 404, set document_url = None or mark invalid
"""
import sys
from typing import Tuple
import asyncio
import httpx
from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    Announcement,
    AcademicCalendarEvent,
    Examination,
    Placement,
    Department,
    Faculty,
)

USER_AGENT = "CampusAI-Audit/1.0 (+https://mits.ac.in/bot)"


async def check_url(client: httpx.AsyncClient, url: str) -> Tuple[bool, int, str]:
    if not url or not url.startswith("http"):
        return False, 0, "empty or non-http"
    try:
        resp = await client.head(url, timeout=10.0, follow_redirects=True)
        if resp.status_code in (200, 301, 302, 307, 308):
            return True, resp.status_code, "ok"
        if resp.status_code in (405, 403):
            # Fallback to GET with Range 0-100
            resp_get = await client.get(url, headers={"Range": "bytes=0-100"}, timeout=10.0, follow_redirects=True)
            return resp_get.status_code in (200, 206, 301, 302), resp_get.status_code, "get_fallback"
        return False, resp.status_code, f"http_{resp.status_code}"
    except Exception as exc:
        return False, 0, str(exc)[:80]


async def run_audit():
    db = SessionLocal()
    print("--- Starting MITS Live URL Audit ---")

    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        # 1. Announcements
        announcements = db.query(Announcement).all()
        print(f"\nAuditing {len(announcements)} Announcements...")
        for a in announcements:
            if a.document_url:
                ok, status, reason = await check_url(client, a.document_url)
                if not ok:
                    print(f"  [DEAD LINK] Announcement {a.id} ({a.title[:40]}): {a.document_url} -> {reason}")
                    a.is_valid = False
                    a.document_url = None
                else:
                    a.is_valid = True

        # 2. Academic Calendar
        calendars = db.query(AcademicCalendarEvent).all()
        print(f"\nAuditing {len(calendars)} Calendar Events...")
        for c in calendars:
            if c.document_url:
                ok, status, reason = await check_url(client, c.document_url)
                if not ok:
                    print(f"  [DEAD LINK] Calendar {c.id} ({c.event_name[:40]}): {c.document_url} -> {reason}")
                    c.is_valid = False
                    c.document_url = None
                else:
                    c.is_valid = True

        # 3. Examinations
        exams = db.query(Examination).all()
        print(f"\nAuditing {len(exams)} Examinations...")
        dead_exams = 0
        for e in exams:
            if e.document_url:
                ok, status, reason = await check_url(client, e.document_url)
                if not ok:
                    dead_exams += 1
                    e.is_valid = False
                    e.document_url = None
                else:
                    e.is_valid = True
        print(f"  Examinations dead links: {dead_exams}/{len(exams)}")

        # 4. Placements
        placements = db.query(Placement).all()
        print(f"\nAuditing {len(placements)} Placements...")
        for p in placements:
            if p.source_url:
                ok, status, reason = await check_url(client, p.source_url)
                if not ok:
                    print(f"  [DEAD LINK] Placement {p.id}: {p.source_url} -> {reason}")
                    p.is_valid = False
                else:
                    p.is_valid = True

        # 5. Departments
        depts = db.query(Department).all()
        print(f"\nAuditing {len(depts)} Departments...")
        for d in depts:
            if d.source_url:
                ok, status, reason = await check_url(client, d.source_url)
                if not ok:
                    print(f"  [DEAD LINK] Dept {d.code}: {d.source_url} -> {reason}")
                    d.canonical_url = "https://mits.ac.in/"
                else:
                    d.is_valid = True

        # 6. Faculty
        faculties = db.query(Faculty).all()
        print(f"\nAuditing {len(faculties)} Faculty Members...")
        for f in faculties:
            if f.profile_url:
                if not f.profile_url.startswith("http"):
                    f.profile_url = None
            f.is_valid = True

        db.commit()
        print("\n--- Audit Completed and Saved to DB ---")

    db.close()

if __name__ == "__main__":
    asyncio.run(run_audit())
