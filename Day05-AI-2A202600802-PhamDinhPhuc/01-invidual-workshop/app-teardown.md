# Day 05 - 01 Individual Workshop: Mổ App AI Thật

**Học viên:** 2A202600802 - Phạm Đình Phúc  
**Hình thức:** Cá nhân trước, chia sẻ finding cho nhóm sau  
**App chọn:** V-App - V-AI  
**Output cần có:** sketch as-is/to-be + một câu product decision  

## 1. Chọn một app để dùng thử

| App | AI feature | Lý do chọn |
|---|---|---|
| V-App - V-AI | Trợ lý ảo voice/text, gợi ý theo context trong app | Gần với bối cảnh học viên/sinh viên, dễ test câu hỏi mơ hồ và xem AI có hỏi lại hay trả lời ngay. |

## 2. Dùng thử: promise vs reality

### Promise

V-AI hứa giúp user hỏi nhanh trong app, nhận hỗ trợ theo ngữ cảnh mà không cần tự tìm nhiều nguồn hoặc hỏi nhiều người.

### Query thử

```text
Em cần làm gì cho bài Day05 này?
```

Query này cố tình hơi mơ hồ vì user chưa nói rõ:

- hỏi phần cá nhân hay phần nhóm;
- hỏi evidence, thin SPEC, prototype hay repo;
- đang làm Day05 hay chuẩn bị Day06;
- cần checklist hay giải thích.

### Reality / điểm cần quan sát

Nếu AI trả lời ngay bằng một đoạn chung chung, user vẫn chưa biết bước tiếp theo. Điểm gãy không phải là thiếu câu trả lời, mà là AI chưa nhận ra câu hỏi thiếu context và chưa hỏi lại.

Evidence cần bổ sung sau khi dùng app thật:

| Evidence | Trạng thái |
|---|---|
| Screenshot V-AI trả lời query mơ hồ | [CẦN THÊM] |
| Prompt/input đã thử | Đã có nháp: "Em cần làm gì cho bài Day05 này?" |
| Observation | [CẦN GHI] AI có hỏi lại không, hay trả lời luôn? |

## 3. Workflow cơ bản

```text
APP: V-App / V-AI
  -> FLOW: user hỏi một câu mơ hồ về bài lab
  -> PATH YẾU: AI không chắc intent nhưng vẫn trả lời ngay
  -> SỬA: hỏi lại bằng option + nhận thêm context
  -> OUTPUT: checklist đúng scope + phần cần hỏi mentor nếu không chắc
```

## 4. Vẽ flow as-is

```text
User mở V-App / V-AI
  -> User hỏi câu mơ hồ: "Em cần làm gì cho bài Day05 này?"
  -> AI trả lời chung hoặc đoán intent
  -> User vẫn chưa rõ phải làm phần cá nhân hay nhóm
  -> User phải tự quay lại slide / repo / Discord / hỏi mentor
  -> Mất thời gian và dễ làm sai deliverable
```

## 5. Vẽ 4 paths

| Path | Trong flow này cần nhìn gì? | Ghi chú |
|---|---|---|
| Happy | AI hiểu đúng user đang hỏi deliverable Day05 và đưa checklist. | Tốt nếu có source hoặc context rõ. |
| Low-confidence | AI thấy câu hỏi mơ hồ và hỏi lại 2-4 câu. | Đây là path cần sửa nhất nếu app chưa có. |
| Failure | AI đoán sai, ví dụ trả lời về nội dung bài học trong khi user hỏi cách nộp. | User dễ làm sai file hoặc sai scope. |
| Correction | User nói "không, ý em là phần group spec" và AI cập nhật câu trả lời. | Cần giữ context trong cùng conversation. |

## 6. Sửa một path yếu nhất

Path yếu nhất: **Low-confidence path**.

Thay vì trả lời ngay, V-AI nên hỏi lại ngắn:

```text
Bạn đang hỏi phần nào của Day05?
1. 01-invidual-workshop: bài cá nhân mổ app
2. 02-group-spec: evidence/thin SPEC cho nhóm
3. Chuẩn bị Day06 prototype
Bạn muốn mình đưa checklist nộp bài hay giải thích từng phần?
```

Sau khi user chọn, AI mới tổng hợp:

- việc cần làm;
- file cần sửa;
- evidence còn thiếu;
- bước tiếp theo.

## 7. Product decision

```text
Khi user hỏi một câu mơ hồ về bài lab hoặc workflow trong app,
V-AI có thể trả lời chung chung hoặc đoán sai intent nếu không hỏi lại,
hậu quả là user vẫn không biết phải làm phần nào, file nào, bước tiếp theo là gì.
Lỗi thuộc layer Intent + UX Recovery.
Nên sửa bằng low-confidence path: hỏi lại 2-4 câu/option, cho user chọn hoặc nhập thêm context, rồi mới tổng hợp checklist dựa trên nguồn/context đã có.
```

## 8. Sketch to-be

```text
User mở V-AI
  -> User hỏi câu mơ hồ
  -> AI nhận diện thiếu context
  -> AI hỏi lại bằng option + ô nhập thêm
  -> User chọn "02-group-spec" hoặc bổ sung context
  -> AI cập nhật conversation hiện tại
  -> AI trả về checklist đúng scope + phần không chắc cần hỏi mentor
```

## 9. Câu nối sang SPEC nhóm

Finding cá nhân này gợi ý cho SPEC nhóm: nếu build Learning OS agent, prototype phải có **ask loop + source-grounded answer + unknown/refusal** để tránh AI đoán khi user hỏi mơ hồ.

## 10. Tự kiểm nhanh

- [ ] Có screenshot/observation thật từ V-AI.
- [x] Có prompt/input đã thử.
- [x] Có sketch as-is/to-be.
- [x] Có 4 paths.
- [x] Có một product decision rõ.
