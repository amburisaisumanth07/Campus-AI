"""
Chat route — receives a user query message, runs the RAG pipeline, and persists both
the user message and the AI assistant message.

POST /api/chat
POST /api/chat/message
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.api.dependencies import get_db
from backend.app.api.deps import get_current_user
from backend.app.core.logging import logger
from backend.app.db.models import Conversation, Message, MessageRole, User
from backend.app.rag import pipeline
from backend.app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    MessageResponse,
    CitationItem,
    SourceCitation,
)

router = APIRouter()


def _message_to_response(msg: Message) -> MessageResponse:
    citations_raw = pipeline.json_to_citations(msg.citations)
    citations = [CitationItem(**c) for c in citations_raw] if citations_raw else None
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role.value,
        content=msg.content,
        citations=citations,
        feedback=None,
        created_at=msg.created_at,
    )


@router.post("", response_model=ChatMessageResponse)
@router.post("/", response_model=ChatMessageResponse)
@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a chat query message and receive a document-grounded AI answer.

    - Requires Bearer JWT authentication.
    - If `conversation_id` is None, a new conversation is created for `current_user`.
    - If `conversation_id` is provided, ownership is strictly verified.
    - Persists user message, executes RAG pipeline, persists assistant answer, and returns structured API response.
    """
    query_text = payload.get_query_text()
    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    # 1. Resolve and authorize conversation
    if payload.conversation_id is not None:
        conv = db.query(Conversation).filter(
            Conversation.id == payload.conversation_id
        ).first()
        if not conv or conv.user_id != current_user.id:
            logger.warning(f"Unauthorized or invalid conversation access. User ID: {current_user.id}, Conv ID: {payload.conversation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
    else:
        title = query_text[:80] + ("…" if len(query_text) > 80 else "")
        conv = Conversation(user_id=current_user.id, title=title)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Persist user message
    user_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER,
        content=query_text,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. Call RAG pipeline
    try:
        pipeline_result = pipeline.run_pipeline(
            query=query_text,
            department=payload.department,
            academic_year=payload.academic_year,
            db=db,
        )
        answer = pipeline_result.get("answer", "")
        grounded = bool(pipeline_result.get("grounded", False))
        retrieval_count = int(pipeline_result.get("retrieval_count", 0))
        retrieval_error = bool(pipeline_result.get("retrieval_error", False))
        generation_error = bool(pipeline_result.get("generation_error", False))
        status_val = pipeline_result.get("status", "SUCCESS")
        
        sources_raw = pipeline_result.get("sources")
        if sources_raw is None:
            sources_raw = pipeline_result.get("citations") or []
        citations_json = pipeline.citations_to_json(sources_raw)
        
        # Log latencies
        total_lat = pipeline_result.get("total_latency", 0)
        retrieval_latency = pipeline_result.get("retrieval_latency")
        llm_latency = pipeline_result.get("llm_latency")
        embedding_ms = pipeline_result.get("embedding_ms")
        retrieval_ms = pipeline_result.get("retrieval_ms")
        prompt_ms = pipeline_result.get("prompt_ms")
        llm_ms = pipeline_result.get("llm_ms")
        citation_ms = pipeline_result.get("citation_ms")
        database_ms = pipeline_result.get("database_ms")
        total_ms = pipeline_result.get("total_ms", round(total_lat * 1000, 2) if total_lat else 0.0)
        logger.info(f"RAG Pipeline completed in {total_ms:.1f}ms | Status: {status_val}")
    except Exception as exc:
        logger.error(f"RAG pipeline execution error in chat endpoint: {exc}")
        answer = "I couldn't find this information in the available college documents."
        grounded = False
        retrieval_count = 0
        retrieval_error = False
        generation_error = True
        status_val = "LLM_ERROR"
        sources_raw = []
        citations_json = None
        retrieval_latency = None
        llm_latency = None
        total_lat = None
        embedding_ms = None
        retrieval_ms = None
        prompt_ms = None
        llm_ms = None
        citation_ms = None
        database_ms = None
        total_ms = None

    # 4. Persist assistant message
    assistant_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        citations=citations_json,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # 5. Touch conversation updated_at
    db.query(Conversation).filter(Conversation.id == conv.id).update(
        {"updated_at": func.now()}
    )
    db.commit()

    sources_models = [SourceCitation(**s) for s in sources_raw] if sources_raw else []

    return ChatMessageResponse(
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        answer=answer,
        grounded=grounded,
        retrieval_count=retrieval_count,
        sources=sources_models,
        user_message=_message_to_response(user_msg),
        assistant_message=_message_to_response(assistant_msg),
        retrieval_error=retrieval_error,
        generation_error=generation_error,
        status=status_val,
        retrieval_latency=retrieval_latency,
        llm_latency=llm_latency,
        total_latency=total_lat,
        embedding_ms=embedding_ms,
        retrieval_ms=retrieval_ms,
        prompt_ms=prompt_ms,
        llm_ms=llm_ms,
        citation_ms=citation_ms,
        database_ms=database_ms,
        total_ms=total_ms,
    )
