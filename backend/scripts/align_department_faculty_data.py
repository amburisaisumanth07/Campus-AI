"""
Script to align and validate MITS department and faculty data in Neon PostgreSQL.
Ensures zero-bleed department isolation, links HODs accurately to their departments,
corrects Dr. M. Sreedevi's department assignment (to CSE, dept_id=1),
and deactivates duplicate/dummy department records (AIML id=2, CSE-HOD id=13).
"""
import sys
import os
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.db.session import SessionLocal
from backend.app.db.models import Department, Faculty
from backend.app.core.canonical_departments import CANONICAL_DEPARTMENTS, CANONICAL_DEPARTMENTS_BY_ID


def align_data():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("STARTING DEPARTMENT & FACULTY DATA ALIGNMENT")
        print("=" * 70)

        # 1. Correct Dr. M. Sreedevi (Faculty ID 133)
        sreedevi = db.query(Faculty).filter(Faculty.id == 133).first()
        if sreedevi:
            print(f"Current Faculty 133: {sreedevi.name} | dept_id={sreedevi.department_id} | dept={sreedevi.department}")
            sreedevi.department_id = 1
            sreedevi.department = "CSE"
            sreedevi.updated_at = datetime.now(timezone.utc)
            print(f" -> Corrected Faculty 133: {sreedevi.name} -> dept_id=1 (CSE)")
        else:
            # Fallback search by name
            sreedevi_by_name = db.query(Faculty).filter(Faculty.name.ilike("%Sreedevi%")).first()
            if sreedevi_by_name:
                print(f"Found Sreedevi by name: ID {sreedevi_by_name.id} | dept_id={sreedevi_by_name.department_id}")
                sreedevi_by_name.department_id = 1
                sreedevi_by_name.department = "CSE"
                sreedevi_by_name.updated_at = datetime.now(timezone.utc)
                print(f" -> Corrected Sreedevi ID {sreedevi_by_name.id} -> dept_id=1 (CSE)")

        # 2. Deactivate obsolete duplicate / dummy departments (ID 2 and ID 13)
        dummy_depts = db.query(Department).filter(Department.id.in_([2, 13])).all()
        for d in dummy_depts:
            print(f"Deactivating obsolete department: ID {d.id} ({d.code} - {d.name})")
            d.is_active = False
            d.updated_at = datetime.now(timezone.utc)

        # 3. Update canonical department records (Names, HODs, Designations, URLs, is_active=True)
        for canon_code, canon in CANONICAL_DEPARTMENTS.items():
            dept = db.query(Department).filter(Department.id == canon.department_id).first()
            if dept:
                print(f"Updating Department ID {dept.id} ({canon_code}):")
                print(f"   Name: '{dept.name}' -> '{canon.official_name}'")
                print(f"   HOD: '{dept.hod_name}' -> '{canon.hod_name}'")
                dept.name = canon.official_name
                dept.code = canon.code
                dept.hod = canon.hod_name
                dept.hod_name = canon.hod_name
                dept.hod_designation = canon.hod_designation
                dept.source_url = canon.source_url
                dept.is_active = True
                dept.updated_at = datetime.now(timezone.utc)

                # Link dept.hod_id if the faculty member exists in this department
                clean_hod = canon.hod_name.replace("Dr. ", "").replace("Prof. ", "").strip()
                hod_fac = db.query(Faculty).filter(
                    Faculty.department_id == dept.id,
                    Faculty.name.ilike(f"%{clean_hod}%"),
                ).first()
                if hod_fac:
                    dept.hod_id = hod_fac.id
                    print(f"   Linked HOD Faculty ID: {hod_fac.id} ({hod_fac.name})")
                else:
                    print(f"   Note: HOD '{canon.hod_name}' not found as a separate Faculty row in dept {dept.id}")
            else:
                print(f"WARNING: Department ID {canon.department_id} ({canon_code}) not found in database!")

        # 4. Sync faculty.department string to match the department's code
        active_depts = {d.id: d.code for d in db.query(Department).filter(Department.is_active == True).all()}
        all_faculty = db.query(Faculty).all()
        synced_count = 0
        for fac in all_faculty:
            if fac.department_id in active_depts:
                expected_code = active_depts[fac.department_id]
                if fac.department != expected_code:
                    fac.department = expected_code
                    synced_count += 1
        print(f"Synced department string for {synced_count} faculty members.")

        # Commit all changes
        db.commit()
        print("\nAll database changes committed successfully.")

        # 5. Print Verification Stats
        print("\n" + "=" * 70)
        print("VERIFICATION STATS POST-ALIGNMENT")
        print("=" * 70)
        for canon_code, canon in CANONICAL_DEPARTMENTS.items():
            dept = db.query(Department).filter(Department.id == canon.department_id).first()
            faculty_count = db.query(Faculty).filter(
                Faculty.department_id == canon.department_id,
                Faculty.is_active == True,
            ).count()
            print(f"Dept [{canon.department_id:2d}] {canon.code:<10} | {canon.official_name:<40} | HOD: {dept.hod_name:<30} | Faculty: {faculty_count:3d}")

        # Check AI vs CSE vs CSE-AIML isolation specifically
        ai_faculty = [f.name for f in db.query(Faculty).filter(Faculty.department_id == 11, Faculty.is_active == True).all()]
        print(f"\nAI (ID 11) Faculty ({len(ai_faculty)}): {ai_faculty}")

        sreedevi_check = db.query(Faculty).filter(Faculty.name.ilike("%Sreedevi%")).first()
        if sreedevi_check:
            print(f"Dr. M. Sreedevi is in Dept ID: {sreedevi_check.department_id} ({sreedevi_check.department})")

    except Exception as e:
        db.rollback()
        print(f"ERROR during alignment: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    align_data()
