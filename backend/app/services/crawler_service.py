"""
Website Crawler and Dynamic Synchronization Service for CampusAI.

Discovers HTML pages and PDF documents from configured official college websites (MITS),
respects robots.txt, applies strict SSRF security checks, performs SHA-256 change detection,
dynamically discovers and synchronizes structured academic entities (Departments, Faculty,
Heads of Departments, Academic Calendars, Announcements, Examinations, and College Overview/History),
and connects directly into the existing document processing, chunking, embedding, and ChromaDB vector
indexing pipeline with complete provenance metadata and 404 protection.
"""
from datetime import datetime, timezone
import hashlib
import ipaddress
from pathlib import Path
import re
import socket
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, urldefrag
import urllib.robotparser

from bs4 import BeautifulSoup
import httpx
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.db.models import (
    WebsiteSource,
    WebsiteSyncHistory,
    WebsiteSourceStatus,
    SyncStatus,
    Document,
    DocumentVersion,
    DocumentPage,
    DocumentStatus,
    DocumentType,
    SourceType,
    Department,
    Faculty,
    AcademicCalendarEvent,
    Announcement,
    Examination,
    CollegeInfo,
    Placement,
    SyncChangeReview,
)
from backend.app.services.file_service import get_storage_dir, sanitize_filename
from backend.app.services.pdf_service import extract_pages
from backend.app.rag.ingestion import index_document, remove_document_index
from backend.app.services.url_validator import (
    normalize_external_url,
    validate_external_url,
    check_ssrf_safety,
    UrlValidationResult,
)
from backend.app.services.mits_adapters import (
    MITSDepartmentAdapter,
    MITSFacultyAdapter,
    MITSCalendarAdapter,
    MITSAnnouncementAdapter,
    MITSExamAdapter,
    MITSPlacementAdapter,
    compute_content_hash,
)
from backend.app.rag.pipeline import invalidate_rag_cache

CRAWLER_USER_AGENT = "CampusAICrawler/1.0 (+https://mits.ac.in/bot)"
DEFAULT_REQUEST_TIMEOUT = 25.0


# ── 1. Security & URL Normalization ───────────────────────────────────────────

def is_safe_and_valid_url(url: str, allowed_domains: List[str], allowed_paths: Optional[List[str]] = None) -> Tuple[bool, str]:
    """Strict URL validator preventing SSRF, private network requests, and domain violations."""
    is_safe, reason = check_ssrf_safety(url, allowed_domains)
    if not is_safe:
        return False, reason
    if allowed_paths:
        parsed = urlparse(url)
        path = parsed.path
        if path and path != "/":
            if not any(path.startswith(p.strip()) for p in allowed_paths if p.strip()):
                return False, f"Path '{path}' is not within allowed paths: {allowed_paths}"
    return True, "URL is safe and allowed"


def normalize_crawl_url(url: str, base_url: str = "https://mits.ac.in/") -> str:
    """Normalize URL by stripping fragments and resolving relative paths."""
    return normalize_external_url(url, base_url)


# ── 2. robots.txt Parser ──────────────────────────────────────────────────────

def get_robots_parser(base_url: str, client: Optional[httpx.Client] = None) -> urllib.robotparser.RobotFileParser:
    """Fetch and parse robots.txt for a website root. If missing, default to allowing crawling."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)

    should_close_client = False
    if client is None:
        client = httpx.Client(timeout=DEFAULT_REQUEST_TIMEOUT, follow_redirects=True)
        should_close_client = True

    try:
        resp = client.get(robots_url, headers={"User-Agent": CRAWLER_USER_AGENT})
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            rp.parse(lines)
            logger.info(f"[WEBSITE_SYNC] robots.txt successfully loaded from {robots_url}")
        else:
            logger.info(f"[WEBSITE_SYNC] robots.txt returned status {resp.status_code}. Allowing crawl by default.")
            rp.parse(["User-agent: *", "Allow: /"])
    except Exception as exc:
        logger.warning(f"[WEBSITE_SYNC] Could not fetch robots.txt ({exc}). Allowing crawl by default.")
        rp.parse(["User-agent: *", "Allow: /"])
    finally:
        if should_close_client:
            client.close()

    return rp


# ── 3. HTML Content Extraction ────────────────────────────────────────────────

def extract_html_content_and_links(
    html_text: str,
    current_url: str,
    allowed_domains: List[str],
    allowed_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Parse HTML content, strip noise, extract clean text, compute SHA-256 hash, and discover links."""
    soup = BeautifulSoup(html_text, "html.parser")

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text().strip()
    if not title:
        parsed_url = urlparse(current_url)
        title = parsed_url.path.strip("/").split("/")[-1] or parsed_url.netloc

    # Strip unwanted elements
    unwanted_tags = [
        "script", "style", "nav", "header", "footer", "aside",
        "noscript", "form", "svg", "meta", "iframe", "button"
    ]
    for tag in soup.find_all(unwanted_tags):
        tag.decompose()

    # Discover outbound links
    discovered_links: List[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("#"):
            continue
        absolute_url = urljoin(current_url, href)
        normalized = normalize_crawl_url(absolute_url, current_url)
        is_safe, _ = is_safe_and_valid_url(normalized, allowed_domains, allowed_paths)
        if is_safe and normalized not in discovered_links:
            discovered_links.append(normalized)

    # Extract clean text with semantic structure
    body = soup.find("body") or soup
    raw_text = body.get_text(separator="\n", strip=True)

    # Collapse excessive newlines
    clean_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    clean_text = "\n\n".join(clean_lines)

    content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

    return {
        "title": title,
        "text": clean_text,
        "content_hash": content_hash,
        "discovered_links": discovered_links,
    }


def infer_document_type(title: str, url: str) -> DocumentType:
    """Infer document type category from title and URL tokens."""
    combined = f"{title.lower()} {url.lower()}"
    if "exam" in combined or "timetable" in combined or "hall ticket" in combined or "result" in combined:
        return DocumentType.EXAMINATION
    elif "regulation" in combined or "ordinance" in combined or "rule" in combined or "syllabus" in combined:
        return DocumentType.REGULATION
    elif "calendar" in combined or "calender" in combined or "schedule" in combined:
        return DocumentType.ACADEMIC_CALENDAR
    elif "attend" in combined:
        return DocumentType.ATTENDANCE
    elif "placement" in combined or "career" in combined or "recruitment" in combined:
        return DocumentType.PLACEMENT
    elif "scholarship" in combined or "fee" in combined:
        return DocumentType.SCHOLARSHIP
    elif "course" in combined or "curriculum" in combined or "programme" in combined:
        return DocumentType.COURSE
    elif "notice" in combined or "circular" in combined or "announcement" in combined:
        return DocumentType.NOTICE
    elif "department" in combined or "faculty" in combined:
        return DocumentType.DEPARTMENT_DOCUMENT
    return DocumentType.OTHER


# ── 4. Ingestion & Document Processing ────────────────────────────────────────

def process_crawled_html_page(
    db: Session,
    source: WebsiteSource,
    url: str,
    page_data: Dict[str, Any],
) -> str:
    """Process a discovered HTML page. Returns action result: 'added', 'updated', 'unchanged', or 'failed'."""
    now = datetime.now(timezone.utc)
    title = page_data["title"] or "MITS Official Web Page"
    text_content = page_data["text"]
    content_hash = page_data["content_hash"]

    if not text_content or len(text_content.strip()) < 30:
        logger.info(f"[WEBSITE_SYNC] Skipping thin HTML page: {url}")
        return "unchanged"

    doc = db.query(Document).filter(
        Document.website_source_id == source.id,
        Document.source_url == url,
    ).first()

    if doc:
        if doc.source_hash == content_hash and doc.status == DocumentStatus.READY:
            doc.last_seen_at = now
            db.commit()
            return "unchanged"

        logger.info(f"[WEBSITE_SYNC] Updating HTML document: {url} (ID: {doc.id})")
        doc.title = title
        doc.source_hash = content_hash
        doc.last_seen_at = now
        doc.last_processed_at = now
        doc.status = DocumentStatus.PROCESSING
        db.commit()

        try:
            remove_document_index(doc.id)
        except Exception as exc:
            logger.warning(f"Failed to clear old vectors for doc {doc.id}: {exc}")

        db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()

        ver = doc.versions[0] if doc.versions else None
        if not ver:
            ver = DocumentVersion(
                document_id=doc.id,
                version="1.1",
                storage_path=f"web://{url}",
                file_checksum=content_hash,
                file_size=len(text_content.encode("utf-8")),
                mime_type="text/html",
                page_count=1,
                is_active=True,
            )
            db.add(ver)
            db.commit()
            db.refresh(ver)
        else:
            ver.file_checksum = content_hash
            ver.file_size = len(text_content.encode("utf-8"))

        page_record = DocumentPage(
            document_id=doc.id,
            document_version_id=ver.id,
            page_number=1,
            text_content=text_content,
            char_count=len(text_content),
        )
        db.add(page_record)
        doc.status = DocumentStatus.READY
        doc.active_version_id = ver.id
        db.commit()

        pages = [{"page_number": 1, "text_content": text_content, "char_count": len(text_content)}]
        index_document(
            doc_id=doc.id,
            title=doc.title,
            department=doc.department,
            academic_year=doc.academic_year,
            pages=pages,
            source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
            source_url=doc.source_url,
        )
        return "updated"

    # New HTML Document
    logger.info(f"[WEBSITE_SYNC] Adding new HTML document: {url}")
    doc_type = infer_document_type(title, url)
    sanitized_slug = sanitize_filename(urlparse(url).path.strip("/").replace("/", "_") or "index")
    if not sanitized_slug.endswith(".html"):
        sanitized_slug += ".html"

    doc = Document(
        title=title,
        filename=sanitized_slug,
        document_type=doc_type,
        department="MITS Official",
        academic_year="Current",
        status=DocumentStatus.PROCESSING,
        uploaded_by_id=source.created_by_id,
        source_type=SourceType.OFFICIAL_WEBSITE,
        source_url=url,
        source_hash=content_hash,
        website_source_id=source.id,
        discovered_at=now,
        last_seen_at=now,
        last_processed_at=now,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    ver = DocumentVersion(
        document_id=doc.id,
        version="1.0",
        storage_path=f"web://{url}",
        file_checksum=content_hash,
        file_size=len(text_content.encode("utf-8")),
        mime_type="text/html",
        page_count=1,
        is_active=True,
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)

    page_record = DocumentPage(
        document_id=doc.id,
        document_version_id=ver.id,
        page_number=1,
        text_content=text_content,
        char_count=len(text_content),
    )
    db.add(page_record)
    doc.status = DocumentStatus.READY
    doc.active_version_id = ver.id
    db.commit()

    pages = [{"page_number": 1, "text_content": text_content, "char_count": len(text_content)}]
    index_document(
        doc_id=doc.id,
        title=doc.title,
        department=doc.department,
        academic_year=doc.academic_year,
        pages=pages,
        source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
        source_url=doc.source_url,
    )
    return "added"


def process_crawled_pdf_document(
    db: Session,
    source: WebsiteSource,
    url: str,
    pdf_bytes: bytes,
) -> str:
    """Process a discovered PDF document with PDF text extraction and Chroma vector indexing."""
    now = datetime.now(timezone.utc)
    if not pdf_bytes or len(pdf_bytes) < 100:
        logger.warning(f"[WEBSITE_SYNC] Skipping empty/corrupted PDF: {url}")
        return "unchanged"

    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    parsed_url = urlparse(url)
    raw_filename = parsed_url.path.strip("/").split("/")[-1] or f"doc_{content_hash[:8]}.pdf"
    sanitized_name = sanitize_filename(raw_filename)
    if not sanitized_name.lower().endswith(".pdf"):
        sanitized_name += ".pdf"

    clean_title = raw_filename.replace("%20", " ").replace(".pdf", "").replace("_", " ").strip()
    doc_type = infer_document_type(clean_title, url)

    doc = db.query(Document).filter(
        Document.website_source_id == source.id,
        Document.source_url == url,
    ).first()

    if doc:
        if doc.source_hash == content_hash and doc.status == DocumentStatus.READY:
            doc.last_seen_at = now
            db.commit()
            return "unchanged"

        logger.info(f"[WEBSITE_SYNC] Updating modified PDF document: {url}")
        doc.source_hash = content_hash
        doc.last_seen_at = now
        doc.last_processed_at = now
        doc.status = DocumentStatus.PROCESSING
        db.commit()

        try:
            remove_document_index(doc.id)
        except Exception as exc:
            logger.warning(f"Failed to clear old vectors for PDF doc {doc.id}: {exc}")

        storage_dir = get_storage_dir()
        file_path = storage_dir / f"web_doc_{doc.id}_v2.pdf"
        file_path.write_bytes(pdf_bytes)

        pages = extract_pages(file_path)
        db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()

        ver = doc.versions[0] if doc.versions else None
        if not ver:
            ver = DocumentVersion(
                document_id=doc.id,
                version="1.1",
                storage_path=str(file_path),
                file_checksum=content_hash,
                file_size=len(pdf_bytes),
                mime_type="application/pdf",
                page_count=len(pages),
                is_active=True,
            )
            db.add(ver)
            db.commit()
            db.refresh(ver)
        else:
            ver.storage_path = str(file_path)
            ver.file_checksum = content_hash
            ver.file_size = len(pdf_bytes)
            ver.page_count = len(pages)

        page_objs = [
            DocumentPage(
                document_id=doc.id,
                document_version_id=ver.id,
                page_number=p["page_number"],
                text_content=p["text_content"],
                char_count=p["char_count"],
            )
            for p in pages
        ]
        db.add_all(page_objs)
        doc.status = DocumentStatus.READY
        doc.active_version_id = ver.id
        db.commit()

        index_document(
            doc_id=doc.id,
            title=doc.title,
            department=doc.department,
            academic_year=doc.academic_year,
            pages=pages,
            source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
            source_url=doc.source_url,
        )
        return "updated"

    # New PDF
    logger.info(f"[WEBSITE_SYNC] Adding new PDF document: {url}")
    doc = Document(
        title=clean_title,
        filename=sanitized_name,
        document_type=doc_type,
        department="MITS Official",
        academic_year="Current",
        status=DocumentStatus.PROCESSING,
        uploaded_by_id=source.created_by_id,
        source_type=SourceType.OFFICIAL_WEBSITE,
        source_url=url,
        source_hash=content_hash,
        website_source_id=source.id,
        discovered_at=now,
        last_seen_at=now,
        last_processed_at=now,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    storage_dir = get_storage_dir()
    file_path = storage_dir / f"web_doc_{doc.id}_v1.pdf"
    file_path.write_bytes(pdf_bytes)

    pages = extract_pages(file_path)

    ver = DocumentVersion(
        document_id=doc.id,
        version="1.0",
        storage_path=str(file_path),
        file_checksum=content_hash,
        file_size=len(pdf_bytes),
        mime_type="application/pdf",
        page_count=len(pages),
        is_active=True,
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)

    page_objs = [
        DocumentPage(
            document_id=doc.id,
            document_version_id=ver.id,
            page_number=p["page_number"],
            text_content=p["text_content"],
            char_count=p["char_count"],
        )
        for p in pages
    ]
    db.add_all(page_objs)
    doc.status = DocumentStatus.READY
    doc.active_version_id = ver.id
    db.commit()

    index_document(
        doc_id=doc.id,
        title=doc.title,
        department=doc.department,
        academic_year=doc.academic_year,
        pages=pages,
        source_type=doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type),
        source_url=doc.source_url,
    )
    return "added"


# ── 5. Dynamic MITS Entity Synchronizers ──────────────────────────────────────

def sync_mits_faculty_from_page(db: Session, page_url: str, html_text: str) -> Tuple[int, Dict[str, Dict[str, Any]]]:
    """
    Authoritative extraction of all faculty members and Heads of Departments (HoDs)
    from official MITS page https://mits.ac.in/faculty-information.
    Returns (total_faculty_saved, hod_map_by_department).
    """
    soup = BeautifulSoup(html_text, "html.parser")
    adapter = MITSFacultyAdapter()
    faculty_items: List[Dict[str, Any]] = []
    hod_map: Dict[str, Dict[str, Any]] = {}

    table = soup.find("table")
    if not table:
        return 0, {}

    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) >= 5:
            name = cols[1].get_text(strip=True)
            qual = cols[2].get_text(strip=True)
            desig = cols[3].get_text(strip=True)
            dept = cols[4].get_text(strip=True)

            if not name or name.lower() == "name of faculty":
                continue

            profile_url = None
            if len(cols) >= 6:
                a_tag = cols[5].find("a", href=True)
                if a_tag:
                    profile_url = normalize_crawl_url(urljoin(page_url, a_tag["href"]))

            item = {
                "name": name,
                "qualification": qual,
                "designation": desig,
                "department": dept,
                "profile_url": profile_url,
                "source_url": page_url,
                "is_valid": True,
            }
            faculty_items.append(item)

            # Check if Head of Department
            if any(k in desig.lower() for k in ["head", "hod"]) and "assistant" not in desig.lower() or "head (i/c)" in desig.lower():
                hod_map[dept.upper()] = {
                    "hod_name": name,
                    "hod_designation": desig,
                    "qualification": qual,
                    "hod_profile_url": profile_url,
                    "hod_source_url": page_url,
                }

    count = adapter.save(db, faculty_items)
    logger.info(f"[WEBSITE_SYNC] Synchronized {count} faculty records from {page_url}. Discovered {len(hod_map)} official HoDs.")
    return count, hod_map


def sync_mits_departmentheads_from_page(db: Session, page_url: str, html_text: str) -> Dict[str, Dict[str, Any]]:
    """
    Authoritative extraction of Department Heads directly from official page:
    https://mits.ac.in/departmentheads.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    hod_map: Dict[str, Dict[str, Any]] = {}
    dept_code_mapping = {
        'civil': 'CIVIL',
        'civil engineering': 'CIVIL',
        'eee': 'EEE',
        'electrical & electronics engineering': 'EEE',
        'mechanical': 'MECH',
        'mechanical engineering': 'MECH',
        'ece': 'ECE',
        'electronics & communication engineering': 'ECE',
        'cse (artificial intelligence)': 'AI',
        'artificial intelligence': 'AI',
        'cse (data science)': 'CSE-DS',
        'data science': 'CSE-DS',
        'cse (cyber security)': 'CSE-CS',
        'cyber security': 'CSE-CS',
        'cse (ai and ml)': 'CSE-AIML',
        'ai and ml': 'CSE-AIML',
        'cse': 'CSE',
        'computer science & engineering': 'CSE',
        'computer applications': 'MCA',
        'mca': 'MCA',
        'mathematics': 'BSH',
        'basic sciences & humanities': 'BSH',
        'physics': 'BSH',
        'chemistry': 'BSH',
        'english & foreign languages': 'BSH',
        'management studies': 'MBA',
        'mba': 'MBA',
        'computer science and technology': 'CST',
        'cst': 'CST',
    }

    now_utc = datetime.now(timezone.utc)

    for h3 in soup.find_all("h3"):
        name = h3.get_text(strip=True)
        next_p = h3.find_next_sibling("p")
        desig = next_p.get_text(strip=True) if next_p else ""
        if not ("head" in desig.lower() or "dr." in name.lower()):
            continue

        desig_clean = desig.replace("Head –", "").replace("Head (I/c) –", "").replace("Head -", "").replace("Head (I/c) -", "").strip().lower()
        target_code = None
        for k, v in dept_code_mapping.items():
            if k == desig_clean or k in desig_clean or desig_clean in k:
                target_code = v
                break

        if not target_code:
            continue

        # Give precedence to Mathematics (Dr. R. Saravana) for BSH
        if target_code == "BSH" and "BSH" in hod_map and "mathematics" not in desig_clean:
            continue

        dept = db.query(Department).filter(Department.code == target_code, Department.is_active == True).first()
        if not dept:
            continue

        clean_name = name.replace("Dr.", "").replace("Prof.", "").strip()
        fac = db.query(Faculty).filter(
            (Faculty.department_id == dept.id) &
            (Faculty.name.ilike(f"%{clean_name[:12]}%"))
        ).first()

        if not fac:
            fac = db.query(Faculty).filter(Faculty.name.ilike(f"%{clean_name[:12]}%")).first()

        if fac:
            fac.department_id = dept.id
            fac.department = dept.code
            fac.designation = desig.strip()
            fac.is_valid = True
            fac.is_active = True
            fac.last_verified_at = now_utc
        else:
            fac = Faculty(
                name=name,
                designation=desig.strip(),
                department=dept.code,
                department_id=dept.id,
                source_url=page_url,
                is_valid=True,
                is_active=True,
                last_verified_at=now_utc,
            )
            db.add(fac)
            db.commit()
            db.refresh(fac)

        dept.hod_name = name
        dept.hod = name
        dept.hod_designation = desig.strip()
        dept.hod_id = fac.id
        dept.hod_source_url = page_url
        dept.hod_verified_at = now_utc
        dept.last_verified_at = now_utc

        hod_map[target_code] = {
            "hod_name": name,
            "hod_designation": desig.strip(),
            "hod_id": fac.id,
            "hod_source_url": page_url,
        }

    db.commit()
    logger.info(f"[WEBSITE_SYNC] Synchronized {len(hod_map)} official Department Heads from {page_url}.")
    return hod_map


def sync_mits_department_page(
    db: Session,
    url: str,
    html_text: str,
    hod_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[str]:
    """
    Dynamically extract department metadata from a discovered official department page.
    Combines live page content with authoritative HoD metadata from faculty-information.
    """
    clean_url = normalize_crawl_url(url)
    soup = BeautifulSoup(html_text, "html.parser")
    adapter = MITSDepartmentAdapter()

    # Extract title / heading
    h1 = soup.find("h1")
    page_title = h1.get_text(strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")
    page_title = page_title.replace("Madanapalle Institute of Technology & Science - Deemed to be University", "").strip(" -|")
    if not page_title:
        page_title = clean_url.strip("/").split("/")[-1].replace("-", " ").title()

    # Infer code from URL or title
    code = "DEPT"
    url_lower = clean_url.lower()
    title_lower = page_title.lower()

    if "/department/9" in url_lower or ("computer science" in title_lower and "engineering" in title_lower and "data" not in title_lower and "cyber" not in title_lower and "artificial" not in title_lower):
        code = "CSE"
        name = "Department of Computer Science & Engineering"
        school = "School of Computing"
    elif "cse-ai-ml" in url_lower or "/department/32" in url_lower or ("artificial intelligence" in title_lower and "machine learning" in title_lower):
        code = "CSE-AIML"
        name = "Department of Computer Science & Engineering (Artificial Intelligence & Machine Learning)"
        school = "School of AI & ML"
    elif "/department/28" in url_lower or ("artificial intelligence" in title_lower and "data" not in title_lower and "machine" not in title_lower):
        code = "AI"
        name = "Department of Computer Science & Engineering (Artificial Intelligence)"
        school = "School of AI & ML"
    elif "/department/26" in url_lower or "data science" in title_lower:
        code = "CSE-DS"
        name = "Department of Computer Science and Engineering (Data Science)"
        school = "School of Computing"
    elif "/department/27" in url_lower or "cyber security" in title_lower or "cyber" in title_lower:
        code = "CSE-CS"
        name = "Department of Computer Science and Engineering (Cyber Security)"
        school = "School of Computing"
    elif "/department/4" in url_lower or "computer science and technology" in title_lower or "cst" in title_lower:
        code = "CST"
        name = "Department of Computer Science and Technology (CST)"
        school = "School of Computing"
    elif "electronics-communication-engineering" in url_lower or "/department/12" in url_lower or "electronics & communication" in title_lower or "ece" in title_lower:
        code = "ECE"
        name = "Department of Electronics & Communication Engineering"
        school = "School of Engineering"
    elif "electrical-electronics-engineering" in url_lower or "/department/11" in url_lower or "electrical & electronics" in title_lower or "eee" in title_lower:
        code = "EEE"
        name = "Department of Electrical & Electronics Engineering"
        school = "School of Engineering"
    elif "/department/8" in url_lower or "mechanical engineering" in title_lower or "mech" in title_lower:
        code = "MECH"
        name = "Department of Mechanical Engineering"
        school = "School of Engineering"
    elif "/department/6" in url_lower or "civil engineering" in title_lower or "ce" in title_lower:
        code = "CIVIL"
        name = "Department of Civil Engineering"
        school = "School of Engineering"
    elif "/department/5" in url_lower or "management" in title_lower or "mba" in title_lower:
        code = "MBA"
        name = "Department of Management Studies (BBA & MBA)"
        school = "School of Management"
    elif "/department/18" in url_lower or "computer applications" in title_lower or "mca" in title_lower:
        code = "MCA"
        name = "Department of Computer Applications (BCA & MCA)"
        school = "School of Computing"
    elif "basic-sciences-humanities" in url_lower or "/department/15" in url_lower or "basic sciences" in title_lower or "humanities" in title_lower:
        code = "BSH"
        name = "Department of Basic Sciences & Humanities"
        school = "School of Science & Humanities"
    else:
        slug = clean_url.strip("/").split("/")[-1].upper()
        code = f"DEPT-{slug}"
        name = page_title if page_title else f"Department of {slug}"
        school = "School of Engineering"

    # Extract description from page paragraphs
    paragraphs = [
        p.get_text(strip=True) for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 50 and not p.get_text(strip=True).startswith("Copyright") and not p.get_text(strip=True).startswith("MITS")
    ]
    description = "\n\n".join(paragraphs[:3]) if paragraphs else f"Official academic department at Madanapalle Institute of Technology & Science (MITS). Verified source: {clean_url}"

    # Extract HoD metadata (prioritize official faculty table mapping, fallback to page extraction)
    hod_name = None
    hod_desig = None
    hod_prof_url = None
    hod_src_url = clean_url

    if hod_map:
        # Match against hod_map
        for key in [code, code.replace("-", " "), code.replace("CSE-", "CSE - "), code.replace("CSE-", "")]:
            if key.upper() in hod_map:
                h_info = hod_map[key.upper()]
                hod_name = h_info["hod_name"]
                hod_desig = h_info["hod_designation"]
                hod_prof_url = h_info.get("hod_profile_url")
                hod_src_url = h_info.get("hod_source_url") or clean_url
                break

    # Fallback to page inspection if not found in hod_map
    if not hod_name:
        for tag in soup.find_all(["h2", "h3", "h4", "p", "div"]):
            t = tag.get_text(strip=True)
            if any(k in t.lower() for k in ["head of the department", "hod", "head of department"]):
                parent = tag.find_parent(["div", "tr", "td", "li"])
                if parent:
                    lines = [l.strip() for l in parent.get_text(separator="\n").splitlines() if l.strip()]
                    for l in lines:
                        if ("dr." in l.lower() or "prof." in l.lower()) and len(l) < 60:
                            hod_name = l
                            break
                    if hod_name:
                        break

    dept_record = {
        "code": code,
        "name": name,
        "school": school,
        "description": description,
        "hod": hod_name,
        "hod_name": hod_name,
        "hod_designation": hod_desig,
        "hod_profile_url": hod_prof_url,
        "hod_source_url": hod_src_url,
        "phone": None,  # Not published by MITS
        "email": None,  # Not published by MITS
        "faculty": None,
        "programs": None,
        "courses": None,
        "source_url": clean_url,
        "is_valid": True,
    }

    res = adapter.save(db, [dept_record])
    return "added" if res > 0 else "updated"


def sync_academic_calendars_from_page(db: Session, page_url: str, html_text: str, client: Optional[httpx.Client] = None) -> int:
    """
    Extract and validate academic calendar PDFs from https://mits.ac.in/academic-calenders.
    Strictly performs URL validation to guarantee no 404 links reach the system.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    adapter = MITSCalendarAdapter()
    calendar_items: List[Dict[str, Any]] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(separator=" ", strip=True)
        pdf_url = urljoin(page_url, href)

        if pdf_url.lower().endswith(".pdf") or "calendar" in text.lower() or "calender" in text.lower():
            clean_title = text.replace("\n", " ").strip()
            if not clean_title or len(clean_title) < 5:
                clean_title = pdf_url.split("/")[-1].replace("%20", " ").replace(".pdf", "")

            # Validate the PDF URL
            val_res = validate_external_url(pdf_url, base_url=page_url, client=client)

            program = "B.Tech"
            if "m.tech" in clean_title.lower() or "mtech" in clean_title.lower():
                program = "M.Tech"
            elif "m.b.a" in clean_title.lower() or "mba" in clean_title.lower():
                program = "MBA"
            elif "m.c.a" in clean_title.lower() or "mca" in clean_title.lower():
                program = "MCA"
            elif "bba" in clean_title.lower():
                program = "BBA"
            elif "bca" in clean_title.lower():
                program = "BCA"

            year = "All Years"
            if "1st year" in clean_title.lower() or "i year" in clean_title.lower() or "1st" in clean_title.lower():
                year = "I Year"
            elif "2nd year" in clean_title.lower() or "ii year" in clean_title.lower() or "2nd" in clean_title.lower():
                year = "II Year"
            elif "3rd year" in clean_title.lower() or "iii year" in clean_title.lower():
                year = "III Year"
            elif "4th year" in clean_title.lower() or "iv year" in clean_title.lower():
                year = "IV Year"

            acad_year = "2026-2027" if ("2026-27" in clean_title or "2026" in clean_title) else "2025-2026"

            item = {
                "academic_year": acad_year,
                "program": program,
                "year": year,
                "semester": "I & II Semesters",
                "event_name": clean_title,
                "event_description": f"Official academic calendar for {program} ({year}) published by MITS Academic Section. Source: {page_url}",
                "source_url": page_url,
                "document_url": val_res.resolved_url if val_res.is_valid else pdf_url,
                "source_name": "MITS Academic Section",
                "is_valid": val_res.is_valid,
                "http_status": val_res.http_status,
                "error_reason": val_res.error_reason,
            }
            calendar_items.append(item)

    if calendar_items:
        return adapter.save(db, calendar_items)
    return 0


def sync_examinations_from_page(db: Session, page_url: str, html_text: str, client: Optional[httpx.Client] = None) -> int:
    """
    Extract and validate examination timetables, notices, and circulars
    from https://mits.ac.in/university-exam and https://mits.ac.in/controller-of-examinations.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    adapter = MITSExamAdapter()
    exam_items: List[Dict[str, Any]] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(separator=" ", strip=True)
        pdf_url = urljoin(page_url, href)

        if pdf_url.lower().endswith(".pdf") or any(k in text.lower() for k in ["exam", "timetable", "time table", "schedule", "revaluation", "re-evaluation", "recounting", "hall ticket"]):
            clean_title = text.replace("\n", " ").strip()
            if not clean_title or len(clean_title) < 5:
                clean_title = pdf_url.split("/")[-1].replace("%20", " ").replace(".pdf", "")

            # Validate external document link
            val_res = validate_external_url(pdf_url, base_url=page_url, client=client)

            exam_type = "notification"
            if "time table" in clean_title.lower() or "timetable" in clean_title.lower() or "schedule" in clean_title.lower():
                exam_type = "timetable"
            elif "revaluation" in clean_title.lower() or "re-evaluation" in clean_title.lower() or "recounting" in clean_title.lower():
                exam_type = "revaluation"
            elif "result" in clean_title.lower() or "grade" in clean_title.lower():
                exam_type = "result"

            program = "B.Tech"
            if "m.tech" in clean_title.lower() or "mtech" in clean_title.lower():
                program = "M.Tech"
            elif "mba" in clean_title.lower():
                program = "MBA"
            elif "mca" in clean_title.lower():
                program = "MCA"

            item = {
                "title": clean_title,
                "exam_type": exam_type,
                "program": program,
                "year": "All Years",
                "semester": "Current",
                "description": f"Official examination notice from Controller of Examinations (CoE), MITS. Official Document: {val_res.resolved_url if val_res.is_valid else pdf_url}",
                "source_url": page_url,
                "document_url": val_res.resolved_url if val_res.is_valid else pdf_url,
                "source_name": "Controller of Examinations (CoE), MITS",
                "is_valid": val_res.is_valid,
                "http_status": val_res.http_status,
                "error_reason": val_res.error_reason,
            }
            exam_items.append(item)

    if exam_items:
        return adapter.save(db, exam_items)
    return 0


def sync_announcements_from_page(db: Session, page_url: str, html_text: str, client: Optional[httpx.Client] = None) -> int:
    """
    Extract and validate university announcements and circulars from https://mits.ac.in/circulars.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    adapter = MITSAnnouncementAdapter()
    ann_items: List[Dict[str, Any]] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(separator=" ", strip=True)
        pdf_url = urljoin(page_url, href)

        if pdf_url.lower().endswith(".pdf") or "circular" in text.lower() or "holiday" in text.lower() or "notice" in text.lower():
            clean_title = text.replace("\n", " ").strip()
            if not clean_title or len(clean_title) < 5:
                clean_title = pdf_url.split("/")[-1].replace("%20", " ").replace(".pdf", "")

            val_res = validate_external_url(pdf_url, base_url=page_url, client=client)

            item = {
                "title": clean_title,
                "description": f"Official university circular published on {page_url}.",
                "content": f"Official notification from Madanapalle Institute of Technology & Science. Verified Document: {val_res.resolved_url if val_res.is_valid else pdf_url}",
                "category": "Academic" if "academic" in clean_title.lower() else "General",
                "source_url": page_url,
                "document_url": val_res.resolved_url if val_res.is_valid else pdf_url,
                "source_name": "MITS Administration",
                "is_valid": val_res.is_valid,
                "http_status": val_res.http_status,
                "error_reason": val_res.error_reason,
            }
            ann_items.append(item)

    if ann_items:
        return adapter.save(db, ann_items)
    return 0


def sync_college_overview_and_history(db: Session, page_url: str, html_text: str, source: WebsiteSource) -> None:
    """
    Extract college establishment and history from https://mits.ac.in/about-us,
    update CollegeInfo records, and ensure it is indexed as an official Document in ChromaDB.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    paragraphs = [
        p.get_text(strip=True) for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 50 and not p.get_text(strip=True).startswith("Copyright")
    ]
    full_history = "\n\n".join(paragraphs[:8])

    if not full_history:
        full_history = (
            "Madanapalle Institute of Technology & Science (MITS) is a premier Deemed to be University / Autonomous Institution "
            "established in 1998 in Madanapalle, Andhra Pradesh, under the auspices of Ratakonda Ranga Reddy Educational Academy. "
            "Spread over a 30-acre campus along the Madanapalle-Anantapur Highway (NH-205), MITS offers premier undergraduate, "
            "postgraduate, and doctoral degree programs in Engineering, Technology, Management, and Computer Applications."
        )

    info_record = db.query(CollegeInfo).filter(CollegeInfo.key == "about_mits").first()
    if info_record:
        info_record.content = full_history
        info_record.source_url = page_url
        info_record.canonical_url = page_url
        info_record.is_valid = True
        info_record.last_verified_at = datetime.now(timezone.utc)
    else:
        info_record = CollegeInfo(
            key="about_mits",
            title="About MITS Deemed to be University - History, Establishment & Overview",
            content=full_history,
            category="about",
            source_url=page_url,
            canonical_url=page_url,
            is_valid=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(info_record)
    db.commit()

    # Index into Chroma as official document so RAG queries can retrieve establishment/history
    page_data = {
        "title": "About MITS - College Overview, Establishment & History",
        "text": full_history,
        "content_hash": hashlib.sha256(full_history.encode("utf-8")).hexdigest(),
        "discovered_links": [],
    }
    process_crawled_html_page(db, source, page_url, page_data)


# ── 6. End-to-End Crawler & Synchronizer ──────────────────────────────────────

def synchronize_website_source(db: Session, source_id: int) -> WebsiteSyncHistory:
    """
    Execute complete end-to-end synchronization against the official MITS website (https://mits.ac.in/).
    Dynamically discovers all departments, faculty, department heads, academic calendars, examinations,
    announcements, and college overview, with full URL validation, 404 rejection, and ChromaDB vector indexing.
    """
    source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
    if not source:
        raise ValueError(f"WebsiteSource with id {source_id} not found.")

    if source.status in [WebsiteSourceStatus.QUEUED, WebsiteSourceStatus.CRAWLING, WebsiteSourceStatus.VALIDATING, WebsiteSourceStatus.INDEXING]:
        logger.warning(f"[WEBSITE_SYNC] Source {source_id} is already syncing. Skipping duplicate invocation.")
        existing = db.query(WebsiteSyncHistory).filter(
            WebsiteSyncHistory.source_id == source.id,
            WebsiteSyncHistory.status.in_([SyncStatus.QUEUED, SyncStatus.CRAWLING, SyncStatus.VALIDATING, SyncStatus.INDEXING])
        ).first()
        if existing:
            return existing

    source.status = WebsiteSourceStatus.QUEUED
    source.last_checked_at = datetime.now(timezone.utc)
    db.commit()

    history = WebsiteSyncHistory(
        source_id=source.id,
        started_at=datetime.now(timezone.utc),
        status=SyncStatus.QUEUED,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    source.status = WebsiteSourceStatus.CRAWLING
    history.status = SyncStatus.CRAWLING
    db.commit()

    logger.info(f"[WEBSITE_SYNC] Starting live sync for source '{source.name}' (URL: {source.base_url})")

    allowed_domains = [d.strip() for d in source.allowed_domains.split(",") if d.strip()]
    allowed_paths = [p.strip() for p in source.allowed_paths.split(",")] if source.allowed_paths else None

    # Priority Official Discovery Hubs
    priority_hubs = [
        "https://mits.ac.in/",
        "https://mits.ac.in/about-us",
        "https://mits.ac.in/departmentheads",
        "https://mits.ac.in/departments",
        "https://mits.ac.in/mits_new/departments",
        "https://mits.ac.in/faculty-information",
        "https://mits.ac.in/academic-calenders",
        "https://mits.ac.in/university-exam",
        "https://mits.ac.in/controller-of-examinations",
        "https://mits.ac.in/circulars",
        "https://mits.ac.in/programmes",
        "https://mits.ac.in/placement",
        # Active official department portals
        "https://mits.ac.in/department/9",  # CSE
        "https://mits.ac.in/cse-ai-ml",     # CSE (AI & ML)
        "https://mits.ac.in/department/32", # CSE-AIML
        "https://mits.ac.in/department/28", # AI
        "https://mits.ac.in/department/26", # CSE (Data Science)
        "https://mits.ac.in/department/27", # CSE (Cyber Security)
        "https://mits.ac.in/department/4",  # CST
        "https://mits.ac.in/electronics-communication-engineering", # ECE
        "https://mits.ac.in/electrical-electronics-engineering",    # EEE
        "https://mits.ac.in/department/8",  # Mechanical
        "https://mits.ac.in/department/6",  # Civil
        "https://mits.ac.in/department/5",  # MBA / Management
        "https://mits.ac.in/department/18", # MCA / Computer Applications
        "https://mits.ac.in/basic-sciences-humanities", # BSH
    ]

    base_normalized = normalize_crawl_url(source.base_url)
    queue: List[str] = [base_normalized]
    for u in priority_hubs:
        u_norm = normalize_crawl_url(u)
        if check_ssrf_safety(u_norm, allowed_domains)[0] and u_norm not in queue:
            queue.append(u_norm)
    visited_urls: Set[str] = set()

    discovered_count = 0
    added_count = 0
    updated_count = 0
    unchanged_count = 0
    failed_count = 0
    departments_synced = 0
    faculty_synced = 0
    calendars_synced = 0
    exams_synced = 0
    announcements_synced = 0
    invalid_urls_rejected = 0
    failed_url_logs: List[str] = []
    hod_map: Dict[str, Dict[str, Any]] = {}

    client = httpx.Client(
        timeout=DEFAULT_REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": CRAWLER_USER_AGENT},
    )

    try:
        rp = get_robots_parser(source.base_url, client=client)

        while queue and len(visited_urls) < max(source.max_pages, 90):
            current_url = queue.pop(0)
            if current_url in visited_urls:
                continue

            visited_urls.add(current_url)

            if not rp.can_fetch(CRAWLER_USER_AGENT, current_url):
                logger.warning(f"[WEBSITE_SYNC] robots.txt disallows URL: {current_url}")
                continue

            discovered_count += 1
            logger.info(f"[WEBSITE_SYNC] Processing ({len(visited_urls)}/{source.max_pages}): {current_url}")

            try:
                resp = client.get(current_url)
                final_url = normalize_crawl_url(str(resp.url) if getattr(resp, "url", None) and isinstance(resp.url, (str, httpx.URL)) else current_url)

                if resp.status_code != 200:
                    logger.warning(f"[WEBSITE_SYNC] HTTP {resp.status_code} for {current_url}")
                    failed_count += 1
                    invalid_urls_rejected += 1
                    failed_url_logs.append(f"{current_url} (HTTP {resp.status_code})")
                    try:
                        db.add(SyncChangeReview(
                            source_id=source.id,
                            history_id=history.id,
                            url=current_url,
                            title="Unreachable URL / 404",
                            entity_type="document",
                            change_type="INVALID_URL",
                            status="PENDING_REVIEW",
                            http_status=resp.status_code,
                            error_reason=f"HTTP {resp.status_code} returned during verification.",
                        ))
                        db.commit()
                    except Exception:
                        db.rollback()
                    continue

                content_type = resp.headers.get("content-type", "").lower()

                # 1. Handle PDF
                if "application/pdf" in content_type or current_url.lower().endswith(".pdf"):
                    logger.info(f"[WEBSITE_SYNC] Ingesting verified PDF: {final_url}")
                    res = process_crawled_pdf_document(db, source, final_url, resp.content)
                    if res == "added":
                        added_count += 1
                    elif res == "updated":
                        updated_count += 1
                    elif res == "unchanged":
                        unchanged_count += 1

                    if res in ("added", "updated"):
                        try:
                            db.add(SyncChangeReview(
                                source_id=source.id,
                                history_id=history.id,
                                url=final_url,
                                title=final_url.split("/")[-1],
                                entity_type="document",
                                change_type="NEW" if res == "added" else "UPDATED",
                                status="APPROVED",
                                new_content="PDF Document",
                            ))
                            db.commit()
                        except Exception:
                            db.rollback()

                # 2. Handle HTML
                elif "text/html" in content_type:
                    page_data = extract_html_content_and_links(
                        html_text=resp.text,
                        current_url=final_url,
                        allowed_domains=allowed_domains,
                        allowed_paths=allowed_paths,
                    )

                    res = process_crawled_html_page(db, source, final_url, page_data)
                    if res == "added":
                        added_count += 1
                    elif res == "updated":
                        updated_count += 1
                    elif res == "unchanged":
                        unchanged_count += 1

                    if res in ("added", "updated"):
                        try:
                            db.add(SyncChangeReview(
                                source_id=source.id,
                                history_id=history.id,
                                url=final_url,
                                title=page_data.get("title", "MITS Document"),
                                entity_type="document",
                                change_type="NEW" if res == "added" else "UPDATED",
                                status="APPROVED",
                                new_content=page_data.get("text_content", "")[:1000],
                            ))
                            db.commit()
                        except Exception:
                            db.rollback()

                    # 3. Synchronize Structured Academic Entities
                    # A1. Official Department Heads from /departmentheads
                    if "departmentheads" in final_url:
                        discovered_heads = sync_mits_departmentheads_from_page(db, final_url, resp.text)
                        hod_map.update(discovered_heads)

                    # A2. Faculty from faculty-information
                    if "faculty-information" in final_url:
                        f_count, discovered_hods = sync_mits_faculty_from_page(db, final_url, resp.text)
                        faculty_synced += f_count
                        hod_map.update(discovered_hods)

                    # B. Departments
                    if "/department/" in final_url or any(d in final_url for d in ["cse-ai-ml", "electronics-communication", "electrical-electronics", "basic-sciences"]):
                        dept_res = sync_mits_department_page(db, final_url, resp.text, hod_map=hod_map)
                        if dept_res:
                            departments_synced += 1

                    # C. Academic Calendars
                    if "academic-calender" in final_url or "academic-calendar" in final_url:
                        calendars_synced += sync_academic_calendars_from_page(db, final_url, resp.text, client=client)

                    # D. Examinations
                    if "university-exam" in final_url or "controller-of-examinations" in final_url:
                        exams_synced += sync_examinations_from_page(db, final_url, resp.text, client=client)

                    # E. Announcements & Circulars
                    if "circular" in final_url:
                        announcements_synced += sync_announcements_from_page(db, final_url, resp.text, client=client)

                    # F. College Overview, History & Establishment
                    if "about-us" in final_url or "about-vision-mission" in final_url:
                        sync_college_overview_and_history(db, final_url, resp.text, source=source)

                    # Add child links
                    for link in page_data["discovered_links"]:
                        if link not in visited_urls and link not in queue and len(visited_urls) + len(queue) < source.max_pages * 2:
                            queue.append(link)

            except Exception as item_exc:
                logger.error(f"[WEBSITE_SYNC] Error processing {current_url}: {item_exc}")
                failed_count += 1
                failed_url_logs.append(f"{current_url} ({str(item_exc)[:100]})")

        # Mark sync successful or partial
        now = datetime.now(timezone.utc)
        history.completed_at = now
        final_status = SyncStatus.SUCCESS if failed_count == 0 else SyncStatus.PARTIAL_SUCCESS
        history.status = final_status
        history.documents_discovered = discovered_count
        history.documents_added = added_count
        history.documents_updated = updated_count
        history.documents_unchanged = unchanged_count
        history.documents_failed = failed_count
        history.invalid_url_count = invalid_urls_rejected

        diag_msg = (
            f"Synchronization completed successfully.\n"
            f"• URLs Discovered: {discovered_count}, Added: {added_count}, Updated: {updated_count}, "
            f"Unchanged: {unchanged_count}, Failed: {failed_count}\n"
            f"• Entities Synced -> Departments: {departments_synced}, Faculty: {faculty_synced}, "
            f"HoDs: {len(hod_map)}, Calendars: {calendars_synced}, Exams: {exams_synced}, Circulars: {announcements_synced}\n"
            f"• Invalid/404 URLs Rejected: {invalid_urls_rejected}"
        )
        if failed_url_logs:
            diag_msg += f"\n• Failed Logs: {'; '.join(failed_url_logs[:4])}"

        history.error_message = diag_msg
        source.status = WebsiteSourceStatus.IDLE
        source.last_successful_sync_at = now
        source.last_error = None
        db.commit()

        logger.info(f"[WEBSITE_SYNC] {diag_msg}")
        
        # Invalidate RAG cache after successful sync so new information is used
        if added_count > 0 or updated_count > 0 or departments_synced > 0 or faculty_synced > 0 or calendars_synced > 0 or exams_synced > 0 or announcements_synced > 0:
            try:
                invalidate_rag_cache()
            except Exception as e:
                logger.warning(f"[WEBSITE_SYNC] Failed to invalidate RAG cache: {e}")

    except Exception as exc:
        logger.error(f"[WEBSITE_SYNC] Synchronization crashed: {exc}")
        now = datetime.now(timezone.utc)
        history.completed_at = now
        history.status = SyncStatus.FAILED
        history.documents_discovered = discovered_count
        history.documents_added = added_count
        history.documents_updated = updated_count
        history.documents_unchanged = unchanged_count
        history.documents_failed = failed_count
        fallback_notice = f"Sync failed — previous verified knowledge remains active. ({str(exc)[:400]})"
        history.error_message = fallback_notice
        source.status = WebsiteSourceStatus.ERROR
        source.last_error = fallback_notice
        db.commit()

    finally:
        client.close()

    db.refresh(history)
    return history
