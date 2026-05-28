# Ngày 1 — Bài Tập & Phản Ánh
## Nền Tảng LLM API | Phiếu Thực Hành

**Thời lượng:** 1:30 giờ  
**Cấu trúc:** Lập trình cốt lõi (60 phút) → Bài tập mở rộng (30 phút)

---

## Phần 1 — Lập Trình Cốt Lõi (0:00–1:00)

Chạy các ví dụ trong Google Colab tại: https://colab.research.google.com/drive/172zCiXpLr1FEXMRCAbmZoqTrKiSkUERm?usp=sharing

Triển khai tất cả TODO trong `template.py`. Chạy `pytest tests/` để kiểm tra tiến độ.

**Điểm kiểm tra:** Sau khi hoàn thành 4 nhiệm vụ, chạy:
```bash
python template.py
```
Bạn sẽ thấy output so sánh phản hồi của GPT-4o và GPT-4o-mini.

---

## Phần 2 — Bài Tập Mở Rộng (1:00–1:30)

### Bài tập 2.1 — Độ Nhạy Của Temperature
Gọi `call_openai` với các giá trị temperature 0.0, 0.5, 1.0 và 1.5 sử dụng prompt **"Hãy kể cho tôi một sự thật thú vị về Việt Nam."**

**Bạn nhận thấy quy luật gì qua bốn phản hồi?** (2–3 câu)
> Khi temperature thấp như 0.0, câu trả lời thường ổn định, trực tiếp và ít thay đổi nếu chạy lại nhiều lần. Khi tăng lên 1.0 hoặc 1.5, câu trả lời có xu hướng sáng tạo và đa dạng hơn, nhưng cũng có thể dài dòng hoặc ít chắc chắn hơn. Em thấy temperature giống như nút điều chỉnh giữa độ an toàn và độ sáng tạo của model.

**Bạn sẽ đặt temperature bao nhiêu cho chatbot hỗ trợ khách hàng, và tại sao?**
> Em sẽ đặt khoảng 0.2 hoặc 0.3 cho chatbot hỗ trợ khách hàng. Lý do là chatbot cần trả lời nhất quán, đúng thông tin và ít tự bịa hơn là sáng tạo. Với các tác vụ chăm sóc khách hàng, sự ổn định quan trọng hơn câu trả lời thú vị.

---

### Bài tập 2.2 — Đánh Đổi Chi Phí
Xem xét kịch bản: 10.000 người dùng hoạt động mỗi ngày, mỗi người thực hiện 3 lần gọi API, mỗi lần trung bình ~350 token.

**Ước tính xem GPT-4o đắt hơn GPT-4o-mini bao nhiêu lần cho workload này:**
> Workload mỗi ngày là 10.000 * 3 * 350 = 10.500.000 token. Nếu chỉ tính output theo giá trong bài, GPT-4o là 0.010 USD / 1K token còn GPT-4o-mini là 0.0006 USD / 1K token, nên GPT-4o đắt hơn khoảng 0.010 / 0.0006 = 16.67 lần.

**Mô tả một trường hợp mà chi phí cao hơn của GPT-4o là xứng đáng, và một trường hợp GPT-4o-mini là lựa chọn tốt hơn:**
> GPT-4o đáng dùng hơn khi bài toán cần chất lượng cao, ví dụ phân tích tài liệu quan trọng, reasoning phức tạp, hoặc trả lời các câu hỏi dễ gây sai nếu model hiểu thiếu ngữ cảnh. GPT-4o-mini phù hợp hơn cho các tác vụ số lượng lớn như chatbot FAQ, tóm tắt ngắn, phân loại nội dung, hoặc các bước xử lý đơn giản cần tiết kiệm chi phí.

---

### Bài tập 2.3 — Trải Nghiệm Người Dùng với Streaming
**Streaming quan trọng nhất trong trường hợp nào, và khi nào thì non-streaming lại phù hợp hơn?** (1 đoạn văn)
> Streaming quan trọng nhất khi câu trả lời dài hoặc người dùng đang chờ tương tác trực tiếp, ví dụ chatbot, trợ lý viết code, giải thích bài học, hoặc tạo nội dung dài. Khi thấy chữ hiện dần, người dùng có cảm giác hệ thống đang phản hồi ngay thay vì bị đứng im. Non-streaming phù hợp hơn khi output ngắn, cần xử lý trọn gói trước khi hiển thị, hoặc cần đảm bảo format cuối cùng như JSON, classification label, hay response cho một API backend.


## Danh Sách Kiểm Tra Nộp Bài
- [x] Tất cả tests pass: `pytest tests/ -v`
- [x] `call_openai` đã triển khai và kiểm thử
- [x] `call_openai_mini` đã triển khai và kiểm thử
- [x] `compare_models` đã triển khai và kiểm thử
- [x] `streaming_chatbot` đã triển khai và kiểm thử
- [x] `retry_with_backoff` đã triển khai và kiểm thử
- [x] `batch_compare` đã triển khai và kiểm thử
- [x] `format_comparison_table` đã triển khai và kiểm thử
- [x] `exercises.md` đã điền đầy đủ
- [ ] Sao chép bài làm vào folder `solution` và đặt tên theo quy định 
