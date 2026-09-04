# Document Ingestion & PDF Extraction Architecture

## Processing Lifecycle

```
[Admin Upload]
      │
      ▼
1. Validate MIME & Magic Bytes (%PDF)
      │
      ▼
2. Enforce File Size Limit (<= 20MB)
      │
      ▼
3. Stream file to data/documents/ (UUID filename)
      │
      ▼
4. Calculate SHA-256 Checksum (Reject duplicates -> 409)
      │
      ▼
5. Create `documents` & `document_versions` rows (Status: UPLOADED -> PROCESSING)
      │
      ▼
6. `pdfplumber` Page-by-Page Text Extraction
      │
      ├── Success ──► Save `document_pages` (1-based page_number) ──► Status: READY
      │
      └── Exception ──► Log sanitized error msg ──────────────────► Status: FAILED
```

## Citation Accuracy & Page Representation
Extracted text is preserved **page-by-page** using 1-based indexing (`page_number: 1, 2, ...`). The text is never merged into a single document blob. This ensures downstream RAG systems can construct exact page-level citations (e.g. `[Academic Regulations 2025, Page 4]`).
