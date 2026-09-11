"""
ChromaDB Re-indexing Script for CampusAI.
Clears stale ChromaDB vector collections and re-indexes all official MITS documents
using gemini-embedding-001 768-dim embeddings with complete provenance metadata.

Usage:
  Local mode (default):
    python backend/scripts/reindex_chromadb.py

  Production mode (Preflight check only):
    python backend/scripts/reindex_chromadb.py --production

  Production mode (Execution):
    python backend/scripts/reindex_chromadb.py --production --confirm-production
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.db.models import Document, DocumentStatus
from backend.app.db.session import SessionLocal
from backend.app.rag.ingestion import index_document
from backend.app.rag.vectorstore import get_collection


def parse_safe_db_host(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.hostname or "unknown-host"
    except Exception:
        return "unknown-host"


def reindex_all_documents(production: bool = False, confirm_production: bool = False):
    print("=" * 60)
    mode_str = "PRODUCTION MODE (Neon + Chroma Cloud)" if production else "LOCAL MODE (Local DB + Local Chroma)"
    print(f"Re-indexing Official Documents into ChromaDB - [{mode_str}]")
    print("=" * 60)

    if production:
        # Require production environment variables
        db_url = getattr(settings, "DATABASE_URL", "") or ""
        chroma_api_key = getattr(settings, "CHROMA_API_KEY", "") or ""
        chroma_tenant = getattr(settings, "CHROMA_TENANT", "") or ""
        chroma_db = getattr(settings, "CHROMA_DATABASE", "") or ""
        chroma_coll = getattr(settings, "CHROMA_COLLECTION", "") or ""
        gemini_api_key = getattr(settings, "GEMINI_API_KEY", "") or ""

        missing = []
        if not db_url.strip():
            missing.append("DATABASE_URL")
        if not chroma_api_key.strip():
            missing.append("CHROMA_API_KEY")
        if not chroma_tenant.strip():
            missing.append("CHROMA_TENANT")
        if not chroma_db.strip():
            missing.append("CHROMA_DATABASE")
        if not chroma_coll.strip():
            missing.append("CHROMA_COLLECTION")
        if not gemini_api_key.strip():
            missing.append("GEMINI_API_KEY")

        if missing:
            print("[ERROR] Production mode requires non-empty values for the following environment variables:")
            for var in missing:
                print(f"  - {var}")
            print("\nAborting production re-index.")
            sys.exit(1)

        db_host = parse_safe_db_host(db_url)
        if db_host in ["127.0.0.1", "localhost", "0.0.0.0"]:
            print(f"[ERROR] Production DATABASE_URL must not point to localhost ({db_host}).")
            print("Aborting production re-index.")
            sys.exit(1)

        print("[SAFE PREFLIGHT CONFIGURATION]")
        print(f"  - Database Host       : {db_host}")
        print(f"  - Chroma Cloud Tenant : {chroma_tenant.strip()}")
        print(f"  - Chroma Cloud DB     : {chroma_db.strip()}")
        print(f"  - Vector Collection   : {chroma_coll.strip()}")

    # 1. Query database for READY documents and close session immediately
    from sqlalchemy.orm import joinedload

    db = SessionLocal()
    try:
        docs = db.query(Document).options(joinedload(Document.pages)).filter(Document.status == DocumentStatus.READY).all()
        ready_count = len(docs)
        print(f"  - READY Documents     : {ready_count}")

        docs_data = []
        for doc in docs:
            pages = [
                {
                    "page_number": p.get("page_number", 1) if isinstance(p, dict) else getattr(p, "page_number", 1),
                    "text_content": p.get("text_content", "") if isinstance(p, dict) else getattr(p, "text_content", ""),
                    "char_count": p.get("char_count", 0) if isinstance(p, dict) else getattr(p, "char_count", 0),
                }
                for p in doc.pages
            ]
            src_type_val = doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type)
            docs_data.append({
                "id": doc.id,
                "title": doc.title,
                "department": doc.department,
                "academic_year": doc.academic_year,
                "pages": pages,
                "source_type": src_type_val,
                "source_url": doc.source_url,
            })
    finally:
        db.close()

    if production and not confirm_production:
        print("=" * 60)
        print("[PREFLIGHT ONLY] Production configuration and database checks passed successfully.")
        print("To clear Chroma Cloud collection and execute full re-indexing, run with:")
        print("  python backend/scripts/reindex_chromadb.py --production --confirm-production")
        print("=" * 60)
        return

    print("-" * 60)
    print("[+] Clearing stale Chroma collection vectors...")

    # 2. Reset vector collection
    try:
        col = get_collection()
        all_ids = col.get().get("ids", [])
        if all_ids:
            col.delete(ids=all_ids)
            print(f"[+] Cleared {len(all_ids)} old vectors from ChromaDB collection.")
        else:
            print("[+] ChromaDB collection is already empty.")
    except Exception as exc:
        print(f"[!] Warning clearing old vectors: {exc}")

    # 3. Ingest ready documents
    print(f"[*] Starting vector indexing for {ready_count} READY documents...")
    import time
    total_chunks = 0
    for idx, doc_item in enumerate(docs_data, 1):
        pages = doc_item["pages"]
        if not pages:
            continue

        count = index_document(
            doc_id=doc_item["id"],
            title=doc_item["title"],
            department=doc_item["department"],
            academic_year=doc_item["academic_year"],
            pages=pages,
            source_type=doc_item["source_type"],
            source_url=doc_item["source_url"],
        )
        total_chunks += count

        if idx % 25 == 0 or idx == ready_count:
            print(f"  [{idx}/{ready_count}] Indexed doc {doc_item['id']} ({count} chunks) - Total vectors so far: {total_chunks}")
        time.sleep(0.05)

    print(f"[+] Successfully indexed {total_chunks} vector chunks across {ready_count} documents into ChromaDB.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Re-index CampusAI documents into ChromaDB.")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Target production Neon PostgreSQL and Chroma Cloud using environment variables.",
    )
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="Explicitly confirm clearing and re-indexing the production Chroma Cloud collection.",
    )
    args = parser.parse_args()

    reindex_all_documents(
        production=args.production,
        confirm_production=args.confirm_production,
    )


if __name__ == "__main__":
    main()

