# Evidence Pack - Learning OS Knowledge Intake Agent

## 1. Nhóm Và Track

**Track:** A - Learning OS  
**Product/app thật để soi:** LMS hiện tại, Discord lớp, public repo lab, slide/README/rubric/public docs của AI Thực Chiến / AI in Action  
**Build slice đang nghĩ:** Agent nhận câu hỏi mơ hồ về nội dung học/lab, hỏi thêm nếu thiếu context, search internet/public sources hoặc loaded docs, rồi trả về explanation/example/checklist có nguồn. Nếu không có nguồn, agent nói không biết và draft câu hỏi gửi mentor/TA.

## 2. Self-use Evidence

| Observation | Screenshot/link | Path liên quan | Điều học được |
|---|---|---|---|
| Day05 có nhiều khái niệm rời rạc: evidence, build slice, Auto/Aug, 4 paths, failure mode. | Screenshot slide / repo Day05 | Low-confidence | User dễ hỏi mơ hồ kiểu "cái này nghĩa là gì" vì không biết hỏi đúng khái niệm nào. |
| README/slide/rubric là nguồn public hoặc có thể paste vào prototype. | GitHub repo Day05 / screenshot | Happy / Correction | Agent có thể search source rồi giải thích kèm ví dụ. |
| Program Operations như deadline/nộp repo dễ sai nếu không có data nội bộ. | Domain observation | Out-of-scope / Unknown | Thu hẹp main scope về Learning Content, câu hỏi vận hành chỉ hỗ trợ draft hỏi mentor. |

## 3. User / Review / Social Evidence

| Quote / observation | Nguồn | User là ai? | Pain/failure mode |
|---|---|---|---|
| "Build slice nghĩa là gì?" | Câu hỏi thật trong quá trình làm lab | Học viên AI Thực Chiến | User cần giải thích khái niệm bằng ngôn ngữ dễ hiểu và có ví dụ. |
| "Failure path khác low-confidence path thế nào?" | Câu hỏi khi làm SPEC | Học viên đang viết thin spec | User cần phân biệt khái niệm để áp dụng vào bài. |
| "Nếu tài liệu không có thông tin đó thì AI có được đoán không?" | Câu hỏi khi thiết kế workflow | Học viên/nhóm làm prototype | Failure mode là AI giải thích không có nguồn hoặc tự bịa framework. |

## 4. Evidence -> Insight

```text
Evidence nổi bật nhất:
Lab có nhiều nguồn học đúng nhưng phân tán: public repo, slide, README, rubric, ví dụ.

Insight:
User không chỉ cần "một chatbot trả lời bài học".
User cần một agent biết hỏi lại để xác định khái niệm/lab đang hỏi,
rồi search public source/loaded docs trước khi giải thích.

Opportunity:
AI có thể giúp bằng cách biến tài liệu internet/public của lớp thành một Learning OS Knowledge Agent:
hỏi thêm context, search/retrieve đúng source, giải thích kèm ví dụ/checklist áp dụng, và nói "không biết" khi source thiếu.
```

## 5. Evidence Đổi SPEC Như Thế Nào?

- [x] Chọn Track A - Learning OS.
- [x] Thu hẹp scope chính thành Learning Content Support.
- [x] Chốt build slice đủ nhỏ: một user hỏi mơ hồ về khái niệm/lab, agent hỏi thêm + search source + trả explanation/checklist.
- [x] Chọn Augmentation, không Automation.
- [x] Thêm failure path: no-source/unknown, out-of-scope operations, correction.
- [x] Thêm owner plan cho research, SPEC, prototype, test, demo.

```text
Trước evidence, ý tưởng còn dễ thành chatbot chung chung.
Sau khi đọc yêu cầu Day05 và quan sát workflow làm bài, nhóm chốt Learning OS Knowledge Intake Agent.
Lý do: scope learning content có nguồn public dễ search hơn operation/internal rule, ít bias hơn, và demo được ask loop + source-grounded refusal trong một prototype nhỏ.
```
