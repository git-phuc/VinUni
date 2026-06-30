# Lab 24 — Production Eval + Guardrail Stack

**Sinh viên:** Phạm Đình Phúc  
**MSSV:** 2A202600802  
**Ngày nộp:** 30/06/2026

---

## Tổng quan

Lab này xây dựng lớp **đánh giá (evaluation)** và **bảo vệ (guardrail)** cho RAG pipeline HR Policy từ Day 18, gồm 3 phases:

```
[Day 18 RAG Pipeline]
        │
        ├──► Phase A: RAGAS 50q ──────────► ragas_50q.json
        │     BM25 + Dense hybrid search
        │
        ├──► Phase B: LLM-as-Judge ───────► judge_results.json
        │     swap-and-average + Cohen κ
        │
        └──► Phase C: NeMo Guardrails ────► guard_results.json
              Presidio PII + pattern rails
```

---

## Cài đặt

```bash
# 1. Tạo và kích hoạt venv
python -m venv .venv
.venv\Scripts\activate          # Windows

# 2. Cài dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# 3. Cấu hình API keys
cp .env.example .env
# Điền GEMINI_API_KEY vào .env

# 4. Khởi động Qdrant (optional — dùng cho Day 18 pipeline)
docker compose up -d
```

---

## Chạy từng phase

```bash
# Generate answers từ test set
python make_answers.py           # BM25-only (không cần GPU)
# hoặc
python setup_answers.py          # Full pipeline (cần Qdrant + BGE-M3)

# Phase A — RAGAS evaluation
python src/phase_a_ragas.py      # → reports/ragas_50q.json

# Phase B — LLM-as-Judge
python src/phase_b_judge.py      # → reports/judge_results.json

# Phase C — NeMo Guardrails
python src/phase_c_guard.py      # → reports/guard_results.json

# Chạy tests
pytest tests/ -v                 # 40/40 tests

# Kiểm tra trước khi nộp
python check_lab.py              # 22/22 checks
```

---

## Cấu trúc thư mục

```
Day24-AI-2A202600802-Pham Dinh Phuc/
│
├── src/
│   ├── m1_chunking.py          ← Day 18: chunking
│   ├── m2_search.py            ← Day 18: BM25 + Dense hybrid search
│   ├── m3_rerank.py            ← Day 18: CrossEncoder reranker
│   ├── m4_eval.py              ← Day 18: RAGAS evaluation
│   ├── m5_enrichment.py        ← Day 18: LLM enrichment
│   ├── pipeline.py             ← Day 18: end-to-end pipeline
│   │
│   ├── phase_a_ragas.py        ★ Tasks 1–4: RAGAS 50q eval
│   ├── phase_b_judge.py        ★ Tasks 5–8: LLM-as-Judge
│   └── phase_c_guard.py        ★ Tasks 9–12: Presidio + NeMo Guardrails
│
├── guardrails/
│   ├── config.yml              ← NeMo config
│   └── rails.co                ← Colang dialogue flows
│
├── data/                       ← 25 HR policy docs (tiếng Việt)
│
├── reports/
│   ├── ragas_50q.json          ← Phase A output
│   ├── judge_results.json      ← Phase B output
│   ├── guard_results.json      ← Phase C output
│   └── blueprint.md            ← Task 13: CI/CD blueprint
│
├── analysis/
│   ├── failure_clusters.md     ← Phân tích Phase A
│   └── bias_report.md          ← Phân tích Phase B
│
├── tests/                      ← 40 unit tests (10A + 15B + 15C)
├── test_set_50q.json           ← 50 câu hỏi (factual/multi_hop/adversarial)
├── human_labels_10q.json       ← 10 nhãn nhân (Cohen κ)
├── adversarial_set_20.json     ← 20 adversarial inputs
├── make_answers.py             ← BM25-only answer generator
├── setup_answers.py            ← Full pipeline answer generator
└── check_lab.py                ← Validation script
```

---

## Kết quả

### Phase A — RAGAS

| Distribution | Số câu | Dominant failure |
|---|---|---|
| factual | 20 | faithfulness |
| multi_hop | 20 | faithfulness |
| adversarial | 10 | faithfulness |

*Lưu ý: RAGAS LLM evaluator bị chặn bởi API proxy — xem `analysis/failure_clusters.md` để phân tích chi tiết.*

### Phase B — LLM-as-Judge

| Metric | Giá trị |
|---|---|
| Tổng cặp được judge | 10 |
| Cohen's κ | 0.000 |
| Position bias rate | 100% |
| Verbosity bias | 0% |

*Lưu ý: Heuristic fallback được kích hoạt do Gemini quota hết và 9router bị chặn — xem `analysis/bias_report.md`.*

### Phase C — NeMo Guardrails

| Metric | Giá trị |
|---|---|
| Adversarial pass rate | 20/20 (100%) |
| PII detection | VN_CCCD + VN_PHONE + EMAIL |
| Presidio P95 latency | ~27ms |
| NeMo P95 latency | ~1986ms (pattern fallback) |

---

## Ghi chú kỹ thuật

- **Python 3.14 + NeMo**: NeMo Guardrails chưa hỗ trợ Python 3.14 — dùng `_PatternRails` fallback (regex-based)
- **BGE-M3 segfault**: Dense encoder crash (exit code -1073741819 = EXCEPTION_ACCESS_VIOLATION) trên Windows → dùng `make_answers.py` với BM25-only
- **Gemini quota**: Free tier 20 req/day bị cạn kiệt → `_call_llm()` có heuristic fallback
- **9router blocked**: Tất cả request bị chặn với `PermissionDeniedError`

---

## Điểm số

| Phase | Điểm tối đa |
|---|---|
| Phase A: RAGAS (Tasks 1–4) | 30 |
| Phase B: Judge (Tasks 5–8) | 35 |
| Phase C: Guard (Tasks 9–12 + blueprint) | 35 |
| **Tổng** | **100** |
