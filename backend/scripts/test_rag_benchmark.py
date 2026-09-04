import time
from backend.app.rag.pipeline import run_pipeline, clear_rag_cache

clear_rag_cache()

test_questions = [
    "What is the minimum attendance requirement for examinations?",
    "Who is the Head of the Department of CSE and what is their designation?",
    "List the faculty members in Computer Science and Engineering",
    "What are the latest examination guidelines and regulations?",
    "What is the establishment history and vision of MITS?"
]

for i, q in enumerate(test_questions, 1):
    res = run_pipeline(q, bypass_cache=True)
    st = res.get("status")
    emb = res.get("embedding_ms")
    ret = res.get("retrieval_ms")
    prm = res.get("prompt_ms")
    cit = res.get("citation_ms")
    llm_t = res.get("llm_ms")
    tot = res.get("total_ms")
    grd = res.get("grounded")
    srcs = res.get("sources", [])
    ans = res.get("answer", "")[:150]
    
    print(f"=== Question {i}: {q} ===")
    print(f"Status:       {st}")
    print(f"Embedding:    {emb} ms")
    print(f"Retrieval:    {ret} ms")
    print(f"Prompt Prep:  {prm} ms")
    print(f"Citations:    {cit} ms")
    print(f"LLM Gen:      {llm_t} ms")
    print(f"Total:        {tot} ms")
    print(f"Grounded:     {grd}")
    print(f"Sources ({len(srcs)}):")
    for s in srcs[:2]:
        title = s.get("title")
        url = s.get("source_url")
        print(f"  - {title} ({url})")
    print(f"Answer Snippet: {ans}...")
    print()
