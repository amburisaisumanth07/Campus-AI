"""
Feedback routes.

POST  /api/feedback     – submit or update thumbs up/down for an assistant message
GET   /api/feedback     – list all feedback (admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db
from backend.app.api.deps import get_current_user, require_admin
from backend.app.db.models import Feedback, FeedbackRating, Message, MessageRole, User
from backend.app.schemas.chat import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit or update feedback (thumbs up/down) for an assistant message.

    - Only the user who sent the query (owns the conversation) can submit feedback.
    - Only one feedback record per message is allowed (upsert behaviour).
    """
    # Validate message exists and belongs to the user
    msg = db.query(Message).filter(Message.id == payload.message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if msg.role != MessageRole.ASSISTANT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Feedback can only be submitted for assistant messages.",
        )
    if msg.conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit feedback for your own conversations.",
        )

    # Upsert: update existing or create new
    existing = db.query(Feedback).filter(Feedback.message_id == payload.message_id).first()
    if existing:
        existing.rating = FeedbackRating(payload.rating)
        existing.comment = payload.comment
        db.commit()
        db.refresh(existing)
        return _to_response(existing)

    fb = Feedback(
        message_id=payload.message_id,
        user_id=current_user.id,
        rating=FeedbackRating(payload.rating),
        comment=payload.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return _to_response(fb)


@router.get("", response_model=list[FeedbackResponse])
def list_feedback(
    _current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all feedback (admin only) — for monitoring response quality."""
    items = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(200).all()
    return [_to_response(f) for f in items]


def _to_response(fb: Feedback) -> FeedbackResponse:
    return FeedbackResponse(
        id=fb.id,
        message_id=fb.message_id,
        user_id=fb.user_id,
        rating=fb.rating.value,
        comment=fb.comment,
        created_at=fb.created_at,
    )
