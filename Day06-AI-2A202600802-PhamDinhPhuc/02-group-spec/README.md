# Day 06 - 02 Group SPEC

## Nhóm

| Thành viên | Mã học viên |
|---|---|
| Phạm Đình Phúc | 2A202600802 |
| Nguyễn Tuấn Anh | 2A202600758 |
| Hà Vũ Anh | 2A202600571 |
| Đỗ Văn Cung | 2A202600793 |

## Chủ đề nhóm

**Track:** A - Learning OS  
**Tên ý tưởng:** Learning OS Knowledge Intake Agent

Nhóm thiết kế một agent hỗ trợ học viên AI Thực Chiến / AI in Action hỏi về **nội dung bài học**: khái niệm, lab, rubric, ví dụ, và cách áp dụng vào bài làm. Agent không trả lời bằng suy đoán; nếu câu hỏi rõ thì agent crawl/search internet/public sources hoặc loaded docs ngay, nếu câu hỏi mơ hồ/khó thì hỏi thêm 1-3 câu, rồi trả về explanation/example/checklist có nguồn. Câu hỏi vận hành như deadline/nộp repo là out-of-scope trừ khi user paste source chính thức.

## Các file trong folder này

| File | Vai trò |
|---|---|
| `evidence-pack.md` | Gom evidence, pain thật, insight và lý do đổi thành SPEC. |
| `workflow.md` | Mô tả workflow ASCII để build prototype Day06: ask loop, source check, unknown/refusal, correction loop. |
| `thin-spec.md` | SPEC mỏng: user, pain, build slice, output contract, 4 paths, failure mode và owner plan. |

## Build slice chốt

```text
Một học viên hỏi mơ hồ về nội dung bài học/lab
  -> Nếu câu hỏi rõ: agent crawl/search source ngay
  -> Nếu câu hỏi mơ hồ/khó: agent hỏi thêm 1-3 câu
  -> Agent xác nhận scope Learning Content
  -> Agent search public internet / loaded docs
  -> Agent trả explanation + example + checklist áp dụng
  -> Nếu không có nguồn, agent nói không biết và draft câu hỏi gửi mentor/TA
```
