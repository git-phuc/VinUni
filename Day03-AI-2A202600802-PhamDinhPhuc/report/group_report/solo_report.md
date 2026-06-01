# Solo Report - Day03 Lab: Chatbot vs ReAct Agent

This submission is completed by one student. The group report is therefore written as a solo project report.

## 1. Project Summary

The lab compares a simple chatbot baseline with a ReAct/hybrid agent for Vietnamese clinical documentation. The system receives a raw clinical note and produces a SOAP draft, missing questions, warnings, and doctor review requirements.

Use case:

```text
Vietnamese raw clinical note -> SOAP draft -> safety/missing data review -> doctor approval
```

Main implementation:

- Chatbot baseline: `VinUni/Day03/src/chatbot/`
- ReAct agent: `VinUni/Day03/src/agent/`
- Mix comparator: `VinUni/Day03/src/mix/`
- Browser UI: `VinUni/Day03/public/`
- Database/session storage: `VinUni/Day03/src/shared/db.py`
- Logs/telemetry: `VinUni/Day03/src/telemetry/logger.py`

## 2. Chatbot Baseline

The chatbot calls the OpenAI model once and does not use tools. It relies entirely on the system prompt and output schema.

Strengths:

- Fast and simple.
- Good enough for clear one-step notes.
- Lower cost than the agent.

Weaknesses:

- No tool grounding.
- No multi-step trace.
- Weaker at detecting missing information and safety-critical cases.

## 3. ReAct / Hybrid Agent

The agent follows the `Thought -> Action -> Observation` pattern. It uses a Python controller to validate actions, execute local tools, append observations, and enforce stopping conditions.

Implemented actions/tools:

- `retrieve_patient_memory`
- `budget_check`
- `extract_clinical_facts`
- `clinical_stage_router`
- `safety_review`
- `guardrail_review`
- `final`

Production-oriented additions:

- Session memory through SQLite.
- Cost/complexity budget check.
- Guardrail block before unsafe finalization.
- `MAX_ITERATIONS = 6` safeguard.
- Doctor/expert finalization chat.
- Structured logs for LLM metrics and agent actions.

## 4. Tool Design Evolution

The initial tool set was simple:

```text
extract_clinical_facts(raw_note)
safety_review(raw_note, facts)
```

It was expanded to support production-style agent behavior:

```text
retrieve_patient_memory -> budget_check -> extract_clinical_facts
-> clinical_stage_router -> safety_review -> guardrail_review -> final
```

This makes the agent clearer as an agent, not just a long prompt. The LLM chooses actions, but the backend validates and executes tools.

## 5. Evaluation

Five synthetic cases are stored in `VinUni/Day03/data/test_cases.json`:

| Case | Expected |
|---|---|
| `TC1_simple_cough` | Chatbot or tie |
| `TC2_simple_back_pain` | Chatbot or tie |
| `TC3_chest_pain_missing` | Agent |
| `TC4_warfarin_bleeding` | Agent |
| `TC5_ambiguous_or_tool_fail` | Agent |

The latest local sample run was saved in both SQLite and structured logs:

- DB: `VinUni/Day03/data/day03.sqlite3`
- Log: `VinUni/Day03/logs/2026-06-01.log`

Latest run summary:

```text
mode: mix
trace_len: 6
actual_winner: agent
chatbot_score: 90
agent_score: 100
```

Trace actions:

```text
retrieve_patient_memory -> budget_check -> extract_clinical_facts
-> clinical_stage_router -> safety_review -> final
```

## 6. Failure / Debugging Case Study

One useful log event shows the guardrail working:

```text
Iteration 2 - Final blocked: extract_clinical_facts is required before final
```

This means the LLM attempted to finalize too early, but the Python controller blocked the final answer until fact extraction had been performed. This is exactly why ReAct systems need a controller and logs, not only a stronger prompt.

## 7. Insight

The chatbot is best for simple notes where the task is mainly formatting. The agent is better when clinical safety requires multi-step reasoning, tool use, missing-question detection, and a defensible trace.

The most important lesson is that the trace is the evidence. A final answer alone is not enough for evaluating an agent. Logs reveal whether the agent used the correct tool, stopped for the right reason, and handled failure safely.

## 8. Flowchart

See:

```text
VinUni/Day03/docs/workflows.md
```

## 9. Future Improvements

- Add RAG over local clinical guidelines.
- Add a log dashboard for aggregate latency, token cost, and failure rates.
- Add ablation studies: without memory, without guardrails, without stage router.
- Add unsupported-claim evaluator.
- Add exportable session report after doctor approval.
