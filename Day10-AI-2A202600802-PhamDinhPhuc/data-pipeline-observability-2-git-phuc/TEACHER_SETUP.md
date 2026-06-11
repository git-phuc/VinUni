# 📋 Hướng Dẫn Thiết Lập Giảng Viên (GitHub Classroom)

Hệ thống này giúp bạn tự động hóa việc chấm điểm cho 150+ học viên, quản lý bài nộp tập trung và chống gian lận hiệu quả.

---

## Bước 1: Chuẩn bị Organization

1. Tạo một **GitHub Organization** mới (ví dụ: `VinUni-AI-Class-2024`).
2. Đăng ký **GitHub Education** cho Organization này để được sử dụng miễn phí Private Repositories và GitHub Actions (không giới hạn phút).

---

## Bước 2: Chuẩn bị Template Repository

1. Đăng nhập vào Organization của bạn.
2. Tạo repo `day10-lab-template` (hoặc sử dụng repo hiện có).
3. Đảm bảo repo có đầy đủ các file:
   - `solution.py` (starter code)
   - `raw_data.json`
   - `experiment_report.md`
   - `tests/test_autograder.py` (file chứa unit tests)
4. Vào **Settings** -> **General** -> Tích chọn **Template repository**.

---

## Bước 3: Tạo Assignment trên GitHub Classroom

1. Truy cập [classroom.github.com](https://classroom.github.com) và tạo một **New Assignment**.
2. **Starter Code:** Chọn repo `day10-lab-template` bạn vừa tạo ở Bước 2.
3. **Repository Visibility:** Chọn **Private** để học viên không thể copy bài của nhau.
4. **Enable Feedback Pull Requests:** Tích chọn (khuyến nghị) để dễ dàng để lại nhận xét trên code của học viên.

---

## Bước 4: Cấu hình Autograding (Quan trọng)

Trong mục **Autograding**, hãy thêm 9 bài test sau bằng cách chọn **Add test -> Run command**:

| Test Name | Setup Command | Run Command | Points |
| :--- | :--- | :--- | :--- |
| 1. ETL Functional | `pip install pandas pytest` | `python -m pytest tests/test_autograder.py::TestETLFunctional -v` | 20 |
| 2. ETL Validation | | `python -m pytest tests/test_autograder.py::TestETLValidation -v` | 10 |
| 3. ETL Transform | | `python -m pytest tests/test_autograder.py::TestETLTransformation -v` | 10 |
| 4. Logging | | `python -m pytest tests/test_autograder.py::TestLogging -v` | 10 |
| 5. Timestamp | | `python -m pytest tests/test_autograder.py::TestTimestamp -v` | 10 |
| 6. Report Completion | | `python -m pytest tests/test_autograder.py::TestReportExists -v` | 10 |
| 7. Critical Thinking | | `python -m pytest tests/test_autograder.py::TestReportAnalysis -v` | 10 |
| 8. File Structure | | `python -m pytest tests/test_autograder.py::TestStructure -v` | 10 |
| 9. README Quality | | `python -m pytest tests/test_autograder.py::TestReadme -v` | 10 |

---

## Bước 5: Phân phối và Quản lý

1. Copy **Invitation Link** từ Classroom và gửi cho học viên.
2. Bạn có thể theo dõi danh sách bài nộp và điểm số trực tiếp trên **Classroom Dashboard**.
3. Khi hết hạn, bạn có thể khóa repo của học viên bằng tính năng **Deadline**.
