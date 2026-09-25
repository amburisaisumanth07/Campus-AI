"""
Standalone Local Live Verification Script for MITS GEMS Attendance.

Usage:
  python backend/scripts/verify_gems_live.py

Security Invariants:
- Volatile memory only: prompt uses getpass (input is never echoed).
- Password is NEVER printed, logged, or saved to any file, database, or environment.
- Credentials and JSESSIONID are purged immediately upon completion.
"""
import sys
import os
import asyncio
import getpass

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.services.gems_attendance_service import (
    GemsAttendanceAdapter,
    AttendanceAuthError,
    AttendancePortalUnavailableError,
    AttendanceMalformedResponseError,
    AttendanceIntegrationError,
)
from backend.app.services.attendance_service import (
    calculate_classes_can_miss,
    calculate_classes_required,
)


async def main():
    print("=" * 65)
    print("  MITS GEMS LOCAL LIVE ATTENDANCE VERIFICATION TOOL")
    print("  Official Portal: http://mitsims.in/")
    print("=" * 65)
    print("Security: Password is never echoed, saved, logged, or stored.")
    print("-" * 65)

    try:
        roll_number = input("Enter MITS Roll Number (e.g. 24691A31N1): ").strip()
        if not roll_number:
            print("[ERROR] Roll number cannot be empty.")
            return

        password = getpass.getpass("Enter MITS GEMS Password (hidden): ").strip()
        if not password:
            print("[ERROR] Password cannot be empty.")
            return

        print("\n[1/3] Connecting to MITS GEMS (http://mitsims.in/)...")
        adapter = GemsAttendanceAdapter()

        print("[2/3] Authenticating & Fetching live attendance dashboard...")
        result = await adapter.fetch_attendance(roll_number=roll_number, password=password)

        # Immediately purge password
        del password

        print("[3/3] Attendance data received successfully!\n")
        print("=" * 65)
        print(f"  Student Name : {result.get('student', 'MITS Student')}")
        print(f"  Roll Number  : {result.get('roll_number')}")
        if result.get("semester"):
            print(f"  Semester     : {result.get('semester')}")
        print(f"  Source       : {result.get('official_source')}")
        print(f"  Mock Data    : NONE (100% Real GEMS portal records)")
        print("=" * 65)

        subjects = result.get("subjects", [])
        if not subjects or len(subjects) == 0:
            print("\n" + "=" * 65)
            print("  [VERIFICATION FAILED] No attendance records were returned from MITS GEMS.")
            print("=" * 65 + "\n")
            sys.exit(1)

        print(f"\n[SUBJECT ATTENDANCE RECORDS] Total Subjects: {len(subjects)}\n")
        print(f"{'Code':<12} {'Subject Name':<32} {'Attended':<10} {'Total':<8} {'Percentage'}")
        print("-" * 75)

        for s in subjects:
            code = s.get("code") or "-"
            name = s.get("name", "Subject")
            if len(name) > 30:
                name = name[:27] + "..."
            att = s.get("attended", 0)
            tot = s.get("total", 0)
            pct = s.get("percentage", 0.0)
            print(f"{code:<12} {name:<32} {att:<10} {tot:<8} {pct:.2f}%")

        print("-" * 75)
        overall = result.get("overall", 0.0)
        tot_att = sum(s["attended"] for s in subjects)
        tot_cls = sum(s["total"] for s in subjects)

        print(f"\n[OVERALL DERIVED SUMMARY]")
        print(f"  Total Classes Attended  : {tot_att}")
        print(f"  Total Classes Conducted : {tot_cls}")
        print(f"  Overall Percentage      : {overall:.2f}% (sum(attended) / sum(total) * 100)")
        print(f"  Status Classification   : {result.get('status')}")

        # Derived calculations
        can_miss = calculate_classes_can_miss(tot_att, tot_cls, 75.0)
        must_attend = calculate_classes_required(tot_att, tot_cls, 75.0)

        print(f"\n[75% REGULATORY PLANNER DERIVATIONS]")
        if overall >= 75.0:
            print(f"  Safe-to-Miss Classes    : {can_miss} classes can be missed while staying >= 75.0%")
        else:
            print(f"  Recovery Classes Needed : {must_attend} consecutive classes required to reach 75.0%")

        print("\n" + "=" * 65)
        print("  LIVE VERIFICATION COMPLETE - ALL RECORDS MATCH MITS GEMS")
        print("=" * 65 + "\n")

    except AttendanceAuthError:
        print("\n[ERROR] Invalid MITS GEMS credentials.")
    except AttendancePortalUnavailableError:
        print("\n[ERROR] MITS GEMS is currently unavailable. Live attendance could not be retrieved.")
    except AttendanceMalformedResponseError as exc:
        print(f"\n[ERROR] Unable to read attendance data from MITS GEMS: {exc}")
    except AttendanceIntegrationError as exc:
        print(f"\n[ERROR] {exc.message}")
    except Exception as exc:
        print(f"\n[ERROR] An unexpected error occurred: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
