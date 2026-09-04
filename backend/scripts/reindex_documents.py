"""
Re-indexing script for CampusAI.
Reads all READY documents from PostgreSQL, generates text chunks and embeddings,
and populates the ChromaDB vector collection.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import SessionLocal
from backend.app.db.models import Document, DocumentPage, DocumentStatus
from backend.app.rag import chunking, embeddings, vectorstore

def reindex_all_documents(target_doc_id: int | None = None):
    print("=" * 60)
    print("CampusAI Vector Re-indexing Utility")
    print(f"Target Chroma Collection: {settings.CHROMA_COLLECTION} at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
    print("=" * 60)

    # 1. Verify Chroma connectivity
    if not vectorstore.health_check():
        print("ERROR: ChromaDB is not reachable. Ensure Chroma container is running.")
        sys.exit(1)
    print("[+] ChromaDB connection verified.")

    # 2. Check API key presence
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        print("ERROR: GEMINI_API_KEY is not set in configuration / .env.")
        sys.exit(1)
    print(f"[+] GEMINI_API_KEY is configured (length: {len(settings.GEMINI_API_KEY)}).")

    db = SessionLocal()
    try:
        query = db.query(Document).filter(Document.status == DocumentStatus.READY)
        if target_doc_id is not None:
            query = query.filter(Document.id == target_doc_id)
        
        docs = query.order_by(Document.id.asc()).all()
        print(f"[+] Found {len(docs)} READY document(s) to index.")

        total_chunks_indexed = 0

        for doc in docs:
            pages = db.query(DocumentPage).filter(
                DocumentPage.document_id == doc.id
            ).order_by(DocumentPage.page_number.asc()).all()

            if not pages:
                print(f"[-] Doc ID {doc.id} ('{doc.title}') has 0 pages; skipping.")
                continue

            page_dicts = [
                {"page_number": p.page_number, "text_content": p.text_content or ""}
                for p in pages
            ]

            # 1. Chunk
            chunk_records = chunking.create_chunks_from_pages(
                doc_id=doc.id,
                title=doc.title,
                department=doc.department,
                academic_year=doc.academic_year,
                pages=page_dicts,
                chunk_size=settings.RAG_CHUNK_SIZE,
                overlap=settings.RAG_CHUNK_OVERLAP,
                source_type=doc.source_type.value if doc.source_type else None,
                source_url=doc.source_url,
            )

            if not chunk_records:
                print(f"[-] Doc ID {doc.id} ('{doc.title}') produced 0 text chunks; skipping.")
                continue

            print(f"[*] Doc ID {doc.id} ('{doc.title}'): {len(pages)} pages -> {len(chunk_records)} chunks. Generating embeddings...")

            # 2. Embed
            texts = [c["text"] for c in chunk_records]
            try:
                vectors = embeddings.embed_documents(texts)
            except Exception as exc:
                print(f"[!] ERROR generating embeddings for Doc ID {doc.id}: {exc}")
                raise

            # 3. Add to Chroma
            # Remove any existing chunks for this doc first to ensure clean idempotent indexing
            vectorstore.delete_document_chunks(doc.id)
            count = vectorstore.add_chunks(chunk_records, vectors)
            total_chunks_indexed += count
            print(f"    -> Successfully indexed {count} chunks for Doc ID {doc.id}.")

        coll = vectorstore.get_collection(settings.CHROMA_COLLECTION)
        print("=" * 60)
        print(f"[+] Re-indexing complete! Total chunks indexed: {total_chunks_indexed}")
        print(f"[+] Total records in ChromaDB collection '{settings.CHROMA_COLLECTION}': {coll.count()}")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    doc_id_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    reindex_all_documents(target_doc_id=doc_id_arg)
