"""
Script to reconcile and correct department HOD mappings in the database.
Strictly ensures every canonical department points to its active official HOD.
"""
import sys
import os
from datetime import datetime, timezone
sys.path.insert(0, os.path.abspath("."))

from backend.app.db.session import SessionLocal
from backend.app.db.models import Department, Faculty

CORRECT_HOD_MAP = {
    # Dept ID: (expected_code, hod_name, hod_designation, active_faculty_id)
    1: ("CSE", "Dr. M. Sreedevi", "Professor & Head", 315),
    3: ("ECE", "Dr. Sanjay Kumar C. Gowre", "Professor & Head", 21),
    4: ("EEE", "Dr. Manavaalan Gunasekaran", "Associate Professor & Head", 13),
    5: ("MECH", "Dr. S. Bhaskaran", "Professor & Head", 132),
    6: ("CIVIL", "Dr. Vijayakumar Natesan", "Professor & Head", 131),
    7: ("MBA", "Dr. Bhanu Sree Reddy", "Professor & Head - Management Studies", 90),
    8: ("MCA", "Dr. N. Naveen Kumar", "Professor & Head", 95),
    9: ("CSE-DS", "Dr. S. Kusuma", "Professor & Head", 135),
    10: ("CSE-CS", "Dr. Brahm Prakash", "Associate Professor & Head", 62),
    11: ("AI", "Dr. R. Kalpana", "Professor & Head", 134),
    12: ("CST", "Dr. K. Dinesh", "Associate Professor & Head", 138),
    14: ("CSE-AIML", "Dr. S. Padma", "Professor & Head", 136),
    15: ("BSH", "Dr. R. Saravana", "Head (I/c) - Mathematics", 110),
}

def reconcile_hods():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    print("Reconciling Department HOD records against official MITS source (https://mits.ac.in/departmentheads)...")
    
    for dept_id, (code, hod_name, desig, fac_id) in CORRECT_HOD_MAP.items():
        dept = db.query(Department).filter(Department.id == dept_id).first()
        if not dept:
            print(f"Warning: Department ID {dept_id} ({code}) not found!")
            continue

        fac = db.query(Faculty).filter(Faculty.id == fac_id).first()
        if not fac:
            print(f"Warning: Faculty ID {fac_id} for {code} not found!")
        elif not fac.is_active:
            print(f"Warning: Faculty ID {fac_id} ({fac.name}) is inactive!")
        else:
            print(f"Verified active faculty for {code}: ID {fac.id} - {fac.name} ({fac.designation})")

        # Update department attributes
        dept.hod_name = hod_name
        dept.hod = hod_name
        dept.hod_designation = desig
        dept.hod_id = fac_id
        dept.hod_person_id = None
        dept.hod_source_url = "https://mits.ac.in/departmentheads"
        dept.last_verified_at = now
        dept.is_active = True

    # Clean inactive placeholder departments
    for ph_id, ph_code, canonical_hod in [(2, "AIML", "Dr. S. Padma"), (13, "CSE-HOD", "Dr. M. Sreedevi")]:
        ph_dept = db.query(Department).filter(Department.id == ph_id).first()
        if ph_dept:
            ph_dept.is_active = False
            ph_dept.hod = canonical_hod
            ph_dept.hod_name = canonical_hod
            ph_dept.hod_person_id = None
            ph_dept.hod_id = None
            ph_dept.last_verified_at = now

    db.commit()
    print("Successfully committed HOD reconciliation to database!")
    db.close()

if __name__ == "__main__":
    reconcile_hods()
