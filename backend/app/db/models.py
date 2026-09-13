import enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    DateTime, String, Boolean, Integer, BigInteger, Text,
    ForeignKey, Enum as SAEnum, sql, Float
)


class Base(DeclarativeBase):
    pass


# ── Auth enums ────────────────────────────────────────────────────────────────

class Role(str, enum.Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


# ── Document enums ────────────────────────────────────────────────────────────

class DocumentType(str, enum.Enum):
    REGULATION = "regulation"
    ACADEMIC_CALENDAR = "academic_calendar"
    EXAMINATION = "examination"
    ATTENDANCE = "attendance"
    PLACEMENT = "placement"
    SCHOLARSHIP = "scholarship"
    COURSE = "course"
    NOTICE = "notice"
    DEPARTMENT_DOCUMENT = "department_document"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class SourceType(str, enum.Enum):
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    OFFICIAL_WEBSITE = "OFFICIAL_WEBSITE"


class WebsiteSourceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    SYNCING = "SYNCING"
    QUEUED = "QUEUED"
    CRAWLING = "CRAWLING"
    VALIDATING = "VALIDATING"
    CHANGED = "CHANGED"
    INDEXING = "INDEXING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class SyncStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"
    QUEUED = "QUEUED"
    CRAWLING = "CRAWLING"
    VALIDATING = "VALIDATING"
    INDEXING = "INDEXING"


# ── Chat enums ────────────────────────────────────────────────────────────────

class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class FeedbackRating(str, enum.Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


# ── Models ────────────────────────────────────────────────────────────────────

class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(default="healthy")
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role, name="user_role"), nullable=False, default=Role.STUDENT)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        onupdate=sql.func.now()
    )

    # Relationships
    uploaded_documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="uploader", foreign_keys="Document.uploaded_by_id"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )
    website_sources: Mapped[List["WebsiteSource"]] = relationship(
        "WebsiteSource", back_populates="creator", foreign_keys="WebsiteSource.created_by_id"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)  # sanitized display name
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"), nullable=False
    )
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.UPLOADED
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("document_versions.id", use_alter=True, name="fk_doc_active_version"),
        nullable=True
    )
    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, name="source_type"), nullable=False, default=SourceType.MANUAL_UPLOAD
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    website_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("website_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    discovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        onupdate=sql.func.now()
    )

    # Relationships
    uploader: Mapped["User"] = relationship("User", back_populates="uploaded_documents", foreign_keys=[uploaded_by_id])
    website_source: Mapped[Optional["WebsiteSource"]] = relationship(
        "WebsiteSource", back_populates="documents", foreign_keys=[website_source_id]
    )
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document",
        primaryjoin="Document.id == DocumentVersion.document_id",
        foreign_keys="DocumentVersion.document_id",
        cascade="all, delete-orphan"
    )
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # absolute path, never returned to clients
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 hex
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="versions", foreign_keys=[document_id]
    )
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="version", cascade="all, delete-orphan"
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    version: Mapped["DocumentVersion"] = relationship("DocumentVersion", back_populates="pages")


# ── Chat models ───────────────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="New Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        onupdate=sql.func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(MessageRole, name="message_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON-encoded list of citations: [{doc_id, title, page_number, snippet}]
    citations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    feedback: Mapped[Optional["Feedback"]] = relationship(
        "Feedback", back_populates="message", uselist=False, cascade="all, delete-orphan"
    )


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id"), nullable=False, unique=True, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    rating: Mapped[FeedbackRating] = mapped_column(
        SAEnum(FeedbackRating, name="feedback_rating"), nullable=False
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="feedback")
    user: Mapped["User"] = relationship("User", back_populates="feedbacks")


# ── Website Source models ─────────────────────────────────────────────────────

class WebsiteSource(Base):
    __tablename__ = "website_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    allowed_domains: Mapped[str] = mapped_column(String(1000), nullable=False)  # comma-separated
    allowed_paths: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # comma-separated
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_interval: Mapped[str] = mapped_column(String(20), nullable=False, default="6h")  # 1h, 6h, 12h, 24h
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_scheduled_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=WebsiteSourceStatus.IDLE.value
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        onupdate=sql.func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="website_sources", foreign_keys=[created_by_id])
    sync_history: Mapped[List["WebsiteSyncHistory"]] = relationship(
        "WebsiteSyncHistory", back_populates="source", cascade="all, delete-orphan",
        order_by="WebsiteSyncHistory.started_at.desc()"
    )
    change_reviews: Mapped[List["SyncChangeReview"]] = relationship(
        "SyncChangeReview", back_populates="source", cascade="all, delete-orphan",
        order_by="SyncChangeReview.created_at.desc()"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="website_source", foreign_keys="Document.website_source_id"
    )


class WebsiteSyncHistory(Base):
    __tablename__ = "website_sync_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("website_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sql.func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SyncStatus.IN_PROGRESS.value
    )
    documents_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_url_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    source: Mapped["WebsiteSource"] = relationship("WebsiteSource", back_populates="sync_history")


class SyncChangeReview(Base):
    __tablename__ = "sync_change_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("website_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    history_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("website_sync_history.id", ondelete="SET NULL"), nullable=True, index=True
    )
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, default="document")  # document, announcement, department, calendar, etc.
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, default="NEW")  # NEW, UPDATED, REMOVED, INVALID_URL, FAILED
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING_REVIEW", index=True)  # PENDING_REVIEW, APPROVED, REJECTED
    previous_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=200)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql.func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now()
    )

    # Relationships
    source: Mapped["WebsiteSource"] = relationship("WebsiteSource", back_populates="change_reviews")
    history: Mapped[Optional["WebsiteSyncHistory"]] = relationship("WebsiteSyncHistory")
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])


# ── MITS Entity Models ────────────────────────────────────────────────────────

class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="General", index=True)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, default="MITS Official Portal")
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=200)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())


class AcademicCalendarEvent(Base):
    __tablename__ = "academic_calendar"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    academic_year: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="2026-2027")
    program: Mapped[str] = mapped_column(String(100), nullable=False, index=True, default="B.Tech")
    year: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # I Year, II Year, III Year, IV Year
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # I Semester, II Semester
    event_name: Mapped[str] = mapped_column(String(500), nullable=False)
    event_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, default="MITS Academic Section")
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=200)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())


class Examination(Base):
    __tablename__ = "examinations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="notification")
    program: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="B.Tech")
    year: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    exam_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, default="MITS Examination Cell")
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=200)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    school: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hod: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hod_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hod_designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hod_profile_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    hod_source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    hod_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    hod_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True
    )
    school_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("schools.id", ondelete="SET NULL"), nullable=True
    )
    hod_person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("people.id", ondelete="SET NULL"), nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    faculty: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or formatted text
    programs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or text
    courses: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or text
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=200)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())

    # Relationships
    school_rel: Mapped[Optional["School"]] = relationship("School", back_populates="departments", foreign_keys=[school_id])
    hod_person: Mapped[Optional["Person"]] = relationship("Person", foreign_keys=[hod_person_id])
    programs_list: Mapped[List["Program"]] = relationship("Program", back_populates="department_rel", cascade="all, delete-orphan")


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    research_interests: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, default="https://mits.ac.in/faculty-information")
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())

    # Relationships
    person: Mapped[Optional["Person"]] = relationship("Person", foreign_keys=[person_id])
    department_rel: Mapped[Optional["Department"]] = relationship("Department", foreign_keys=[department_id])


class Placement(Base):
    __tablename__ = "placements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    drive_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    eligibility: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    package_details: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())


class CollegeInfo(Base):
    __tablename__ = "college_info"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())


class ImportantLink(Base):
    __tablename__ = "important_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="portals")
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())


# ── Structured College Knowledge Models ───────────────────────────────────────

class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Dr., Prof., Sri, etc.
    designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())

    # Relationships
    leadership_roles: Mapped[List["Leadership"]] = relationship("Leadership", back_populates="person", cascade="all, delete-orphan")


class RoleRecord(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="GENERAL")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Leadership(Base):
    __tablename__ = "leadership"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True)
    role_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # CHANCELLOR, VC, REGISTRAR, PRINCIPAL, DEAN, etc.
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    term_start: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    term_end: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())

    # Relationships
    person: Mapped["Person"] = relationship("Person", back_populates="leadership_roles")


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # COMPUTING, ENGINEERING, MANAGEMENT, SCIENCE_HUMANITIES
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dean_person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())

    # Relationships
    dean_person: Mapped[Optional["Person"]] = relationship("Person", foreign_keys=[dean_person_id])
    departments: Mapped[List["Department"]] = relationship("Department", back_populates="school_rel")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # BTECH_CSE, BTECH_ECE, MTECH_CSE, MBA, MCA, PHD
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    degree_level: Mapped[str] = mapped_column(String(50), nullable=False, default="UG", index=True)  # UG, PG, PHD, DIPLOMA
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    eligibility: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intake: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    regulations_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # R20, R25
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())

    # Relationships
    department_rel: Mapped[Optional["Department"]] = relationship("Department", back_populates="programs_list")


class FacultyDepartment(Base):
    __tablename__ = "faculty_department"

    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Committee(Base):
    __tablename__ = "committees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # ACADEMIC_COUNCIL, BOS_CSE, ANTI_RAGGING, ICC, GRIEVANCE
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="STATUTORY")  # STATUTORY, ACADEMIC, WELFARE, ANTI_RAGGING, GRIEVANCE
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meeting_frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now(), onupdate=sql.func.now())

    # Relationships
    members: Mapped[List["CommitteeMember"]] = relationship("CommitteeMember", back_populates="committee", cascade="all, delete-orphan")


class CommitteeMember(Base):
    __tablename__ = "committee_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    committee_id: Mapped[int] = mapped_column(ForeignKey("committees.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    role_in_committee: Mapped[str] = mapped_column(String(100), nullable=False, default="Member")  # Chairperson, Member Secretary, Member
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())

    # Relationships
    committee: Mapped["Committee"] = relationship("Committee", back_populates="members")
    person: Mapped["Person"] = relationship("Person")


class Cell(Base):
    __tablename__ = "cells"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # NSS, NCC, INNOVATION, PLACEMENT, WOMEN_CELL, COUNSELLING
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="STUDENT_SUPPORT")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())

    # Relationships
    coordinators: Mapped[List["CellCoordinator"]] = relationship("CellCoordinator", back_populates="cell", cascade="all, delete-orphan")


class CellCoordinator(Base):
    __tablename__ = "cell_coordinators"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cell_id: Mapped[int] = mapped_column(ForeignKey("cells.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="Coordinator")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    cell: Mapped["Cell"] = relationship("Cell", back_populates="coordinators")
    person: Mapped["Person"] = relationship("Person")


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="GENERAL")  # LIBRARY, HOSTEL, TRANSPORT, SPORTS, CANTEEN, MEDICAL, COUNSELLING
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timings: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"), nullable=True)
    rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())

    # Relationships
    contact_person: Mapped[Optional["Person"]] = relationship("Person")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    department_or_unit: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_or_purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())

    # Relationships
    person: Mapped[Optional["Person"]] = relationship("Person")


class AdmissionRule(Base):
    __tablename__ = "admissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    program_id: Mapped[Optional[int]] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=True, index=True)
    academic_year: Mapped[str] = mapped_column(String(50), nullable=False, default="2026-2027", index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="GENERAL")  # CONVENOR_QUOTA, MANAGEMENT_QUOTA, NRI_INTERNATIONAL, LATERAL_ENTRY
    eligibility_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    application_process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fee_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entrance_exam: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # EAPCET, ICET, PGECET, GATE
    intake: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scholarship_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())

    # Relationships
    program: Mapped[Optional["Program"]] = relationship("Program")


class AcademicRule(Base):
    __tablename__ = "academic_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # ATTENDANCE, GRADING, PROMOTION, DETENTION, CONDONATION, SGPA_CALCULATION, CGPA_CALCULATION
    regulation_code: Mapped[str] = mapped_column(String(50), nullable=False, default="R20", index=True)  # R20, R25, AUTONOMOUS
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g. 75.0, 65.0, 40.0
    penalties_or_remedies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())


class ExamRule(Base):
    __tablename__ = "examination_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # EVALUATION, REVALUATION, RECOUNTING, MALPRACTICE, SUPPLEMENTARY, ATTENDANCE_ELIGIBILITY
    regulation_code: Mapped[str] = mapped_column(String(50), nullable=False, default="R20")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    see_weightage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g. 60.0 or 70.0
    cie_weightage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g. 40.0 or 30.0
    min_pass_marks: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    revaluation_deadline_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())


class PlacementData(Base):
    __tablename__ = "placement_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    academic_year: Mapped[str] = mapped_column(String(50), nullable=False, default="2026-2027", index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    package_lpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tier_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # CORE, PRODUCT, TIER1, DREAM, SUPER_DREAM
    role_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    eligibility_cgpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eligible_branches: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    process_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_offers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())


class InstitutionHistory(Base):
    __tablename__ = "institution_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    milestone_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="MILESTONE")  # FOUNDATION, AUTONOMY, NAAC, NBA, NIRF, DEEMED_UNIVERSITY
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql.func.now())

