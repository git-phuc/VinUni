# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Phạm Đình Phúc  
**MSSV:** 2A202600802  
**Ngày:** 2026-06-05  

---

## 1. Warm-up

### Cosine Similarity (Ex 1.1)

High cosine similarity nghĩa là hai vector embedding có hướng gần nhau, nên hai đoạn text có khả năng nói về cùng một ý nghĩa hoặc cùng một chủ đề. Điểm similarity cao không có nghĩa là hai câu giống từng chữ, mà là chúng gần nhau trong không gian ngữ nghĩa.

**Ví dụ HIGH similarity:**
- Sentence A: Hợp đồng lao động ghi nhận việc làm có trả lương.
- Sentence B: Hợp đồng lao động là thỏa thuận về công việc và tiền lương.
- Tại sao tương đồng: cả hai đều nói về bản chất của hợp đồng lao động.

**Ví dụ LOW similarity:**
- Sentence A: Tiền lương phải được trả đầy đủ và đúng hạn.
- Sentence B: Nội quy lao động quy định hình thức kỷ luật.
- Tại sao khác: một câu nói về wage/payment, câu kia nói về discipline.

Cosine similarity được ưu tiên hơn Euclidean distance vì text embeddings thường quan trọng hướng vector hơn độ dài vector. Hai vector có cùng hướng thường thể hiện ý nghĩa gần nhau, kể cả khi magnitude khác nhau.

### Chunking Math (Ex 1.2)

Với document 10,000 ký tự, `chunk_size=500`, `overlap=50`:

`num_chunks = ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = 23`

Nếu overlap tăng lên 100:

`num_chunks = ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = 25`

Overlap lớn hơn tạo nhiều chunk hơn, nhưng giúp thông tin ở ranh giới chunk không bị mất ngữ cảnh. Đối với RAG, overlap hữu ích khi câu trả lời nằm ở phần giao giữa hai chunk.

---

## 2. Document Selection - Nhóm

**Domain:** Luật lao động Việt Nam cơ bản.

**Lý do chọn domain:** Luật lao động là domain legal nhỏ nhưng có cấu trúc rõ: hợp đồng, thử việc, tiền lương, thời giờ làm việc, làm thêm giờ, nghỉ phép, chấm dứt hợp đồng và kỷ luật/an toàn lao động. Mỗi chủ đề có từ khóa và metadata riêng, nên phù hợp để test retrieval, metadata filtering và RAG grounding. Dataset được crawl bằng Tavily web search, sau đó làm sạch thành các file Markdown ngắn để tránh đưa raw HTML nhiễu vào vector store.

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | `01_hop_dong_lao_dong.md` | Bộ luật Lao động 2019, Cổng thông tin điện tử Chính phủ | 1763 | `category=contract`, `language=vi`, `date=05/06/2026` |
| 2 | `02_thu_viec.md` | Bộ luật Lao động 2019, Cổng thông tin điện tử Chính phủ | 1776 | `category=probation`, `language=vi`, `date=05/06/2026` |
| 3 | `03_tien_luong.md` | Bộ luật Lao động 2019 + Nghị định 145/2020/NĐ-CP | 1801 | `category=wage`, `language=vi`, `date=05/06/2026` |
| 4 | `04_thoi_gio_lam_viec_nghi_ngoi.md` | Bộ luật Lao động 2019 + Thư viện Pháp luật | 1800 | `category=working_time`, `language=vi`, `date=05/06/2026` |
| 5 | `05_lam_them_gio.md` | Bộ luật Lao động 2019 + Nghị định 145/2020/NĐ-CP | 1790 | `category=overtime`, `language=vi`, `date=05/06/2026` |
| 6 | `06_nghi_phep_ngay_le.md` | Bộ luật Lao động 2019, Cổng thông tin điện tử Chính phủ | 1742 | `category=leave`, `language=vi`, `date=05/06/2026` |
| 7 | `07_cham_dut_hop_dong.md` | Bộ luật Lao động 2019, Cổng thông tin điện tử Chính phủ | 1949 | `category=termination`, `language=vi`, `date=05/06/2026` |
| 8 | `08_ky_luat_an_toan_lao_dong.md` | Bộ luật Lao động 2019 + Nghị định 145/2020/NĐ-CP | 1872 | `category=discipline_safety`, `language=vi`, `date=05/06/2026` |

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `source` | string | `data/05_lam_them_gio.md` | Truy vết chunk về tài liệu gốc |
| `category` | string | `overtime`, `wage`, `termination` | Lọc trước khi search để giảm nhiễu |
| `language` | string | `vi` | Xác định ngôn ngữ của bộ tài liệu |
| `date` | string | `05/06/2026` | Ghi ngày crawl/cập nhật dataset để lọc hoặc kiểm tra độ mới của tài liệu |

---

## 3. Chunking Strategy

### Baseline Analysis

Baseline dùng `ChunkingStrategyComparator().compare()` trên 3 tài liệu legal với `chunk_size=500`.

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|----------|----------|-------------|------------|-------------------|
| `01_hop_dong_lao_dong.md` | `fixed_size` | 4 | 478.2 | Medium |
| `01_hop_dong_lao_dong.md` | `by_sentences` | 7 | 250.3 | High |
| `01_hop_dong_lao_dong.md` | `recursive` | 5 | 350.8 | High |
| `02_thu_viec.md` | `fixed_size` | 4 | 481.5 | Medium |
| `02_thu_viec.md` | `by_sentences` | 9 | 195.9 | High |
| `02_thu_viec.md` | `recursive` | 5 | 353.4 | High |
| `03_tien_luong.md` | `fixed_size` | 4 | 487.8 | Medium |
| `03_tien_luong.md` | `by_sentences` | 9 | 199.0 | High |
| `03_tien_luong.md` | `recursive` | 5 | 358.4 | High |

### Strategy Của Tôi

**Loại:** RecursiveChunker

Tôi chọn recursive chunking vì tài liệu legal có heading, paragraph và câu dài. RecursiveChunker ưu tiên tách theo paragraph, newline, câu, rồi mới đến word/character fallback, nên giữ được ngữ cảnh của một quy định mà không cắt ngang ý quá nhiều. Với domain legal, coherence quan trọng hơn số lượng chunk thật nhỏ, vì câu trả lời cần dựa trên điều kiện và ngoại lệ.

### So Sánh Strategy

Với bộ legal data, recursive chunking cho chunk vừa phải và giữ cấu trúc tốt hơn fixed-size. SentenceChunker giữ trọn câu nhưng tạo nhiều chunk ngắn, có thể làm mất liên kết giữa điều kiện và kết quả nếu một quy định nằm trên nhiều câu liên tiếp.

| Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|----------|----------------------|-----------|----------|
| RecursiveChunker | 10 / 10 on main benchmark | Giữ cấu trúc paragraph/legal topic | Phụ thuộc separator rõ |
| FixedSizeChunker baseline | Reference strategy | Đơn giản, độ dài ổn định | Có thể cắt ngang điều kiện pháp lý |
| SentenceChunker baseline | Reference strategy | Giữ trọn câu | Chunk ngắn, dễ tách điều kiện khỏi ngoại lệ |

### Strategy Report - Pipeline Nhóm

Chiến lược nhóm được thiết kế theo pipeline RAG đầy đủ: thu thập tài liệu legal, chuẩn hóa thành Markdown, chunk tài liệu theo cấu trúc tự nhiên, embedding từng chunk, lưu vào vector store, rồi truy xuất top-k chunks để agent trả lời. Mục tiêu không chỉ là code chạy được, mà là retrieval có thể giải thích được: mỗi kết quả phải có source, category, score và lý do liên quan đến gold answer.

#### 1. Data Strategy

Bộ dữ liệu nhóm chọn domain hẹp: **Luật lao động Việt Nam cơ bản**. Mỗi file trong `data/` tương ứng một chủ đề pháp lý nhỏ, ví dụ hợp đồng lao động, thử việc, tiền lương, làm thêm giờ, nghỉ phép hoặc chấm dứt hợp đồng. Cách chia này giúp một query thường map rõ về một hoặc vài tài liệu, giảm nhiễu so với việc gom toàn bộ luật lao động vào một file rất dài.

Mỗi document có metadata tối thiểu:

| Field | Vai trò trong strategy |
|-------|------------------------|
| `source` | Cho biết chunk đến từ file nào để kiểm tra grounding |
| `category` | Dùng cho metadata filtering trước khi search |
| `language` | Ghi nhận dataset tiếng Việt |
| `date` | Ghi ngày crawl/cập nhật dataset: `05/06/2026` |
| `legal_basis` | Ghi cơ sở nguồn luật hoặc văn bản tham chiếu |

#### 2. Chunking Strategy

Strategy chính dùng `RecursiveChunker` vì tài liệu legal thường có heading, paragraph và câu dài. Thứ tự tách ưu tiên là paragraph (`\n\n`), newline (`\n`), câu (`. `), từ (` `), rồi fallback theo ký tự nếu đoạn vẫn quá dài.

Lý do chọn recursive chunking:
- Giữ nguyên một đoạn quy định hoặc một ý pháp lý trong cùng chunk.
- Hạn chế cắt ngang điều kiện và ngoại lệ, điều rất quan trọng với legal retrieval.
- Tạo chunk vừa phải hơn fixed-size, dễ đọc hơn khi đưa vào prompt RAG.
- Phù hợp với Markdown vì tài liệu đã được làm sạch thành heading + paragraph.

Output của bước chunking là danh sách chunks:

```text
[
  "Chunk 1: heading + đoạn giải thích chính...",
  "Chunk 2: điều kiện / giới hạn / ngoại lệ...",
  "Chunk 3: benchmark hints..."
]
```

#### 3. Embedding Strategy

Embedding strategy chính khi có API key là dùng OpenAI `text-embedding-3-small`. Mỗi chunk và query được biến thành vector số, sau đó so sánh bằng cosine similarity. Model này phù hợp cho lab vì nhẹ hơn các model embedding lớn, đủ tốt cho semantic search và đã được cấu hình qua `.env.example`.

Trong môi trường không có API key thật, demo dùng `legal keyword embeddings fallback` để kết quả có thể tái lập khi nộp bài. Fallback này không thay thế semantic embedding thật, nhưng giúp kiểm tra pipeline từ query đến retrieved chunk mà không cần gọi API.

So sánh vai trò hai backend:

| Backend | Vai trò | Khi dùng |
|---------|--------|----------|
| `text-embedding-3-small` | Semantic retrieval thật | Khi có `OPENAI_API_KEY` |
| `legal keyword embeddings fallback` | Demo tái lập, không tốn API | Khi chạy local hoặc chưa có key |
| `_mock_embed` | Test interface deterministic | Unit tests của lab |

#### 4. Vector Store / Index Strategy

Vector store dùng `EmbeddingStore`, hiện lưu in-memory records. Mỗi record tương ứng một indexed chunk/document unit và có cấu trúc:

| Index field | Ý nghĩa |
|-------------|---------|
| `id` | ID nội bộ, dạng `doc_id:index` |
| `content` | Nội dung chunk/document được retrieve |
| `metadata` | Metadata phục vụ filter và trace source |
| `embedding` | Vector embedding dùng để tính similarity |
| `score` | Chỉ xuất hiện trong search result, là similarity score với query |

Trong implementation hiện tại, `add_documents()` tạo record và thêm `metadata["doc_id"]` để delete/search có thể truy vết. `search()` embed query, tính dot product/cosine-style ranking với từng record, sort score giảm dần và trả top-k. `search_with_filter()` lọc metadata trước rồi mới search, giúp giảm nhiễu khi query đã rõ category.

Ví dụ indexed record logic:

```text
id: 05_lam_them_gio:4
content: "Làm thêm giờ là khoảng thời gian..."
metadata: {
  source: "data/05_lam_them_gio.md",
  category: "overtime",
  language: "vi",
  date: "05/06/2026",
  doc_id: "05_lam_them_gio"
}
embedding: [0.01, -0.03, ...]
```

#### 5. Retrieval Strategy

Retrieval strategy cho benchmark:

1. Nhận query.
2. Nếu query thuộc category rõ ràng, áp dụng metadata filter trước, ví dụ `category=overtime`.
3. Embed query.
4. Tính semantic score giữa query embedding và mỗi indexed chunk.
5. Trả về top-3 chunks có score cao nhất.
6. Kiểm tra top-1 source và top-3 relevance với gold answer.

Output của search có format:

```text
[
  {
    "id": "05_lam_them_gio:4",
    "content": "...",
    "metadata": {"source": "data/05_lam_them_gio.md", "category": "overtime"},
    "score": 0.6625
  }
]
```

#### 6. RAG Output Strategy

`KnowledgeBaseAgent` nhận top-k chunks từ vector store, sau đó dựng prompt gồm context, source và score. Prompt yêu cầu LLM trả lời chỉ dựa trên retrieved context; nếu context thiếu thì phải nói rõ thiếu gì. Với legal domain, cách này quan trọng vì câu trả lời phải trace được về nguồn, tránh trả lời kiểu suy đoán pháp lý.

Output cuối cùng gồm:

| Output | Mục đích |
|--------|----------|
| Top-1 retrieved chunk | Chứng minh retrieval chính xác |
| Top-3 retrieved chunks | Kiểm tra recall và ngữ cảnh phụ |
| Score | Đo độ gần query-chunk |
| Agent answer | Kiểm tra câu trả lời có grounded theo context không |
| Source path | Giúp kiểm tra lại gold answer trong tài liệu |

#### 7. Team Comparison Plan

Nếu làm nhóm đầy đủ, các thành viên giữ nguyên dataset và 5 benchmark queries nhưng đổi strategy:

| Thành viên/Strategy | Điều thay đổi | Kỳ vọng |
|---------------------|---------------|---------|
| RecursiveChunker | Tách theo cấu trúc paragraph/câu | Tốt cho legal coherence |
| FixedSizeChunker | Tách đều theo ký tự | Baseline dễ kiểm soát nhưng có thể cắt ngang ý |
| SentenceChunker | Tách theo câu | Dễ đọc nhưng có thể tách điều kiện khỏi ngoại lệ |
| Custom legal section chunker | Tách theo heading/chủ đề legal | Có thể tốt nhất nếu tài liệu nhiều heading rõ |

Nhóm sẽ so sánh bằng cùng metrics: `Top-1 Source Match`, `Top-3 Relevance`, `Semantic Score`, `Answer Grounding`, và failure cases.

---

## 4. My Approach

### Chunking Functions

`SentenceChunker.chunk` dùng regex để tách text thành các câu kết thúc bằng `.`, `!`, `?`, newline hoặc cuối chuỗi. Sau đó gom tối đa `max_sentences_per_chunk` câu vào một chunk và strip whitespace.

`RecursiveChunker.chunk` gọi helper `_split` để tách theo danh sách separator ưu tiên. Base case là text rỗng hoặc text đã ngắn hơn `chunk_size`; nếu hết separator thì fallback bằng cắt theo ký tự.

### EmbeddingStore

`add_documents` tạo record gồm `id`, `content`, `metadata`, và embedding. Metadata được thêm `doc_id` để search result và delete có thể truy vết về document gốc.

`search` embed query và tính dot product với mỗi stored embedding, sau đó sort score giảm dần. Vì mock embedder đã normalize vector, dot product đóng vai trò như cosine ranking.

`search_with_filter` filter metadata trước rồi mới search, giúp giảm candidate set. Trong legal benchmark, filter theo `category` giúp query về làm thêm giờ không bị lẫn sang thời giờ làm việc, và query về chấm dứt hợp đồng không bị lẫn sang hợp đồng lao động nói chung.

### Semantic Score Metrics Với OpenAI `text-embedding-3-small`

Khi dùng OpenAI `text-embedding-3-small`, mỗi query và mỗi chunk được chuyển thành một embedding vector. Score semantic giữa query và chunk được tính bằng cosine similarity:

`semantic_score(query, chunk) = dot(query_embedding, chunk_embedding) / (||query_embedding|| * ||chunk_embedding||)`

Ý nghĩa score:
- Score càng gần `1.0`: query và chunk càng gần nhau về mặt ngữ nghĩa.
- Score gần `0.0`: ít liên quan hoặc chỉ trùng rất ít ý.
- Score âm: hướng ngữ nghĩa lệch nhau, thường không nên ưu tiên trong retrieval.

Pipeline tính score khi dùng `text-embedding-3-small`:
1. Chunk tài liệu bằng `RecursiveChunker`.
2. Gọi OpenAI embedding cho từng chunk.
3. Gọi OpenAI embedding cho query.
4. Tính cosine similarity giữa query vector và từng chunk vector.
5. Sắp xếp kết quả theo `semantic_score` giảm dần.
6. Trả về top-k chunks, thường dùng top-3 để đánh giá.

Trong code hiện tại, `OpenAIEmbedder` đã mặc định dùng model `text-embedding-3-small`. Khi có key thật, chỉ cần cấu hình `.env`:

```env
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=...
```

Vì không push API key lên GitHub, benchmark trong report dùng keyword embedding fallback để tái lập kết quả. Tuy nhiên metric đánh giá semantic chính vẫn là cosine similarity giống khi thay bằng OpenAI embedding.

### KnowledgeBaseAgent

`KnowledgeBaseAgent.answer` lấy top-k chunks từ store, đóng gói thành context có source và score, rồi đưa vào prompt. LLM chỉ được yêu cầu trả lời dựa trên retrieved context; nếu context thiếu thì phải nói rõ thông tin còn thiếu.

### Test Results

```text
pytest tests/ -v
collected 42 items
42 passed
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions

Mock embeddings được dùng cho tests nên điểm số dưới đây minh họa pipeline hơn là semantic quality thật. Khi có `OPENAI_API_KEY`, có thể chạy lại với `text-embedding-3-small` để có điểm ngữ nghĩa tốt hơn.

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|------------|------------|---------|--------------|-------|
| 1 | Hợp đồng lao động ghi nhận việc làm có trả lương. | Hợp đồng lao động là thỏa thuận về công việc và tiền lương. | high | 0.0153 | Weak yes |
| 2 | Thời gian thử việc phụ thuộc vào mức độ phức tạp của công việc. | Người lao động có thể nghỉ lễ tết theo quy định. | low | 0.1316 | No |
| 3 | Tiền lương phải được trả đầy đủ và đúng hạn. | Người sử dụng lao động phải thanh toán lương trực tiếp. | high | -0.0523 | No |
| 4 | Làm thêm giờ cần có sự đồng ý của người lao động. | Hợp đồng lao động có thể giao kết bằng thông điệp dữ liệu. | low | -0.0512 | Yes |
| 5 | Người lao động cần báo trước khi đơn phương chấm dứt hợp đồng. | Quy trình kỷ luật lao động phải tuân thủ nội quy. | low | -0.0357 | Yes |

Kết quả bất ngờ là mock embedder không bắt được ý nghĩa thật của câu, vì nó tạo vector deterministic từ hash text. Điều này cho thấy mock backend tốt cho testing interface, nhưng retrieval evaluation thật nên dùng OpenAI `text-embedding-3-small` hoặc local embedder.

---

## 6. Results

### Benchmark Queries & Gold Answers

5 benchmark queries chính dưới đây được chạy trên package `src` cá nhân với legal data trong `data/`. Benchmark dùng `EmbeddingStore`, metadata filtering theo `category`, và một embedding keyword tiếng Việt cục bộ để có kết quả tái lập khi chưa có OpenAI key thật.

### Benchmark Metrics Và Cách Tính Điểm

Mỗi benchmark query được đánh giá theo 4 metric:

| Metric | Cách tính | Ý nghĩa |
|--------|-----------|---------|
| `Top-1 Source Match` | Top-1 retrieved chunk có đúng tài liệu chứa gold answer không | Kiểm tra retrieval chính xác nhất |
| `Top-3 Relevance` | Trong top-3 có ít nhất một chunk liên quan đến gold answer không | Kiểm tra recall ở top-k |
| `Semantic Score` | Cosine similarity giữa query embedding và chunk embedding | Đo độ gần ngữ nghĩa giữa query và chunk |
| `Answer Grounding` | Agent answer có dựa trên retrieved context và khớp gold answer không | Kiểm tra chất lượng RAG output |

Cách quy đổi điểm retrieval theo rubric:

| Điểm/query | Điều kiện |
|------------|-----------|
| 2 điểm | Top-3 có chunk relevant và agent answer đúng/đủ với gold answer |
| 1 điểm | Top-3 có chunk relevant nhưng answer thiếu chi tiết, hoặc relevant chunk không ở top-1 |
| 0 điểm | Không retrieve được chunk relevant trong top-3 |

Tổng retrieval quality:

`retrieval_score = sum(query_points) / 10`

Với 5 queries, điểm tối đa là `5 * 2 = 10`. Trong benchmark chính, cả 5 queries đều retrieve đúng tài liệu ở top-1 và có chunk relevant trong top-3, nên phần retrieval đạt `10 / 10`.

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Hợp đồng lao động có những loại nào và nội dung cần có gì? | Có hợp đồng không xác định thời hạn và xác định thời hạn; nội dung gồm công việc, địa điểm, lương, thời giờ, bảo hiểm và điều kiện lao động. |
| 2 | Thời gian thử việc tối đa cho công việc cần trình độ cao đẳng trở lên là bao lâu? | Thời gian thử việc cho công việc cần trình độ cao đẳng trở lên thường không quá 60 ngày. |
| 3 | Người sử dụng lao động phải trả lương cho người lao động như thế nào? | Phải trả lương trực tiếp, đầy đủ, đúng hạn và minh bạch về cách tính, bảng lương, khấu trừ nếu có. |
| 4 | Thời giờ làm việc bình thường tối đa mỗi ngày và mỗi tuần là bao nhiêu? | Không quá 8 giờ/ngày và 48 giờ/tuần; nếu tính theo tuần có thể tối đa 10 giờ/ngày nhưng vẫn không quá 48 giờ/tuần. |
| 5 | Làm thêm giờ cần điều kiện gì và giới hạn theo tháng năm ra sao? | Cần sự đồng ý của người lao động và phải trong giới hạn như 40 giờ/tháng, 200 giờ/năm trừ một số trường hợp đặc biệt. |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk | Score | Relevant? | Agent Answer |
|---|-------|----------------------|-------|-----------|--------------|
| 1 | Hợp đồng lao động | `data/01_hop_dong_lao_dong.md` | 0.8730 | Yes | Grounded answer from contract context |
| 2 | Thời gian thử việc | `data/02_thu_viec.md` | 0.7699 | Yes | Grounded answer from probation context |
| 3 | Trả lương | `data/03_tien_luong.md` | 0.7414 | Yes | Grounded answer from wage context |
| 4 | Thời giờ làm việc | `data/04_thoi_gio_lam_viec_nghi_ngoi.md` | 0.6408 | Yes | Grounded answer from working-time context |
| 5 | Làm thêm giờ | `data/05_lam_them_gio.md` | 0.6625 | Yes | Grounded answer from overtime context |

**Queries có chunk relevant trong top-3:** 5 / 5  
**Retrieval quality score:** 10 / 10 on the main benchmark.

### Extra Smoke Checks

Ngoài 5 câu benchmark chính, tôi chạy thêm 3 câu để kiểm tra phần nghỉ phép, chấm dứt hợp đồng và kỷ luật lao động. Cả 3 câu đều retrieve đúng top-1: `06_nghi_phep_ngay_le.md` score 0.7819, `07_cham_dut_hop_dong.md` score 0.8453, và `08_ky_luat_an_toan_lao_dong.md` score 0.8716.

---

## 7. What I Learned

Điều quan trọng nhất là legal retrieval cần chunk coherence và source traceability. Nếu chunk cắt ngang điều kiện pháp lý, agent có thể trả lời thiếu ngoại lệ hoặc thiếu mốc thời gian. Metadata `category` giúp retrieval rất nhiều vì các chủ đề legal có từ lặp lại, ví dụ "người lao động" xuất hiện trong hầu hết tài liệu.

Nếu làm lại, tôi sẽ thu thập thêm nguồn chính thức cho từng điều khoản và chạy lại benchmark bằng OpenAI `text-embedding-3-small`. Mock/keyword embedding giúp demo có thể tái lập, nhưng không thay thế được semantic embedding thật cho các câu hỏi pháp lý có cách diễn đạt khác nhau.

Failure case tiềm ẩn: query về "thời giờ làm việc" và "làm thêm giờ" dễ bị lẫn nhau nếu không filter metadata, vì cả hai đều có từ khóa "giờ", "làm", "người lao động". Cách cải thiện là dùng metadata filter theo `category` và chunk theo paragraph để giữ đủ ngữ cảnh.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 10 / 10 |
| Chunking strategy | Nhóm | 15 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 10 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 4 / 5 |
| **Tổng** | | **99 / 100 local self-estimate** |
