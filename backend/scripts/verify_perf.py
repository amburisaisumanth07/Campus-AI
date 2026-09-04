"""
Performance and Cache Latency Benchmark for CampusAI RAG.
"""
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.pipeline import run_pipeline


def benchmark():
    query = "What is the minimum attendance requirement for semester exams?"

    # 1. Warm-up / Initial Call
    t0 = time.perf_counter()
    res1 = run_pipeline(query, bypass_cache=True)
    t1 = time.perf_counter() - t0

    # 2. Cached Call
    t0 = time.perf_counter()
    res2 = run_pipeline(query)
    t2 = time.perf_counter() - t0

    print("=" * 60)
    print("CAMPUSAI RAG PERFORMANCE BENCHMARK")
    print("=" * 60)
    print(f"Initial Uncached Query Latency: {t1:.3f}s")
    print(f"Cached Query Latency:          {t2*1000:.2f}ms")
    print(f"Speedup Factor:                {t1 / max(t2, 0.0001):.1f}x")
    print(f"Grounded:                      {res2['grounded']}")
    print(f"Citations Count:               {len(res2['citations'])}")
    print("=" * 60)


if __name__ == "__main__":
    benchmark()
