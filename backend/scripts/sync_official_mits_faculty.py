"""
Sync Official MITS Faculty Script.

Live crawler and database synchronizer that extracts authoritative faculty rosters
directly from official MITS department-specific pages (https://mits.ac.in/).

Sources of Truth Hierarchy:
1. Current official department-specific MITS pages
2. Current official https://mits.ac.in/departmentheads
3. Current official https://mits.ac.in/faculty-information
4. Current official MITS Mandatory Disclosure & Public Self Disclosures

Covers all 13 official academic departments:
- AI: https://mits.ac.in/department/28
- CSE-AIML: https://mits.ac.in/cse-ai-ml
- CSE: https://mits.ac.in/department/9
- CSE-DS: https://mits.ac.in/department/26
- CSE-CS: https://mits.ac.in/department/27
- CST: https://mits.ac.in/department/4
- MCA: https://mits.ac.in/department/18
- MECH: https://mits.ac.in/department/8
- MBA: https://mits.ac.in/department/5
- CIVIL: https://mits.ac.in/department/6
- ECE: https://mits.ac.in/electronics-communication-engineering
- EEE: https://mits.ac.in/electrical-electronics-engineering
- BSH: https://mits.ac.in/basic-sciences-humanities
"""
import os
import sys
import re
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from bs4 import BeautifulSoup

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.db.session import SessionLocal
from backend.app.db.models import Faculty, Department, Person
from backend.app.core.canonical_departments import CANONICAL_DEPARTMENTS, CanonicalDepartment
from backend.app.core.logging import logger

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

DEPARTMENT_PAGES = {
    "AI": {
        "dept_id": 11,
        "url": "https://mits.ac.in/department/28",
        "official_name": "Department of Computer Science & Engineering (Artificial Intelligence)",
    },
    "CSE-AIML": {
        "dept_id": 14,
        "url": "https://mits.ac.in/cse-ai-ml",
        "official_name": "Department of Computer Science & Engineering (Artificial Intelligence & Machine Learning)",
    },
    "CSE": {
        "dept_id": 1,
        "url": "https://mits.ac.in/department/9",
        "official_name": "Department of Computer Science & Engineering",
    },
    "CSE-DS": {
        "dept_id": 9,
        "url": "https://mits.ac.in/department/26",
        "official_name": "Department of Computer Science and Engineering (Data Science)",
    },
    "CSE-CS": {
        "dept_id": 10,
        "url": "https://mits.ac.in/department/27",
        "official_name": "Department of Computer Science and Engineering (Cyber Security)",
    },
    "CST": {
        "dept_id": 12,
        "url": "https://mits.ac.in/department/4",
        "official_name": "Department of Computer Science and Technology (CST)",
    },
    "MCA": {
        "dept_id": 8,
        "url": "https://mits.ac.in/department/18",
        "official_name": "Department of Computer Applications (BCA & MCA)",
    },
    "MECH": {
        "dept_id": 5,
        "url": "https://mits.ac.in/department/8",
        "official_name": "Department of Mechanical Engineering",
    },
    "MBA": {
        "dept_id": 7,
        "url": "https://mits.ac.in/department/5",
        "official_name": "Department of Management Studies (BBA & MBA)",
    },
    "CIVIL": {
        "dept_id": 6,
        "url": "https://mits.ac.in/department/6",
        "official_name": "Department of Civil Engineering",
    },
    "ECE": {
        "dept_id": 3,
        "url": "https://mits.ac.in/electronics-communication-engineering",
        "official_name": "Department of Electronics & Communication Engineering",
    },
    "EEE": {
        "dept_id": 4,
        "url": "https://mits.ac.in/electrical-electronics-engineering",
        "official_name": "Department of Electrical & Electronics Engineering",
    },
    "BSH": {
        "dept_id": 15,
        "url": "https://mits.ac.in/basic-sciences-humanities",
        "official_name": "Department of Basic Sciences & Humanities",
    },
}


def decode_cf_email(cf_hex: str) -> Optional[str]:
    """Decode Cloudflare hex-obfuscated email string."""
    try:
        key = int(cf_hex[:2], 16)
        email = "".join([chr(int(cf_hex[i:i+2], 16) ^ key) for i in range(2, len(cf_hex), 2)])
        return email.strip().lower()
    except Exception:
        return None


def fetch_html(url: str, timeout: int = 35) -> str:
    """Fetch raw HTML from official MITS URL."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def normalize_profile_url(href: str) -> str:
    """Normalize profile URL to absolute https://mits.ac.in format."""
    href = href.strip()
    if href.startswith("../"):
        return "https://mits.ac.in/" + href[3:]
    elif href.startswith("/"):
        return "https://mits.ac.in" + href
    elif not href.startswith("http"):
        return "https://mits.ac.in/" + href
    return href


def parse_department_page(code: str, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse faculty members from a specific department page."""
    url = meta["url"]
    print(f"--> Crawling {code} from {url} ...", flush=True)
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    
    faculty_list = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "facultyprofile/" in href:
            abs_url = normalize_profile_url(href)
            if abs_url in seen_urls:
                continue
            seen_urls.add(abs_url)
            
            # Find the card container
            card = a.parent
            for _ in range(6):
                if card and any(c in card.get("class", []) for c in ["fac-dec", "fac-content-dec", "card", "col", "team-item", "item"]):
                    break
                if card and card.name in ["li", "tr"]:
                    break
                if card:
                    card = card.parent
            if not card:
                card = a.parent.parent
                
            # Extract email if protected by Cloudflare
            cf_span = card.find(attrs={"data-cfemail": True}) if card else None
            email = decode_cf_email(cf_span["data-cfemail"]) if cf_span else None
            
            # Check mailto link if email not found
            if not email and card:
                mailto = card.find("a", href=lambda h: h and h.startswith("mailto:"))
                if mailto:
                    email = mailto["href"].replace("mailto:", "").strip().lower()

            # Extract plain text lines
            raw_lines = [l.strip() for l in card.get_text(separator="\n", strip=True).split("\n") if l.strip()] if card else []
            filtered = [
                l for l in raw_lines 
                if l not in ["View Profile", "Email:", "Profile", "View", "Read More", "Faculty"] 
                and not l.startswith("[email")
                and not l.startswith("Email")
            ]
            
            name = filtered[0] if len(filtered) > 0 else "Faculty Member"
            designation = filtered[1] if len(filtered) > 1 else "Faculty Member"
            qualification = filtered[2] if len(filtered) > 2 else None
            
            # Normalize designation & qualification if swapped
            if designation.startswith("Ph.D") or designation.startswith("M.Tech") or designation.startswith("M.E.") or designation.startswith("M.Sc") or designation.startswith("MCA") or designation.startswith("M.B.A"):
                qualification = designation
                designation = "Faculty Member"

            # Clean name
            name = name.strip()

            # Determine specialization / division for BSH
            specialization = None
            if code == "BSH" and card:
                card_text = card.get_text(" ", strip=True).lower()
                if "math" in card_text:
                    specialization = "Mathematics"
                elif "physic" in card_text:
                    specialization = "Physics"
                elif "chem" in card_text:
                    specialization = "Chemistry"
                elif any(k in card_text for k in ["english", "verbal", "eflu", "linguist"]):
                    specialization = "English & Foreign Languages"
            
            faculty_list.append({
                "name": name,
                "designation": designation.strip(),
                "qualification": qualification.strip() if qualification else None,
                "email": email,
                "profile_url": abs_url,
                "source_url": url,
                "department_code": code,
                "department_id": meta["dept_id"],
                "specialization": specialization,
            })

    print(f"    Extracted {len(faculty_list)} faculty members for {code}.", flush=True)
    return faculty_list


def parse_central_directory() -> Dict[str, List[Dict[str, Any]]]:
    """Parse faculty from central directory (https://mits.ac.in/faculty-information) for enrichment."""
    url = "https://mits.ac.in/faculty-information"
    print(f"--> Crawling central directory for metadata enrichment from {url} ...", flush=True)
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    
    table = soup.find("table")
    if not table:
        print("    [WARNING] No table found on faculty-information page.", flush=True)
        return {}

    dept_faculty: Dict[str, List[Dict[str, Any]]] = {}
    rows = table.find_all("tr")
    
    table_dept_map = {
        "ECE": ("ECE", 3),
        "EEE": ("EEE", 4),
        "Physics": ("BSH", 15),
        "Mathematics": ("BSH", 15),
        "Chemistry": ("BSH", 15),
        "English & FL": ("BSH", 15),
    }

    for r in rows[1:]:
        cols = [c.get_text(strip=True) for c in r.find_all(["th", "td"])]
        if len(cols) >= 5:
            name = cols[1]
            qual = cols[2] if cols[2] else None
            desig = cols[3]
            dept_str = cols[4]
            a_tag = r.find("a", href=True)
            prof_url = normalize_profile_url(a_tag["href"].strip()) if a_tag else ""

            if dept_str in table_dept_map:
                code, dept_id = table_dept_map[dept_str]
                if code not in dept_faculty:
                    dept_faculty[code] = []
                    
                dept_faculty[code].append({
                    "name": name,
                    "designation": desig,
                    "qualification": qual,
                    "email": None,
                    "profile_url": prof_url,
                    "source_url": url,
                    "department_code": code,
                    "department_id": dept_id,
                    "specialization": dept_str if code == "BSH" else None,
                })

    for c, facs in dept_faculty.items():
        print(f"    Extracted {len(facs)} enrichment records for {c} from central directory.", flush=True)
        
    return dept_faculty


def sync_faculty_to_neon():
    """Main synchronization routine to update PostgreSQL adhering to Source of Truth hierarchy."""
    db = SessionLocal()
    now_utc = datetime.now(timezone.utc)
    
    print("\n========================================================")
    print("STARTING OFFICIAL MITS FACULTY RECONCILIATION")
    print("========================================================\n", flush=True)

    # 1. Crawl all 13 department pages (Primary Source of Truth)
    scraped_by_dept: Dict[str, List[Dict[str, Any]]] = {}
    for code, meta in DEPARTMENT_PAGES.items():
        try:
            scraped_by_dept[code] = parse_department_page(code, meta)
        except Exception as e:
            print(f"    [ERROR] Failed crawling {code}: {e}", flush=True)
            scraped_by_dept[code] = []

    # 2. Enrich qualifications / specializations from central directory without overriding roster counts
    try:
        central_data = parse_central_directory()
        for code, c_list in central_data.items():
            if code in scraped_by_dept:
                # Build lookup by normalized name
                c_by_name = {re.sub(r'[^a-zA-Z]', '', item["name"]).lower(): item for item in c_list}
                for f in scraped_by_dept[code]:
                    norm = re.sub(r'[^a-zA-Z]', '', f["name"]).lower()
                    if norm in c_by_name:
                        c_item = c_by_name[norm]
                        if not f["qualification"] and c_item.get("qualification"):
                            f["qualification"] = c_item["qualification"]
                        if not f["specialization"] and c_item.get("specialization"):
                            f["specialization"] = c_item["specialization"]
    except Exception as e:
        print(f"    [WARNING] Central directory enrichment skipped: {e}", flush=True)

    print("\n--------------------------------------------------------")
    print("APPLYING SYNCHRONIZATION TO POSTGRESQL DATABASE")
    print("--------------------------------------------------------\n", flush=True)

    added_count = 0
    updated_count = 0
    historical_count = 0
    total_active_count = 0

    for code, faculty_records in scraped_by_dept.items():
        if not faculty_records:
            print(f"[{code}] Skipping sync (no scraped records).", flush=True)
            continue

        canon_dept = CANONICAL_DEPARTMENTS.get(code)
        if not canon_dept:
            print(f"[{code}] Unknown canonical department, skipping.", flush=True)
            continue

        target_dept_id = canon_dept.department_id
        
        # Collect profile URLs and normalized names of live scraped faculty
        live_profile_urls = set(f["profile_url"] for f in faculty_records if f["profile_url"])
        live_names_norm = set(re.sub(r'[^a-zA-Z]', '', f["name"]).lower() for f in faculty_records)

        # Query all existing faculty currently assigned to this department
        existing_dept_faculty = db.query(Faculty).filter(
            Faculty.department_id == target_dept_id
        ).all()

        existing_by_url = {f.profile_url: f for f in existing_dept_faculty if f.profile_url}
        existing_by_norm_name = {re.sub(r'[^a-zA-Z]', '', f.name).lower(): f for f in existing_dept_faculty}

        synced_ids = set()

        for record in faculty_records:
            prof_url = record["profile_url"]
            name = record["name"]
            norm_name = re.sub(r'[^a-zA-Z]', '', name).lower()

            target_fac = None
            if prof_url and prof_url in existing_by_url:
                target_fac = existing_by_url[prof_url]
            elif norm_name in existing_by_norm_name:
                target_fac = existing_by_norm_name[norm_name]

            if target_fac:
                # Update existing record
                target_fac.name = name
                target_fac.designation = record["designation"]
                if record["qualification"]:
                    target_fac.qualification = record["qualification"]
                if record["email"]:
                    target_fac.email = record["email"]
                if prof_url:
                    target_fac.profile_url = prof_url
                target_fac.department = code
                target_fac.department_id = target_dept_id
                target_fac.source_url = record["source_url"]
                target_fac.is_active = True
                target_fac.is_valid = True
                target_fac.last_verified_at = now_utc
                if record.get("specialization") and not target_fac.specialization:
                    target_fac.specialization = record["specialization"]
                
                synced_ids.add(target_fac.id)
                updated_count += 1
            else:
                # Insert new record
                new_fac = Faculty(
                    name=name,
                    designation=record["designation"],
                    qualification=record["qualification"],
                    department=code,
                    department_id=target_dept_id,
                    email=record["email"],
                    profile_url=prof_url,
                    source_url=record["source_url"],
                    specialization=record.get("specialization"),
                    is_active=True,
                    is_valid=True,
                    last_verified_at=now_utc,
                )
                db.add(new_fac)
                db.flush()
                synced_ids.add(new_fac.id)
                added_count += 1

        # Mark records not in the live official page as inactive / historical (preserve history)
        for existing in existing_dept_faculty:
            if existing.id not in synced_ids:
                if existing.is_active:
                    existing.is_active = False
                    historical_count += 1
                    print(f"    [HISTORICAL] {existing.name} (ID {existing.id}) marked inactive for {code}.", flush=True)

        dept_active_count = len(synced_ids)
        total_active_count += dept_active_count
        print(f"[{code}] Synced {dept_active_count} active faculty members.", flush=True)

    # Commit all database transactions
    db.commit()
    db.close()

    print("\n========================================================")
    print("FACULTY SYNCHRONIZATION COMPLETE")
    print(f"Added Records:               {added_count}")
    print(f"Updated Records:             {updated_count}")
    print(f"Marked Inactive/Historical:  {historical_count}")
    print(f"Total Active Faculty Synced: {total_active_count}")
    print("========================================================\n", flush=True)


if __name__ == "__main__":
    sync_faculty_to_neon()
