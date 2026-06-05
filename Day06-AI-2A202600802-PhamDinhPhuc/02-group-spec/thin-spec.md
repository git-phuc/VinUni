# Thin SPEC - Learning OS Knowledge Intake Agent

## 1. Track, Product/App Và User

**Track:** A - Learning OS  
**Product/app thật:** LMS hiện tại, GitHub repo lab, slide/README/rubric/public docs của AI Thực Chiến / AI in Action  
**User cụ thể:** Học viên AI Thực Chiến đang hỏi mơ hồ về nội dung bài học, khái niệm, bài lab, rubric, ví dụ, hoặc cách áp dụng kiến thức vào bài làm  
**Nhóm có phải user thật không?** Có. Nhóm đang trực tiếp gặp pain này khi đọc Day05/Day06 và phân biệt file `01` với `02`.

## 2. Scope

| Scope | Bao gồm | Không bao gồm |
|---|---|---|
| Learning Content Support | Giải thích khái niệm, lab, rubric, ví dụ, cách làm bài. | Không tự chấm điểm cuối cùng. |
| Program Operations Support | Deadline, nộp repo, grading, lịch, team rule. | Out of scope, trừ khi user paste source chính thức. |

## 3. Evidence Summary

| Evidence | Nguồn | User/pain nói lên điều gì? | SPEC phải đổi gì? |
|---|---|---|---|
| Slide/README có nhiều khái niệm product: build slice, thin spec, 4 paths, failure mode. | Public repo / slide note | User dễ hỏi mơ hồ và cần giải thích kèm ví dụ. | Agent phải hỏi rõ khái niệm/lab trước khi trả lời. |
| Tài liệu học nằm ở nhiều nơi: public repo, slide, README, rubric. | Self-use observation | User không biết nguồn nào là source of truth. | Agent phải search/source-grounded và nêu source status. |
| Câu hỏi vận hành như deadline/nộp repo dễ sai nếu không có data nội bộ. | Domain observation | AI đoán có thể làm sai rule. | Program Operations đưa ra out-of-scope/unknown nếu không có source chính thức. |

## 4. Pain Statement

```text
Học viên AI Thực Chiến đang gặp khó khi hỏi về nội dung bài học hoặc bài lab,
vì khái niệm và ví dụ nằm rải rác ở public GitHub repo, slide, README và rubric,
dẫn tới user không biết hỏi đúng khái niệm nào, áp dụng vào bài làm ra sao,
và dễ hiểu sai nếu AI trả lời bằng suy đoán.
```

## 5. Build Slice

```text
Cho một học viên hỏi "Build slice nghĩa là gì?",
prototype dùng AI để crawl/search internet/public sources hoặc loaded docs trước nếu câu hỏi đã rõ; nếu câu hỏi mơ hồ/khó thì hỏi thêm 1-3 câu,
rồi tạo source-grounded answer gồm explanation, example, application checklist, missing info, source status,
và xử lý failure mode "không có nguồn hoặc hỏi sang rule vận hành" bằng ask loop, no-source/unknown response, correction loop, và draft câu hỏi gửi mentor/TA.
```

## 6. Agent Workflow

```text
Understand question
  -> Decide scope: Learning Content / Out-of-scope Program Operations / Ambiguous
  -> Nếu câu hỏi rõ: crawl/search source ngay
  -> Nếu câu hỏi mơ hồ/khó: ask loop 1-3 câu
  -> Synthesize nếu có nguồn
  -> Refuse/Unknown nếu không có nguồn hoặc source outdated
  -> Correction loop nếu user sửa scope/day/context
```

## 7. Output Contract

Prototype luôn phải có:

- Detected route
- Source status
- Answer summary
- Action checklist
- Missing info
- Refusal/unknown note nếu thiếu nguồn

## 8. Auto/Aug Decision

- [x] **Augmentation:** AI hỏi, tìm nguồn, tổng hợp, tạo checklist.
- [ ] Conditional automation
- [ ] Automation

**Lý do chọn:** AI không nên tự quyết định rule/deadline/nộp bài thay user. AI chỉ hỗ trợ hiểu tài liệu và chuẩn bị next step; user/mentor vẫn xác nhận cuối.

**Human role:** learner, verifier, corrector, mentor/TA khi source thiếu hoặc mâu thuẫn.

## 9. Four Paths

| Path | Prototype phải thể hiện gì? |
|---|---|
| Happy | User hỏi "Build slice nghĩa là gì?" -> agent tìm source và giải thích kèm ví dụ. |
| Low-confidence | User hỏi "bài này làm sao?" -> agent hỏi khái niệm/lab/output mong muốn. |
| No-source / Unknown | User hỏi một framework không có trong public/searchable sources -> agent không đoán, draft câu hỏi gửi mentor. |
| Correction | User sửa "không phải build slice, là failure path" -> agent update memory và đổi giải thích. |
| Out-of-scope | User hỏi deadline/nộp repo nhưng không paste source chính thức -> agent không đoán, draft câu hỏi gửi mentor/Discord. |

## 10. Failure Mode Nguy Hiểm Nhất

```text
Nếu user hỏi một câu mơ hồ về khái niệm/lab,
AI có thể giải thích sai hoặc đưa ví dụ không có nguồn,
hậu quả là user áp dụng sai vào bài làm hoặc hiểu lệch rubric.
Prototype xử lý bằng ask loop, source status, no-source/unknown response, correction loop, và draft câu hỏi gửi mentor/TA.
```

## 11. Owner Plan Cho Day06

| Thành viên | Việc phụ trách | Bằng chứng cần có trong repo |
|---|---|---|
| Phúc | Research / evidence | Screenshot slide, README Day05, quote câu hỏi mơ hồ |
| Tuấn Anh | SPEC | `evidence-pack.md`, `workflow.md`, `thin-spec.md` |
| Vũ Anh | Prototype | `prototype/index.html`, `styles.css`, `app.js` |
| Cung | Test / failure path | Test happy, low-confidence, no-source/unknown, correction, wrong-scope |
| Phúc | Demo script / repo | README hoặc demo notes |
