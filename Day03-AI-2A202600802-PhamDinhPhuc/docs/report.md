# Day03 Lab Report: Chatbot vs ReAct Agent

## 1. Tóm tắt bài lab

Bài lab này triển khai lại yêu cầu của repo `VinUni-AI20k/Day-3-Lab-Chatbot-vs-react-agent` trên use case của repo hiện tại: hỗ trợ bác sĩ/chuyên gia chuyển raw clinical note tiếng Việt thành bản nháp SOAP, phát hiện thiếu dữ kiện, cảnh báo rủi ro và yêu cầu bác sĩ duyệt trước khi coi là bản cuối.

Repo mẫu yêu cầu các phần chính:

- Chatbot baseline: một lần gọi LLM, không tool.
- ReAct agent: vòng lặp `Thought -> Action -> Observation -> Final`.
- Tool design: ít nhất 2 tools, mô tả input/output rõ.
- Structured logs: ghi LLM metric, action, loop count, lỗi/failure.
- Evaluation: so sánh chatbot và agent bằng test cases.
- Report: giải thích trace, failure analysis, insight, flowchart.

Phiên bản trong `VinUni/Day03` đã chuyển lab thành một production prototype nhỏ: có backend Python, OpenAI provider, browser UI, SQLite session DB, agent memory, staged reasoning, budget check, guardrails và doctor-in-the-loop chat.

## 2. Vị trí code trong repo

| Thành phần | File/thư mục |
|---|---|
| Browser UI | `VinUni/Day03/public/` |
| Python backend/API | `VinUni/Day03/src/server.py` |
| LLM provider abstraction | `VinUni/Day03/src/core/` |
| Chatbot baseline | `VinUni/Day03/src/chatbot/` |
| ReAct/hybrid agent | `VinUni/Day03/src/agent/` |
| Clinical tools | `VinUni/Day03/src/agent/tools.py`, `VinUni/Day03/src/tools/clinical_tools.py` |
| Comparator/mix mode | `VinUni/Day03/src/mix/` |
| SQLite DB/session storage | `VinUni/Day03/src/shared/db.py` |
| Telemetry logger | `VinUni/Day03/src/telemetry/logger.py` |
| Test cases | `VinUni/Day03/data/test_cases.json` |
| Workflows | `VinUni/Day03/docs/workflows.md` |

Các phần cũ của repo như `product/app/`, `product/pipeline/` và `research/eval/` không bị phá. Day03 là module lab riêng, dùng ý tưởng clinical documentation của repo nhưng tổ chức lại theo cấu trúc chatbot/agent rõ ràng hơn.

## 3. Chatbot baseline

Chatbot trong bài này là baseline tối giản:

```text
Raw clinical note
      |
      v
Chatbot system prompt
      |
      v
OpenAI LLM, 1 call
      |
      v
SOAP draft + warnings + missing questions
```

Code chính:

- `VinUni/Day03/src/chatbot/prompt.py`: system prompt cho documentation assistant.
- `VinUni/Day03/src/chatbot/runner.py`: gọi LLM thật, parse JSON output, normalize schema.
- API: `POST /api/day03/chatbot`.

Chatbot phù hợp với input đơn giản, đủ dữ kiện, ít rủi ro. Điểm yếu là không có tool grounding, không có multi-step trace và khó kiểm chứng vì sao model đưa ra quyết định.

## 4. ReAct/hybrid agent

Agent không trả lời ngay. Nó chạy theo vòng lặp có kiểm soát:

```text
Raw clinical note
      |
      v
Agent prompt + tool descriptions + memory
      |
      v
LLM returns Thought + Action + Args
      |
      v
Controller validates action
      |
      v
Local tool runs
      |
      v
Observation is added back to context
      |
      v
Repeat until enough evidence / escalation / fail / max iterations
      |
      v
Final SOAP draft + warnings + trace
```

Code chính:

- `VinUni/Day03/src/agent/prompt.py`: ReAct system prompt, allowed actions, stop conditions.
- `VinUni/Day03/src/agent/agent.py`: hybrid staged controller.
- `VinUni/Day03/src/agent/runner.py`: public runner, `MAX_ITERATIONS = 6`.
- `VinUni/Day03/src/agent/tools.py`: tools local.
- API: `POST /api/day03/agent`.

Agent hiện có các tools/stages:

| Tool/stage | Vai trò |
|---|---|
| `retrieve_patient_memory` | Lấy context cũ của session để agent hiểu cuộc hội thoại bệnh nhân hiện tại. |
| `budget_check` | Ước lượng cost/latency/complexity để tránh loop quá dài. |
| `extract_clinical_facts` | Tách facts, category, source span, risk level từ raw note. |
| `clinical_stage_router` | Quyết định động bước tiếp theo: đủ dữ kiện, cần safety review hay cần escalation. |
| `safety_review` | Tìm missing questions, red flags, contradictions, human escalation. |
| `guardrail_review` | Chặn unsupported claim, yêu cầu doctor review, đảm bảo không tự chẩn đoán/kê đơn. |
| `final` | Trả SOAP draft cuối cùng kèm warnings và trace. |

Điểm quan trọng: tool trong agent không chỉ là prompt. LLM dùng prompt để chọn action, nhưng action được controller Python validate và chạy bằng function local. Observation của tool sau đó được đưa ngược vào vòng lặp để model quyết định bước tiếp theo.

## 5. Mixed workflow và comparator

Mix mode dùng cùng một raw note để chạy cả chatbot và agent:

```text
Same raw note
      |
      +-------------------------+
      |                         |
      v                         v
Chatbot baseline           ReAct agent
1 LLM call                 LLM + tools + trace
      |                         |
      v                         v
Chatbot output             Agent output
      |                         |
      +-----------+-------------+
                  |
                  v
Comparator / scoring
                  |
                  v
Expected vs actual winner
```

Code chính:

- `VinUni/Day03/src/mix/runner.py`
- `VinUni/Day03/src/mix/scoring.py`
- API: `POST /api/day03/compare`

Comparator chấm demo theo các tín hiệu:

- Có giữ facts quan trọng không.
- Có phát hiện missing questions không.
- Có cảnh báo red flag/high-risk medication không.
- Có yêu cầu doctor review/human escalation đúng lúc không.
- Agent có trace hợp lệ không.

## 6. Test cases

File: `VinUni/Day03/data/test_cases.json`

| Case | Mục đích | Expected winner |
|---|---|---|
| `TC1_simple_cough` | Ho đơn giản, phủ định sốt/khó thở | `chatbot_or_tie` |
| `TC2_simple_back_pain` | Đau lưng có phủ định red flags | `chatbot_or_tie` |
| `TC3_chest_pain_missing` | Đau ngực thiếu onset, đau lan, khó thở, tiền sử tim mạch | `agent` |
| `TC4_warfarin_bleeding` | Warfarin + chảy máu + thiếu INR | `agent` |
| `TC5_ambiguous_or_tool_fail` | Input mơ hồ/tool fail để kiểm tra fallback | `agent` |

## 7. Evidence từ sample local vừa chạy

Sample vừa chạy đã được lưu local ở hai nơi:

- Structured log: `VinUni/Day03/logs/2026-06-01.log`
- SQLite DB: `VinUni/Day03/data/day03.sqlite3`

Snapshot local lúc kiểm tra:

| Artifact | Kích thước | Last write |
|---|---:|---|
| `logs/2026-06-01.log` | 40,988 bytes | 2026-06-01 16:16:35 |
| `data/day03.sqlite3` | 118,784 bytes | 2026-06-01 16:16:35 |

SQLite hiện có:

| Table | Số dòng |
|---|---:|
| `sessions` | 1 |
| `messages` | 18 |
| `runs` | 4 |
| `final_notes` | 0 |

Session mới nhất:

```text
id: ses_9f455b64ad3d4b4e
title: Bệnh Nhân : Lê Dương Hiếu -- Ho, cơ thể mệt mỏi
status: draft
updated_at: 2026-06-01T09:16:35+00:00
```

Run mới nhất:

```text
id: run_2cb889d854fc48cf
mode: mix
trace_len: 6
actual_winner: agent
chatbot_score: 90
agent_score: 100
```

Ngoài run `mix`, DB cũng đang có các run riêng cho chatbot và agent:

| Run | Mode | Trace length | Score | Nhận xét |
|---|---:|---:|---:|---|
| `run_e32228d12e3843bb` | chatbot | 0 | 100 | Chatbot xử lý note ho/mệt mỏi đơn giản, không cần tool. |
| `run_e31f881251fe4700` | chatbot | 0 | 90 | Chatbot tạo SOAP nhưng escalates hơi mạnh với case ho kéo dài. |
| `run_9f4f888f988c45b5` | agent | 3 | n/a | Agent chạy đủ ReAct cơ bản: fact extraction -> safety review -> final. |
| `run_2cb889d854fc48cf` | mix | 6 | chatbot 90, agent 100 | So sánh trực tiếp chatbot vs agent trên cùng session; agent thắng. |

### 7.1 Chatbot run riêng

Chatbot output được lưu trong DB dưới dạng:

```json
{
  "mode": "chatbot_baseline",
  "soap": {
    "subjective": "Bệnh nhân Lê Dương Hiếu có biểu hiện ho kéo dài, cơ thể mệt mỏi...",
    "objective": "",
    "assessment": "Chưa có chẩn đoán trong input; cần bác sĩ xác nhận.",
    "plan": ""
  },
  "warnings": [
    {
      "severity": "major",
      "type": "red_flag",
      "message": "Bệnh nhân có triệu chứng ho kéo dài và cơ thể mệt mỏi, cần được đánh giá thêm."
    }
  ],
  "missing_questions": [
    "Bệnh nhân có sốt không?",
    "Bệnh nhân có tiền sử bệnh lý gì không?",
    "Bệnh nhân có dị ứng thuốc nào không?"
  ],
  "doctor_review_required": true,
  "human_escalation_required": true
}
```

Nhận xét:

- Chatbot giữ được nội dung raw note.
- Chatbot biết hỏi thêm câu hỏi thiếu.
- Tuy nhiên chatbot không có trace để chứng minh vì sao coi đây là `red_flag`.
- Với cùng case này, chatbot bị scorer trừ điểm ở `escalation_correct` vì escalation hơi mạnh so với note ho không có red flag rõ ràng.

### 7.2 Agent run riêng

Agent run riêng có trace 3 bước:

```text
extract_clinical_facts -> safety_review -> final
```

Output agent:

```json
{
  "mode": "react_agent",
  "soap": {
    "subjective": "Bệnh nhân Lê Dương Hiếu có biểu hiện ho kéo dài...",
    "objective": "Không có thông tin khách quan được cung cấp trong ghi chú.",
    "assessment": "Bệnh nhân có triệu chứng ho kéo dài, mệt mỏi, đau rát họng, và ăn uống kém...",
    "plan": "Hỏi thêm về tình trạng dị ứng thuốc. Đánh giá thêm các triệu chứng..."
  },
  "warnings": [
    {
      "severity": "minor",
      "type": "missing_question",
      "message": "Cần hỏi tình trạng dị ứng thuốc của bệnh nhân."
    }
  ],
  "missing_questions": ["Hỏi tình trạng dị ứng thuốc."],
  "doctor_review_required": true,
  "human_escalation_required": false
}
```

Nhận xét:

- Agent không escalate quá mức.
- Agent có trace nên chứng minh được đã gọi `extract_clinical_facts` và `safety_review`.
- Agent output phù hợp vai trò clinical documentation hơn: bản nháp + câu hỏi thiếu + bác sĩ duyệt.

### 7.3 Mix run: so sánh trực tiếp chatbot vs agent

Mix run chạy cùng một session/raw note qua cả hai hệ thống.

| Tiêu chí | Chatbot | Agent |
|---|---|---|
| Mode | `chatbot_baseline` | `react_agent` |
| LLM behavior | 1 call, không tool | Multi-step loop |
| Trace | Không có | 6 bước |
| Memory | Không dùng | Có `retrieve_patient_memory` |
| Budget | Không dùng | Có `budget_check` |
| Safety tool | Không dùng tool | Có `safety_review` |
| Human escalation | `true` | `false` |
| Missing questions | Sốt, tiền sử bệnh, dị ứng thuốc | Dị ứng thuốc |
| Score | 90 | 100 |
| Winner | thua | thắng |

Điểm khác biệt quan trọng trong mix run là agent dùng memory của session:

```json
{
  "patient_memory_available": true,
  "prior_turn_count": 16,
  "prior_run_count": 3,
  "latest_mode": "agent"
}
```

Điều này chứng minh yêu cầu memory/long-horizon: khi bác sĩ quay lại một bệnh nhân/session cũ, agent không chỉ nhìn raw note mới mà còn đọc lại hội thoại và output trước đó như context. Memory có rule rõ:

```text
Use memory only as context, not as new clinical fact unless doctor supplied it.
Prefer newer doctor messages over older static outputs.
If memory conflicts with raw_note, flag contradiction and ask doctor to confirm.
```

Budget object trong mix run:

```json
{
  "max_iterations": 6,
  "max_tool_calls": 6,
  "max_llm_calls": 6,
  "estimated_context_chars": 6328,
  "complexity": "high"
}
```

Điều này phù hợp yêu cầu production: không chỉ dựa vào model quality mà còn có giới hạn cost, loop và context.

Stage router trong mix run:

```json
{
  "recommended_stages": [
    "memory",
    "budget",
    "fact_extraction",
    "safety_review",
    "context_reconciliation",
    "guardrail_review",
    "finalization"
  ],
  "safety_review_required": true,
  "long_horizon_required": true
}
```

Nhận xét:

- Chatbot trả lời nhanh nhưng không có bằng chứng hành động.
- Agent chạy dài hơn nhưng có memory, budget, stage decision, safety review và final trace.
- Đây là điểm cốt lõi của bài lab: chatbot tốt cho format đơn giản, agent tốt cho task cần hành động, kiểm chứng và dừng an toàn.

Trace actions của run mới nhất:

```text
1. retrieve_patient_memory    -> continue
2. budget_check               -> continue
3. extract_clinical_facts     -> continue
4. clinical_stage_router      -> continue
5. safety_review              -> continue
6. final                      -> enough_evidence
```

Log local cũng ghi đúng các loại event mà repo mẫu yêu cầu:

- `LLM_METRIC`: model, latency, prompt tokens, completion tokens, total tokens.
- `AGENT_THINK`: bắt đầu mỗi iteration.
- `AGENT_ACTION`: thought, action, args, stop condition.
- `GUARDRAIL_BLOCK`: ví dụ agent muốn final trước khi gọi `extract_clinical_facts`, controller chặn lại.
- `AGENT_SUCCESS`: agent hoàn tất thành công.

Một failure/guardrail case đã được log:

```text
Iteration 2 - Final blocked: extract_clinical_facts is required before final
```

Điều này phù hợp tinh thần của lab: không chỉ có final answer, mà phải đọc trace/log để hiểu agent đúng hoặc sai ở đâu.

## 8. Đối chiếu rubric repo mẫu

| Rubric repo mẫu | Tình trạng trong `VinUni/Day03` |
|---|---|
| Chatbot Baseline | Có: `src/chatbot/runner.py`, 1 LLM call, no tools. |
| Agent v1 working | Có: ReAct loop với `Thought -> Action -> Observation`. |
| Agent v2 improved | Có: staged controller, memory, budget, guardrails, dynamic router. |
| Tool Design Evolution | Có: tools tách riêng, re-export ở `src/tools/clinical_tools.py`. |
| Trace Quality | Có: trace JSON trong response, structured log trong `logs/`. |
| Evaluation & Analysis | Có: 5 test cases, mix comparator, scoring. |
| Flowchart & Insight | Có: `docs/workflows.md` và report này. |
| Code Quality | Có: module tách `chatbot`, `agent`, `mix`, `core`, `shared`, `telemetry`. |
| Bonus: Monitoring | Có: latency/tokens/loop/action logs. |
| Bonus: Failure Handling | Có: max iterations, guardrail block, JSON normalization, tool failure path. |
| Bonus: Production Ready | Có một phần: SQLite session DB, doctor-in-loop UI, budget guardrail. |

## 9. Nhận định Chatbot vs Agent

Chatbot không sai trong mọi trường hợp. Với notes đơn giản như ho nhẹ hoặc đau lưng đã phủ định red flags, chatbot nhanh hơn, rẻ hơn và đủ dùng vì nhiệm vụ chỉ là chuyển đổi format sang SOAP.

Agent tạo giá trị khi bài toán cần quyết định nhiều bước:

- Cần tách fact có source span trước khi viết SOAP.
- Cần kiểm tra thiếu dữ kiện.
- Cần phát hiện red flags hoặc thuốc nguy cơ cao.
- Cần biết dừng và yêu cầu bác sĩ/chuyên gia duyệt.
- Cần lưu lại trace để debug và chứng minh chất lượng.

Trong bối cảnh clinical documentation, agent không nên được hiểu là hệ thống tự chẩn đoán. Vai trò đúng là hỗ trợ documentation, phát hiện rủi ro, hỏi lại dữ kiện thiếu và giữ bác sĩ ở vòng duyệt cuối.

## 10. Hạn chế hiện tại

- Scoring vẫn là heuristic demo, chưa phải clinical evaluation chuẩn.
- Tool local còn rule-based, chưa có medical knowledge base/RAG.
- Một số test case synthetic; chưa dùng dữ liệu thật và không nên dùng PHI trong lab.
- Latency agent cao hơn chatbot vì nhiều LLM calls.
- Final note hiện là bản nháp; `final_notes` chưa có bản approved vì sample chưa bấm lưu bản cuối.

## 11. Hướng phát triển

- Thêm RAG guideline nội bộ để grounding tốt hơn.
- Thêm dashboard parse log để tính aggregate token/cost/latency.
- Thêm ablation: agent không memory vs có memory, không guardrail vs có guardrail.
- Thêm evaluator riêng cho unsupported claims.
- Thêm export report cho từng session bác sĩ/chuyên gia.

## 12. Cách chạy

```powershell
cd "E:\My Dream\PhD Pipeline"
python -m pip install -r VinUni\Day03\requirements.txt
python VinUni\Day03\src\server.py
```

Mở browser:

```text
http://localhost:8783
```

Yêu cầu `.env`:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
PORT=8783
```

Chạy test structure:

```powershell
python -m pytest VinUni\Day03\tests -q
```
