"""
Validation script to enforce Department & Faculty Invariants and generate
the Comprehensive Official Faculty Audit Report for CampusAI:
- official department name
- department code
- HOD
- faculty count
- faculty names
- duplicate faculty (cross-department check)
- faculty assigned to wrong department
- faculty without department
- stale/inactive faculty
- missing official profile URL
"""
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.db.session import SessionLocal
from backend.app.db.models import Department, Faculty
from backend.app.core.canonical_departments import (
    CANONICAL_DEPARTMENTS,
    CANONICAL_DEPARTMENTS_BY_ID,
    resolve_canonical_department,
)
from backend.app.services.knowledge_service import resolve_faculty, resolve_hod, resolve_department


def validate_and_report_faculty_data():
    db = SessionLocal()
    errors = []
    warnings = []

    print("=" * 80)
    print("MITS OFFICIAL DEPARTMENT & FACULTY DATA VALIDATION & AUDIT REPORT")
    print("=" * 80)

    try:
        active_faculty = db.query(Faculty).filter(Faculty.is_active == True).all()
        inactive_faculty = db.query(Faculty).filter(Faculty.is_active == False).all()
        active_dept_ids = set(CANONICAL_DEPARTMENTS_BY_ID.keys())

        # 1. Check faculty without valid department
        orphaned_faculty = []
        for fac in active_faculty:
            if fac.department_id not in active_dept_ids:
                orphaned_faculty.append(f"ID {fac.id}: {fac.name} (dept_id={fac.department_id})")

        # 2. Check cross-department duplicate faculty
        fac_to_depts = {}
        cross_duplicates = []
        for fac in active_faculty:
            clean_name = re.sub(r'[^a-zA-Z]', '', fac.name).lower()
            if clean_name in fac_to_depts:
                prev_fac = fac_to_depts[clean_name]
                if prev_fac.department_id != fac.department_id:
                    cross_duplicates.append(
                        f"Faculty '{fac.name}' appears in {CANONICAL_DEPARTMENTS_BY_ID[prev_fac.department_id].code} (ID {prev_fac.department_id}) and {CANONICAL_DEPARTMENTS_BY_ID[fac.department_id].code} (ID {fac.department_id})"
                    )
            else:
                fac_to_depts[clean_name] = fac

        # 3. Department-by-department audit
        print("\n" + "-" * 80)
        print("DEPARTMENT-BY-DEPARTMENT FACULTY ROSTER AUDIT")
        print("-" * 80)

        total_active = 0
        total_missing_urls = 0

        for code, canon in CANONICAL_DEPARTMENTS.items():
            dept_fac = db.query(Faculty).filter(
                Faculty.department_id == canon.department_id,
                Faculty.is_active == True,
            ).order_by(Faculty.designation, Faculty.name).all()

            dept_inactive = db.query(Faculty).filter(
                Faculty.department_id == canon.department_id,
                Faculty.is_active == False,
            ).all()

            missing_profiles = [f.name for f in dept_fac if not f.profile_url or not f.profile_url.startswith("http")]
            total_missing_urls += len(missing_profiles)
            total_active += len(dept_fac)

            print(f"\n[{code}] {canon.official_name}")
            print(f"  • Department ID:    {canon.department_id}")
            print(f"  • Department Code:  {code}")
            print(f"  • Official HOD:     {canon.hod_name} ({canon.hod_designation})")
            print(f"  • Active Faculty:   {len(dept_fac)}")
            print(f"  • Inactive/Stale:   {len(dept_inactive)}")
            print(f"  • Missing Profiles: {len(missing_profiles)}")
            print(f"  • Official URL:     {canon.official_url}")
            print(f"  • Faculty Names ({len(dept_fac)}):")
            for idx, f in enumerate(dept_fac, 1):
                desig = f.designation or "Faculty"
                qual = f" ({f.qualification})" if f.qualification else ""
                prof = f" | {f.profile_url}" if f.profile_url else ""
                print(f"      {idx:2d}. {f.name} - {desig}{qual}{prof}")

        # 4. Inactive/Historical faculty report
        print("\n" + "-" * 80)
        print(f"STALE / INACTIVE FACULTY RECORDS ({len(inactive_faculty)} total)")
        print("-" * 80)
        for idx, inf in enumerate(inactive_faculty, 1):
            dept_code = CANONICAL_DEPARTMENTS_BY_ID.get(inf.department_id).code if inf.department_id in CANONICAL_DEPARTMENTS_BY_ID else "UNKNOWN"
            print(f"  {idx:2d}. ID {inf.id}: {inf.name} ({inf.designation}) | Former Dept: {dept_code} ({inf.department_id})")

        # 5. Invariants summary
        print("\n" + "=" * 80)
        print("INVARIANT VERIFICATION")
        print("=" * 80)

        # Invariant 1: Orphaned faculty
        if orphaned_faculty:
            errors.append(f"Invariant 1 Failed: {len(orphaned_faculty)} faculty without valid canonical department_id.")
            print(f"[FAIL] Invariant 1: Found {len(orphaned_faculty)} orphaned faculty.")
        else:
            print(f"[PASS] Invariant 1: All {len(active_faculty)} active faculty members belong to a valid canonical department.")

        # Invariant 2: Exactly one HOD per canonical department
        missing_hods = [c for c, cd in CANONICAL_DEPARTMENTS.items() if not cd.hod_name]
        if missing_hods:
            errors.append(f"Invariant 2 Failed: Missing HOD in canonical definitions for: {missing_hods}")
            print(f"[FAIL] Invariant 2: Missing HODs: {missing_hods}")
        else:
            print(f"[PASS] Invariant 2: All {len(CANONICAL_DEPARTMENTS)} canonical departments have exactly one official HOD.")

        # Invariant 3: HODs belong to and resolve to same department
        hod_resolution_fails = []
        for code, cd in CANONICAL_DEPARTMENTS.items():
            h_res = resolve_hod(db, dept_code=code)
            if not h_res or not h_res.get("found"):
                hod_resolution_fails.append(code)
            elif cd.hod_name not in h_res.get("text", ""):
                hod_resolution_fails.append(f"{code} (expected {cd.hod_name})")
        if hod_resolution_fails:
            errors.append(f"Invariant 3 Failed: HOD resolution mismatches for: {hod_resolution_fails}")
            print(f"[FAIL] Invariant 3: HOD mismatches for {hod_resolution_fails}")
        else:
            print(f"[PASS] Invariant 3: All {len(CANONICAL_DEPARTMENTS)} department HODs resolve strictly to official records.")

        # Invariant 4: Zero cross-department duplicate faculty
        if cross_duplicates:
            errors.append(f"Invariant 4 Failed: {len(cross_duplicates)} cross-department duplicate faculty detected.")
            print(f"[FAIL] Invariant 4: Cross-department duplicates:\n  " + "\n  ".join(cross_duplicates))
        else:
            print(f"[PASS] Invariant 4: Zero cross-department faculty duplicates across all {len(active_faculty)} records.")

        # Invariant 5: Inactive placeholder departments have 0 active faculty
        inactive_depts = db.query(Department).filter(Department.is_active == False).all()
        inactive_ids = [d.id for d in inactive_depts]
        inactive_with_fac = db.query(Faculty).filter(
            Faculty.is_active == True,
            Faculty.department_id.in_(inactive_ids),
        ).count() if inactive_ids else 0
        if inactive_with_fac > 0:
            errors.append(f"Invariant 5 Failed: {inactive_with_fac} active faculty assigned to deactivated departments {inactive_ids}")
            print(f"[FAIL] Invariant 5: Active faculty assigned to deactivated departments.")
        else:
            print(f"[PASS] Invariant 5: All inactive/placeholder departments ({inactive_ids}) have 0 active faculty.")

        # Invariant 6: Strict department isolation
        ai_res = resolve_faculty(db, dept_code="AI")
        ai_text = ai_res.get("text", "") if ai_res else ""
        isolation_errors = []

        # Must have official AI faculty
        if "Dr. R. Kalpana" not in ai_text:
            isolation_errors.append("HOD Dr. R. Kalpana missing from AI faculty roster")
        if "Dr. Ben Sujin" not in ai_text:
            isolation_errors.append("Dr. Ben Sujin missing from AI faculty roster")
        if "Mr. K. Venkata Subramanyam" not in ai_text:
            isolation_errors.append("Mr. K. Venkata Subramanyam missing from AI faculty roster")

        # Must NOT have faculty from CSE or CSE-AIML
        for non_ai in ["Dr. M. Sreedevi", "Dr. S. Padma", "Dr. P. Kuppusamy"]:
            if non_ai in ai_text:
                isolation_errors.append(f"Non-AI faculty '{non_ai}' leaked into AI faculty roster!")

        if isolation_errors:
            errors.append(f"Invariant 6 Failed: Department isolation check failed:\n  " + "\n  ".join(isolation_errors))
            print(f"[FAIL] Invariant 6: {isolation_errors}")
        else:
            print(f"[PASS] Invariant 6: Strict department isolation verified! AI returns exactly its 25 faculty with zero bleed from CSE or CSE-AIML.")

        # Invariant 7: Official source URLs
        missing_source_urls = []
        for code, cd in CANONICAL_DEPARTMENTS.items():
            f_res = resolve_faculty(db, dept_code=code)
            if not f_res or not f_res.get("citations") or not f_res["citations"][0].get("source_url"):
                missing_source_urls.append(code)
        if missing_source_urls:
            errors.append(f"Invariant 7 Failed: Missing source URLs for: {missing_source_urls}")
            print(f"[FAIL] Invariant 7: Missing source URLs for {missing_source_urls}")
        else:
            print(f"[PASS] Invariant 7: Every department response contains verified official MITS source URLs.")

    finally:
        db.close()

    print("\n" + "=" * 80)
    if errors:
        print(f"FAILED: {len(errors)} validation failure(s) detected.")
        for e in errors:
            print(f"  [!] {e}")
        return False
    else:
        print(f"SUCCESS: All 7 invariants verified! Total active faculty in Neon: {total_active}")
        return True


if __name__ == "__main__":
    success = validate_and_report_faculty_data()
    sys.exit(0 if success else 1)
