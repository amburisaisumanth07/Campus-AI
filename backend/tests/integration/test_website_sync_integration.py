"""
Integration test for full website crawl, change detection, document creation, and citation generation.
"""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
import httpx

from backend.app.db.models import (
    User,
    Role,
    WebsiteSource,
    WebsiteSyncHistory,
    WebsiteSourceStatus,
    SyncStatus,
    Document,
    SourceType,
)
from backend.app.services.crawler_service import synchronize_website_source
from backend.app.rag.chunking import chunk_document_pages
from backend.app.rag.citations import build_citation


def test_website_sync_and_change_detection(db):
    # 1. Create Admin User
    admin = User(
        email="admin_sync_test@college.edu",
        name="Sync Admin",
        password_hash="fakehash",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # 2. Create WebsiteSource
    source = WebsiteSource(
        name="Engineering College Portal",
        base_url="https://engineering.college.edu",
        allowed_domains="engineering.college.edu",
        active=True,
        sync_interval="6h",
        max_pages=10,
        status=WebsiteSourceStatus.IDLE,
        created_by_id=admin.id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # 3. Setup mock HTML responses
    html_home = """
    <!DOCTYPE html>
    <html>
      <head><title>Engineering College Home</title></head>
      <body>
        <h1>Welcome to Engineering College</h1>
        <p>The academic semester begins on August 1st, 2026.</p>
        <a href="/circulars/exam_schedule.html">Exam Circular</a>
      </body>
    </html>
    """

    html_exam = """
    <!DOCTYPE html>
    <html>
      <head><title>Exam Circular 2026</title></head>
      <body>
        <h1>Midterm Examination Timetable</h1>
        <p>Midterm examinations will commence on October 15, 2026 for all departments.</p>
      </body>
    </html>
    """

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "robots.txt" in url:
            resp.text = "User-agent: *\nAllow: /"
            resp.headers = {"content-type": "text/plain"}
        elif url.endswith("exam_schedule.html"):
            resp.text = html_exam
            resp.headers = {"content-type": "text/html"}
        else:
            resp.text = html_home
            resp.headers = {"content-type": "text/html"}
        return resp

    with patch("httpx.Client.get", side_effect=mock_get):
        with patch("backend.app.services.crawler_service.index_document", return_value=1) as mock_index:
            # 4. First Crawl (Initial Add)
            history1 = synchronize_website_source(db, source.id)
            assert history1.status == SyncStatus.SUCCESS
            assert history1.documents_discovered == 2
            assert history1.documents_added == 2
            assert history1.documents_updated == 0
            assert history1.documents_unchanged == 0
            assert mock_index.call_count == 2

    # Verify documents saved in DB with source_type and source_url
    docs = db.query(Document).filter(Document.website_source_id == source.id).all()
    assert len(docs) == 2
    for doc in docs:
        assert doc.source_type == SourceType.OFFICIAL_WEBSITE
        assert doc.source_url is not None
        assert doc.source_hash is not None
        assert "engineering.college.edu" in doc.source_url

    # 5. Second Crawl (Content Unchanged)
    with patch("httpx.Client.get", side_effect=mock_get):
        with patch("backend.app.services.crawler_service.index_document") as mock_index_unchanged:
            history2 = synchronize_website_source(db, source.id)
            assert history2.status == SyncStatus.SUCCESS
            assert history2.documents_discovered == 2
            assert history2.documents_added == 0
            assert history2.documents_updated == 0
            assert history2.documents_unchanged == 2
            assert mock_index_unchanged.call_count == 0

    # 6. Verify Citations & Chunking include source_type and source_url
    sample_doc = docs[0]
    chunks = chunk_document_pages(
        pages=[{"page_number": 1, "text_content": "Midterm examinations will commence on October 15, 2026."}],
        document_id=sample_doc.id,
        document_version_id=1,
        title=sample_doc.title,
        source_type="OFFICIAL_WEBSITE",
        source_url=sample_doc.source_url,
    )
    assert len(chunks) == 1
    assert chunks[0].metadata["source_type"] == "OFFICIAL_WEBSITE"
    assert chunks[0].metadata["source_url"] == sample_doc.source_url

    citation = build_citation(chunks[0].to_dict())
    assert citation["source_type"] == "OFFICIAL_WEBSITE"
    assert citation["source_url"] == sample_doc.source_url
    assert citation["title"] == sample_doc.title
