# Reflection — Lab 18: Production RAG Pipeline
**Họ tên:** Phạm Đình Phúc  
**Ngày:** 2026-06-22

---

## Phần 1: Mapping bài giảng → Code

| Lecture Concept | Module | Hàm cụ thể | Observation |
|----------------|--------|-------------|-------------|
| Semantic chunking | M1 | `chunk_semantic()` | Threshold 0.85 nhóm câu cùng chủ đề bằng cosine similarity của `all-MiniLM-L6-v2`. Tạo ít chunks hơn basic nhưng mỗi chunk giữ nguyên ý nghĩa ngữ nghĩa. |
| Hierarchical chunking | M1 | `chunk_hierarchical()` | Parent (2048 chars) chứa ngữ cảnh rộng, child (256 chars) để retrieve chính xác. Mỗi child có `parent_id` → khi retrieve child sẽ trả về parent để có đủ context. |
| Structure-aware chunking | M1 | `chunk_structure_aware()` | Parse markdown headers bằng regex `^#{1,3}\s+.+$` → chunk theo section logic. Metadata `section` giúp filter theo chủ đề khi cần. |
| BM25 + Dense fusion | M2 | `reciprocal_rank_fusion()` | RRF giải quyết vấn đề score scale khác nhau giữa BM25 và cosine: `1/(k + rank)` chuẩn hóa tất cả về cùng không gian. k=60 giảm ảnh hưởng của rank 1 để tránh over-weight. |
| Vietnamese BM25 | M2 | `segment_vietnamese()` + `BM25Search` | underthesea tokenize nối từ ghép bằng `_` → phải replace để BM25 split đúng token. Không segment thì "nghỉ phép" thành 2 token riêng lẻ, mất đặc trưng tiếng Việt. |
| Dense vector search | M2 | `DenseSearch.index()` + `.search()` | BAAI/bge-m3 (1024-dim) index vào Qdrant với cosine distance. `query_points()` thay `search()` cho qdrant-client >= 2.0. |
| Cross-encoder reranking | M3 | `CrossEncoderReranker.rerank()` | bge-reranker-v2-m3 score từng pair (query, doc) → rerank top-20 → top-3. Latency cao hơn bi-encoder nhưng precision tốt hơn vì xem xét query-doc jointly. |
| RAGAS 4 metrics | M4 | `evaluate_ragas()` | Faithfulness (LLM có hallucinate không), Answer Relevancy (câu trả lời có liên quan query không), Context Precision (context có noise không), Context Recall (có đủ context không). Cần OPENAI_API_KEY vì RAGAS dùng LLM judge. |
| Failure Diagnostic Tree | M4 | `failure_analysis()` | Map worst metric → root cause: faithfulness thấp → LLM hallucinating; context_recall thấp → chunking thiếu; context_precision thấp → cần reranking. |
| Contextual embeddings | M5 | `contextual_prepend()` | Anthropic benchmark giảm 49% retrieval failure. Prepend 1 câu mô tả chunk nằm ở đâu trong tài liệu → embedding vector mang thêm context, giảm ambiguity. |
| HyDE / HyQA | M5 | `generate_hypothesis_questions()` | Generate câu hỏi giả định chunk có thể trả lời. Index cả questions → bridge vocabulary gap giữa query của user và text trong chunk. |
| Combined enrichment | M5 | `_enrich_single_call()` | 1 API call/chunk thay vì 4 calls riêng → giảm latency và cost 4x. Single JSON response chứa summary + questions + context + metadata. |

---

## Phần 2: Khó khăn & Giải quyết

### Lỗi 1: qdrant-client API thay đổi
- **Error:** `AttributeError: 'QdrantClient' object has no attribute 'search'`  
- **Debug:** Đọc ASSIGNMENT.md thấy ghi chú `⚠️ LƯU Ý: qdrant-client >= 2.0 dùng query_points(), KHÔNG phải search()`  
- **Fix:** Dùng `self.client.query_points(collection, query=query_vector, limit=top_k)` và đọc từ `response.points`

### Lỗi 2: BM25 tokenization mismatch tiếng Việt
- **Error:** BM25 không tìm được "nghỉ phép" vì underthesea output "nghỉ_phép" (1 token) nhưng query "nghỉ phép" split thành 2 tokens
- **Debug:** Test thủ công với `segment_vietnamese("nghỉ phép")`
- **Fix:** `replace("_", " ")` sau `word_tokenize()` để đồng nhất tokenization

### Lỗi 3: RAGAS cần Python 3.11+ cho asyncio
- **Error:** `RuntimeError: This event loop is already running` trên Python 3.10
- **Debug:** Đọc README Prerequisites
- **Fix:** Dùng Python 3.11+; wrap evaluate_ragas trong try/except để fallback gracefully

### Lỗi 4: FlagEmbedding vs sentence_transformers CrossEncoder
- **Error:** `FlagReranker` crash với `transformers>=5.0`
- **Debug:** ASSIGNMENT.md ghi rõ `⚠️ Dùng sentence_transformers.CrossEncoder, KHÔNG dùng FlagEmbedding`
- **Fix:** `from sentence_transformers import CrossEncoder` thay vì `from FlagEmbedding import FlagReranker`

---

## Phần 3: Action Plan cho Project

## Project: HR Policy QA Bot (VinUni Internal)

### Hiện tại
- RAG pipeline hiện tại: basic paragraph splitting + single BM25 search + no reranking
- Known issues:
  - Mất ngữ cảnh khi câu hỏi cần multi-hop (nghỉ phép + thâm niên)
  - Version confusion: trả lời theo policy cũ (v2023) khi user hỏi policy hiện hành (v2024)
  - BM25 đơn độc miss câu hỏi paraphrase (user hỏi "휴가" → không match "nghỉ phép")

### Plan áp dụng
1. [ ] **Chunking strategy:** Dùng `chunk_structure_aware()` cho policy documents (có markdown headers rõ ràng) + `chunk_hierarchical()` cho PDFs (BCTC, Nghị định). Structure-aware giữ nguyên section context, hierarchical cho recall tốt khi cần look-up cụ thể.
2. [ ] **Search:** Hybrid BM25 + bge-m3 dense + RRF. BM25 tốt cho từ khóa exact (số ngày, mức phạt), dense tốt cho semantic similarity. RRF combine 2 list mà không cần tune threshold.
3. [ ] **Reranking:** CrossEncoder bge-reranker-v2-m3, top-20 → top-3. Cần vì HR corpus có nhiều documents về cùng chủ đề (nghỉ phép v2023 vs v2024) — reranker sẽ chọn đúng version.
4. [ ] **Evaluation:** RAGAS với custom test set 50 Q&A pairs tiếng Việt. Focus vào context_recall (thiếu chunk) và context_precision (chunk sai version). Đặt threshold: faithfulness > 0.8, context_recall > 0.75.
5. [ ] **Enrichment:** `contextual_prepend()` cho mỗi chunk với document title + version date (e.g., "Đoạn này từ Chính sách Nghỉ phép năm 2024, quy định số ngày nghỉ phép chính thức hiện hành.") → giảm version confusion khi embed.

### Timeline
- Tuần 1: Implement chunking (structure + hierarchical) cho toàn bộ 40 docs, index Qdrant
- Tuần 2: Setup hybrid search + RRF, build test set 50 Q&A, chạy RAGAS baseline
- Tuần 3: Add reranking + contextual enrichment, so sánh RAGAS scores trước/sau
- Tuần 4: Fine-tune threshold (RRF k, semantic threshold), deploy internal API endpoint
