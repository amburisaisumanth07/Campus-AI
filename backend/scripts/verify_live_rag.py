"""
Real backend verification for CampusAI across the 5 required test queries.
Measures and prints:
- Query
- Status
- Grounded flag
- Retrieval count & top hits
- Citations
- Latency profile: Embedding, Retrieval, LLM, Total
- Answer text
"""
import time
from backend.app.rag import pipeline

QUERIES = [
    "What is the minimum attendance requirement for semester exams?",
    "What are the pass criteria and grading rules?",
    "What are the placement eligibility criteria?",
    "What is the college history?",
    "What are the college timings?",
]

def run_verification():
    print("=" * 80)
    print("CAMPUSAI — REAL LIVE BACKEND RAG VERIFICATION REPORT")
    print("=" * 80)

    results_summary = []

    for idx, query in enumerate(QUERIES, 1):
        print(f"\n[{idx}/5] QUERY: {query}")
        print("-" * 80)

        # Clear cache for fresh query test
        pipeline.clear_rag_cache()
        t0 = time.time()
        res = pipeline.run_pipeline(query, bypass_cache=True)
        total_time = time.time() - t0

        status = res.get("status")
        grounded = res.get("grounded")
        answer = res.get("answer", "")
        sources = res.get("sources", [])
        retrieval_count = res.get("retrieval_count", 0)
        retrieval_lat = res.get("retrieval_latency", 0.0)
        llm_lat = res.get("llm_latency", 0.0)

        print(f"Status:            {status}")
        print(f"Grounded:          {grounded}")
        print(f"Retrieval Count:   {retrieval_count}")
        print(f"Retrieval Latency: {retrieval_lat * 1000:.1f} ms")
        print(f"LLM Latency:       {llm_lat * 1000:.1f} ms")
        print(f"Total Latency:     {total_time * 1000:.1f} ms")
        print("\nTop Sources / Citations:")
        for sidx, src in enumerate(sources[:3], 1):
            print(f"  [{sidx}] Title: {src.get('title')}")
            print(f"      Page: {src.get('page_number')}, URL: {src.get('source_url')}")
            print(f"      Snippet: {src.get('snippet', '')[:100]}...")

        print("\nAnswer:")
        print(answer)

        results_summary.append({
            "query": query,
            "status": status,
            "grounded": grounded,
            "retrieval_count": retrieval_count,
            "retrieval_lat_ms": round(retrieval_lat * 1000, 1),
            "llm_lat_ms": round(llm_lat * 1000, 1),
            "total_lat_ms": round(total_time * 1000, 1),
            "citations_count": len(sources),
            "answer_preview": answer[:120].replace("\n", " "),
        })

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Query':<45} | {'Status':<10} | {'Hits':<5} | {'Retr(ms)':<8} | {'LLM(ms)':<8} | {'Total(ms)':<9} | {'Citations'}")
    print("-" * 105)
    for r in results_summary:
        print(f"{r['query'][:43]:<45} | {r['status']:<10} | {r['retrieval_count']:<5} | {r['retrieval_lat_ms']:<8} | {r['llm_lat_ms']:<8} | {r['total_lat_ms']:<9} | {r['citations_count']}")

if __name__ == "__main__":
    run_verification()
