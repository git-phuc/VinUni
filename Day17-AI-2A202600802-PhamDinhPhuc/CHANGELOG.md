# Changelog — Day 17 (Memory Systems for AI Agent)

Bản ghi lại các thay đổi đã thực hiện khi dọn dẹp và làm lại bài.

## Tổng quan

Làm lại phần lõi (memory + agent) cho **đúng bản chất** thay vì overfit dataset,
sửa UI, và dọn data sinh ra. Tất cả test pass, benchmark phản ánh đúng câu chuyện
trade-off của Rubric.

## `src/memory_store.py` — viết lại lớp trích xuất & recall

- Thêm `from typing import Any` (trước đây dùng `Any` nhưng chưa import).
- **Bỏ toàn bộ hardcode dataset**: trước đây tên "DũngCT"/"Phúc", các thành phố và
  từng câu correction được nhúng cứng. Nay `extract_profile_updates()` bắt **giá trị
  generic** từ cấu trúc câu: `tên là <X>`, `ở <Nơi>`, `<Z> engineer`, `đồ uống/món ăn
  yêu thích là <X>`, `nuôi <con>`, `N bullet`/`ngắn gọn`, interest `Python/AI/RAG`.
- Tên chỉ nhận khi có copula `tên là …` → *"corgi tên Bơ"* không bị nhầm là tên người dùng.
- Địa điểm: nhận diện hoa/thường **đúng Unicode** (`str.isupper()` thay cho regex
  `[A-ZÀ-Ỹ]` vốn nuốt cả chữ thường có dấu như `đ`); xử lý correction bằng
  negation (`không còn`, `chứ không`…) → ví dụ *"đang ở Huế chứ không còn ở Đà Nẵng"*
  ra đúng **Huế**.
- Không lưu giá trị nghi vấn (`gì`, `đâu`, `ai`…) bắt nhầm từ câu hỏi recall.
- `answer_from_facts()`: trả lời **chỉ từ fact đã lưu**, không còn default cứng.
- `CompactMemoryManager`: tóm tắt được **giới hạn kích thước** (`_cap_summary`) để
  prompt của advanced không phình theo lịch sử — đó mới là điểm lợi của compact.

## `src/agent_baseline.py`

- Fact lưu **theo từng thread** (ephemeral) → sang thread mới là quên (đúng yêu cầu).
- Recall dùng helper chung, bỏ các hàm regex hardcode; thêm `reset_thread()`.

## `src/agent_advanced.py`

- **Sửa lỗi live mode không bao giờ chạy**: `__init__` giờ build LangChain model khi
  có API key (giống baseline). Trước đây advanced luôn rơi về offline.
- Bỏ default tên cứng (`facts.get("name", "DũngCT")`) — không còn “recall ảo”.
- Tách rõ: câu hỏi → `answer_from_facts`, câu trần thuật → acknowledgement; thêm `reset_thread()`.

## `src/app.py` (UI Gradio)

- Nút **Clear** giờ reset cả short-term memory của thread + stats + inspector
  (giữ nguyên `User.md`), không chỉ xoá khung chat.
- Toggle Offline/Live **build model on-demand** khi bật live; báo rõ nếu thiếu key.
- Chặn gửi message rỗng; gọn lại event handler.

## Dọn data

- Xoá `state/profiles` (có file rác `dungct.md` rỗng), `state/chat_logs`,
  `.pytest_cache`, `__pycache__` — **chỉ trong Day17**.

## Kết quả kiểm chứng

`pytest`: **4 passed**.

Standard benchmark (hội thoại ngắn):

| Agent | Recall | Prompt tokens |
|-------|--------|---------------|
| Baseline | 0% | 13.9k |
| Advanced | 100% | 24.1k (tốn hơn — đúng kỳ vọng ở hội thoại ngắn) |

Long-context stress benchmark (hội thoại dài):

| Agent | Recall | Prompt tokens | Compactions |
|-------|--------|---------------|-------------|
| Baseline | 0% | 23.0k | 0 |
| Advanced | 100% | 12.4k (compact giảm ~½) | 4 |

> Live mode đã wire xong nhưng **chưa gọi API thật** (cần key + mạng); chỉ verify model build được.
