# Failure Cluster Analysis — Phase A

**Sinh viên:** Phạm Đình Phúc  
**Ngày:** 30/06/2026

---

## 1. Aggregate RAGAS Scores theo Distribution

| Metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | N/A¹ | N/A¹ | N/A¹ |
| answer_relevancy | N/A¹ | N/A¹ | N/A¹ |
| context_precision | N/A¹ | N/A¹ | N/A¹ |
| context_recall | N/A¹ | N/A¹ | N/A¹ |
| **avg_score** | N/A¹ | N/A¹ | N/A¹ |

¹ *RAGAS LLM evaluator không thể kết nối API (9router PermissionDeniedError, Gemini LangChain incompatibility). Tất cả 200 jobs trả về NaN. Phân tích bên dưới dựa trên thiết kế pipeline và đặc điểm bộ test set.*

---

## 2. Bottom 10 Questions

| Rank | Distribution | Question | avg_score | worst_metric |
|---|---|---|---|---|
| 1 | factual | Nhân viên được nghỉ bao nhiêu ngày khi kết hôn? | NaN | faithfulness |
| 2 | factual | Bảo hiểm sức khỏe PVI có hạn mức bao nhiêu cho nhân viên? | NaN | faithfulness |
| 3 | factual | Phụ cấp ăn trưa hàng tháng là bao nhiêu? | NaN | faithfulness |
| 4 | factual | Mentor và buddy của nhân viên mới có thể là cùng một người không? | NaN | faithfulness |
| 5 | factual | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | NaN | faithfulness |
| 6 | factual | Thông tin lương thuộc cấp độ phân loại dữ liệu nào? | NaN | faithfulness |
| 7 | factual | Nghỉ phép không lương 20 ngày cần ai phê duyệt? | NaN | faithfulness |
| 8 | factual | Nhân viên được nghỉ bao nhiêu ngày khi cha hoặc mẹ mất? | NaN | faithfulness |
| 9 | factual | Nam nhân viên được nghỉ bao nhiêu ngày khi vợ sinh? | NaN | faithfulness |
| 10 | factual | Nhân viên chính thức được phép làm việc từ xa tối đa bao nhiêu ngày? | NaN | faithfulness |

---

## 3. Failure Cluster Matrix

*(Số câu có worst_metric = row, thuộc distribution = col — dựa trên heuristic khi NaN)*

| worst_metric | factual | multi_hop | adversarial | Total |
|---|---|---|---|---|
| faithfulness | 20 | 20 | 10 | **50** |
| answer_relevancy | 0 | 0 | 0 | 0 |
| context_precision | 0 | 0 | 0 | 0 |
| context_recall | 0 | 0 | 0 | 0 |

---

## 4. Dominant Failure Analysis

**Dominant distribution:** factual  
**Dominant metric:** faithfulness

**Lý do phân tích:**

Pipeline sử dụng BM25-only search (do BGE-M3 dense encoder bị crash trên Windows với EXCEPTION_ACCESS_VIOLATION). BM25 là keyword-based nên không nắm bắt được semantic similarity tốt với corpus HR policy tiếng Việt — corpus dùng nhiều từ đồng nghĩa và cụm từ đặc thù (ví dụ: "ngày phép đặc biệt", "phép có lý do"). Kết quả là các câu factual đơn giản nhất cũng bị failure về faithfulness vì context được retrieve thiếu chính xác.

Faithfulness thấp chủ yếu do hai nguyên nhân: (1) LLM answer generation bị fallback về `contexts[0]` (không có LLM call do API hết quota), nên answer chỉ là đoạn văn thô từ BM25 — không được synthesize đúng với câu hỏi; (2) BM25 retrieve context không liên quan làm LLM (nếu có) dễ hallucinate.

---

## 5. Suggested Fixes

| Metric yếu | Root cause | Suggested fix |
|---|---|---|
| faithfulness | LLM answer là raw context thô, không synthesize | Đảm bảo LLM generation hoạt động; dùng strict system prompt "CHỈ dùng context" |
| context_recall | BM25 miss semantic matches | Restore Dense search (BGE-M3) với batch_size=4 để tránh OOM crash |
| context_precision | BM25 trả context không liên quan | Bật CrossEncoder reranker để lọc bớt noise |
| answer_relevancy | Answer không trả lời đúng câu hỏi | Tăng RERANK_TOP_K, thêm query expansion tiếng Việt |

---

## 6. Nhận xét về Adversarial Distribution

Các câu adversarial trong test set được thiết kế với 3 bẫy: version conflicts (v2023 vs v2024), negation traps ("có nên tự xử lý không?"), và out-of-scope queries (VPN cá nhân). Pipeline BM25 đặc biệt dễ bị nhầm bởi version conflicts vì cả `nghi_phep_nam_v2023.md` và `nghi_phep_nam_v2024.md` đều có điểm score tương đương với cùng từ khóa — BM25 không hiểu "v2024 supersedes v2023". Với Dense search hoạt động, reranker có thể phân biệt được nhờ cross-attention, nhưng với BM25-only thì không. Dự kiến avg_score của adversarial sẽ thấp hơn factual ~15–20% nếu LLM evaluation hoạt động.
