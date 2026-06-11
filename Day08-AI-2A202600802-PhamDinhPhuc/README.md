# Day08 - RAG Pipeline

**Sinh viên:** Pham Dinh Phuc  
**MSSV:** 2A202600802

## Cấu trúc

```text
Day08-AI-2A202600802-PhamDinhPhuc/
├── 01-ca-nhan/   # 10 task cá nhân, test bằng tests/test_individual.py
└── 02-nhom/      # group_project và evaluation pipeline
```

## Chạy phần cá nhân

```powershell
cd 01-ca-nhan
python -m pytest tests/ -v
```

Nếu máy chưa có `pytest`, có thể chạy test bằng `unittest`:

```powershell
python -m unittest discover -s tests -v
```

## Ghi chú dữ liệu thật

`01-ca-nhan/data/landing/` cần dữ liệu thật trước khi nộp:

- `legal/`: tối thiểu 3 file PDF/DOCX từ nguồn pháp luật chính thống.
- `news/`: tối thiểu 5 bài báo crawl bằng Tavily hoặc crawler thật, có URL, title, ngày crawl và nội dung.

Sau khi có dữ liệu thật, chạy lại Task 3 để tạo Markdown trong `data/standardized/`.
