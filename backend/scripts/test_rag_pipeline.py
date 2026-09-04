"""
Test script for verifying all critical student dashboard RAG queries.
"""
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.retrieval import retrieve_context
from backend.app.rag.pipeline import run_pipeline


def test_student_queries():
    queries = [
        "What is the grading system and SGPA calculation?",
        "What is the minimum attendance requirement for semester exams?",
        "What are the end-semester exam rules?",
        "What are the placement eligibility criteria and company requirements?",
        "Can you tell me college rules?",
        "Give me an overview of the college, its establishment, and history.",
        "Who is the Head of Department for Electronics & Communication Engineering?",
    ]

    for q in queries:
        print("\n" + "=" * 75)
        print(f"QUERY: {q}")
        print("=" * 75)
        t0 = time.perf_counter()
        res = run_pipeline(q)
        dt = time.perf_counter() - t0
        print(f"[TIME] Response Time: {dt:.2f}s | Grounded: {res['grounded']} | Retrieval Count: {res['retrieval_count']} | Cached: {res.get('cached', False)}")
        print(f"GROUNDED ANSWER:\n{res['answer']}")
        print(f"\nCITATIONS ({len(res['citations'])}):")
        for cit in res["citations"]:
            print(f"  - {cit['title']} | URL: {cit.get('source_url')} | Page: {cit.get('page_number', 1)}")


if __name__ == "__main__":
    test_student_queries()
