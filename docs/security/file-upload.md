# File Upload Security Controls

## Security Controls Implemented

1. **Role Enforcement**: Only users with `role: ADMIN` can invoke upload and deletion endpoints.
2. **Magic Byte Verification**: Uploaded files are inspected for `%PDF` magic bytes (`b"%PDF"`) at the binary head, ignoring client-provided extensions or Content-Type headers.
3. **Strict Size Enforcement**: Streaming read enforces `MAX_UPLOAD_SIZE_MB = 20`. Uploads exceeding this threshold are aborted and cleaned up immediately.
4. **Filename Sanitization & Path Traversal Prevention**:
   - Original client filenames are stripped of directory components (`Path(filename).name`).
   - Non-alphanumeric characters are replaced with underscores.
   - Internal storage filenames are generated using UUIDs: `doc_{id}_{version}_{uuid}.pdf`. Original client filenames are never used as filesystem paths.
5. **Checksum & Duplicate Control**: SHA-256 digests are computed during upload streaming. Identical files trigger HTTP 409 Conflict.
6. **Information Disclosure Prevention**:
   - Internal filesystem paths (`storage_path`) are never returned in public API responses.
   - Stack traces are suppressed from API responses on processing failures; sanitized error summaries are logged internally.
7. **Storage Isolation**: Raw PDF files are stored under `backend/data/documents/`, which is excluded from Git via `.gitignore`.
