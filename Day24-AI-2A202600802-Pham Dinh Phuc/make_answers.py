"""
Lightweight answers generator using BM25-only search (no GPU/PyTorch crash risk).
Creates answers_50q.json from test_set_50q.json + HR policy documents.
"""
from __future__ import annotations
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_documents() -> list[dict]:
    """Load all HR policy documents from data/."""
    docs = []
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    for fname in sorted(os.listdir(data_dir)):
        fpath = os.path.join(data_dir, fname)
        if fname.endswith(".md"):
            with open(fpath, encoding="utf-8") as f:
                text = f.read().strip()
            docs.append({"text": text, "source": fname})
        elif fname.endswith(".txt"):
            with open(fpath, encoding="utf-8") as f:
                text = f.read().strip()
            docs.append({"text": text, "source": fname})
    print(f"Loaded {len(docs)} documents")
    return docs


def simple_chunk(doc: dict, chunk_size: int = 300) -> list[dict]:
    """Split document into ~300-word chunks."""
    words = doc["text"].split()
    chunks = []
    for i in range(0, len(words), chunk_size // 2):  # 50% overlap
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) < 20:
            continue
        chunks.append({
            "text": " ".join(chunk_words),
            "source": doc["source"],
        })
    return chunks


def build_bm25(chunks: list[dict]):
    """Build BM25 index from chunks."""
    from rank_bm25 import BM25Okapi
    corpus = [c["text"].lower().split() for c in chunks]
    return BM25Okapi(corpus)


def bm25_search(query: str, bm25, chunks: list[dict], top_k: int = 3) -> list[str]:
    """Return top-k chunk texts for query."""
    scores = bm25.get_scores(query.lower().split())
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [chunks[i]["text"] for i in top_indices if scores[i] > 0]


def main():
    print("=" * 60)
    print("MAKE ANSWERS — BM25-only, no GPU/PyTorch")
    print("=" * 60)

    with open("test_set_50q.json", encoding="utf-8") as f:
        test_set = json.load(f)
    print(f"Loaded {len(test_set)} questions")

    docs = load_documents()
    all_chunks = []
    for doc in docs:
        all_chunks.extend(simple_chunk(doc))
    print(f"Created {len(all_chunks)} chunks")

    print("Building BM25 index...")
    bm25 = build_bm25(all_chunks)

    print(f"Running {len(test_set)} queries...")
    answers = []
    t_start = time.time()

    for i, item in enumerate(test_set):
        contexts = bm25_search(item["question"], bm25, all_chunks, top_k=3)
        if not contexts:
            contexts = [all_chunks[0]["text"]] if all_chunks else ["Không tìm thấy thông tin."]
        answer = contexts[0]  # Use first context as answer (no LLM available)
        answers.append({
            "id": item["id"],
            "distribution": item["distribution"],
            "question": item["question"],
            "answer": answer,
            "contexts": contexts,
            "ground_truth": item["ground_truth"],
        })
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(test_set)}] done ({time.time()-t_start:.1f}s)")

    with open("answers_50q.json", "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(answers)} answers → answers_50q.json")
    print(f"Total time: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
