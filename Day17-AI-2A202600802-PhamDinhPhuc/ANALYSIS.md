# Kết quả Benchmark & Phân tích — Day 17 (Memory Systems for AI Agent)

Tài liệu này là phần **phân tích kết quả** (Guide — Bước 8) đối chiếu trực tiếp với
`Rubric.md`. Bảng số được sinh tự động bởi `src/benchmark.py` và lưu ở
`metrics/benchmark_results.{md,json}`.

## 1. Cách chạy

```bash
cd src
python -m pytest test_agents.py -v     # 4 passed
python benchmark.py                    # in bảng + lưu metrics/benchmark_results.{md,json}
```

Benchmark chạy **offline (rule-based)** để kết quả tái lập được và không tốn API.

## 2. Bảng kết quả (đủ 6 cột bắt buộc theo Rubric)

### 2.1 Standard Benchmark (10 phiên hội thoại ngắn — `data/conversations.json`)

| Agent | Agent Tokens Only | Prompt Tokens Processed | Cross-Session Recall | Response Quality | Memory Growth (Bytes) | Compactions |
|-------|------:|------:|:------:|:------:|------:|------:|
| Baseline Agent | 1382 | 13 912 | 0.00% | 0.00% | 0 | 0 |
| Advanced Agent | 1756 | 24 142 | **100.00%** | **100.00%** | 273 | 0 |

### 2.2 Long-Context Stress Benchmark (1 phiên rất dài — `data/advanced_long_context.json`)

| Agent | Agent Tokens Only | Prompt Tokens Processed | Cross-Session Recall | Response Quality | Memory Growth (Bytes) | Compactions |
|-------|------:|------:|:------:|:------:|------:|------:|
| Baseline Agent | 371 | 22 964 | 0.00% | 0.00% | 0 | 0 |
| Advanced Agent | 342 | **12 372** | **100.00%** | **100.00%** | 185 | **4** |

> Điểm mấu chốt: ở hội thoại **ngắn**, Advanced *tốn token hơn*; ở hội thoại **dài**,
> compact memory kéo `Prompt Tokens Processed` của Advanced xuống **gần một nửa** so với Baseline.

## 3. Phân tích

### 3.1 Vì sao Advanced recall tốt hơn Baseline (0% → 100%)

Câu hỏi recall luôn được hỏi ở một **thread mới** (`benchmark.py` đặt
`recall_thread = f"recall-{conv_id}-{i}"`).

- **Baseline** chỉ có short-term memory trong cùng thread. Sang thread mới là rỗng →
  trả lời "chưa có thông tin" → recall 0%. Đây là hành vi *đúng kỳ vọng* của mốc đối chứng.
- **Advanced** ghi fact ổn định vào `User.md` (persistent) theo `user_id`. Thread mới vẫn
  đọc lại được hồ sơ → recall 100%.

### 3.2 Vì sao Advanced tốn token hơn ở hội thoại ngắn (Rubric 75–90)

Standard: Advanced `Prompt Tokens Processed` = 24 142 > Baseline 13 912. Vì mỗi lượt Advanced
phải **kéo theo `User.md` + summary** vào ngữ cảnh. Ở hội thoại ngắn, lịch sử vốn đã nhỏ nên
phần overhead của profile/summary **không được bù lại** → compact chưa kịp phát huy (0 lần
compact ở Standard). Kết luận: **compact không phải lúc nào cũng thắng**; với hội thoại ngắn
nó là chi phí thuần.

### 3.3 Vì sao Compact chủ yếu tối ưu `Prompt Tokens Processed` (Rubric 75–90)

Stress: Advanced 12 372 vs Baseline 22 964 prompt tokens, với **4 lần compaction**.

- Baseline nhồi **toàn bộ** lịch sử vào mỗi lượt → ngữ cảnh phình tuyến tính theo độ dài thread.
- Advanced khi vượt ngưỡng token sẽ **nén các lượt cũ thành summary có giới hạn kích thước**
  (`CompactMemoryManager._cap_summary`) và chỉ giữ vài lượt gần nhất → ngữ cảnh bị **chặn trên**.
- Vì compact tác động vào *lượng ngữ cảnh mang theo mỗi lượt*, nó tối ưu mạnh ở cột
  **Prompt Tokens Processed**, chứ không phải ở `Agent Tokens Only` (token sinh ra ~ không đổi:
  342 vs 371).

### 3.4 Memory growth & rủi ro (Rubric 75–90)

`Memory Growth` = kích thước `User.md` (273 B standard, 185 B stress). File tăng theo số fact
ổn định. Rủi ro khi mở rộng:

- **Phình to**: nhiều phiên → `User.md` lớn dần, làm tăng lại prompt cost (mất chính lợi thế của compact).
- **Lưu sai fact**: nếu trích nhầm từ câu hỏi/đùa cợt, hồ sơ bị nhiễu.
- Hướng giảm thiểu: confidence threshold, memory decay, dọn fact trùng/cũ.

## 4. Tách bạch 3 lớp memory (Rubric 75–90)

| Lớp | Phạm vi | Hiện thực |
|-----|---------|-----------|
| **Short-term** | trong 1 thread | `SessionState.messages` (baseline) / kept messages (advanced) |
| **Persistent** | xuyên thread/phiên | `UserProfileStore` → `state/profiles/<user_id>.md` |
| **Compact** | nén lịch sử dài | `CompactMemoryManager` (ngưỡng token + giữ N lượt + summary có cap) |

## 5. Đối chiếu Rubric

- **0–60 (triển khai cơ bản):** ✓ Baseline thread-only, Advanced có `User.md`, có compact, dataset
  tiếng Việt tự nhiên (có correction/follow-up/open thread), README/Guide/Rubric đầy đủ.
- **60–75 (benchmark + test lõi):** ✓ benchmark cùng input cho cả 2 agent, đủ 6 cột; `pytest`
  có test cho `User.md` read/write/edit, compact trigger, cross-session recall, và compact giảm
  prompt load — **4 passed**.
- **75–90 (phân tích thật):** ✓ có Standard + Stress; stress đủ dài để lộ chi phí ngữ cảnh của
  baseline (22 964 prompt tokens); giải thích vì sao compact không phải lúc nào cũng thắng và vì
  sao chủ yếu tối ưu prompt tokens; nêu rủi ro phình file.
- **90–100 (bonus thực dụng):** ✓ **Conflict handling** — correction "Huế → Đà Nẵng",
  "backend → MLOps engineer" được xử lý bằng nhận diện phủ định (`không còn`, `chứ không`) +
  latest-wins, không giữ đồng thời fact cũ sai; ✓ **Guard chống lưu sai** — không trích fact có
  giá trị nghi vấn (`gì/đâu/ai`) từ câu hỏi recall, tên chỉ nhận khi có copula "tên là" nên
  *"corgi tên Bơ"* không bị nhầm; ✓ **Entity extraction** có cấu trúc (name/location/profession/
  drink/food/pet/style/interests) thay vì lưu thô.
