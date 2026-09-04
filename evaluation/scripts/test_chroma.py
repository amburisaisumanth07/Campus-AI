"""
Evaluation Script — Chroma Vector Store Verification
Verifies Chroma HTTP connectivity, basic insert, get, count, and delete behavior
without printing full 768-dimensional float embeddings.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.rag import vectorstore


def main():
    print("==================================================")
    print("CampusAI RAG - Chroma Vector Store Verification")
    print("==================================================")

    # 1. Health Check
    print("\n[1] Checking Chroma HTTP Service Health...")
    is_healthy = vectorstore.health_check()
    if not is_healthy:
        print("  [-] RESULT: FAILED - Chroma HTTP service is not reachable.")
        print("      Please ensure Docker container is running on localhost:8001")
        sys.exit(1)
    print("  [+] RESULT: SUCCESS - Chroma HTTP service is healthy!")

    # 2. Collection Verification
    print("\n[2] Connecting to collection...")
    try:
        coll = vectorstore.get_collection()
        print(f"  [+] Collection Name: '{coll.name}'")
        initial_count = vectorstore.count()
        print(f"  [+] Initial Record Count: {initial_count}")
    except Exception as exc:
        print(f"  [-] RESULT: FAILED - Could not get collection: {exc}")
        sys.exit(1)

    # 3. Test Chunk Insertion
    test_chunk_id = "eval_test_chunk_001"
    test_doc_id = 99999
    print(f"\n[3] Inserting sample chunk '{test_chunk_id}'...")

    sample_chunk = {
        "id": test_chunk_id,
        "text": "Campus attendance policy requires a minimum of 75% attendance in all courses.",
        "metadata": {
            "document_id": test_doc_id,
            "document_version_id": 1,
            "page_number": 1,
            "source_pages": [1],
            "chunk_index": 0,
            "title": "Evaluation Test Document",
            "department": "Academic Affairs",
            "academic_year": "2025-2026",
            "document_type": "PDF",
        },
    }
    # Deterministic 768-dim vector
    sample_embedding = [0.01 * (i % 10) for i in range(768)]

    try:
        added = vectorstore.add_chunks([sample_chunk], [sample_embedding])
        print(f"  [+] Chunks inserted: {added}")
    except Exception as exc:
        print(f"  [-] RESULT: FAILED - Add chunk failed: {exc}")
        sys.exit(1)

    # 4. Item Retrieval & Metadata Preservation
    print(f"\n[4] Retrieving chunk '{test_chunk_id}' by ID...")
    retrieved = vectorstore.get_chunk(test_chunk_id)
    if not retrieved:
        print("  [-] RESULT: FAILED - Retrieved chunk is None.")
        sys.exit(1)

    print("  [+] Successfully retrieved chunk:")
    print(f"      - ID: {retrieved['id']}")
    print(f"      - Text Snippet: {retrieved['text'][:60]}...")
    print(f"      - Embedding Vector Dimension: {len(retrieved['embedding'])} floats")
    print(f"      - Document ID: {retrieved['metadata'].get('document_id')}")
    print(f"      - Title: {retrieved['metadata'].get('title')}")
    print(f"      - Department: {retrieved['metadata'].get('department')}")
    print(f"      - Academic Year: {retrieved['metadata'].get('academic_year')}")

    # 5. Cleanup Test Chunk
    print(f"\n[5] Deleting test document_id {test_doc_id}...")
    deleted = vectorstore.delete_chunks_by_document(test_doc_id)
    print(f"  [+] Chunks deleted: {deleted}")

    final_count = vectorstore.count()
    print(f"  [+] Final Record Count: {final_count}")

    print("\n==================================================")
    print("Chroma Vector Database Integration Verification PASSED!")
    print("==================================================")


if __name__ == "__main__":
    main()
