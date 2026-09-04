"""
ChromaDB Re-indexing Script for CampusAI.
Clears stale ChromaDB vector collections and re-indexes all official MITS documents
using gemini-embedding-001 768-dim embeddings with complete provenance metadata.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.db.models import Document, DocumentStatus
from backend.app.rag.vectorstore import get_collection
from backend.app.rag.ingestion import index_document


def reindex_all_documents():
    print("=" * 60)
    print("Re-indexing Official Documents into ChromaDB...")
    print("=" * 60)

    # 1. Reset vector collection
    try:
        col = get_collection()
        all_ids = col.get().get("ids", [])
        if all_ids:
            col.delete(ids=all_ids)
            print(f"[+] Cleared {len(all_ids)} old vectors from ChromaDB collection.")
    except Exception as exc:
        print(f"[!] Warning clearing old vectors: {exc}")

    # 2. Ingest ready documents
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.status == DocumentStatus.READY).all()
        print(f"[*] Found {len(docs)} ready documents to index.")

        total_chunks = 0
        for doc in docs:
            pages = []
            for p in doc.pages:
                pages.append({
                    "page_number": p.page_number,
                    "text_content": p.text_content,
                    "char_count": p.char_count,
                })

            if not pages:
                continue

            src_type_val = doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type)
            count = index_document(
                doc_id=doc.id,
                title=doc.title,
                department=doc.department,
                academic_year=doc.academic_year,
                pages=pages,
                source_type=src_type_val,
                source_url=doc.source_url,
            )
            total_chunks += count

        print(f"[+] Successfully indexed {total_chunks} vector chunks across {len(docs)} documents.")
    finally:
        db.close()


if __name__ == "__main__":
    reindex_all_documents()
