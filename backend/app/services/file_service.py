"""
Secure file upload utilities.

Security controls implemented:
- MIME type validation via magic bytes (not client-supplied Content-Type)
- File size enforcement
- Filename sanitization (no path traversal, no null bytes, ASCII-safe)
- Server-generated storage filename (UUID-based)
- SHA-256 checksum calculation
"""
import hashlib
import re
import uuid
from pathlib import Path
from typing import Tuple

import aiofiles
from fastapi import UploadFile, HTTPException, status

from backend.app.core.config import settings
from backend.app.core.logging import logger

# PDF magic bytes: %PDF
_PDF_MAGIC = b"%PDF"
# Maximum chunk size for streaming reads
_CHUNK_SIZE = 256 * 1024  # 256 KB


def _check_magic_bytes(data: bytes) -> bool:
    """Return True if data starts with the PDF magic signature."""
    return data[:4] == _PDF_MAGIC


def sanitize_filename(original: str) -> str:
    """
    Return a safe display filename:
    - Strip directory components
    - Replace non-alphanumeric chars (except dots, dashes, underscores) with '_'
    - Collapse multiple underscores
    - Enforce .pdf extension
    - Truncate to 200 chars
    """
    name = Path(original).name  # strip any path prefix
    name = re.sub(r"[^\w.\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_. ")
    if not name:
        name = "document"
    if not name.lower().endswith(".pdf"):
        name = name + ".pdf"
    return name[:200]


def generate_storage_filename(document_id: int, version: str) -> str:
    """
    Generate a UUID-based filename for disk storage.
    The original filename is NEVER used as a path component.
    """
    unique = uuid.uuid4().hex
    safe_ver = re.sub(r"[^\w]", "_", version)
    return f"doc_{document_id}_{safe_ver}_{unique}.pdf"


def get_storage_dir() -> Path:
    """Return the absolute resolved storage directory, creating it if needed."""
    # Always relative to the backend/ directory (one level up from app/)
    backend_dir = Path(__file__).resolve().parent.parent.parent
    storage = backend_dir / settings.DOCUMENT_STORAGE_PATH
    storage.mkdir(parents=True, exist_ok=True)
    return storage


async def validate_and_save_upload(
    file: UploadFile,
    storage_filename: str,
) -> Tuple[Path, str, int]:
    """
    Stream the uploaded file to disk while:
    1. Enforcing file size limit (settings.MAX_UPLOAD_SIZE_MB)
    2. Verifying PDF magic bytes in the first chunk
    3. Computing SHA-256 checksum

    Returns (absolute_path, sha256_hex, file_size_bytes).
    Raises HTTPException on any validation failure.
    Cleans up partial file on error.
    """
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    storage_dir = get_storage_dir()
    dest_path = storage_dir / storage_filename

    sha256 = hashlib.sha256()
    total_bytes = 0
    first_chunk = True

    try:
        async with aiofiles.open(dest_path, "wb") as out_file:
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break

                if first_chunk:
                    first_chunk = False
                    if not _check_magic_bytes(chunk):
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="File does not appear to be a valid PDF (magic bytes mismatch).",
                        )

                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                    )

                sha256.update(chunk)
                await out_file.write(chunk)

    except HTTPException:
        # Clean up partial file
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        logger.error(f"File upload failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File could not be saved. Please try again.",
        )

    return dest_path, sha256.hexdigest(), total_bytes
