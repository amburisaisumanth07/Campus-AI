"""
API Integration & Unit Tests for Milestone 10: Chat API Integration.
Verifies authentication, authorization, conversation ownership, message persistence,
RAG pipeline orchestration, grounding response, no-context handling, and error safety.
"""

import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.models import Conversation, Message, MessageRole

client = TestClient(app)


def get_unique_email(prefix: str = "chat10_user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@campusai.edu"


def create_authenticated_user(email_prefix: str = "chat10_user"):
    email = get_unique_email(email_prefix)
    password = "Password123!"
    client.post("/api/auth/register", json={
        "name": "Milestone 10 User",
        "email": email,
        "password": password
    })
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers


# ── 1. Authentication Tests ───────────────────────────────────────────────────

def test_chat_unauthenticated_request_rejected():
    """Unauthenticated POST /api/chat requests must return 401 Unauthorized."""
    resp = client.post("/api/chat", json={"message": "What is the fee structure?"})
    assert resp.status_code == 401

    resp_msg = client.post("/api/chat/message", json={"content": "What is the fee structure?"})
    assert resp_msg.status_code == 401


def test_chat_invalid_token_rejected():
    """Requests with invalid Bearer token must return 401 Unauthorized."""
    headers = {"Authorization": "Bearer invalid_token_12345"}
    resp = client.post("/api/chat", headers=headers, json={"message": "Query?"})
    assert resp.status_code == 401


# ── 2. Conversation & Ownership Tests ─────────────────────────────────────────

@patch("backend.app.rag.pipeline.run_pipeline")
def test_chat_auto_create_conversation(mock_pipeline):
    """If conversation_id is None, endpoint automatically creates a new conversation."""
    mock_pipeline.return_value = {
        "answer": "Passing score is 40%.",
        "grounded": True,
        "retrieval_count": 1,
        "sources": [
            {
                "document_id": 1,
                "document_version_id": 1,
                "title": "Exam Ordinance",
                "page_number": 2,
                "source_pages": [2],
            }
        ],
    }

    headers = create_authenticated_user()
    resp = client.post(
        "/api/chat",
        headers=headers,
        json={"message": "What is the passing score?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] is not None
    assert data["message_id"] is not None
    assert data["answer"] == "Passing score is 40%."
    assert data["grounded"] is True
    assert data["retrieval_count"] == 1
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_id"] == 1


@patch("backend.app.rag.pipeline.run_pipeline")
def test_chat_existing_conversation(mock_pipeline):
    """Supplying a valid conversation_id continues the existing conversation."""
    mock_pipeline.return_value = {
        "answer": "Library hours are 8 AM to 10 PM.",
        "grounded": True,
        "retrieval_count": 1,
        "sources": [],
    }

    headers = create_authenticated_user()

    # Create initial conversation via /api/conversations
    conv_resp = client.post(
        "/api/conversations",
        headers=headers,
        json={"title": "Library Queries"}
    )
    conv_id = conv_resp.json()["id"]

    # Send message to existing conversation
    resp = client.post(
        "/api/chat",
        headers=headers,
        json={"conversation_id": conv_id, "message": "What are the library hours?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == conv_id
    assert data["answer"] == "Library hours are 8 AM to 10 PM."


def test_chat_nonexistent_conversation():
    """Supplying a non-existent conversation_id returns 404 Not Found."""
    headers = create_authenticated_user()
    resp = client.post(
        "/api/chat",
        headers=headers,
        json={"conversation_id": 999999, "message": "Test query?"}
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_chat_cross_user_conversation_access_forbidden():
    """User A attempting to send a message to User B's conversation ID returns 404 Not Found."""
    headers_user_a = create_authenticated_user("usera")
    headers_user_b = create_authenticated_user("userb")

    # User B creates a conversation
    conv_resp_b = client.post(
        "/api/conversations",
        headers=headers_user_b,
        json={"json": "User B Private Chat"}
    )
    conv_id_b = conv_resp_b.json()["id"]

    # User A attempts to message User B's conversation
    resp = client.post(
        "/api/chat",
        headers=headers_user_a,
        json={"conversation_id": conv_id_b, "message": "I am eavesdropping!"}
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── 3. Input Validation & Security Tests ──────────────────────────────────────

def test_chat_empty_query_rejected():
    """Empty or whitespace-only messages must be rejected with 422 Unprocessable Entity."""
    headers = create_authenticated_user()

    resp1 = client.post("/api/chat", headers=headers, json={"message": "   "})
    assert resp1.status_code == 422

    resp2 = client.post("/api/chat", headers=headers, json={"content": ""})
    assert resp2.status_code == 422


# ── 4. RAG Orchestration & No-Context Behavior ───────────────────────────────

@patch("backend.app.rag.pipeline.run_pipeline")
def test_chat_no_context_behavior(mock_pipeline):
    """When retrieval finds no evidence, grounded = False, retrieval_count = 0, sources = []."""
    mock_pipeline.return_value = {
        "answer": "I couldn't find this information in the available college documents.",
        "grounded": False,
        "retrieval_count": 0,
        "sources": [],
    }

    headers = create_authenticated_user()
    resp = client.post(
        "/api/chat",
        headers=headers,
        json={"message": "Out of domain query?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounded"] is False
    assert data["retrieval_count"] == 0
    assert data["sources"] == []
    assert "couldn't find this information" in data["answer"]


@patch("backend.app.rag.pipeline.run_pipeline")
def test_chat_pipeline_failure_gracefully_handled(mock_pipeline):
    """Internal exceptions during RAG execution are handled gracefully without 500 crash."""
    mock_pipeline.side_effect = Exception("Chroma connection timeout")

    headers = create_authenticated_user()
    resp = client.post(
        "/api/chat",
        headers=headers,
        json={"message": "Failure test query?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounded"] is False
    assert data["retrieval_count"] == 0
    assert data["sources"] == []
    assert "couldn't find this information" in data["answer"]
