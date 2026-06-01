# Day03 Workflows

## 1. Workflow Chatbot Baseline

```text
Raw clinical note
      |
      v
Chatbot system prompt
role + job + rules + safety boundary + output JSON
      |
      v
Single real LLM call
      |
      v
Parse JSON response
      |
      v
Display SOAP + warnings + missing questions
```

Chatbot không có tool, không có observation, không có ReAct trace. Đây là baseline để chứng minh case đơn giản có thể xử lý nhanh hơn và rẻ hơn.

Code tương ứng:
- `VinUni/Day03/src/chatbot/prompt.py`
- `VinUni/Day03/src/chatbot/runner.py`

## 2. Workflow ReAct Agent

```text
Raw clinical note
      |
      v
Agent system prompt + tool descriptions
      |
      v
LLM step JSON
Thought + Action + Action Args + Stop Condition
      |
      +---------------------------------+
      |                                 |
      v                                 v
extract_clinical_facts()         safety_review()
      |                                 |
      +----------------+----------------+
                       |
                       v
Observation returned to LLM
                       |
                       v
Continue loop or final
                       |
                       v
Stop:
- enough_evidence
- needs_human_escalation
- tool_fail
- max_iterations
                       |
                       v
SOAP + warnings + full trace
```

Agent có giá trị khi cần grounding, evidence, warning, red flag, medication risk hoặc fallback khi tool fail.

Code tương ứng:
- `VinUni/Day03/src/agent/prompt.py`
- `VinUni/Day03/src/agent/runner.py`
- `VinUni/Day03/src/agent/tools.py`

## 3. Workflow Mixed Comparison

```text
Same test case
      |
      v
Raw note
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
Comparator / Scorer
                  |
                  v
Check:
- critical facts covered
- missing questions found
- red flags/high-risk medication
- unsupported claim risk
- human escalation
                  |
                  v
Expected winner vs actual winner
```

Comparator không thay thế bác sĩ. Nó chỉ giúp bài lab có căn cứ rõ khi nhận định chatbot hay agent phù hợp hơn cho từng case.

Code tương ứng:
- `VinUni/Day03/src/mix/runner.py`
- `VinUni/Day03/src/mix/scoring.py`
