from __future__ import annotations

"""Module 3: Reranking — Cross-encoder via HF Inference API + latency benchmark."""

import os, sys, time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RERANK_TOP_K, HF_TOKEN

# HF sentence-similarity models — không cần tải về local
# bge-reranker dùng text-classification (không support sentence-similarity task qua API)
# Dùng multilingual sentence-transformer để rerank — hỗ trợ tiếng Việt
_RERANK_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class RerankResult:
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


def _score_via_hf_api(query: str, texts: list[str], token: str) -> list[float]:
    """Dùng HF sentence_similarity API — Qwen/bge-m3 trên server, không tải về local."""
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=token)
    # sentence_similarity: query vs danh sách docs → cosine scores
    try:
        scores = client.sentence_similarity(
            query,
            other_sentences=texts,
            model=_RERANK_MODEL,  # Qwen/Qwen3-Reranker-0.6B
        )
        return [float(s) for s in scores]
    except Exception as e:
        print(f"  ⚠️  {_RERANK_MODEL} API failed: {e}, trying fallback...")
        scores = client.sentence_similarity(
            query,
            other_sentences=texts,
            model=_FALLBACK_MODEL,  # BAAI/bge-reranker-base
        )
        return [float(s) for s in scores]


class CrossEncoderReranker:
    def __init__(self, model_name: str = _RERANK_MODEL):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        # Không load local model — dùng HF API
        return None

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        """Rerank documents via HF sentence_similarity API (Qwen/bge, không download)."""
        if not documents:
            return []

        texts = [doc["text"] for doc in documents]

        scores = None
        if HF_TOKEN:
            try:
                scores = _score_via_hf_api(query, texts, HF_TOKEN)
            except Exception as e:
                print(f"  ⚠️  HF API rerank failed: {e}")

        # Fallback: score bằng keyword overlap nếu API không dùng được
        if scores is None:
            query_words = set(query.lower().split())
            scores = [
                len(query_words & set(t.lower().split())) / max(len(query_words), 1)
                for t in texts
            ]

        scored = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        return [
            RerankResult(
                text=doc["text"],
                original_score=float(doc.get("score", 0.0)),
                rerank_score=float(score),
                metadata=doc.get("metadata", {}),
                rank=i,
            )
            for i, (score, doc) in enumerate(scored[:top_k])
        ]


class FlashrankReranker:
    """Lightweight alternative (<5ms). Optional."""
    def __init__(self):
        self._model = None

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        # Optional: use flashrank as lightweight alternative
        return []


def benchmark_reranker(reranker, query: str, documents: list[dict], n_runs: int = 5) -> dict:
    """Benchmark latency over n_runs. (Đã implement sẵn)"""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        reranker.rerank(query, documents)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {"avg_ms": sum(times) / len(times), "min_ms": min(times), "max_ms": max(times)}


if __name__ == "__main__":
    query = "Nhân viên được nghỉ phép bao nhiêu ngày?"
    docs = [
        {"text": "Nhân viên được nghỉ 12 ngày/năm.", "score": 0.8, "metadata": {}},
        {"text": "Mật khẩu thay đổi mỗi 90 ngày.", "score": 0.7, "metadata": {}},
        {"text": "Thời gian thử việc là 60 ngày.", "score": 0.75, "metadata": {}},
    ]
    reranker = CrossEncoderReranker()
    for r in reranker.rerank(query, docs):
        print(f"[{r.rank}] {r.rerank_score:.4f} | {r.text}")
