# Day03 - Chatbot vs ReAct Agent

Lab 3 cho repo ViClinDocAgent: so sánh **chatbot baseline** và **ReAct agent** trên cùng use case chuyển ghi chú lâm sàng tiếng Việt thành SOAP note có cảnh báo an toàn.

## Repo này liên quan gì?

Repo gốc đã có:

- `product/app/`: UI mock ClinNote AI Viet Nam.
- `product/pipeline/viclin/mock_pipeline.py`: pipeline deterministic sinh SOAP.
- `research/data/pilot/cases_v0_20.jsonl`: synthetic pilot cases.
- `research/eval/`: validate và score artifacts.

`VinUni/Day03/` là lab riêng, không sửa các phần trên. Lab này dùng lại domain của repo nhưng viết rõ thành ba phần:

- **Chatbot baseline**: code riêng trong `src/chatbot/`, gọi LLM thật đúng 1 lần, không dùng tool.
- **Hybrid ReAct agent**: code riêng trong `src/agent/`, dùng LLM reasoning kết hợp function-control/stage controller, memory, tool observation, budget, guardrails, trace, stop condition và fallback/human escalation.
- **Mix/comparator**: code riêng trong `src/mix/`, chạy cùng một case qua chatbot và agent rồi chấm expected vs actual.
- **DB session workspace**: UI mới không tự hiện ca mẫu; người dùng nhập raw note thật của demo, mỗi phiên chạy được lưu vào SQLite.
- **Doctor/expert finalization chat**: bác sĩ/chuyên gia trao đổi với agent để chỉnh bản nháp cuối, nhưng bản cuối vẫn cần người duyệt.

## Khớp với repo VinUni-AI20k

Bài này được cấu trúc lại theo skeleton `VinUni-AI20k/Day-3-Lab-Chatbot-vs-react-agent`, nhưng tùy biến cho một người làm và dùng OpenAI API:

- Không cần tải local model `.gguf`.
- `.env.example` đặt `DEFAULT_PROVIDER=openai`.
- `src/core/` có provider interface và OpenAI provider.
- `src/agent/agent.py` chứa ReAct loop chính.
- `src/tools/` là extension point cho tools, đúng tinh thần template.
- `src/telemetry/logger.py` ghi JSON logs vào `VinUni/Day03/logs/`.
- `report/individual_reports/individual_report.md` là báo cáo cá nhân cho solo submission.
- `report/group_report/solo_report.md` thay cho group report vì bài này làm một mình.

## Cấu trúc code

```text
VinUni/Day03/
  .env.example                      Mẫu cấu hình API key/model

  src/
    core/
      llm_provider.py               Interface provider
      openai_provider.py            OpenAI API provider có telemetry

    chatbot/
      prompt.py                     System prompt của chatbot bằng Python
      runner.py                     Code chatbot baseline riêng

    agent/
      agent.py                      ReAct loop OO theo template VinUni
      finalizer.py                  Chat bác sĩ-agent để chốt bản nháp cuối
      prompt.py                     System prompt + tool descriptions của agent
      runner.py                     Code ReAct agent riêng

    tools/
      clinical_tools.py             Tool extension point theo template:
                                     memory, budget, routing, facts, safety, guardrail

    mix/
      runner.py                     Chạy chatbot + agent trên cùng case
      scoring.py                    Scorer demo expected vs actual

    shared/
      common.py                     Load env, gọi LLM, parse JSON, load cases
      db.py                         SQLite sessions/messages/runs/final notes

    telemetry/
      logger.py                     Structured JSON logs

    server.py                       Python HTTP server + API + static UI

  public/
    index.html                      UI browser
    app.js                          Gọi API chatbot/agent/compare
    styles.css                      Giao diện

  data/
    test_cases.json                 5 test cases của Lab 3
    day03.sqlite3                   DB local khi chạy app, bị gitignore

  docs/
    workflows.md                    3 workflow ASCII
    report.md                       Nhận định + trace mẫu
```

Các file Python quan trọng:

```text
src/chatbot/prompt.py               Prompt rõ ràng cho chatbot baseline
src/chatbot/runner.py               Chatbot: raw note -> prompt -> LLM -> JSON
src/agent/prompt.py                 Prompt ReAct + tool descriptions
src/agent/runner.py                 Agent: staged controller + LLM action -> tool -> observation -> final
src/agent/tools.py                  memory, budget, stage router, fact extraction, safety, guardrail
src/mix/runner.py                   Chạy so sánh chatbot vs agent
src/mix/scoring.py                  score_clinical_output()
src/server.py                       Day03Handler HTTP API + static UI
```

## Agent production-ish hơn chatbot ở đâu?

Agent hiện không còn chỉ là prompt ReAct đơn giản. Backend ép pipeline theo stage:

```text
Session memory
  -> budget_check
  -> extract_clinical_facts
  -> clinical_stage_router
  -> safety_review nếu cần
  -> final draft
  -> guardrail_review trước khi trả kết quả
```

Các điểm chính:

- **Memory**: khi chạy trong UI session, agent nhận `messages`, `runs`, `final_notes` gần nhất để hiểu bối cảnh bệnh nhân/phiên làm việc.
- **Multi-step reasoning**: mỗi bước vẫn có LLM thought/action, nhưng controller có quyền ép stage bắt buộc.
- **Dynamic decisions**: `clinical_stage_router()` quyết định có cần safety review, long-horizon reconciliation hay escalation.
- **Hybrid FC + reasoning**: tools chạy bằng Python local như function-call/controller layer; LLM dùng cho reasoning và final drafting.
- **Guardrails**: `guardrail_review()` chặn unsupported claim, tự chẩn đoán/kê đơn, thiếu doctor review hoặc thiếu escalation.
- **Cost budget**: `budget_check()` đặt giới hạn `max_iterations`, `max_tool_calls`, `max_llm_calls`; nếu hết budget thì fallback an toàn thay vì đoán tiếp.

## Cách chạy

```powershell
cd "E:\My Dream\PhD Pipeline"
Copy-Item VinUni\Day03\.env.example VinUni\Day03\.env
```

Điền API key thật vào `VinUni\Day03\.env`. Vì bạn dùng OpenAI API nên không cần tải model local:

```text
OPENAI_API_KEY=your_key_here
DEFAULT_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
PORT=8783
```

Chạy Python server:

```powershell
python VinUni/Day03/src/server.py
```

Chạy riêng chatbot:

```powershell
python VinUni/Day03/src/chatbot/runner.py --case TC1_simple_cough
```

Chạy riêng agent:

```powershell
python VinUni/Day03/src/agent/runner.py --case TC3_chest_pain_missing
```

Chạy riêng phần mix/comparator:

```powershell
python VinUni/Day03/src/mix/runner.py --case TC3_chest_pain_missing
```

Mở:

```text
http://localhost:8783
```

## API chính

```text
GET  /api/day03/health
GET  /api/day03/cases
GET  /api/day03/sessions
GET  /api/day03/sessions/:id
POST /api/day03/sessions
POST /api/day03/sessions/:id/run
POST /api/day03/sessions/:id/chat
POST /api/day03/sessions/:id/finalize
POST /api/day03/chatbot
POST /api/day03/agent
POST /api/day03/compare
```

Body tối thiểu:

```json
{
  "case_id": "TC3_chest_pain_missing"
}
```

Hoặc truyền raw note thủ công:

```json
{
  "raw_note": "BN đau ngực. Chưa hỏi thời gian khởi phát...",
  "case_meta": {
    "id": "custom_case",
    "title": "Custom case"
  }
}
```

Luồng app cho người dùng thử nên dùng session API:

```json
{
  "title": "Ca ho cần SOAP",
  "raw_note": "BN ho 3 ngày, không sốt, không khó thở."
}
```

Sau đó gọi `/api/day03/sessions/:id/run` với `mode` là `chatbot`, `agent`, hoặc `mix`. Nếu bác sĩ muốn chỉnh bản nháp, gọi `/api/day03/sessions/:id/chat`; khi bác sĩ/chuyên gia đã duyệt thì lưu qua `/api/day03/sessions/:id/finalize`.

## Deliverables

- `src/core/`: provider pattern theo template.
- `src/chatbot/prompt.py`: Python prompt riêng cho chatbot baseline.
- `src/chatbot/runner.py`: Python code riêng cho chatbot baseline.
- `src/agent/agent.py`: ReAct loop chính theo `Thought -> Action -> Observation`.
- `src/agent/finalizer.py`: doctor-in-the-loop chat để thống nhất bản nháp cuối.
- `src/agent/prompt.py`: Python prompt riêng cho ReAct agent và tool descriptions.
- `src/agent/runner.py`: Python code riêng cho ReAct agent.
- `src/tools/clinical_tools.py`: Python tools thật cho agent.
- `src/telemetry/logger.py`: structured logs cho metrics/debug.
- `src/mix/runner.py`: Python code riêng cho comparator.
- `src/mix/scoring.py`: Python scorer cho expected vs actual.
- `src/server.py`: Python backend chính, gọi chatbot/agent APIs và serve UI.
- `src/shared/db.py`: SQLite DB lưu sessions, messages, runs và final notes.
- `public/`: UI demo chạy trên browser.
- `data/test_cases.json`: 5 cases đúng rubric.
- `docs/workflows.md`: 3 workflow ASCII riêng biệt.
- `docs/report.md`: nhận định, expected vs actual, trace mẫu.
- `report/individual_reports/individual_report.md`: báo cáo cá nhân.
- `report/group_report/solo_report.md`: báo cáo solo thay cho group report.

## Lưu ý an toàn

Demo này chỉ dùng synthetic notes. Không nhập dữ liệu bệnh nhân thật. Agent và chatbot chỉ hỗ trợ documentation, không tự chẩn đoán hoặc kê đơn.
