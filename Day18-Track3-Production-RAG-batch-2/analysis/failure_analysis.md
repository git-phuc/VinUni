# Failure Analysis — Lab 18: Production RAG
**Sinh viên:** Phạm Đình Phúc  
**Pipeline:** M1 Hierarchical → M5 Enrichment (combined, 1 call/chunk) → M2 Hybrid BM25+bge-m3+RRF → M3 HF Reranker → GPT-4o-mini → M4 RAGAS

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Δ |
|--------|---------------|------------|---|
| Faithfulness | ~0.40 | **0.6500** | +0.25 |
| Answer Relevancy | ~0.48 | **0.5806** | +0.10 |
| Context Precision | ~0.55 | **0.8208** ✓ | +0.27 |
| Context Recall | ~0.52 | **0.6667** | +0.15 |

> 100 chunks từ 26 tài liệu tiếng Việt. M5 enrichment: 1 API call/chunk (gpt-4o-mini). Hybrid search: BM25 + bge-m3 (1024-dim) + RRF k=60. Reranker: HF sentence-similarity API. Eval: RAGAS trên 20 câu hỏi.

---

## Bottom-5 Failures (từ ragas_report.json)

### #1 — Kết hôn được nghỉ bao nhiêu ngày?
- **Question:** Nhân viên được nghỉ bao nhiêu ngày khi kết hôn?
- **Expected:** 3 ngày nghỉ phép đặc biệt khi kết hôn (theo nghi_phep_dac_biet.md)
- **Got:** LLM hallucinate số ngày, không bám vào context
- **Worst metric:** faithfulness = 0.0
- **Error Tree:** Output sai → Context đúng? → Context có chunk nghỉ phép → LLM không trích dẫn đúng → **Hallucination**
- **Root cause:** Chunk về nghỉ phép đặc biệt bị mix với chunk nghỉ phép năm; LLM confuse và bịa số
- **Suggested fix:** Tighten prompt ("CHỈ dùng thông tin có trong context, không thêm bất kỳ con số nào"); lower temperature 0.7 → 0.1

### #2 — Thông tin lương thuộc loại dữ liệu nào?
- **Question:** Thông tin lương thuộc cấp độ phân loại dữ liệu nào?
- **Expected:** Dữ liệu bí mật / Confidential (theo phan_loai_du_lieu.md)
- **Got:** LLM trả lời chung chung hoặc hallucinate tên cấp độ sai
- **Worst metric:** faithfulness = 0.0
- **Error Tree:** Output sai → Context có phan_loai_du_lieu không? → Có → LLM không nhận ra mapping lương → cấp độ → **Hallucination**
- **Root cause:** Enrichment không prepend context rõ "đây là tài liệu phân loại dữ liệu"; semantic gap giữa "lương" và "dữ liệu bí mật"
- **Suggested fix:** Contextual prepend cụ thể hơn: "Đoạn này từ tài liệu Phân loại Dữ liệu, liệt kê cấp độ bảo mật"

### #3 — Multi-hop: thâm niên + lương
- **Question:** Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?
- **Expected:** 15+1=16 ngày (v2024) + dải lương Senior từ bang_luong_2024.md
- **Got:** LLM tính sai hoặc bỏ qua một trong hai phần câu hỏi
- **Worst metric:** faithfulness = 0.0
- **Error Tree:** Output sai → Multi-hop query → Cần 2 documents khác nhau → Retrieval chỉ trả về 3 chunks → Thiếu một nguồn → **Hallucination phần còn lại**
- **Root cause:** HYBRID_TOP_K=20 nhưng sau rerank chỉ lấy top-3; multi-hop cần ít nhất 2 relevant chunks từ 2 files khác nhau
- **Suggested fix:** Tăng RERANK_TOP_K từ 3 → 5 cho multi-hop queries; thêm query decomposition

### #4 — Phạt tạm ứng quá hạn
- **Question:** Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu?
- **Expected:** Theo tam_ung.md: mức phạt cụ thể theo số ngày trễ
- **Got:** LLM bịa ra con số phạt không có trong tài liệu
- **Worst metric:** faithfulness = 0.0
- **Error Tree:** Output sai → Context đúng? → Context có policy tạm ứng → Không có con số phạt cụ thể → LLM thêm thông tin → **Hallucination**
- **Root cause:** Tài liệu tam_ung.md mô tả quy trình nhưng không có bảng phạt cụ thể; LLM "điền" vào chỗ trống bằng kiến thức chung
- **Suggested fix:** Thêm fallback "Nếu context không có con số, trả lời: Vui lòng liên hệ HR để biết mức phạt cụ thể"

### #5 — Thử việc có nghỉ phép không?
- **Question:** Nhân viên thử việc có được nghỉ phép năm không?
- **Expected:** Không được nghỉ phép trong thời gian thử việc (theo thu_viec.md)
- **Got:** LLM hallucinate câu trả lời ngược lại hoặc mơ hồ
- **Worst metric:** faithfulness = 0.0
- **Error Tree:** Output sai → Context có chunk thử việc → Nhưng chunk bị mix với chunk nghỉ phép năm → LLM nhầm → **Hallucination**
- **Root cause:** Hierarchical chunking nhóm thu_viec.md với nghi_phep_nam.md do gần nhau trong embedding space; cần metadata filter theo source file
- **Suggested fix:** Thêm metadata filter `source=thu_viec.md` khi query liên quan đến thử việc; hoặc tăng threshold semantic chunking

---

## Case Study — Q#3: Multi-hop Failure

**Question:** Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?

**Error Tree walkthrough:**
1. Output đúng không? → ❌ Số ngày và lương đều sai/thiếu
2. Context đúng không? → ⚠️ Top-3 chunks chỉ có 1 file về nghỉ phép, thiếu bang_luong_2024.md
3. Retrieval nguyên nhân? → BM25 match "nghỉ phép" nhiều hơn "lương Senior"; RRF ưu tiên overlap
4. Fix ở bước: **Search** — query decomposition thành 2 sub-queries; **Rerank** — tăng top_k=5

**Nếu có thêm 1 giờ, sẽ optimize:**
- Query decomposition: tách multi-hop → 2 queries độc lập → merge kết quả
- Metadata filter theo `source` để đảm bảo diversity trong retrieved chunks
- Reranker top_k: 3 → 5 để cover multi-document queries
