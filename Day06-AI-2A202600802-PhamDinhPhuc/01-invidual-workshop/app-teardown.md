# Day 06 - 01 Individual Workshop: Learning Content Agent Prep

**Học viên:** 2A202600802 - Phạm Đình Phúc  
**Track:** A - Learning OS  
**Product/app:** Learning Content Intake Agent cho AI Thực Chiến / AI in Action  
**Workflow test:** Học viên hỏi một câu mơ hồ hoặc khó về nội dung bài học/lab, agent hỏi thêm nếu cần, tìm nguồn, rồi tổng hợp câu trả lời có source.  

## 1. App / Flow Chọn Để Build

| App/flow | AI feature | Lý do chọn |
|---|---|---|
| Learning OS Knowledge Intake Agent | Hỏi thêm context, search/crawl source, tổng hợp explanation/checklist, từ chối khi thiếu nguồn | Phù hợp với bài Day06 vì có thể demo một flow nhỏ: input -> source retrieval -> answer/refusal -> correction. |

## 2. Promise vs Reality

### Promise

Agent giúp học viên hiểu nội dung bài học nhanh hơn bằng cách đọc/tìm nguồn trước khi trả lời. User không cần tự mở nhiều README, slide, PDF, notebook, hoặc repo để hiểu một khái niệm.

### Reality / Risk

Nếu không có source ingestion rõ, agent dễ trả lời bằng trí nhớ hoặc suy đoán. Với nội dung lớp, điều này nguy hiểm vì user có thể áp dụng sai vào lab hoặc hiểu lệch rubric.

## 3. Workflow Cơ Bản

```text
User hỏi về nội dung bài học/lab
  -> Agent đọc context hiện tại
  -> Detect scope: Learning Content / Out-of-scope Ops / Ambiguous
  -> Nếu câu hỏi rõ: search/crawl source ngay
  -> Nếu câu hỏi mơ hồ/khó: hỏi thêm 1-3 câu
  -> Ingest source: Tavily web search / GitHub reader / PDF reader / pasted text
  -> Source check: found / missing / conflict / outdated risk
  -> Nếu có source: explanation + example + checklist
  -> Nếu thiếu source: unknown/refusal + draft câu hỏi gửi mentor/TA
  -> Nếu user correction: update cùng conversation và chạy lại
```

## 4. Path Yếu Cần Sửa

Path yếu nhất là **source missing / low-confidence**:

```text
User: "Framework thầy nói sáng nay là gì?"
  -> Agent không thấy source trong public web / loaded docs
  -> Agent không đoán
  -> Agent hỏi user paste slide/link/text hoặc draft câu hỏi gửi mentor
```

## 5. Product Decision

```text
Khi học viên hỏi về nội dung bài học/lab,
agent chỉ nên trả lời chắc khi có source từ public search, GitHub/PDF reader, hoặc text user cung cấp.
Nếu câu hỏi mơ hồ thì agent hỏi thêm trong cùng conversation.
Nếu không có nguồn thì agent nói không biết và giúp user hỏi mentor/TA.
```

## 6. To-be Sketch

```text
Learning Content Agent
  -> Source input: Tavily / GitHub link / PDF link / pasted text
  -> Question input
  -> Ask loop nếu thiếu context
  -> Source retrieval
  -> Answer contract:
       Detected route
       Source status
       Explanation
       Example
       Checklist
       Unknown/refusal note
```
