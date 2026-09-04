"""
Pydantic schemas for conversations, messages, and feedback.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    message_id: int
    rating: str = Field(..., pattern="^(thumbs_up|thumbs_down)$")
    comment: Optional[str] = Field(None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: int
    message_id: int
    user_id: int
    rating: str
    comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Citations ─────────────────────────────────────────────────────────────────

class SourceCitation(BaseModel):
    document_id: Optional[int] = None
    document_version_id: Optional[int] = None
    title: Optional[str] = None
    document_type: Optional[str] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None
    page_number: Optional[int] = None
    source_pages: List[int] = Field(default_factory=list)
    snippet: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None


class CitationItem(BaseModel):
    doc_id: Optional[int] = None
    document_id: Optional[int] = None
    document_version_id: Optional[int] = None
    title: Optional[str] = None
    document_type: Optional[str] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None
    page_number: Optional[int] = None
    source_pages: List[int] = Field(default_factory=list)
    snippet: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    citations: Optional[List[CitationItem]] = None
    feedback: Optional[FeedbackResponse] = None
    retrieval_latency: Optional[float] = None
    llm_latency: Optional[float] = None
    total_latency: Optional[float] = None
    embedding_ms: Optional[float] = None
    retrieval_ms: Optional[float] = None
    prompt_ms: Optional[float] = None
    llm_ms: Optional[float] = None
    citation_ms: Optional[float] = None
    database_ms: Optional[float] = None
    total_ms: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Conversations ─────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str = Field("New Chat", max_length=500)


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: List[ConversationResponse]
    total: int


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    conversation_id: Optional[int] = None   # None → create new conversation
    message: Optional[str] = None           # query string ("message" or "content")
    content: Optional[str] = None           # query string ("content" or "message")
    department: Optional[str] = None        # optional metadata filter for RAG
    academic_year: Optional[str] = None     # optional metadata filter for RAG

    @model_validator(mode="after")
    def validate_query(self) -> "ChatMessageRequest":
        text = (self.message or self.content or "").strip()
        if not text:
            raise ValueError("Either 'message' or 'content' must be a non-empty string.")
        if len(text) > 4000:
            raise ValueError("Message content exceeds maximum length of 4000 characters.")
        return self

    def get_query_text(self) -> str:
        return (self.message or self.content or "").strip()


class ChatMessageResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    grounded: bool
    retrieval_count: int
    sources: List[SourceCitation] = Field(default_factory=list)
    user_message: Optional[MessageResponse] = None
    assistant_message: Optional[MessageResponse] = None
    retrieval_error: bool = False
    generation_error: bool = False
    status: str = "SUCCESS"
    retrieval_latency: Optional[float] = None
    llm_latency: Optional[float] = None
    total_latency: Optional[float] = None
    embedding_ms: Optional[float] = None
    retrieval_ms: Optional[float] = None
    prompt_ms: Optional[float] = None
    llm_ms: Optional[float] = None
    citation_ms: Optional[float] = None
    database_ms: Optional[float] = None
    total_ms: Optional[float] = None

