import sys
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.db.models import (
    Announcement, AcademicCalendarEvent, Examination, Department,
    Placement, CollegeInfo, Document, Faculty
)

def scan_urls():
    db = SessionLocal()
    urls = set()
    
    for a in db.query(Announcement).filter(Announcement.is_valid == True).all():
        if a.source_url: urls.add(a.source_url)
        if a.document_url: urls.add(a.document_url)
        
    for c in db.query(AcademicCalendarEvent).filter(AcademicCalendarEvent.is_valid == True).all():
        if c.source_url: urls.add(c.source_url)
        if c.document_url: urls.add(c.document_url)

    for e in db.query(Examination).filter(Examination.is_valid == True).all():
        if e.source_url: urls.add(e.source_url)
        if e.document_url: urls.add(e.document_url)

    for d in db.query(Department).filter(Department.is_active == True).all():
        if d.source_url: urls.add(d.source_url)

    for p in db.query(Placement).filter(Placement.is_valid == True).all():
        if p.source_url: urls.add(p.source_url)

    for info in db.query(CollegeInfo).filter(CollegeInfo.is_valid == True).all():
        if info.source_url: urls.add(info.source_url)
        if info.canonical_url: urls.add(info.canonical_url)

    for fac in db.query(Faculty).filter(Faculty.is_active == True).all():
        if fac.profile_url: urls.add(fac.profile_url)
        if fac.source_url: urls.add(fac.source_url)

    for doc in db.query(Document).filter(Document.status == "READY").all():
        if doc.source_url: urls.add(doc.source_url)

    print(f"Total distinct URLs to scan: {len(urls)}")
    
    dead_urls = []
    redirected = []
    healthy = []

    client = httpx.Client(verify=False, timeout=10.0, follow_redirects=True)
    
    for u in sorted(urls):
        try:
            resp = client.head(u)
            if resp.status_code in [404, 403, 500, 502, 503]:
                # Try GET if HEAD is forbidden or method not allowed
                resp = client.get(u)
            
            if resp.status_code >= 400:
                dead_urls.append((u, resp.status_code))
                print(f"[DEAD] {resp.status_code}: {u}")
            else:
                healthy.append((u, resp.status_code))
        except Exception as err:
            dead_urls.append((u, str(err)))
            print(f"[ERROR] {err}: {u}")

    print("\n--- SCAN SUMMARY ---")
    print(f"Healthy: {len(healthy)}")
    print(f"Dead / Error: {len(dead_urls)}")
    
    # If any dead URLs found, let's list them
    if dead_urls:
        print("List of dead URLs:")
        for u, status in dead_urls:
            print(f"  {status} -> {u}")

if __name__ == "__main__":
    scan_urls()
