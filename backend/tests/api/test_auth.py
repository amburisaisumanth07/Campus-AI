import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.db.models import User, Role
from backend.app.db.session import SessionLocal

client = TestClient(app)

def get_unique_email():
    return f"user_{uuid.uuid4().hex[:8]}@campusai.edu"

def test_successful_registration():
    email = get_unique_email()
    payload = {
        "name": "Test Student",
        "email": email,
        "password": "Password123!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["name"] == "Test Student"
    assert data["role"] == "STUDENT"
    assert data["is_active"] is True
    assert "password_hash" not in data

def test_duplicate_email_registration():
    email = get_unique_email()
    payload = {
        "name": "First User",
        "email": email,
        "password": "Password123!"
    }
    client.post("/api/auth/register", json=payload)
    
    # Attempt second registration with same email
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

def test_invalid_registration():
    payload = {
        "name": "",
        "email": "not-an-email",
        "password": "short"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422

def test_successful_login():
    email = get_unique_email()
    password = "MySecurePassword123"
    client.post("/api/auth/register", json={
        "name": "Login User",
        "email": email,
        "password": password
    })

    response = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_invalid_login():
    email = get_unique_email()
    password = "RealPassword123"
    client.post("/api/auth/register", json={
        "name": "Login User",
        "email": email,
        "password": password
    })

    # Wrong password
    response = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword123"
    })
    assert response.status_code == 401

    # Non-existent email
    response = client.post("/api/auth/login", json={
        "email": "nonexistent@campusai.edu",
        "password": password
    })
    assert response.status_code == 401

def test_get_current_user_me():
    email = get_unique_email()
    password = "Password123!"
    reg_resp = client.post("/api/auth/register", json={
        "name": "Me User",
        "email": email,
        "password": password
    })
    user_id = reg_resp.json()["id"]

    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    token = login_resp.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == email
    assert data["role"] == "STUDENT"

def test_missing_and_invalid_authentication():
    # Missing token header
    response = client.get("/api/auth/me")
    assert response.status_code == 401

    # Invalid token
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert response.status_code == 401
