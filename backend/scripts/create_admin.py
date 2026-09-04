"""
Seed script to create an initial ADMIN account.

Reads ADMIN_EMAIL, ADMIN_PASSWORD, and ADMIN_NAME from environment variables
(loaded via the shared .env file).  Does nothing if those values are blank or
if the admin account already exists.

Usage:
    python -m scripts.create_admin
"""
import sys
from pathlib import Path

# Ensure the backend package is on sys.path so "backend.app.*" imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.db.models import User, Role
from backend.app.db.session import SessionLocal


def seed_admin() -> None:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        print("[seed] ADMIN_EMAIL or ADMIN_PASSWORD not set – skipping admin seed.")
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if existing:
            print(f"[seed] Admin account '{settings.ADMIN_EMAIL}' already exists – skipping.")
            return

        admin = User(
            name=settings.ADMIN_NAME,
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role=Role.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"[seed] Admin account '{settings.ADMIN_EMAIL}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
