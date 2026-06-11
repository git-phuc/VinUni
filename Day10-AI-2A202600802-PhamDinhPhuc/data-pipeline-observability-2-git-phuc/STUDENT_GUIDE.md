# 🎓 Hướng Dẫn Làm Bài & Nộp Bài (Dành cho Học viên)

Chào mừng bạn đến với bài Lab ngày 10! Bài này sẽ được chấm điểm tự động thông qua **GitHub Classroom**. Hãy làm theo các bước dưới đây để hoàn thành bài tập.

---

## Bước 1: Nhận bài tập (Accept Assignment)

1. Click vào link bài tập mà giảng viên đã gửi cho bạn.
2. Đăng nhập vào GitHub (nếu chưa).
3. Nhấn nút **"Accept this assignment"**. 
4. **Lưu ý Kiểm tra Emmail để accept Invitation vào bài kiểm tra.**
5. GitHub sẽ tự động tạo cho bạn một repository riêng trong Organization của lớp.
6. Chờ 1-2 phút, sau đó click vào link repo vừa được tạo để bắt đầu.

---

## Bước 2: Clone dự án về máy

Mở terminal trên máy tính của bạn và chạy lệnh sau (thay `URL_CUA_BAN` bằng link repo của bạn):

```bash
git clone URL_CUA_BAN
```

---

## Bước 3: Chuẩn bị môi trường & Làm bài (Tasks)

Trước khi bắt đầu, bạn nên tạo môi trường ảo để quản lý các thư viện:

1. **Khởi tạo và kích hoạt Virtual Environment (venv):**
   - **Trên Windows:**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **Trên macOS/Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

2. **Cài đặt thư viện cần thiết:**
   ```bash
   pip install pandas pytest
   ```

3. **Thực hiện các nhiệm vụ:**
   - **Viết code ETL:** Mở file `solution.py` và hoàn thành các hàm `extract`, `validate`, `transform`, `load` theo yêu cầu trong docstrings.
   - **Làm báo cáo Stress Test:** Thử nghiệm chạy Agent với dữ liệu "sạch" và dữ liệu "rác", sau đó ghi lại kết quả vào bảng trong file `experiment_report.md`.
   - **Cập nhật README:** Điền mã số học viên (Student ID) và mô tả ngắn gọn về bài làm của bạn vào file `README.md`.

---

## Bước 4: Kiểm tra tại máy (Local Test)

Sau khi viết code, bạn nên chạy thử để đảm bảo không có lỗi:

```bash
python solution.py
```
Sau đó kiểm tra xem file `processed_data.csv` đã được tạo ra chưa.

---

## Bước 5: Nộp bài & Xem điểm

Mỗi khi bạn `push` code lên GitHub, hệ thống sẽ tự động chấm điểm.

1. **Lệnh nộp bài:**
   ```bash
   git add .
   git commit -m "feat: hoan thanh bai lab ngay 10"
   git push origin main
   ```
2. **Xem điểm:**
   - Quay lại trang repo của bạn trên GitHub.
   - Click vào tab **"Actions"**.
   - Chọn lần chạy (Workflow Run) mới nhất.
   - Bạn sẽ thấy điểm số và chi tiết các bài test đạt được/thất bại.

> [!TIP]
> **Gợi ý:** Bạn có thể push code nhiều lần trước khi hết hạn. Hệ thống sẽ lấy điểm của lần push cuối cùng.

Chúc bạn làm bài tốt!
