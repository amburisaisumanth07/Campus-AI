"""
Manual Integration Test Script for Gemini Embeddings API.

This script makes a real API call to Gemini using GEMINI_API_KEY.
It is excluded from automated test suites.

Usage:
    python evaluation/scripts/test_gemini_embeddings.py
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from app.core.config import settings
from app.rag.embeddings import embed_document, embed_query


def main():
    print("=== Gemini Embedding Manual Integration Test ===")
    api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY

    if not api_key or not api_key.strip():
        print("[ERROR] GEMINI_API_KEY is missing or empty.")
        print("Please set GEMINI_API_KEY in your environment or .env file before running this script.")
        sys.exit(1)

    print(f"Embedding model configured: {settings.GEMINI_EMBEDDING_MODEL}")
    sample_text = "Attendance of at least 75% is required for end-semester examinations."

    try:
        print("Sending document embedding request...")
        doc_vector = embed_document(sample_text, api_key=api_key)
        print(f"[SUCCESS] Document embedding generated. Vector dimension: {len(doc_vector)}")

        print("Sending query embedding request...")
        query_vector = embed_query("What is the minimum attendance requirement?", api_key=api_key)
        print(f"[SUCCESS] Query embedding generated. Vector dimension: {len(query_vector)}")

        print("=== Test Completed Successfully ===")

    except Exception as e:
        print(f"[FAILED] Embedding request failed: {type(e).__name__} - {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
