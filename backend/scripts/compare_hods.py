"""
Audit script: Compare Department HODs in Database, Canonical Registry, and Official MITS Source.
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from backend.app.db.session import SessionLocal
from backend.app.db.models import Department, Faculty
from backend.app.core.canonical_departments import CANONICAL_DEPARTMENTS

OFFICIAL_HODS_MITS = {
    "CSE": "Dr. M. Sreedevi",
    "AI": "Dr. R. Kalpana",
    "CSE-DS": "Dr. S. Kusuma",
    "CSE-CS": "Dr. Brahm Prakash",
    "CSE-AIML": "Dr. S. Padma",
    "MCA": "Dr. N. Naveen Kumar",
    "ECE": "Dr. Sanjay Kumar C. Gowre",
    "EEE": "Dr. Manavaalan Gunasekaran",
    "MECH": "Dr. S. Bhaskaran",
    "CIVIL": "Dr. Vijayakumar Natesan",
    "MBA": "Dr. Bhanu Sree Reddy",
    "CST": "Dr. K. Dinesh",
    "BSH": "Dr. R. Saravana (Maths) / Dr. Jagadeesh Babu Bellam (Physics) / Dr. Renjith Bhaskaran (Chemistry) / Dr. Sudhakar Beedam (English)",
}

def audit_hods():
    db = SessionLocal()
    print("=" * 140)
    print("MITS HOD COMPREHENSIVE AUDIT REPORT")
    print("=" * 140)
    fmt = "{:<8} | {:<25} | {:<28} | {:<28} | {:<6} | {:<25} | {:<8}"
    print(fmt.format("Code", "Official MITS HOD", "DB Department.hod_name", "Canonical Dept HOD", "hod_id", "Linked Faculty Name", "Active"))
    print("-" * 140)

    mismatches = []
    for code, official in OFFICIAL_HODS_MITS.items():
        canon = CANONICAL_DEPARTMENTS.get(code)
        dept_id = canon.department_id
        d = db.query(Department).filter(Department.id == dept_id).first()

        db_hod = d.hod_name if d else "None"
        canon_hod = canon.hod_name if canon else "None"
        
        fac = db.query(Faculty).filter(Faculty.id == d.hod_id).first() if d and d.hod_id else None
        fac_name = fac.name if fac else "None"
        fac_active = str(fac.is_active) if fac else "N/A"

        # Check for discrepancies
        has_mismatch = False
        if code == "BSH":
            # Check division heads or primary
            if "Saravana" not in db_hod:
                has_mismatch = True
        else:
            if official.lower() not in db_hod.lower() and db_hod.lower() not in official.lower():
                has_mismatch = True
            if official.lower() not in canon_hod.lower() and canon_hod.lower() not in official.lower():
                has_mismatch = True
            if fac and not fac.is_active:
                has_mismatch = True

        status = "MISMATCH" if has_mismatch else "MATCH"
        if has_mismatch:
            mismatches.append(code)

        print(fmt.format(
            code,
            official[:25],
            db_hod[:28],
            canon_hod[:28],
            str(d.hod_id if d else ""),
            fac_name[:25],
            fac_active
        ))

    print("-" * 140)
    print(f"Total departments checked: {len(OFFICIAL_HODS_MITS)}")
    print(f"Mismatches or inactive linked faculty: {len(mismatches)} {mismatches}")
    print("=" * 140)
    db.close()

if __name__ == "__main__":
    audit_hods()
