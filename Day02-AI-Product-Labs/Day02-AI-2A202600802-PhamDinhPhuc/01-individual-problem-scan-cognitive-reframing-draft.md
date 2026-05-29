# 01 — Individual Problem Scan

## Domain

```text
Domain lớn: Empathy
Hướng cụ thể: Cognitive Reframing (tái cấu trúc nhận thức nhẹ)
```

Trong domain Empathy, bài này tập trung vào những tình huống người dùng bị kẹt trong một diễn giải tiêu cực về bản thân hoặc về người khác. Hướng cụ thể là **Cognitive Reframing**: giúp người dùng nhìn lại automatic thoughts, tách sự kiện khỏi diễn giải, tìm một cách diễn đạt cân bằng hơn, rồi chuyển thành bước hành động nhỏ.

Mục tiêu không phải là "làm AI therapist", mà là tìm một workflow cụ thể nơi AI có thể hỗ trợ self-reflection trong bối cảnh học tập/công việc/đời sống nhẹ.

Boundary xuyên suốt:

```text
AI không chẩn đoán, không trị liệu, không xử lý khủng hoảng tâm lý, không khẳng định người khác đang nghĩ gì. AI chỉ hỗ trợ self-reflection và cognitive reframing trong các tình huống học tập/công việc/đời sống nhẹ, và luôn để người dùng tự kiểm tra, chỉnh sửa, hoặc tìm người thật hỗ trợ khi cần.
```

---

## AI intervention nằm ở đâu?

AI có tham gia, nhưng chỉ tham gia ở một đoạn rõ trong workflow. AI không thay người dùng quyết định cảm xúc nào là "đúng", không đánh giá năng lực của người dùng, và không đưa lời khuyên trị liệu.

```text
[Người dùng nhập sự kiện / feedback / suy nghĩ ban đầu]
        |
        v
[AI hỏi câu gợi mở]
    - Chuyện gì đã xảy ra?
    - Bạn đang cảm thấy gì?
    - Bạn đang tự nói gì với mình?
    - Có bằng chứng nào ủng hộ hoặc phản bác suy nghĩ đó?
        |
        v
[AI hỗ trợ Cognitive Reframing]
    - Tách fact / feeling / interpretation
    - Gợi ý cách diễn đạt cân bằng hơn
    - Không ép "nghĩ tích cực"
        |
        v
[AI gợi ý action items nhỏ]
        |
        v
[Người dùng chọn, sửa, hoặc bỏ gợi ý]  <-- human boundary
```

Vì vậy mức chọn hợp lý là **Workflow**: AI nằm trong một chuỗi bước có kiểm soát, còn người dùng vẫn là người quyết định cuối.

---

## 1. Scan rộng: 10 candidate problems

| # | Lăng kính | Problem quan sát được | Ai đang đau? | Dấu hiệu thật / cách kiểm chứng |
|---|---|---|---|---|
| 1 | Feedback / học tập | Sinh viên nhận feedback hoặc điểm thấp rồi diễn giải thành "mình kém", thay vì chuyển feedback thành việc cần sửa | Sinh viên | Sau feedback dễ mất động lực, né đọc kỹ comment, sửa bài muộn |
| 2 | Social overthinking | Người dùng nhận tin nhắn ngắn/lạnh hoặc bị seen rồi suy diễn "người ta ghét mình" | Sinh viên, người trẻ, người làm nhóm | Đọc lại chat nhiều lần, hỏi bạn bè diễn giải giúp |
| 3 | Deadline stress | Khi deadline gần, sinh viên nghĩ "mình không làm nổi" và trì hoãn thay vì chia nhỏ việc | Sinh viên | Panic, né task, bắt đầu rất muộn |
| 4 | Presentation reflection | Sau khi thuyết trình chưa tốt, người học chỉ nhớ lỗi sai và bỏ qua phần đã làm được | Sinh viên, intern | Self-talk tiêu cực sau presentation, ngại trình bày lần sau |
| 5 | Rejection / no response | Khi không được phản hồi email, tin nhắn, hoặc đơn ứng tuyển, người dùng cá nhân hóa thành "mình không đủ tốt" | Sinh viên, người xin việc | Mất tự tin dù chưa có bằng chứng rõ |
| 6 | Workplace feedback | Intern/junior nhận comment thẳng từ senior và cảm thấy bị công kích cá nhân | Intern, nhân viên mới | Khó tách feedback về task khỏi đánh giá về bản thân |
| 7 | Journaling khó bắt đầu | Người dùng muốn journal để bình tĩnh lại nhưng không biết tự hỏi câu gì | Người hay stress nhẹ | Viết lan man, càng viết càng rối |
| 8 | Peer support thiếu cấu trúc | Bạn bè muốn an ủi nhau nhưng chỉ nói "đừng nghĩ nhiều", không giúp người kia reframe vấn đề được | Peer supporter, bạn bè | Có thiện chí nhưng lời khuyên chung chung |
| 9 | Group conflict | Khi bị teammate góp ý, người dùng nghĩ "họ đang chống lại mình" thay vì nhìn vào mục tiêu chung | Sinh viên làm nhóm | Tranh luận nhóm căng, khó nhận feedback |
| 10 | Impostor feeling | Người học thấy bạn bè làm nhanh hơn rồi nghĩ "mình không thuộc về lớp này" | Sinh viên | So sánh bản thân, giảm tự tin, ngại hỏi |

Nhận xét sau scan:

- Các problem đều nằm trong Empathy vì người dùng cần được phản hồi theo cách không phán xét.
- Các problem đều có yếu tố Cognitive Reframing vì người dùng đang diễn giải tình huống theo hướng tiêu cực.
- Những problem tốt nhất cho lab là problem có workflow rõ, đo được impact, và không quá clinical.

---

## 2. Chọn top 3 candidate problems

| Rank | Problem | Vì sao chọn | Điều còn chưa chắc |
|---|---|---|---|
| 1 | Cognitive reframing khi nhận feedback tiêu cực | Actor rõ, context học tập quen thuộc, workflow vẽ được, có thể đo bằng action items sau feedback | Cần validate xem đây là pain phổ biến hay chỉ xảy ra với một số người |
| 2 | Reframing tin nhắn mơ hồ để giảm overthinking | Empathy mạnh, rất đời thường, bottleneck rõ là suy diễn thiếu bằng chứng | Rủi ro AI đoán sai ý định người gửi nếu boundary không chặt |
| 3 | Cognitive reframing cho deadline panic thành bước hành động nhỏ | Dễ đo bằng thời gian bắt đầu task và số micro-tasks tạo được | Dễ bị trượt thành productivity tool nếu không giữ trọng tâm Cognitive Reframing |

Card muốn pitch nhất:

```text
Problem #1 — Cognitive reframing khi nhận feedback tiêu cực.
```

Lý do:

```text
Problem này vừa đủ gần với trải nghiệm học tập, vừa có workflow rõ. AI không cần can thiệp vào nội dung chuyên môn hay đánh giá điểm số; AI chỉ hỗ trợ sinh viên tách feedback về bài làm khỏi đánh giá tiêu cực về bản thân, rồi chuyển feedback thành action items cụ thể.
```

---

## 3. Problem Card #1 — Cognitive reframing khi nhận feedback tiêu cực

### Problem 1 câu

```text
Sinh viên khi nhận feedback hoặc điểm thấp thường diễn giải nó thành đánh giá tiêu cực về bản thân, thay vì chuyển feedback thành các điểm sửa cụ thể và kế hoạch cải thiện.
```

### Actor

```text
Sinh viên nhận feedback từ giảng viên, TA, peer review, hoặc hệ thống chấm bài.
```

### Thời điểm / bối cảnh

```text
Sau khi nhận điểm thấp, nhận comment phê bình, hoặc thấy bài làm bị đánh giá là thiếu/chưa đạt kỳ vọng.
```

### Current workflow

```text
1. Sinh viên nhận feedback hoặc điểm.
2. Đọc nhanh comment hoặc chỉ nhìn điểm tổng.
3. Cảm thấy thất vọng, xấu hổ, defensive, hoặc mất động lực.
4. Diễn giải thành: "mình kém", "mình không hợp môn này", "mình làm gì cũng sai".
5. Né đọc kỹ feedback hoặc để việc sửa bài tới sát deadline.
6. Khi quay lại sửa, không biết bắt đầu từ đâu.
```

### Bottleneck

```text
Bottleneck nằm ở bước diễn giải feedback. Sinh viên trộn feedback về sản phẩm/bài làm với đánh giá về năng lực cá nhân, nên không chuyển được feedback thành hành động cụ thể.
```

### Impact

```text
Sinh viên giảm động lực, trì hoãn sửa bài, bỏ lỡ thông tin hữu ích trong feedback, và có thể lặp lại lỗi cũ trong lần nộp sau.
```

### Success metric

```text
- Giảm thời gian từ lúc nhận feedback đến lúc có 3 action items cụ thể.
- Tăng số feedback comments được chuyển thành task sửa bài.
- Giảm self-rated distress sau bước cognitive reframing, ví dụ từ 4/5 xuống 2-3/5.
- Không làm giảm trách nhiệm của sinh viên trong việc tự đọc và sửa bài.
```

### Non-AI alternative

```text
Một template reflection thủ công:
1. Sự kiện thực tế là gì?
2. Mình đang diễn giải nó như thế nào?
3. Có bằng chứng nào ủng hộ hoặc phản bác diễn giải đó?
4. Feedback này nói gì về bài làm, không phải về con người mình?
5. Một bước sửa nhỏ có thể làm trong 10 phút là gì?
```

### AI hypothesis

```text
AI có thể đóng vai một reflection guide: hỏi câu gợi mở, giúp người dùng tách fact/thought/feeling, đề xuất một số câu reframe cân bằng hơn, rồi chuyển feedback thành action items. Người dùng vẫn phải chọn câu reframe đúng với mình và tự sửa bài.
```

### Quick gut

```text
Workflow.
```

---

## 4. Workflow cho Problem #1

### Current workflow

```text
CURRENT STATE — feedback dễ bị cá nhân hóa

[1 Nhận feedback/điểm]
        |
        v
[2 Đọc nhanh hoặc chỉ nhìn điểm tổng]
        |
        v
[3 Cảm thấy thất vọng / xấu hổ / defensive]
        |
        v
[4 Diễn giải tiêu cực: "mình kém"]  <-- bottleneck chính
        |
        v
[5 Né đọc kỹ feedback]
        |
        v
[6 Trì hoãn sửa bài]
        |
        v
[7 Sát deadline mới quay lại sửa, nhưng không biết bắt đầu từ đâu]
```

### Future workflow

```text
FUTURE STATE — feedback được chuyển thành reflection + action

[1 Nhận feedback/điểm]
        |
        v
[2 Sinh viên paste feedback hoặc tự nhập ý chính]
        |
        v
[3 AI hỏi gợi mở]
    - Sự kiện thực tế là gì?
    - Bạn đang cảm thấy gì?
    - Bạn đang diễn giải feedback như thế nào?
    - Feedback này nói về bài làm hay nói về con người bạn?
        |
        v
[4 AI tách fact / feeling / interpretation]
        |
        v
[5 AI gợi ý 2-3 câu reframe cân bằng]  <-- AI intervention
        |
        v
[6 Sinh viên chọn/sửa câu reframe đúng với mình]  <-- human boundary
        |
        v
[7 AI chuyển feedback thành 3 action items cụ thể]
        |
        v
[8 Sinh viên chọn action item nhỏ nhất để bắt đầu]

Fallback:
Nếu AI gợi ý quá chung, quá tích cực giả tạo, hoặc không đúng cảm xúc thật,
sinh viên bỏ gợi ý và dùng template reflection thủ công.
```

### Before / after impact dự kiến

| Metric | Trước | Sau kỳ vọng | Ghi chú |
|---|---:|---:|---|
| Thời gian để bắt đầu đọc kỹ feedback | Có thể trì hoãn vài giờ hoặc vài ngày | Dưới 15 phút sau khi nhận feedback | Cần validate bằng hỏi nhanh bạn học |
| Số action items rõ ràng | 0 hoặc rất mơ hồ | Ít nhất 3 action items | Action item phải gắn với feedback thật |
| Mức distress tự đánh giá | 4/5 hoặc 5/5 | Giảm xuống 2-3/5 | Không dùng như chỉ số lâm sàng |
| Rủi ro AI | Không có AI | AI an ủi sáo rỗng hoặc hiểu sai feedback | Người dùng phải kiểm tra và chỉnh lại |

---

## 5. Problem Statement v0 cho Problem #1

| Field | Nội dung |
|---|---|
| **Actor** | Sinh viên nhận feedback hoặc điểm thấp từ giảng viên, TA, peer review, hoặc hệ thống chấm bài. |
| **Workflow** | Nhận feedback/điểm → đọc nhanh hoặc chỉ nhìn điểm → cảm thấy thất vọng/defensive → diễn giải thành "mình kém" → né đọc kỹ feedback → trì hoãn sửa bài → quay lại sát deadline nhưng không biết bắt đầu từ đâu. |
| **Bottleneck** | Bước diễn giải feedback: sinh viên trộn feedback về bài làm với đánh giá về bản thân, nên không chuyển được feedback thành việc cần sửa. |
| **Impact** | Giảm động lực, trì hoãn sửa bài, bỏ lỡ thông tin hữu ích trong feedback, và dễ lặp lại lỗi cũ. |
| **Success Metric** | Tạo được ít nhất 3 action items từ feedback; giảm thời gian từ lúc nhận feedback đến lúc bắt đầu sửa; giảm self-rated distress sau bước cognitive reframing; không làm thay phần tự học của sinh viên. |
| **Boundary** | AI không chẩn đoán, không trị liệu, không đánh giá năng lực cá nhân, không chấm lại bài. AI chỉ hỗ trợ self-reflection, cognitive reframing và chuyển feedback thành action items; sinh viên tự kiểm tra và quyết định. |
| **Điểm AI can thiệp** | Sau khi sinh viên nhập feedback hoặc cảm xúc ban đầu, trước khi họ né đọc kỹ feedback hoặc trì hoãn sửa bài. |
| **Mức chọn** | **Workflow**: AI hỗ trợ một chuỗi bước rõ ràng gồm hỏi gợi mở, tách fact/thought/feeling, gợi ý reframe, và tạo action items. |
| **Rủi ro & HITL** | Rủi ro: AI an ủi sáo rỗng, hiểu sai feedback, hoặc làm người dùng phụ thuộc. HITL: sinh viên chọn/sửa câu reframe, tự kiểm action items, và tìm người thật/chuyên gia nếu distress nghiêm trọng. |

---

## 6. Rule / Workflow / Agent decision cho Problem #1

| Mức | Phương án | Khi nào đủ | Rủi ro | Chọn? |
|---|---|---|---|---|
| **No AI / process fix** | Dùng checklist reflection giấy hoặc Google Form | Đủ nếu sinh viên tự điền đều và biết tự phản biện suy nghĩ | Dễ bỏ qua khi đang stress; câu hỏi cố định có thể khô | Không chọn làm toàn bộ, nhưng dùng làm fallback |
| **Rule** | Form cố định: fact → feeling → thought → evidence → action | Đủ cho case đơn giản, không cần ngôn ngữ linh hoạt | Ít empathy, khó phản hồi theo ngữ cảnh feedback cụ thể | Không chọn làm toàn bộ |
| **Workflow** | AI hỏi gợi mở → tách fact/thought/feeling → gợi ý reframe → tạo action items → người dùng chọn/sửa | Hợp vì các bước rõ, AI chỉ hỗ trợ ngôn ngữ và phản tư | Có thể gợi ý chung chung hoặc quá tích cực | **Chọn** |
| **Agent** | Agent tự theo dõi feedback, tự đánh giá cảm xúc, tự lập kế hoạch học dài hạn | Chỉ cần nếu có nhiều nguồn dữ liệu, nhiều buổi học, nhiều quyết định động | Quá rộng, nhạy cảm, dễ vượt boundary | Chưa chọn |

Decision:

```text
Go with Workflow, nhưng chỉ trong scope nhỏ: hỗ trợ cognitive reframing cho một feedback cụ thể và tạo action items. Không làm hệ thống mental health, không tự theo dõi cảm xúc dài hạn, không đưa lời khuyên trị liệu.
```

---

## 7. Problem Card #2 — Reframing tin nhắn mơ hồ

### Problem 1 câu

```text
Người dùng nhận một tin nhắn ngắn hoặc mơ hồ rồi diễn giải theo hướng tiêu cực như "họ ghét mình" hoặc "mình làm sai gì đó", dẫn đến overthinking và phản hồi thiếu bình tĩnh.
```

### Current workflow

```text
[1 Nhận tin nhắn ngắn/lạnh hoặc bị seen]
        |
        v
[2 Đọc lại tin nhắn nhiều lần]
        |
        v
[3 Tự suy đoán ý định của người kia]  <-- bottleneck
        |
        v
[4 Hỏi bạn bè hoặc tiếp tục giữ trong đầu]
        |
        v
[5 Trả lời phòng thủ, hỏi dồn, hoặc né giao tiếp]
```

### Future workflow

```text
[1 Nhận tin nhắn gây khó chịu]
        |
        v
[2 Người dùng nhập tin nhắn + cảm xúc của mình]
        |
        v
[3 AI tách fact khỏi interpretation]
        |
        v
[4 AI gợi ý 2-3 cách hiểu trung tính hơn]
        |
        v
[5 Người dùng chọn cách hiểu hợp lý nhất]
        |
        v
[6 AI gợi ý câu trả lời bình tĩnh, không defensive]
        |
        v
[7 Người dùng tự sửa và gửi nếu muốn]

Boundary:
AI không khẳng định người gửi đang nghĩ gì. AI chỉ giúp người dùng thấy nhiều khả năng diễn giải và phản hồi bình tĩnh hơn.
```

Quick gut:

```text
Workflow.
```

---

## 8. Problem Card #3 — Tái cấu trúc suy nghĩ hoảng deadline

### Problem 1 câu

```text
Khi deadline gần, sinh viên thường nghĩ "mình không làm nổi" và rơi vào panic/trì hoãn, thay vì reframe tình huống thành một kế hoạch nhỏ có thể bắt đầu ngay.
```

### Current workflow

```text
[1 Nhìn deadline hoặc task list]
        |
        v
[2 Cảm thấy quá tải]
        |
        v
[3 Nghĩ: "mình không làm nổi"]  <-- bottleneck
        |
        v
[4 Né task bằng việc khác]
        |
        v
[5 Áp lực tăng lên]
        |
        v
[6 Bắt đầu muộn và làm trong stress]
```

### Future workflow

```text
[1 Nhìn deadline hoặc task list]
        |
        v
[2 Người dùng nhập deadline + nỗi lo chính]
        |
        v
[3 AI hỏi: điều gì làm task này đáng sợ nhất?]
        |
        v
[4 AI reframe: từ "mình không làm nổi" sang "mình cần bắt đầu bằng bước nhỏ nhất"]
        |
        v
[5 AI chia task thành 3-5 micro tasks]
        |
        v
[6 Người dùng chọn việc 10 phút đầu tiên]
        |
        v
[7 Bắt đầu làm và tự cập nhật tiến độ]

Boundary:
AI không làm bài thay, không cam kết kết quả. AI chỉ hỗ trợ giảm cảm giác quá tải và giúp người dùng chọn bước đầu tiên.
```

Quick gut:

```text
Rule + Workflow.
```

---

## 9. Câu hỏi muốn nhóm challenge

Khi pitch, mình muốn nhóm challenge các điểm này:

```text
1. Problem feedback reframing có đủ thật và đủ đau không?
2. Non-AI reflection template đã đủ chưa, hay AI thật sự tạo thêm giá trị?
3. Metric "giảm distress" có nên dùng không, hay chỉ nên đo action items và thời gian bắt đầu sửa?
4. Làm sao tránh để AI an ủi sáo rỗng kiểu "bạn làm tốt lắm"?
5. Boundary thế nào để không biến thành AI therapist?
6. Workflow này nên dừng ở một feedback cụ thể hay mở rộng thành learning coach?
```

---

## 10. Quick validation plan

Có thể hỏi nhanh **5 người tính cả mình**. Câu hỏi nên hơi "đào vào pain" một chút để kiểm tra problem có thật sự đau không, không chỉ hỏi chung chung kiểu "bạn có thấy hữu ích không?".

```text
1. Lần gần nhất bạn nhận feedback/điểm thấp, suy nghĩ tiêu cực đầu tiên của bạn là gì?
2. Bạn có từng nghĩ kiểu "mình kém", "mình không hợp môn này", hoặc "mình làm gì cũng sai" không?
3. Sau feedback đó, bạn thường đọc kỹ comment ngay hay né/trì hoãn vì thấy khó chịu?
4. Feedback đó có làm bạn mất động lực, sửa bài muộn, hoặc không biết bắt đầu từ đâu không?
5. Bạn mất khoảng bao lâu để biến feedback thành việc cần sửa cụ thể?
6. Nếu có một workflow hỏi gợi mở, giúp reframe suy nghĩ và tạo 3 action items, bạn có dùng không?
7. Điều gì sẽ làm bạn không tin tool đó: an ủi sáo rỗng, hiểu sai feedback, quá giống AI therapist, hay sợ phụ thuộc?
```

### Bảng ghi kết quả dự kiến

> Ghi chú: bảng này để điền sau khi hỏi thật. Nếu chưa hỏi đủ, giữ nhãn "draft" để không biến giả định thành evidence.

| Người được hỏi | Có gặp problem không? | Workflow hiện tại | Bottleneck | Insight |
|---|---|---|---|---|
| Tôi | Có / Chưa chắc | Nhận feedback → hơi hụt mood → đọc lướt → nghĩ tiêu cực → để sau mới sửa | Cá nhân hóa feedback, khó tách "bài làm chưa tốt" khỏi "mình kém" | Đây là lý do chọn problem này để pitch |
| Người 2 | | | | |
| Người 3 | | | | |
| Người 4 | | | | |
| Người 5 | | | | |

### Cách đọc kết quả hơi tiêu cực hơn

Khi tổng hợp, không chỉ ghi "mọi người thấy có ích". Nên tìm tín hiệu đau thật:

```text
- Có bao nhiêu người né đọc feedback vì thấy khó chịu?
- Có bao nhiêu người từng cá nhân hóa feedback thành đánh giá về bản thân?
- Có bao nhiêu người mất hơn 30 phút hoặc hơn 1 ngày mới bắt đầu sửa?
- Có bao nhiêu người không chuyển được feedback thành action items rõ?
- Có ai nói AI có thể gây phản tác dụng nếu an ủi quá chung hoặc hiểu sai context không?
```

Nếu kết quả tiêu cực mạnh, problem được validate tốt hơn. Nếu nhiều người nói họ đọc feedback và sửa ngay, problem cần thu hẹp lại cho nhóm sinh viên dễ self-criticize hoặc dễ trì hoãn sau feedback.

---

## 11. Tóm tắt để pitch trong 60 giây

```text
Domain của mình là Empathy, nhưng mình thu hẹp vào Cognitive Reframing. Candidate mạnh nhất là feedback reframing cho sinh viên.

Problem là: khi nhận feedback hoặc điểm thấp, sinh viên dễ diễn giải thành "mình kém" thay vì biến feedback thành việc cần sửa. Bottleneck nằm ở bước diễn giải feedback, không phải ở việc thiếu thông tin.

Workflow hiện tại là nhận feedback, đọc nhanh, cảm thấy thất vọng, cá nhân hóa feedback, rồi né sửa bài. Workflow tương lai là sinh viên nhập feedback, AI hỏi gợi mở để tách fact/thought/feeling, gợi ý câu reframe cân bằng, sau đó tạo 3 action items. Sinh viên vẫn tự chọn, sửa và quyết định.

Mức chọn là Workflow, không phải Agent, vì AI chỉ cần hỗ trợ một chuỗi bước rõ ràng. Boundary là AI không trị liệu, không chẩn đoán, không chấm lại bài, và không thay người học chịu trách nhiệm sửa bài.
```
