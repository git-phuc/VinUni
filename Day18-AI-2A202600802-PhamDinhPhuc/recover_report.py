"""
Recovery script: tái dùng Qdrant collection đã index, chỉ chạy lại eval + save report.
Tránh chờ M5 enrichment (7 phút) và M2 dense indexing (11 phút).
"""
from __future__ import annotations
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.m1_chunking import load_documents, chunk_hierarchical
from src.m2_search import BM25Search, DenseSearch, reciprocal_rank_fusion
from src.m3_rerank import CrossEncoderReranker
from src.m4_eval import load_test_set, evaluate_ragas, failure_analysis, save_report
from config import RERANK_TOP_K, BM25_TOP_K, DENSE_TOP_K, HYBRID_TOP_K, OPENAI_API_KEY

print("=" * 60)
print("RECOVERY: Reusing existing Qdrant collection")
print("=" * 60)

# 1. Chunk (nhanh, để build BM25)
print("\n[1/3] Chunking for BM25 re-index...")
docs = load_documents()
raw_chunks = []
for doc in docs:
    _, children = chunk_hierarchical(doc["text"], metadata=doc["metadata"])
    for c in children:
        raw_chunks.append({"text": c.text, "metadata": c.metadata})
print(f"  ✓ {len(raw_chunks)} chunks")

# 2. BM25 re-index (in-memory, nhanh)
print("\n[2/3] Re-indexing BM25...")
bm25 = BM25Search()
bm25.index(raw_chunks)
print("  ✓ BM25 ready")

# 3. Dense reuse existing Qdrant collection
dense = DenseSearch()  # connects to localhost:6333
reranker = CrossEncoderReranker()
print("  ✓ Dense (existing Qdrant) + Reranker ready")

def run_query(query: str) -> tuple[str, list[str]]:
    bm25_results = bm25.search(query, top_k=BM25_TOP_K)
    dense_results = dense.search(query, top_k=DENSE_TOP_K)
    results = reciprocal_rank_fusion([bm25_results, dense_results], top_k=HYBRID_TOP_K)
    docs_for_rerank = [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
    reranked = reranker.rerank(query, docs_for_rerank, top_k=RERANK_TOP_K)
    contexts = [r.text for r in reranked] if reranked else [r.text for r in results[:3]]

    if OPENAI_API_KEY and contexts:
        try:
            from openai import OpenAI
            client = OpenAI()
            context_str = "\n\n".join(contexts)
            resp = client.chat.completions.create(model="gpt-4o-mini", messages=[
                {"role": "system", "content": "Trả lời CHỈ dựa trên context. Nếu không có → nói 'Không tìm thấy.'"},
                {"role": "user", "content": f"Context:\n{context_str}\n\nCâu hỏi: {query}"},
            ])
            answer = resp.choices[0].message.content
        except Exception as e:
            print(f"  ⚠️  LLM failed: {e}")
            answer = contexts[0]
    else:
        answer = contexts[0] if contexts else "Không tìm thấy."
    return answer, contexts

# 4. Run queries + RAGAS
print("\n[3/3] Running queries + RAGAS eval...")
test_set = load_test_set()
questions, answers, all_contexts, ground_truths = [], [], [], []
for i, item in enumerate(test_set):
    answer, contexts = run_query(item["question"])
    questions.append(item["question"])
    answers.append(answer)
    all_contexts.append(contexts)
    ground_truths.append(item["ground_truth"])
    print(f"  [{i+1}/{len(test_set)}] {item['question'][:55]}...")

print(f"\nRunning RAGAS ({len(test_set)} questions)...")
results = evaluate_ragas(questions, answers, all_contexts, ground_truths)

print("\n" + "=" * 60)
print("PRODUCTION RAG SCORES")
print("=" * 60)
for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
    s = results.get(m, 0)
    print(f"  {'✓' if s >= 0.75 else '✗'} {m}: {s:.4f}")

per_q = results.get("per_question", [])
failures = failure_analysis(per_q)
os.makedirs("reports", exist_ok=True)
save_report(results, failures, path="reports/ragas_report.json")
print(f"\n✅ Report saved to reports/ragas_report.json")
print(f"   Bottom-5 failures: {len(failures[:5])} cases")
