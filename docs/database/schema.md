# Database Schema Reference

## Overview
CampusAI uses PostgreSQL with SQLAlchemy ORM and Alembic migrations.

---

## Tables

### `health_checks`
Stores database connection health checks.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Primary key |
| `status` | String | Default: `'healthy'` | Health status |
| `checked_at` | DateTime(tz) | Default: `now()` | Timestamp of check |

---

### `users`
Stores student and administrator user accounts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Primary key |
| `name` | String(255) | NOT NULL | User full name |
| `email` | String(255) | Unique, NOT NULL, Index | Unique email address |
| `password_hash` | String(255) | NOT NULL | bcrypt password hash |
| `role` | Enum(`STUDENT`, `ADMIN`) | NOT NULL, Default: `STUDENT` | RBAC role |
| `is_active` | Boolean | NOT NULL, Default: `true` | Account status |
| `created_at` | DateTime(tz) | Default: `now()` | Account creation timestamp |
| `updated_at` | DateTime(tz) | Default: `now()`, onupdate | Last update timestamp |

---

### `documents`
Stores master document metadata.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Primary key |
| `title` | String(500) | NOT NULL | Display title of document |
| `filename` | String(500) | NOT NULL | Sanitized display filename |
| `document_type` | Enum | NOT NULL | Type: `regulation`, `academic_calendar`, etc. |
| `department` | String(255) | Nullable | Associated department |
| `academic_year` | String(20) | Nullable | Academic year string |
| `status` | Enum | NOT NULL, Default: `UPLOADED` | Lifecycle status: `UPLOADED`, `PROCESSING`, `READY`, `FAILED` |
| `error_message` | Text | Nullable | Brief error details if processing failed |
| `active_version_id` | Integer | FK(`document_versions.id`), Nullable | ID of current active version |
| `uploaded_by_id` | Integer | FK(`users.id`), NOT NULL, Index | User ID of admin who uploaded |
| `created_at` | DateTime(tz) | Default: `now()` | Record creation timestamp |
| `updated_at` | DateTime(tz) | Default: `now()`, onupdate | Record update timestamp |

---

### `document_versions`
Tracks document versions, storage paths, file sizes, and checksums.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Primary key |
| `document_id` | Integer | FK(`documents.id`), NOT NULL, Index | Associated document ID |
| `version` | String(50) | NOT NULL, Default: `'1.0'` | Version identifier |
| `storage_path` | String(1000) | NOT NULL | Internal absolute file path (never exposed in API) |
| `file_checksum` | String(64) | NOT NULL, Index | SHA-256 hex digest for duplicate detection |
| `file_size` | BigInteger | NOT NULL | File size in bytes |
| `mime_type` | String(100) | NOT NULL | File MIME type (`application/pdf`) |
| `page_count` | Integer | Nullable | Extracted page count |
| `is_active` | Boolean | NOT NULL, Default: `true` | Active version flag |
| `created_at` | DateTime(tz) | Default: `now()` | Version creation timestamp |

---

### `document_pages`
Stores page-by-page extracted text for citation-accurate downstream processing.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Primary key |
| `document_id` | Integer | FK(`documents.id`), NOT NULL, Index | Document ID |
| `document_version_id` | Integer | FK(`document_versions.id`), NOT NULL, Index | Version ID |
| `page_number` | Integer | NOT NULL | 1-based page number |
| `text_content` | Text | Nullable | Extracted plain text for page |
| `char_count` | Integer | NOT NULL, Default: `0` | Character count |
| `created_at` | DateTime(tz) | Default: `now()` | Extraction timestamp |

---

## Migration History
1. `9766308ed13d_add_users_table.py` — Add `users` table.
2. `7184395c9186_add_document_tables.py` — Add `documents`, `document_versions`, `document_pages` tables.
