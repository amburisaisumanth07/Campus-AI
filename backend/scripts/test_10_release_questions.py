import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag import pipeline

QUESTIONS = [
    ("Q1", "Who is the HOD of Civil Engineering?"),
    ("Q2", "Who is the HOD of CSE?"),
    ("Q3", "Who is the HOD of CSE AI and ML?"),
    ("Q4", "Who is the HOD of CSE Data Science?"),
    ("Q5", "How many faculty members are in CSE?"),
    ("Q6", "What is the minimum attendance requirement at MITS?"),
    ("Q7", "What are the pass criteria and grading rules at MITS?"),
    ("Q8", "What are the latest examination notifications at MITS?"),
    ("Q9", "What is the rocket launch schedule at MITS Madanapalle space center?"), # Question that DOES NOT exist in knowledge base
    ("Q10", "Who are the HODs for Civil Engineering and Mechanical Engineering?"), # Compound question involving two departments
]

def run_test():
    print("=" * 80)
    print("CAMPUSAI — 10 FINAL RELEASE BENCHMARK QUESTIONS")
    print("=" * 80)
    results = []
    
    for qid, q in QUESTIONS:
        t0 = time.perf_counter()
        res = pipeline.run_pipeline(q, bypass_cache=True)
        dt = (time.perf_counter() - t0) * 1000
        
        status = res.get("status")
        grounded = res.get("grounded", False)
        ans = res.get("answer", "")
        sources = res.get("sources", [])
        tb = res.get("timing_breakdown") or {}
        
        print(f"\n[{qid}] {q}")
        print(f"  • Latency: {dt:.1f}ms | Grounded: {grounded} | Status: {status}")
        print(f"  • Timing Breakdown: embed={tb.get('embedding_ms', 0):.1f}ms, search={tb.get('retrieval_ms', 0):.1f}ms, llm={tb.get('llm_ms', 0):.1f}ms")
        print(f"  • Sources ({len(sources)}): {[s.get('title') for s in sources[:2]]}")
        snippet = ans.replace('\n', ' ')[:150]
        print(f"  • Answer: {snippet}...")
        
        results.append({
            "id": qid,
            "question": q,
            "latency": dt,
            "grounded": grounded,
            "sources": len(sources),
            "snippet": snippet
        })
        time.sleep(1.0)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for r in results:
        print(f"{r['id']}: {r['latency']:.0f}ms | Grounded={r['grounded']} | Sources={r['sources']}")

if __name__ == "__main__":
    run_test()
