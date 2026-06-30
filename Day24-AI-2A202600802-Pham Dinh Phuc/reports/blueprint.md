# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh viên:** Phạm Đình Phúc  
**Ngày:** 30/06/2026

---

## Guard Stack Architecture

```
User Input
    │
    ▼ (~27ms P95)
[Presidio PII Scan]
    │ block if: VN_CCCD / VN_PHONE / EMAIL detected
    │ action:   return 400 + "PII detected in query"
    ▼ (~1986ms P95 — pattern fallback)
[NeMo Input Rail]
    │ block if: off-topic / jailbreak / prompt injection
    │ action:   return 503 + refuse message
    ▼
[RAG Pipeline (Day 18)]
    │ M1 Chunk → M2 Search → M3 Rerank → GPT-4o-mini
    ▼
[NeMo Output Rail]
    │ flag if:  PII in response / sensitive content
    │ action:   replace with safe response
    ▼
User Response
```

---

## Latency Budget

*(Điền từ kết quả Task 12 — measure_p95_latency())*

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---|---|---|---|
| Presidio PII | 22.83 | 26.95 | 26.95 | <10ms |
| NeMo Input Rail | 0.08 | 1986.29 | 1986.29 | <300ms |
| RAG Pipeline | — | — | — | <2000ms |
| NeMo Output Rail | — | — | — | <300ms |
| **Total Guard** | 23.46 | **2009.13** | 2009.13 | **<500ms** |

**Budget OK?** [x] No  
**Comment:** Bottleneck là NeMo Rail (P95 ≈ 1986ms) do dùng `_PatternRails` fallback thay vì NeMo LLM thực (Python 3.14 chưa tương thích). Với NeMo LLM thực tế P95 ≈ 200–400ms — tổng vẫn có thể vượt 500ms budget, cần cache kết quả NeMo cho các query pattern lặp lại. Presidio P95 ≈ 27ms vượt budget <10ms — tối ưu bằng cách dùng `BatchAnalyzer` thay vì `analyze()` tuần tự.

---

## CI/CD Gates (phải pass trước khi merge to main)

```yaml
# .github/workflows/rag_eval.yml
- name: RAGAS Quality Gate
  run: python src/phase_a_ragas.py
  env:
    MIN_FAITHFULNESS: 0.75
    MIN_AVG_SCORE: 0.65

- name: Guardrail Gate
  run: pytest tests/test_phase_c.py -k "test_adversarial_suite_pass_rate"
  # phải ≥ 15/20 (75%)

- name: Latency Gate
  run: python -c "from src.phase_c_guard import measure_p95_latency; ..."
  # P95 total < 500ms
```

---

## Monitoring Dashboard (production)

| Metric | Alert Threshold | Action |
|---|---|---|
| RAGAS faithfulness (daily sample) | < 0.70 | Page on-call |
| Adversarial block rate | < 80% | Review new attack patterns |
| Guard P95 latency | > 600ms | Scale NeMo model |
| PII detected count | spike >10/hour | Security alert |

---

## Kết quả thực tế từ Lab

| | Kết quả |
|---|---|
| RAGAS avg_score (50q) | NaN (LLM API unavailable — 9router blocked, Gemini quota hết) |
| Worst metric | faithfulness (tất cả 50 câu) |
| Dominant failure distribution | factual |
| Cohen's κ | 0.000 (heuristic fallback — chưa đo được thực tế) |
| Adversarial pass rate | 20 / 20 (100%) |
| Guard P95 latency (Presidio) | 26.95 ms |
| Guard P95 latency (NeMo) | 1986.29 ms (pattern fallback) |
| Guard P95 latency (Total) | 2009.13 ms |

---

## Nhận xét & Cải tiến

Điều hoạt động tốt nhất trong lab này là **Presidio PII detection**: phát hiện VN_CCCD, VN_PHONE, EMAIL chính xác với P95 ≈ 27ms — chấp nhận được cho production. Adversarial guardrail đạt 20/20 pass rate nhờ pattern-based rails hoạt động ổn định không phụ thuộc LLM.

Điều cần cải thiện quan trọng nhất là **LLM connectivity**: cả RAGAS evaluation (Phase A) lẫn LLM-as-Judge (Phase B) đều không hoạt động được do API bị chặn/hết quota. Trong production, cần có LLM API key riêng với rate limit đủ cao, không dùng shared proxy.

Nếu deploy production thực sự, tôi sẽ: (1) thay `_PatternRails` bằng NeMo LLM thực với Python 3.11 để giảm latency xuống ~300ms; (2) thêm **response caching** cho các query pattern lặp lại nhằm giảm P95 total xuống dưới 500ms budget; (3) dùng **BGE-M3 dense search** thay BM25-only để cải thiện faithfulness — cần giải quyết OOM crash bằng cách giảm batch_size hoặc dùng ONNX CPU runtime thay PyTorch.
