"""
Conversation management routes.

GET    /api/conversations           – list user's conversations
POST   /api/conversations           – create new conversation
GET    /api/conversations/{id}      – get conversation + messages
DELETE /api/conversations/{id}      – delete conversation
PATCH  /api/conversations/{id}      – rename conversation
"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.api.deps import get_current_user
from backend.app.db.models import Conversation, Message, User
from backend.app.rag.pipeline import json_to_citations
from backend.app.schemas.chat import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
    CitationItem,
    FeedbackResponse,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _message_to_response(msg: Message) -> MessageResponse:
    citations_raw = json_to_citations(msg.citations)
    citations = [CitationItem(**c) for c in citations_raw] if citations_raw else None

    feedback_resp = None
    if msg.feedback:
        feedback_resp = FeedbackResponse(
            id=msg.feedback.id,
            message_id=msg.feedback.message_id,
            user_id=msg.feedback.user_id,
            rating=msg.feedback.rating.value,
            comment=msg.feedback.comment,
            created_at=msg.feedback.created_at,
        )

    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role.value,
        content=msg.content,
        citations=citations,
        feedback=feedback_resp,
        created_at=msg.created_at,
    )


def _conv_to_response(conv: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages),
    )


def _get_conv_or_404(db: Session, conv_id: int, user_id: int) -> Conversation:
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conv


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=ConversationListResponse)
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's conversations, newest first."""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return ConversationListResponse(
        items=[_conv_to_response(c) for c in convs],
        total=len(convs),
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new empty conversation."""
    conv = Conversation(user_id=current_user.id, title=payload.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _conv_to_response(conv)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a conversation with all its messages."""
    conv = _get_conv_or_404(db, conversation_id, current_user.id)
    return ConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[_message_to_response(m) for m in conv.messages],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    conv = _get_conv_or_404(db, conversation_id, current_user.id)
    db.delete(conv)
    db.commit()


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: int,
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a conversation."""
    conv = _get_conv_or_404(db, conversation_id, current_user.id)
    conv.title = payload.title
    db.commit()
    db.refresh(conv)
    return _conv_to_response(conv)
