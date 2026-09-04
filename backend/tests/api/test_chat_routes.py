import pytest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def get_unique_email():
    return f"chat_user_{uuid.uuid4().hex[:8]}@campusai.edu"


def create_authenticated_user():
    email = get_unique_email()
    password = "Password123!"
    reg_resp = client.post("/api/auth/register", json={
        "name": "Chat User",
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


def test_conversations_crud():
    headers = create_authenticated_user()

    # 1. Create conversation
    create_resp = client.post(
        "/api/conversations",
        headers=headers,
        json={"title": "Academic Calendar Queries"}
    )
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]
    assert create_resp.json()["title"] == "Academic Calendar Queries"

    # 2. List conversations
    list_resp = client.get("/api/conversations", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    assert any(c["id"] == conv_id for c in list_resp.json()["items"])

    # 3. Rename conversation
    rename_resp = client.patch(
        f"/api/conversations/{conv_id}",
        headers=headers,
        json={"title": "Updated Title"}
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["title"] == "Updated Title"

    # 4. Get detail
    detail_resp = client.get(f"/api/conversations/{conv_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == conv_id

    # 5. Delete conversation
    del_resp = client.delete(f"/api/conversations/{conv_id}", headers=headers)
    assert del_resp.status_code == 204


@patch("backend.app.rag.pipeline.run_pipeline")
def test_send_chat_message_and_feedback(mock_pipeline):
    mock_pipeline.return_value = {
        "answer": "The semester exams start on November 15th.",
        "citations": [
            {
                "doc_id": 10,
                "title": "Academic Calendar",
                "page_number": 2,
                "snippet": "Exams start Nov 15",
            }
        ],
        "had_context": True,
    }

    headers = create_authenticated_user()

    # Send message (auto-creates conversation)
    msg_resp = client.post(
        "/api/chat/message",
        headers=headers,
        json={
            "content": "When do semester exams start?",
            "department": "CSE",
        }
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["conversation_id"] is not None
    assert data["user_message"]["content"] == "When do semester exams start?"
    assert data["assistant_message"]["content"] == "The semester exams start on November 15th."
    assert len(data["assistant_message"]["citations"]) == 1

    assistant_msg_id = data["assistant_message"]["id"]

    # Submit feedback
    fb_resp = client.post(
        "/api/feedback",
        headers=headers,
        json={
            "message_id": assistant_msg_id,
            "rating": "thumbs_up",
            "comment": "Helpful answer!",
        }
    )
    assert fb_resp.status_code == 201
    assert fb_resp.json()["rating"] == "thumbs_up"
