# Individual Report - Day03 Lab

## Student

- Name: Solo submission
- Repository use case: ViClinDocAgent clinical documentation assistant
- Provider: OpenAI API
- Model used in local run: `gpt-4o-mini`

## I. Technical Contribution

I implemented a complete solo version of the Day03 lab inside `VinUni/Day03`, following the structure and learning objectives of `VinUni-AI20k/Day-3-Lab-Chatbot-vs-react-agent`.

Main code contributions:

| Area | Files |
|---|---|
| Chatbot baseline | `src/chatbot/prompt.py`, `src/chatbot/runner.py`, `src/chatbot/schema.py` |
| ReAct/hybrid agent | `src/agent/agent.py`, `src/agent/runner.py`, `src/agent/prompt.py` |
| Agent tools | `src/agent/tools.py`, `src/tools/clinical_tools.py` |
| Doctor finalization chat | `src/agent/finalizer.py` |
| LLM provider layer | `src/core/llm_provider.py`, `src/core/openai_provider.py` |
| Mix comparison | `src/mix/runner.py`, `src/mix/scoring.py` |
| Session database | `src/shared/db.py` |
| Telemetry/logging | `src/telemetry/logger.py` |
| Browser UI | `public/index.html`, `public/app.js`, `public/styles.css` |
| Test cases | `data/test_cases.json` |

The chatbot is intentionally simple: it makes one real LLM call and does not use tools. The agent is implemented as a controlled ReAct system: it asks the LLM for `Thought`, `Action`, and `Action Args`, then the Python backend validates and executes local tools.

## II. Debugging Case Study

### Failure observed

During local testing, the agent sometimes attempted to finalize before completing the required fact extraction step. The structured log captured this event:

```text
Iteration 2 - Final blocked: extract_clinical_facts is required before final
```

This is a useful failure because it shows that a ReAct agent cannot rely only on prompt instructions. The model may choose a plausible but premature `final` action. Without a controller, the system could return an answer without evidence extraction.

### Fix

The agent controller enforces required stages:

```text
retrieve_patient_memory -> budget_check -> extract_clinical_facts
-> clinical_stage_router -> safety_review -> final
```

If the LLM tries to skip an essential step, the guardrail blocks finalization and forces the loop to continue. This improved the reliability of the agent and made the trace easier to grade.

### Evidence from local logs

The local log file is:

```text
VinUni/Day03/logs/2026-06-01.log
```

It contains:

- `LLM_METRIC`: latency, prompt tokens, completion tokens, total tokens.
- `AGENT_THINK`: iteration start.
- `AGENT_ACTION`: selected action and arguments.
- `GUARDRAIL_BLOCK`: blocked unsafe/premature final answer.
- `AGENT_SUCCESS`: successful completion.

## III. Actual Local Comparison

I ran chatbot, agent, and mix mode in the local browser UI. The results were saved in SQLite:

```text
VinUni/Day03/data/day03.sqlite3
```

Current local DB summary:

| Table | Rows |
|---|---:|
| `sessions` | 1 |
| `messages` | 18 |
| `runs` | 4 |
| `final_notes` | 0 |

Latest mix run:

```text
run_id: run_2cb889d854fc48cf
mode: mix
trace_len: 6
actual_winner: agent
chatbot_score: 90
agent_score: 100
```

Mix comparison:

| Criteria | Chatbot | Agent |
|---|---|---|
| Calls/tools | 1 LLM call, no tools | LLM + tools + trace |
| Memory | No | Yes |
| Budget control | No | Yes |
| Safety review | Prompt only | Tool-backed `safety_review` |
| Human escalation | `true` | `false` for this sample |
| Missing questions | Fever, medical history, drug allergy | Drug allergy |
| Score | 90 | 100 |
| Winner | No | Yes |

Agent trace in mix mode:

```text
retrieve_patient_memory
-> budget_check
-> extract_clinical_facts
-> clinical_stage_router
-> safety_review
-> final
```

This demonstrates multi-step reasoning, tool use, memory, dynamic decision-making, and stopping logic.

## IV. Personal Insights

The most important difference between chatbot and agent is not that the agent writes a longer answer. The difference is that the agent can act, observe, revise, and provide evidence for its process.

Chatbot is better when:

- The clinical note is simple.
- The goal is only to convert text into a SOAP format.
- Speed and cost matter more than traceability.

Agent is better when:

- The case has missing data.
- The case has possible safety issues.
- The system needs to remember previous doctor messages.
- The output needs a trace for debugging or grading.
- The system must know when not to finalize automatically.

For clinical documentation, the agent should not replace the doctor. Its best role is to prepare a safer draft, highlight uncertainties, and keep the doctor/expert in the loop.

## V. Future Improvements

- Add RAG over hospital documentation policies and clinical guidelines.
- Add an analytics dashboard for cost, token usage, latency, and failure rate.
- Run ablation experiments:
  - agent without memory vs with memory
  - agent without guardrail vs with guardrail
  - chatbot prompt v1 vs chatbot prompt v2
- Add stronger unsupported-claim detection.
- Add final-note export after doctor approval.
