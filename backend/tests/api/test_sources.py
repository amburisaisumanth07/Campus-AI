"""
Tests for Admin Website Sources & Knowledge Sync API routes.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.models import User, Role, WebsiteSource, WebsiteSourceStatus
from backend.app.db.session import SessionLocal

client = TestClient(app)


def _make_unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@campusai.test"


def _create_user_and_token(role: Role) -> str:
    db = SessionLocal()
    try:
        email = _make_unique_email()
        user = User(
            email=email,
            name="Test User",
            password_hash=hash_password("Password123!"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role.value})
        return token
    finally:
        db.close()


def test_sources_permission_enforcement():
    # 1. Unauthenticated -> 401
    resp = client.get("/api/admin/sources")
    assert resp.status_code == 401

    # 2. Student -> 403
    student_token = _create_user_and_token(Role.STUDENT)
    resp = client.get("/api/admin/sources", headers={"Authorization": f"Bearer {student_token}"})
    assert resp.status_code == 403

    # 3. Admin -> 200
    admin_token = _create_user_and_token(Role.ADMIN)
    resp = client.get("/api/admin/sources", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_website_source_validation():
    admin_token = _create_user_and_token(Role.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Reject localhost SSRF
    resp = client.post(
        "/api/admin/sources",
        json={
            "name": "Localhost Source",
            "base_url": "http://localhost:8000",
            "allowed_domains": "localhost",
            "sync_interval": "6h",
            "max_pages": 50,
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert "unsafe" in resp.json()["detail"].lower() or "forbidden" in resp.json()["detail"].lower()

    # Reject domain mismatch
    resp = client.post(
        "/api/admin/sources",
        json={
            "name": "Mismatch Source",
            "base_url": "https://othercollege.edu",
            "allowed_domains": "mycollege.edu",
            "sync_interval": "6h",
            "max_pages": 50,
        },
        headers=headers,
    )
    assert resp.status_code == 422

    # Successfully create valid source
    unique_name = f"College Source {uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/admin/sources",
        json={
            "name": unique_name,
            "base_url": "https://college.edu",
            "allowed_domains": "college.edu",
            "allowed_paths": "/academics, /examinations",
            "sync_interval": "12h",
            "max_pages": 30,
            "active": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == unique_name
    assert data["base_url"] == "https://college.edu"
    assert data["status"] == "IDLE"
    assert data["document_count"] == 0


def test_crud_and_status_lifecycle():
    admin_token = _create_user_and_token(Role.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create
    resp = client.post(
        "/api/admin/sources",
        json={
            "name": "Test Portal",
            "base_url": "https://portal.univ.edu",
            "allowed_domains": "portal.univ.edu, univ.edu",
            "sync_interval": "6h",
            "max_pages": 20,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    # Get details
    resp = client.get(f"/api/admin/sources/{source_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Portal"

    # Update
    resp = client.put(
        f"/api/admin/sources/{source_id}",
        json={"name": "Updated Portal Name", "max_pages": 45, "sync_interval": "24h"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Portal Name"
    assert resp.json()["max_pages"] == 45
    assert resp.json()["sync_interval"] == "24h"

    # Live Status
    resp = client.get(f"/api/admin/sources/{source_id}/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Portal Name"

    # Sync History
    resp = client.get(f"/api/admin/sources/{source_id}/sync-history", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Delete
    resp = client.delete(f"/api/admin/sources/{source_id}", headers=headers)
    assert resp.status_code == 204

    # Confirm 404 after delete
    resp = client.get(f"/api/admin/sources/{source_id}", headers=headers)
    assert resp.status_code == 404
