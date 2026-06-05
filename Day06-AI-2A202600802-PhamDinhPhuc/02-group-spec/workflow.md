# Workflow - Learning OS Knowledge Intake Agent

## 1. Scope Chốt

Chọn **Track A - Learning OS**.

Prototype là một **Learning Content Chatbot Agent** cho chương trình **AI Thực Chiến / AI in Action**: học viên hỏi về nội dung bài học, khái niệm, lab, rubric, ví dụ, hoặc cách áp dụng kiến thức vào bài làm. Agent có 2 kiểu trả lời:

```text
1. Course-grounded answer:
   Nếu user hỏi về bài học/slide/lab/rubric/khóa học cụ thể,
   agent cần source của khóa học: GitHub link, PDF, slide text, README, rubric, pasted note.

2. General learning answer:
   Nếu user hỏi kiến thức chung không gắn với tài liệu khóa học cụ thể,
   agent dùng Tavily để search web, tổng hợp reasoning, rồi trả lời có nguồn.
```

Nếu câu hỏi gắn với khóa học nhưng user chưa đưa source liên quan, agent không đoán nội dung khóa học. Agent hỏi user cung cấp link/tài liệu trước.

Chốt chỉ làm 1 scope chính:

| Scope | User hỏi gì? | Agent giúp gì? |
|---|---|---|
| Course-grounded Learning Support | Nội dung bài học, lab, rubric, slide, README, PDF, repo khóa học. | Xin/đọc source khóa học, giải thích lại, chia nhỏ bước làm, tạo checklist học tập. |
| General Learning Support | Khái niệm AI/product/coding chung không cần bám tài liệu khóa học. | Tavily search web, tổng hợp reasoning, giải thích kèm nguồn. |
| Program Operations Support | Deadline, rule nộp repo, grading, lịch, team rule. | **Out of scope cho prototype chính** vì dễ sai nếu không có dữ liệu nội bộ. Chỉ hỗ trợ draft câu hỏi gửi mentor/TA hoặc trả lời nếu user paste source chính thức. |

## 2. Painpoint Chốt

Học viên không thiếu mỗi câu trả lời. Pain thật là phần nội dung học nằm rải rác ở nhiều nguồn: public repo, README, slide, rubric, notebook, ví dụ code, website/public docs. Khi hỏi một câu mơ hồ như:

```text
Build slice nghĩa là gì?
```

agent cần hiểu user đang hỏi:

- khái niệm nào trong bài học;
- đang áp dụng vào lab nào;
- cần giải thích, ví dụ, checklist học tập hay gợi ý sửa bài;
- có tài liệu/source nào để dựa vào không.

Nếu AI trả lời bằng trí nhớ hoặc suy đoán, output dễ giải thích sai khái niệm, ví dụ lệch rubric, hoặc hướng dẫn lab sai. Vì vậy workflow phải có **crawl/search**, **source check**, **selective ask loop**, **unknown/refusal**, và **correction loop**. Agent không hỏi lại mọi câu; nếu câu hỏi rõ thì đi tìm nguồn và tổng hợp luôn.

## 2.1 Routing Rule Chốt Lại

Agent phải phân biệt **user đang hỏi nội dung khóa học cụ thể** hay **hỏi kiến thức chung**.

| User hỏi | Agent route | Có hỏi link không? |
|---|---|---|
| "Trong slide Day05, build slice là gì?" | Course-grounded | Có, nếu chưa có slide/repo/PDF/source. |
| "Bài này thầy yêu cầu làm gì?" | Course-grounded | Có, xin link/tài liệu bài học. |
| "Build slice là gì trong product management?" | General learning | Không, Tavily search web rồi tổng hợp. |
| "RAG là gì?" | General learning | Không, Tavily search web rồi tổng hợp. |
| "Deadline nộp repo mấy giờ?" | Program Operations | Không đoán; xin source chính thức hoặc draft câu hỏi mentor. |

Rule ngắn:

```text
Nếu câu hỏi nhắc tới "bài này", "slide", "lab", "Day05/Day06", "rubric",
"thầy nói", "khóa học", "AI Thực Chiến":
  -> cần course source.
  -> nếu chưa có source, hỏi user paste Git/PDF/link/text.

Nếu câu hỏi là kiến thức chung:
  -> Tavily search.
  -> tổng hợp reasoning + nguồn.

Nếu câu hỏi là deadline/rule nội bộ:
  -> chỉ trả lời khi user paste source chính thức.
  -> nếu không có, unknown/refusal.
```

## 3. Knowledge Sources

Agent không cần truy cập hệ thống nội bộ thật ngay. Knowledge của prototype đến từ 2 nhóm:

```text
1. Internet / public search:
   - GitHub repo public của lab
   - README / docs / public course material
   - trang hoặc link public mà user cung cấp

2. Loaded docs:
   - file markdown trong repo
   - screenshot text / slide note
   - mentor note / Discord pinned message do user copy vào
```

Prototype hôm nay có thể hard-code một vài source trong app trước. Nếu có thời gian, thêm ô "source/link" để user dán URL hoặc text. Không cần truy cập LMS/Discord nội bộ thật.

## 3.1 Knowledge Pack Lấy Ở Đâu?

Chốt thực tế cho hôm nay:

```text
Knowledge pack không lấy từ LMS/Discord nội bộ thật.
Knowledge pack lấy từ public sources + source user copy/paste + file trong repo.
```

### Nguồn tối thiểu để demo

| Source | Lấy từ đâu? | Dùng để trả lời gì? |
|---|---|---|
| Day05 lab README | Public GitHub repo Day05 hoặc file đã copy trong repo cá nhân | Day05 cần làm gì, cấu trúc `01` và `02`, cuối Day05 cần artifact nào. |
| Day05 group spec files | `Day05-AI-.../02-group-spec/*.md` | Evidence, build slice, workflow, thin SPEC nhóm. |
| Day06 group spec files | `Day06-.../02-group-spec/*.md` | Prototype hôm nay build theo workflow nào. |
| Slide screenshots / text | User copy nội dung từ ảnh hoặc paste note | Gate checklist, 5 tracks, yêu cầu demo/repo. |
| Mentor/Discord note | User paste thủ công vào app | Update mới như deadline, rule nộp, group decision. |

### Public search source

Nếu prototype có internet/search tool:

```text
Agent search:
  - GitHub repo public của lab
  - README / docs public
  - link public user đưa

Agent không search:
  - LMS private
  - Discord private
  - tài liệu nội bộ không có quyền truy cập
```

### Loaded source trong prototype

Nếu không kịp làm real internet search, prototype vẫn hợp lệ bằng cách hard-code một source pack nhỏ:

```text
sourcePack = [
  Product management concept summaries,
  Day05 learning concept notes,
  thin spec / build slice / 4 paths definitions,
  rubric or slide text copied from screenshots,
  examples generated from source text
]
```

Sau đó agent search trong `sourcePack` bằng keyword/scope. Nếu làm được internet thật, agent crawl/search public pages trước rồi lưu kết quả vào searchable sources. Demo vẫn chứng minh được:

```text
clear question -> crawl/search -> summarize -> answer
ambiguous/hard topic -> ask 1-3 questions -> crawl/search -> answer
no source -> unknown/refusal
correction -> search lại
```

### Source status bắt buộc

Mỗi output phải nói rõ nó lấy từ đâu:

| Status | Khi nào dùng? |
|---|---|
| Public source found | Tìm thấy trong GitHub/public docs/link user đưa. |
| Loaded source found | Tìm thấy trong source pack hard-code hoặc text user paste. |
| Missing | Không tìm thấy trong public/loaded sources. |
| Outdated risk | Có nguồn nhưng có thể bị update mới thay thế. |
| Conflict | Nhiều nguồn nói khác nhau. |

Điểm quan trọng:

```text
Nếu user hỏi "deadline đổi chưa?"
mà không có public source hoặc mentor note mới,
agent phải trả lời Unknown, không được đoán.
```

| Source group | Ví dụ tài liệu | Dùng cho scope |
|---|---|---|
| Public internet search | GitHub repo lab, README public, public docs/link user đưa. | Learning Content Support |
| Course content docs | Slide bài học, notebook, README lab, prompt examples, code template. | Learning Content Support |
| Assignment docs | Lab brief, rubric, acceptance checklist, repo instructions. | Learning Content Support nếu liên quan đến cách làm bài. |
| Program ops docs | Schedule, deadline, submission rule, team rule, demo instruction, FAQ. | Out of scope, chỉ dùng khi user paste source chính thức. |
| Live updates | Discord pinned messages, mentor note, change log. | Out of scope, chỉ dùng làm pasted source nếu user cung cấp. |

Source rule:

```text
Nếu thông tin không tìm thấy trong internet/public source hoặc loaded docs,
hoặc source có thể outdated/conflict,
agent không được bịa.
Agent phải nói rõ: "mình chưa tìm thấy nguồn đủ tin cậy".
```

## 3.2 Source Ingestion Pipeline

Khi user paste GitHub link hoặc PDF/link tài liệu, agent không trả lời ngay từ URL thô. Agent phải biến source thành text searchable trước.

### Tool split cho bản build

```text
Tavily Search Tool
  -> dùng cho internet/public web search, public docs, public pages.

GitHub Reader Tool
  -> dùng khi user paste GitHub repo/file link.
  -> đọc README/docs/rubric/notebook markdown trước, không đọc toàn repo nếu không cần.

PDF Reader Tool
  -> dùng khi user paste PDF link/file.
  -> extract text theo page, chunk theo page/section, cite page nếu có.

Guard / Unknown Rule
  -> nếu tool không đọc được source, agent không đoán.
  -> agent yêu cầu user paste text/link public hoặc draft câu hỏi gửi mentor/TA.
```

Tavily đã đủ cho web search, nhưng không nên coi Tavily là cách duy nhất để đọc Git/PDF. GitHub link và PDF cần một bước ingestion riêng để biến tài liệu thành chunks có metadata.

### Link type detection

```text
User paste source
  -> Agent detect loại source
     A. GitHub repo link
     B. GitHub file link
     C. Raw text/markdown link
     D. PDF link
     E. Unknown/private link
```

### Cách đọc từng loại source

| Source type | Tool/cách đọc | Output trung gian |
|---|---|---|
| GitHub repo link | List files -> ưu tiên README, docs, `.md`, notebooks, assignment/rubric files | Repo source pack |
| GitHub file link | Fetch raw file content | File text |
| Raw markdown/text link | Fetch URL text | Page/file text |
| PDF link | Download/read PDF -> extract text per page | PDF page chunks |
| Unknown/private link | Không đọc được -> yêu cầu user paste nội dung hoặc đổi link public | Unknown source status |

### Pipeline chi tiết

```text
+--------------------------------------------------------------+
| USER PASTES SOURCE                                           |
| Example: GitHub repo URL / PDF URL / raw file URL             |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| 1. DETECT SOURCE TYPE                                        |
| - github repo                                                |
| - github file                                                |
| - pdf                                                        |
| - webpage/text                                               |
| - private/unknown                                            |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| 2. LOAD SOURCE CONTENT                                       |
| GitHub repo: list + read relevant files                      |
| GitHub file: fetch raw text                                  |
| PDF: extract page text                                       |
| Web/text: fetch readable text                                |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| 3. NORMALIZE + CHUNK                                         |
| - clean text                                                 |
| - split into chunks                                          |
| - attach metadata                                            |
|   source_url, source_title, file_path/page, chunk_id          |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| 4. SEARCH / RETRIEVE                                         |
| - keyword search or simple semantic search                   |
| - filter by topic/question                                   |
| - return top relevant chunks                                 |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| 5. SOURCE CHECK                                              |
| Found / Missing / Outdated risk / Conflict                   |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| 6. ANSWER WITH CITATION                                      |
| - explanation                                                |
| - example                                                    |
| - checklist                                                  |
| - cite source URL + file/page/chunk                          |
+--------------------------------------------------------------+
```

### GitHub repo reading rule

Nếu user paste một repo, prototype không cần đọc mọi file. Đọc theo ưu tiên:

```text
1. README.md
2. docs/*.md
3. assignment / rubric / guide files
4. notebooks hoặc `.ipynb` nếu có title/markdown cells
5. source code chỉ đọc nếu user hỏi code/lab implementation
```

Nếu repo quá lớn:

```text
Agent hỏi user muốn đọc phần nào:
- README / assignment
- rubric
- docs
- notebook
- code file cụ thể
```

### PDF reading rule

Nếu user paste PDF link:

```text
1. Extract text theo page.
2. Nếu PDF scan ảnh không có text:
   - nói cần OCR hoặc user paste nội dung/screenshot text.
3. Chunk theo page/section.
4. Khi trả lời, cite page number nếu có.
```

### Source metadata bắt buộc

Mỗi chunk phải có metadata để câu trả lời không bị mơ hồ:

```text
source_id
source_type: github_repo / github_file / pdf / webpage / pasted_text
source_url
title
file_path_or_page
chunk_text
retrieved_at
```

### Failure handling

```text
Nếu link private / không đọc được:
  "Mình không truy cập được source này. Bạn paste nội dung hoặc đổi sang link public được không?"

Nếu PDF không extract được text:
  "PDF này có thể là scan/image. Prototype chưa OCR; bạn paste đoạn cần hỏi hoặc gửi bản text."

Nếu repo quá lớn:
  "Repo khá rộng. Bạn muốn mình ưu tiên README, rubric, docs hay một file cụ thể?"
```

## 4. Workflow Tổng Thể Bằng ASCII

```text
+--------------------------------------------------------------------------------+
| USER ASKS                                                                       |
| Example A: "Trong slide Day05, build slice là gì?"                              |
| Example B: "Build slice là gì trong product management?"                        |
+--------------------------------------+-----------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
| 1. READ CONVERSATION MEMORY                                                     |
| - câu hỏi hiện tại                                                               |
| - source user đã paste trước đó                                                  |
| - correction/follow-up trong cùng chat                                           |
+--------------------------------------+-----------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
| 2. ROUTER: QUESTION TYPE                                                        |
| A. Course-grounded question                                                      |
|    Có nhắc tới bài học, slide, lab, Day05/Day06, rubric, thầy nói, khóa học       |
| B. General learning question                                                     |
|    Kiến thức chung, không cần bám tài liệu khóa học cụ thể                       |
| C. Program operations / private rule                                             |
|    Deadline, grading, nộp repo, lịch, team rule                                  |
| D. Ambiguous                                                                     |
|    "Bài này làm sao?", "cái này là gì?"                                          |
+---------------------+-----------------------+----------------------+----------------+
                      |                       |                      |
                      v                       v                      v
+--------------------------------+  +---------------------------+  +---------------------------+
| 3A. COURSE-GROUNDED            |  | 3B. GENERAL LEARNING      |  | 3C. OPS / PRIVATE RULE    |
| Need course source             |  | Use public web search     |  | Do not guess internal info|
+---------------+----------------+  +-------------+-------------+  +-------------+-------------+
                |                                 |                              |
                v                                 v                              v
+--------------------------------+  +---------------------------+  +---------------------------+
| 4A. HAS COURSE SOURCE?         |  | 4B. TAVILY SEARCH         |  | 4C. HAS OFFICIAL SOURCE?  |
| GitHub/PDF/text already loaded |  | Find public explanations  |  | Mentor note / slide / FAQ |
+----------+---------------------+  | docs/examples             |  +--------+------------------+
           |                        +-------------+-------------+           |
     +-----+------+                               |                    +----+----+
     |            |                               v                    |         |
     v            v                  +---------------------------+     v         v
+---------+  +--------------------+   | 5B. SYNTHESIZE REASONING  | +---------+ +------------------+
| YES     |  | NO                 |   | - compare sources         | | YES     | | NO               |
| Ingest  |  | ASK FOR SOURCE     |   | - explain simply          | | summarize| | UNKNOWN/REFUSAL |
| source  |  | "Paste Git/PDF..." |   | - cite URLs               | | source  | | draft question   |
+----+----+  +----------+---------+   +-------------+-------------+ +----+----+ +--------+---------+
     |                  |                           |                  |               |
     v                  v                           v                  v               v
+----------------+  +--------------------+   +----------------+ +----------------+ +----------------+
| 5A. SOURCE     |  | WAIT USER SOURCE   |   | GENERAL ANSWER | | OPS ANSWER     | | REFUSAL        |
| INGESTION      |  | keep same chat     |   | with sources   | | with caution   | | no guessing    |
| GitHub/PDF/Web |  +----------+---------+   +--------+-------+ +--------+-------+ +--------+-------+
+--------+-------+             |                      |                  |                  |
         |                     |                      +------------------+------------------+
         v                     |                                         |
+----------------+             |                                         v
| 6A. RETRIEVE   |<------------+                         +-------------------------------+
| course chunks  | user pastes source                    | 8. OUTPUT CONTRACT            |
+--------+-------+                                       | - detected route              |
         |                                               | - source status               |
         v                                               | - answer / unknown note       |
+----------------+                                       | - reasoning summary           |
| 7A. SOURCE     |                                       | - checklist / next action     |
| CHECK          |                                       +---------------+---------------+
| found/missing  |                                                       |
+----+------+---+                                                       v
     |      |                                           +-------------------------------+
     |      +--------------------+                      | 9. CORRECTION LOOP            |
     v                           v                      | User sửa topic/source/goal     |
+---------+              +------------------+           | -> update memory              |
| FOUND   |              | MISSING /        |           | -> rerun router/retrieve      |
| answer  |              | LOW TRUST        |           +-------------------------------+
| w cite  |              | unknown/refusal  |
+---------+              +------------------+
```

## 5. Ba Route Chạy Như Thế Nào

### 5.1 Course-grounded Learning Support

```text
User hỏi:
  "Trong slide Day05, thin spec là gì?"
  "Bài lab này yêu cầu build slice như thế nào?"
  "Theo rubric của khóa học, happy path với failure path khác nhau ra sao?"

Agent làm:
  1. Detect route = Course-grounded.
  2. Kiểm tra user đã paste source khóa học chưa:
       - GitHub repo/file link
       - PDF/slide link
       - README/rubric text
       - screenshot text / mentor note
  3. Nếu chưa có source:
       - hỏi user paste link/tài liệu liên quan.
       - không tự đoán nội dung khóa học.
  4. Nếu có source:
       - ingest Git/PDF/Web/text;
       - retrieve chunk liên quan;
       - giải thích ngắn;
       - đưa ví dụ bám theo tài liệu khóa học;
       - gợi ý cách áp dụng vào file đang làm.
  5. Nếu source không đọc được:
       - nói unknown/refusal;
       - draft câu hỏi gửi mentor;
       - xin link public hoặc pasted text.

Output:
  - Detected route: Course-grounded
  - Source status
  - Explanation
  - Example
  - Next action
```

### 5.2 General Learning Support

```text
User hỏi:
  "Build slice là gì trong product management?"
  "RAG là gì?"
  "Agentic workflow là gì?"

Agent làm:
  1. Detect route = General learning.
  2. Không yêu cầu user paste tài liệu khóa học.
  3. Dùng Tavily search public web.
  4. Lấy 2-4 nguồn/snippet liên quan.
  5. Tổng hợp reasoning:
       - định nghĩa ngắn;
       - giải thích vì sao;
       - ví dụ dễ hiểu;
       - nếu áp dụng được vào bài lab thì nói là "gợi ý áp dụng", không nói là rubric chính thức.

Output:
  - Detected route: General learning
  - Source status: Public source found
  - Reasoning summary
  - Explanation
  - Example
  - Suggested application
```

### 5.3 Out-of-scope: Program Operations

```text
User hỏi:
  "Day05 phải nộp gì?"
  "Deadline là mấy giờ?"
  "Nộp repo cá nhân hay nhóm?"

Agent làm:
  1. Detect scope = Program Operations.
  2. Không dùng đây làm main flow vì thiếu data nội bộ dễ gây bias.
  3. Nếu user paste source chính thức:
       - tóm tắt source đó;
       - nhắc user kiểm chứng với mentor/TA nếu có deadline/rule.
  4. Nếu không có source:
       - nói out-of-scope/unknown;
       - draft câu hỏi gửi mentor/TA.

Output:
  - Detected route: Out-of-scope Program Operations
  - Source status
  - Unknown/refusal note
  - Draft question for mentor/TA
```

## 6. Working Memory

Agent giữ một working memory cho **case hiện tại**, không mở conversation mới khi user bổ sung context.

| Field | Ý nghĩa |
|---|---|
| Current case | Câu hỏi/task hiện tại user đang xử lý. |
| Scope | Learning Content, Out-of-scope Program Operations, hoặc Ambiguous. |
| Day/module | Day05, Day06, lab nào, khái niệm nào. |
| User role | Learner, reviewer, builder, hoặc người đang làm lab. |
| Knowledge source used | Internet/public link, file, slide, README, screenshot, Discord note nào đã dùng. |
| Source status | Found, missing, outdated risk, conflict. |
| Missing info | Khái niệm, lab, source, ví dụ, output format còn thiếu. |
| Desired output | Explanation, example, learning checklist, application guide, question to mentor. |
| Conversation corrections | User đã sửa scope/day/context gì trong cuộc trò chuyện. |

## 7. Selective Ask Loop Policy

Agent không hỏi cố định 3 câu, và cũng không hỏi lại mọi câu. Agent chỉ hỏi khi việc hỏi thêm giúp giảm sai lệch rõ ràng.

```text
Nếu câu hỏi rõ và là kiến thức chung:
  không hỏi thêm.
  dùng Tavily search web rồi tổng hợp reasoning.

Nếu câu hỏi rõ nhưng gắn với bài học/slide/lab/rubric cụ thể:
  kiểm tra đã có course source chưa.
  nếu có source: ingest/retrieve rồi trả lời.
  nếu chưa có source: hỏi user paste GitHub/PDF/link/text.

Nếu câu hỏi mơ hồ:
  hỏi 1-3 câu.

Nếu topic quá rộng hoặc khó:
  hỏi user muốn học ở mức nào hoặc áp dụng vào lab nào.

Nếu user trả lời vẫn thiếu:
  hỏi tiếp vòng sau, nhưng vẫn giữ cùng conversation.
```

Khi nào phải hỏi lại:

| Trường hợp | Có hỏi không? | Ví dụ |
|---|---|---|
| Câu hỏi kiến thức chung rõ | Không hỏi | "Build slice là gì trong product management?" -> Tavily search luôn. |
| Câu hỏi khóa học rõ nhưng thiếu source | Có hỏi source | "Trong slide Day05 build slice là gì?" -> xin slide/repo/PDF/text nếu chưa có. |
| Câu hỏi mơ hồ | Hỏi | "Bài này làm sao?" -> hỏi bài nào/khái niệm nào. |
| Topic quá rộng | Hỏi | "Giải thích AI product management" -> hỏi muốn phần nào. |
| Topic khó/đa nghĩa | Hỏi | "Agentic workflow là gì?" -> hỏi trong context lab hay kỹ thuật. |
| Thiếu mục tiêu học | Hỏi | "Thin spec" -> hỏi muốn định nghĩa, ví dụ hay áp dụng vào file. |
| Thiếu source cho nội dung lớp | Hỏi | "Framework thầy nói sáng nay là gì?" -> xin slide/link/text. |

Ví dụ ask loop:

```text
User: Bài này làm sao?

Agent:
Mình cần làm rõ một chút trước khi tìm nguồn:
1. Bạn đang hỏi Day05 hay Day06?
2. Bạn hỏi khái niệm nào hoặc phần nào của lab?
3. Bạn muốn giải thích ngắn, ví dụ, hay checklist áp dụng?
```

Ví dụ không hỏi:

```text
User: Build slice là gì trong product management?

Agent:
Không cần hỏi thêm vì intent đã rõ.
Đi Tavily search public web về "build slice" trong product management,
rồi tổng hợp định nghĩa + reasoning + ví dụ + nguồn.
```

Ví dụ hỏi source khóa học:

```text
User: Trong slide Day05, build slice là gì?

Agent:
Mình cần source của khóa học để tránh đoán sai nội dung slide.
Bạn paste GitHub repo, PDF/slide link, hoặc đoạn text liên quan được không?
```

## 8. Source Check Policy

Agent chỉ trả lời chắc khi có nguồn từ internet/public search hoặc loaded docs.

Nguồn ưu tiên:

1. GitHub repo public / README / lab brief / rubric của chương trình.
2. Public docs, website, hoặc link chính thức user cung cấp.
3. Slide hoặc screenshot chính thức của buổi học.
4. Schedule, submission rule, Discord pinned message nếu user copy/dán vào.
5. Mentor note/change log nếu user cung cấp.
6. Context user cung cấp trong conversation.

Nếu nhiều nguồn mâu thuẫn:

```text
Agent không chọn bừa.
Agent nêu mâu thuẫn:
  - Source A nói gì
  - Source B nói gì
Agent ưu tiên nguồn mới hơn/chính thức hơn nếu rõ.
Nếu không rõ, agent draft câu hỏi gửi mentor/TA.
```

## 9. Unknown / Refusal Policy

Agent phải nói không biết khi:

- không tìm thấy thông tin qua internet/public search hoặc loaded docs;
- user hỏi deadline/rule vận hành nhưng không paste source chính thức;
- câu hỏi quá mơ hồ và user chưa bổ sung context;
- nguồn mâu thuẫn nhau;
- user yêu cầu agent đoán thay vì dựa vào tài liệu.

Mẫu trả lời:

```text
Mình chưa tìm thấy nguồn đủ tin cậy cho thông tin này.
Mình không muốn đoán vì có thể làm sai deadline/rubric.
Bạn có thể gửi thêm link/source, hoặc hỏi mentor/TA bằng câu này:
"[draft question]"
```

## 10. Output Contract

Mỗi câu trả lời của prototype nên có format ổn định:

| Output | Nội dung |
|---|---|
| Detected route | Course-grounded / General learning / Program Operations / Ambiguous. |
| Source status | Found / Missing / Outdated risk / Conflict. |
| Answer summary | Câu trả lời ngắn dựa trên course source hoặc Tavily web source. |
| Reasoning summary | Vì sao agent trả lời như vậy, dựa trên source nào. |
| Action checklist | 3-5 bước tiếp theo. |
| Missing info | Thứ còn thiếu để trả lời chắc hơn. |
| Unknown note | Phần agent không biết hoặc cần mentor/TA xác nhận. |
| Suggested follow-up | Câu hỏi tiếp theo hoặc draft hỏi mentor/TA. |

Ví dụ output:

```text
Detected route: Course-grounded
Source status: Found in loaded slide note + Day05 README

Summary:
Build slice là lát cắt nhỏ của sản phẩm: một user, một task,
một AI decision, một output đủ để demo.

Checklist:
1. Xác định user cụ thể.
2. Chọn một task hẹp.
3. Chọn AI hỗ trợ quyết định nào.
4. Định nghĩa output nhìn thấy được.
5. Viết failure path cần test.

Unknown note:
Mình chưa thấy ví dụ cụ thể hơn trong source hiện có; nếu cần, hãy gửi thêm slide hoặc rubric.
```

## 11. Four Paths Cần Test

| Path | Input demo | Agent behavior | Output mong muốn |
|---|---|---|---|
| General happy | "Build slice là gì trong product management?" | Detect General learning, dùng Tavily search, tổng hợp reasoning. | Explanation + reasoning + source URLs. |
| Course happy | User paste Day05 GitHub/PDF, hỏi "Trong Day05 build slice là gì?" | Detect Course-grounded, ingest source, retrieve chunk, trả lời bám tài liệu. | Explanation + example + checklist áp dụng vào lab. |
| Low-confidence | "Bài này làm sao?" | Không trả lời ngay; hỏi bài nào/source nào/output mong muốn. | Ask loop trong cùng chat. |
| Course no-source | "Trong slide thầy nói framework X là gì?" nhưng chưa có slide/source. | Không đoán; hỏi user paste GitHub/PDF/link/text. | Request source rõ ràng. |
| No-source / Unknown | User paste source nhưng tool không đọc được hoặc không thấy chunk liên quan. | Không đoán; nói chưa thấy nguồn, draft câu hỏi gửi mentor. | Refusal rõ + cách kiểm chứng. |
| Correction | User sửa "không phải build slice, là failure path." | Update working memory, retrieve source mới, đổi câu trả lời. | Explanation mới đúng context. |
| Out-of-scope | User hỏi "deadline nộp repo mấy giờ?" mà không paste source. | Không trả lời rule; draft câu hỏi gửi mentor/TA. | Unknown/refusal rõ. |

## 12. Day06 Build Slice

Prototype hôm nay chỉ cần build lát cắt nhỏ:

```text
Một học viên hỏi chatbot agent về nội dung học tập
  -> Agent route câu hỏi
  -> Nếu là kiến thức chung: Tavily search web -> tổng hợp reasoning -> trả lời có source
  -> Nếu là nội dung khóa học cụ thể:
       nếu đã có GitHub/PDF/text source -> ingest/retrieve -> trả lời bám source
       nếu chưa có source -> hỏi user paste link/tài liệu liên quan
  -> Nếu là deadline/rule nội bộ -> không đoán, xin source chính thức hoặc draft câu hỏi mentor/TA
  -> Nếu user correction -> update cùng conversation và chạy lại
```

Không build cả LMS. Không build full chatbot cho mọi môn học. Chỉ cần chứng minh một flow:

```text
input -> route -> Tavily search or ask course source -> source ingestion -> answer/unknown -> correction
```

## 13. Owner Plan

| Owner | Việc làm | Output |
|---|---|---|
| Phúc | Evidence | Screenshot slide/repo + quote câu hỏi mơ hồ |
| Phúc | SPEC | `evidence-pack.md`, `thin-spec.md`, `workflow.md` |
| Phúc | Prototype | UI có chat, quick options, source status, checklist |
| Phúc | Test | Happy, low-confidence, no-source, correction, wrong-scope |
| Phúc | Demo | Demo script cho input -> AI -> output -> failure handling |

## 14. Agent Count Decision

### Chốt cho Day06 prototype

```text
Không cần build nhiều agent thật.
Prototype nên có 1 user-facing agent chính,
bên trong chia thành 4 role/step logic.
```

Lý do:

- bài Day06 cần demo một flow chạy được, không cần kiến trúc multi-agent phức tạp;
- nguồn dữ liệu nhỏ: public GitHub repo, README, slide text, rubric, screenshot, FAQ;
- nếu tách quá nhiều agent thật, dễ mất thời gian vào plumbing thay vì demo failure path;
- vẫn thể hiện đủ "agentic" vì agent chủ động hỏi thêm, chọn scope, tìm source, từ chối khi thiếu nguồn, và sửa theo context mới.

### Kiến trúc khuyến nghị

```text
+--------------------------------------------------------------+
| 1 USER-FACING AGENT: Learning OS Knowledge Intake Agent       |
|                                                              |
|  Internal roles / logic steps:                               |
|                                                              |
|  [A] Intake + Router                                         |
|      - đọc câu hỏi                                           |
|      - xem conversation context                              |
|      - detect route: Course-grounded / General / Ops         |
|      - nếu general thì cho Tavily search luôn                |
|      - nếu course-grounded thiếu source thì hỏi link/tài liệu|
|      - nếu mơ hồ/khó thì tạo câu hỏi follow-up               |
|                                                              |
|  [B] Source Retriever                                        |
|      - Tavily search cho câu hỏi general                     |
|      - GitHub/PDF/text ingestion cho course source           |
|      - lấy đoạn tài liệu/snippet liên quan                   |
|      - ghi source status                                     |
|                                                              |
|  [C] Answer Composer                                         |
|      - tạo summary                                           |
|      - tạo checklist                                         |
|      - tạo missing info                                      |
|      - tạo suggested next step                               |
|                                                              |
|  [D] Safety / Unknown Guard                                  |
|      - chặn suy đoán                                         |
|      - nếu thiếu nguồn thì nói không biết                    |
|      - draft câu hỏi gửi mentor/TA                           |
+--------------------------------------------------------------+
```

Trong code có thể làm 1 function/agent chính, nhưng UI hoặc log nên show rõ agent đang ở step nào.

### Agent nằm ở đâu trong sản phẩm?

```text
backend/learning_agent.py
  -> LearningOSAgent
       Step A: detect_route()
       Step B: load_source()
       Step C: retrieve()
       Step D: compose_with_llm()
       Step E: guard/refusal trong ask()

backend/llm_provider.py
  -> LLMClient
       OpenAI / Groq / Gemini / mock

backend/server.py
  -> API layer
       /api/ask
       /api/source
       /api/health
```

Agent không nằm ở frontend. Frontend chỉ là UI demo. Quyết định route, gọi tool, refusal, và compose answer nằm ở backend.

### LLM provider dùng ở đâu?

LLM provider chỉ dùng ở bước **Answer Composer**:

```text
route -> tools/retrieval -> source check -> LLM compose
```

Không dùng LLM để bỏ qua source check. Nếu thiếu source khóa học, agent phải hỏi user paste GitHub/PDF/text trước.

## 15. Step-by-step Build Workflow

### Step 0 - Prepare Searchable Knowledge

```text
Input:
  - Tavily API search cho câu hỏi kiến thức chung
  - GitHub repo/file link nếu user cung cấp
  - PDF/link tài liệu nếu user cung cấp
  - pasted text từ slide/README/rubric/mentor note
  - local files như thin-spec.md, workflow.md, evidence-pack.md nếu dùng trong demo

Agent action:
  - với Tavily: lưu title, URL, snippet/content, retrieved_at
  - với GitHub/PDF/text: extract text, chia chunks
  - gắn metadata: source_name, route, file/page/url, retrieved_at

Output:
  - searchable source chunks hoặc web search results sẵn sàng để retrieve
```

Prototype đơn giản có thể hard-code vài source public trong `app.js` trước. Nếu có thời gian thì thêm ô nhập URL/text để user dán source.

### Step 1 - User asks

```text
Input:
  User: "Build slice nghĩa là gì?"

Agent action:
  - đọc câu hỏi mới
  - đọc working memory cũ nếu có

Output:
  - raw_user_intent
```

### Step 2 - Intake + Router

```text
Agent quyết định:
  A. Course-grounded Learning
  B. General Learning
  C. Program Operations
  D. Ambiguous

Nếu câu hỏi general rõ:
  đi Step 4B - Tavily Search.

Nếu câu hỏi course-grounded rõ:
  kiểm tra đã có source khóa học chưa.
  nếu chưa có source, hỏi user paste GitHub/PDF/link/text.
  nếu có source, đi Step 4A - Source Ingestion/Retrieve.

Nếu câu hỏi mơ hồ/khó/quá rộng:
  đi Step 3 - Ask Loop.
```

Routing examples:

| User input | Detected route |
|---|---|
| "Build slice là gì trong product management?" | General Learning |
| "Trong slide Day05, thin spec là gì?" | Course-grounded Learning |
| "Day05 phải nộp gì?" | Program Operations |
| "Bài này làm sao?" | Ambiguous |
| "Repo cá nhân hay nhóm?" | Program Operations |

### Step 3 - Selective Ask Loop

```text
Input:
  Câu hỏi mơ hồ, topic quá rộng, topic khó/đa nghĩa, hoặc thiếu mục tiêu học.

Agent asks:
  - Bạn hỏi khái niệm/lab nào?
  - Bạn muốn giải thích, ví dụ, hay checklist áp dụng?
  - Câu này cần bám tài liệu khóa học không?
  - Nếu có, bạn paste GitHub/PDF/link/text của khóa học được không?

User response:
  - bấm option
  - hoặc nhập thêm context tự do

Output:
  - updated_working_memory
```

Important:

```text
User trả lời follow-up thì không mở conversation mới.
Agent append context vào case hiện tại rồi chạy lại Step 2.
```

### Step 4 - Search / Ingest / Retrieve Source

```text
Input:
  - detected_route
  - user question
  - working memory
  - Tavily search tool
  - GitHub/PDF/text source nếu có

Agent action:
  - nếu route = General Learning:
       dùng Tavily search public web
  - nếu route = Course-grounded:
       ingest GitHub/PDF/text source trước
       search chunks theo keyword/semantic match
  - nếu route = Program Operations:
       chỉ dùng source chính thức user paste
  - chọn source liên quan nhất
  - đánh dấu source status

Output:
  - relevant_sources
  - source_status
```

Source status có 4 trạng thái:

| Status | Ý nghĩa |
|---|---|
| Found | Có nguồn đủ liên quan để trả lời. |
| Missing | Không tìm thấy nguồn trong internet/public search hoặc loaded docs. |
| Outdated risk | Có nguồn nhưng có thể đã đổi, ví dụ deadline/update. |
| Conflict | Hai nguồn nói khác nhau. |

### Step 5 - Source Check

```text
Nếu source_status = Found:
  -> Step 6A - Compose Answer.

Nếu source_status = Missing / Outdated risk / Conflict:
  -> Step 6B - Unknown / Refusal.
```

Decision rule:

```text
Agent chỉ trả lời chắc khi có source.
Nếu không có source, agent không được đoán.
```

### Step 6A - Compose Answer

```text
Output format:
  - Detected route
  - Source status
  - Reasoning summary
  - Answer summary
  - Action checklist
  - Missing info
  - Suggested next step
```

Example:

```text
Detected route: Course-grounded
Source status: Found

Summary:
Build slice là một lát cắt nhỏ đủ để demo product decision:
một user, một task, một AI decision, một output.

Checklist:
1. Chọn user cụ thể.
2. Chọn task hẹp.
3. Chọn AI decision cần demo.
4. Định nghĩa output nhìn thấy được.
5. Gắn một failure path cần test.
```

### Step 6B - Unknown / Refusal

```text
Output format:
  - Detected route
  - Source status
  - What is unknown
  - Why agent will not guess
  - Draft question for mentor/TA
```

Example:

```text
Mình chưa tìm thấy source đủ tin cậy cho framework bạn hỏi.
Mình không muốn tự bịa định nghĩa vì có thể làm lệch bài lab.

Câu hỏi gửi mentor/TA:
"Trong bài AI Thực Chiến, framework X được định nghĩa như thế nào và có ví dụ áp dụng nào không?"
```

### Step 7 - Correction Loop

```text
User correction examples:
  - "Không phải build slice, tôi hỏi failure path."
  - "Không phải thin spec, tôi hỏi evidence pack."
  - "Có thêm screenshot này."
  - "Mentor vừa giải thích thêm khái niệm này."

Agent action:
  - update working memory
  - update source nếu có
  - quay lại Step 2 hoặc Step 4

Output:
  - answer mới đúng context
```

## 16. Nếu Muốn Nhiều Agent Thật Thì Chia Thế Nào?

Không khuyến nghị cho bản 1 ngày, nhưng nếu muốn nói trong SPEC hoặc demo kiến trúc:

| Agent | Vai trò | Có cần build thật Day06 không? |
|---|---|---|
| Intake Router Agent | Hỏi thêm, detect Learning Content/out-of-scope, update memory. | Có thể giả lập trong 1 agent chính. |
| Retriever Agent | Search public internet + loaded docs. | Có thể là function search đơn giản. |
| Answer Agent | Viết summary/checklist dựa trên source. | Có thể là prompt/logic trong agent chính. |
| Guard Agent | Chặn đoán, xử lý unknown/refusal. | Nên có rule rõ, không nhất thiết tách agent. |

Chốt:

```text
Day06 build:
  1 main agent + 4 internal steps.

Không build:
  4 separate agents thật.
```
