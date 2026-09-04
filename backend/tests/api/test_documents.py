"""
Tests for document management API.

Tests run against a real PostgreSQL instance (same as integration tests).
Each test creates unique content to avoid collisions.
"""
import io
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.db.models import User, Role, Document, DocumentVersion
from backend.app.db.session import SessionLocal
from backend.app.core.security import hash_password

client = TestClient(app)

# ── Fixtures ──────────────────────────────────────────────────────────────────

TEST_PDF_PATH = Path(__file__).parent.parent / "fixtures" / "test_document.pdf"


def _get_pdf_bytes() -> bytes:
    unique_str = uuid.uuid4().hex
    return (
        f"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        f"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        f"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        f"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        f"5 0 obj<</Length 44>>\nstream\nBT /F1 12 Tf 50 700 Td ({unique_str}) Tj ET\nendstream\nendobj\n"
        f"xref\n0 6\n0000000000 65535 f \n"
        f"trailer<</Size 6/Root 1 0 R>>\nstartxref\n9\n%%EOF"
    ).encode("utf-8")



def _make_unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@campusai.test"


def _create_user_and_token(role: Role) -> str:
    """Create a DB user with the given role and return a JWT token."""
    db = SessionLocal()
    try:
        email = _make_unique_email()
        user = User(
            name=f"{role.value} User",
            email=email,
            password_hash=hash_password("Password123!"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(data={"sub": str(user.id)})
        return token
    finally:
        db.close()


def _upload_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _pdf_form(title: str = "Test Document") -> dict:
    return {
        "title": (None, title),
        "document_type": (None, "notice"),
        "department": (None, "Computer Science"),
        "academic_year": (None, "2025-2026"),
        "version": (None, "1.0"),
    }


# ── Admin upload tests ────────────────────────────────────────────────────────

def test_admin_can_upload_valid_pdf():
    token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Test Document"
    assert data["status"] in ("READY", "FAILED")  # processing attempted
    assert "storage_path" not in str(data)  # filesystem path must not leak


def test_student_can_upload():
    token = _create_user_and_token(Role.STUDENT)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("student_upload.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form("Student Doc"),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Student Doc"


def test_user_cannot_access_or_delete_other_user_document():
    user1_token = _create_user_and_token(Role.STUDENT)
    user2_token = _create_user_and_token(Role.STUDENT)

    # User 1 uploads document
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("user1.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form("User 1 Doc"),
    }
    upload_resp = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(user1_token),
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # User 2 attempts to get User 1's document -> 403
    get_resp = client.get(f"/api/documents/{doc_id}", headers=_upload_headers(user2_token))
    assert get_resp.status_code == 403

    # User 2 attempts to delete User 1's document -> 403
    del_resp = client.delete(f"/api/documents/{doc_id}", headers=_upload_headers(user2_token))
    assert del_resp.status_code == 403

    # User 1 can access and delete own document
    user1_get = client.get(f"/api/documents/{doc_id}", headers=_upload_headers(user1_token))
    assert user1_get.status_code == 200

    user1_del = client.delete(f"/api/documents/{doc_id}", headers=_upload_headers(user1_token))
    assert user1_del.status_code == 200


def test_admin_can_access_and_delete_any_document():
    user_token = _create_user_and_token(Role.STUDENT)
    admin_token = _create_user_and_token(Role.ADMIN)

    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("student_for_admin.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form("Student Doc for Admin"),
    }
    upload_resp = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(user_token),
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Admin gets document
    get_resp = client.get(f"/api/documents/{doc_id}", headers=_upload_headers(admin_token))
    assert get_resp.status_code == 200

    # Admin deletes document
    del_resp = client.delete(f"/api/documents/{doc_id}", headers=_upload_headers(admin_token))
    assert del_resp.status_code == 200


def test_unauthenticated_upload_denied():
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(),
    }
    response = client.post("/api/documents", files=files)
    assert response.status_code == 401


def test_non_pdf_rejected():
    token = _create_user_and_token(Role.ADMIN)
    fake_text = b"This is just a text file, not a PDF"
    files = {
        "file": ("doc.txt", io.BytesIO(fake_text), "text/plain"),
        **_pdf_form(),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 415


def test_non_pdf_content_type_rejected():
    """A file with application/pdf content-type but non-PDF magic bytes is rejected."""
    token = _create_user_and_token(Role.ADMIN)
    fake_pdf = b"NOT A PDF - fake content"
    files = {
        "file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf"),
        **_pdf_form(),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 415


def test_oversized_file_rejected():
    token = _create_user_and_token(Role.ADMIN)
    # Create a valid PDF header followed by enough dummy data to exceed 20 MB
    from backend.app.core.config import settings
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    big_data = b"%PDF-1.4\n" + b"X" * (max_bytes + 1)
    files = {
        "file": ("big.pdf", io.BytesIO(big_data), "application/pdf"),
        **_pdf_form(),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 413


def test_unsafe_filename_sanitized():
    """Uploading a file with a path-traversal filename must not cause errors."""
    token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("../../../etc/passwd.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(title="Traversal Test"),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    # Should succeed (sanitized) or reject on validation, never expose paths
    assert response.status_code in (201, 400, 422)
    if response.status_code == 201:
        assert "../" not in response.json().get("filename", "")


def test_checksum_generated_on_upload():
    token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("checksum_test.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(title="Checksum Test"),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 201
    data = response.json()
    if data.get("active_version"):
        checksum = data["active_version"]["file_checksum"]
        assert len(checksum) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in checksum)


def test_duplicate_file_rejected():
    """Uploading the same file bytes twice should return 409 Conflict."""
    token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length 44>>\nstream\nBT /F1 12 Tf 50 700 Td (Static Duplicate Test Content) Tj ET\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n9\n%%EOF"
    )

    for i in range(2):
        files = {
            "file": (f"dup_{i}.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
            **_pdf_form(title=f"Duplicate Test {i}"),
        }
        resp = client.post(
            "/api/documents",
            files=files,
            headers=_upload_headers(token),
        )
        if i == 0:
            assert resp.status_code == 201
        else:
            assert resp.status_code == 409



def test_document_metadata_stored():
    token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("metadata_check.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        "title": (None, "Metadata Title"),
        "document_type": (None, "examination"),
        "department": (None, "Electronics"),
        "academic_year": (None, "2024-2025"),
        "version": (None, "2.0"),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Metadata Title"
    assert data["document_type"] == "examination"
    assert data["department"] == "Electronics"
    assert data["academic_year"] == "2024-2025"
    assert data["active_version"]["version"] == "2.0"


def test_document_status_becomes_ready_or_failed():
    token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("status_test.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(title="Status Test"),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(token),
    )
    assert response.status_code == 201
    status_val = response.json()["status"]
    assert status_val in ("READY", "FAILED")


# ── Read tests ────────────────────────────────────────────────────────────────

def test_list_documents_requires_auth():
    response = client.get("/api/documents")
    assert response.status_code == 401


def test_student_can_list_documents():
    token = _create_user_and_token(Role.STUDENT)
    response = client.get("/api/documents", headers=_upload_headers(token))
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_get_document_detail():
    user_token = _create_user_and_token(Role.STUDENT)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("detail_test.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(title="Detail Test"),
    }
    upload_resp = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(user_token),
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Read as same user
    get_resp = client.get(f"/api/documents/{doc_id}", headers=_upload_headers(user_token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == doc_id


def test_get_nonexistent_document_returns_404():
    token = _create_user_and_token(Role.STUDENT)
    response = client.get("/api/documents/999999", headers=_upload_headers(token))
    assert response.status_code == 404


# ── Delete tests ──────────────────────────────────────────────────────────────

def test_admin_can_delete_document():
    admin_token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("delete_me.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(title="Delete Me"),
    }
    upload_resp = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(admin_token),
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    del_resp = client.delete(f"/api/documents/{doc_id}", headers=_upload_headers(admin_token))
    assert del_resp.status_code == 200
    assert del_resp.json()["document_id"] == doc_id

    # Confirm it's gone
    get_resp = client.get(f"/api/documents/{doc_id}", headers=_upload_headers(admin_token))
    assert get_resp.status_code == 404


def test_no_storage_path_in_response():
    """Verify that internal file system paths are never returned."""
    admin_token = _create_user_and_token(Role.ADMIN)
    pdf_bytes = _get_pdf_bytes()
    files = {
        "file": ("path_test.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        **_pdf_form(title="Path Leak Test"),
    }
    response = client.post(
        "/api/documents",
        files=files,
        headers=_upload_headers(admin_token),
    )
    assert response.status_code == 201
    response_text = response.text
    assert "storage_path" not in response_text
    assert "data/documents" not in response_text
    assert "C:\\" not in response_text
