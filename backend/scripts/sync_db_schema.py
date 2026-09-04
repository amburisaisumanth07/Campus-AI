"""
Database Schema Synchronization Script.
Ensures all tables and new columns exist in PostgreSQL.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from backend.app.db.session import engine
from backend.app.db.models import Base


def sync_schema():
    print("[*] Synchronizing database tables with SQLAlchemy Base...")
    Base.metadata.create_all(bind=engine)

    # Apply ALTER TABLE ADD COLUMN IF NOT EXISTS for any existing tables
    alter_statements = [
        # Important Links
        "ALTER TABLE important_links ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);",
        "ALTER TABLE important_links ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE important_links ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;",

        # Announcements
        "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);",
        "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS http_status INTEGER DEFAULT 200;",
        "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS error_reason TEXT;",

        # Academic Calendar
        "ALTER TABLE academic_calendar ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);",
        "ALTER TABLE academic_calendar ADD COLUMN IF NOT EXISTS http_status INTEGER DEFAULT 200;",
        "ALTER TABLE academic_calendar ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE academic_calendar ADD COLUMN IF NOT EXISTS error_reason TEXT;",
        "ALTER TABLE academic_calendar ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;",

        # Examinations
        "ALTER TABLE examinations ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);",
        "ALTER TABLE examinations ADD COLUMN IF NOT EXISTS http_status INTEGER DEFAULT 200;",
        "ALTER TABLE examinations ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE examinations ADD COLUMN IF NOT EXISTS error_reason TEXT;",
        "ALTER TABLE examinations ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;",

        # Departments
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS hod_name VARCHAR(255);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS hod_designation VARCHAR(255);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS hod_profile_url VARCHAR(1000);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS hod_source_url VARCHAR(1000);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS hod_verified_at TIMESTAMPTZ;",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS phone VARCHAR(100);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS email VARCHAR(255);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64);",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS http_status INTEGER DEFAULT 200;",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS error_reason TEXT;",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;",

        # Placements
        "ALTER TABLE placements ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);",
        "ALTER TABLE placements ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE placements ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;",

        # College Info
        "ALTER TABLE college_info ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(1000);",
        "ALTER TABLE college_info ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE college_info ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;",
    ]

    with engine.begin() as conn:
        for stmt in alter_statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"[!] Warning on stmt: {stmt} -> {e}")

    print("[+] Database schema successfully synchronized.")


if __name__ == "__main__":
    sync_schema()
