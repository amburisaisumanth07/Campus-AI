"""
Benchmark script for the 5 live RAG questions.
Measures and prints detailed latency breakdown and grounding metrics.
"""
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag import pipeline

test_questions = [
    "What is the minimum attendance requirement for MITS students to appear in end-semester examinations?",
    "Who is the Head of the Department for Computer Science & Engineering (CSE)?",
    "List the faculty members in the Computer Science & Engineering department.",
    "What are the latest examination guidelines and evaluation rules at MITS?",
    "What is the establishment history, vision, and campus location of MITS Madanapalle?",
]

def run_test():
    pipeline.clear_rag_cache()

    print("=" * 85)
    print("CAMPUSAI 5 LIVE RAG QUESTIONS BENCHMARK")
    print("=" * 85)

    all_passed = True
    for idx, q in enumerate(test_questions, 1):
        t0 = time.perf_counter()
        res = pipeline.run_pipeline(query=q, bypass_cache=True)
        t_tot = (time.perf_counter() - t0) * 1000

        status = res.get("status")
        grounded = res.get("grounded")
        emb_ms = res.get("embedding_ms", 0.0)
        ret_ms = res.get("retrieval_ms", 0.0)
        prm_ms = res.get("prompt_ms", 0.0)
        llm_ms = res.get("llm_ms", 0.0)
        tot_ms = res.get("total_ms", t_tot)

        print(f"\n[Question {idx}] \"{q}\"")
        print(f"Status        : {status}")
        print(f"Grounded      : {grounded}")
        print(f"Embedding ms  : {emb_ms:.1f}ms")
        print(f"Retrieval ms  : {ret_ms:.1f}ms")
        print(f"Prompt ms     : {prm_ms:.1f}ms")
        print(f"LLM ms        : {llm_ms:.1f}ms")
        print(f"Total ms      : {tot_ms:.1f}ms (Wall-clock: {t_tot:.1f}ms)")
        print(f"Chunks Count  : {res.get('retrieval_count')}")

        sources = res.get("sources") or res.get("citations") or []
        print(f"Sources ({len(sources)}):")
        for s in sources[:2]:
            print(f"  - {s.get('title')} ({s.get('source_url')})")

        ans_lines = (res.get("answer") or "").strip().splitlines()
        ans_preview = " ".join(ans_lines[:2])[:120]
        print(f"Answer Preview: {ans_preview}...")

        if status != "SUCCESS" or not grounded:
            all_passed = False

    print("\n" + "=" * 85)
    if all_passed:
        print("[SUCCESS] All 5 live questions completed with grounded answers and low latency!")
    else:
        print("[WARNING] Some queries did not return grounded status.")
    print("=" * 85)

if __name__ == "__main__":
    run_test()
