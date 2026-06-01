# Evaluation Metrics for Lab 3: Agentic reasoning

In this lab, we don't just ask "Does it work?". We ask **"How well does it perform?"**.

## Key Industry Metrics

### 1. Token Efficiency (Token count)
- **Prompt vs. Completion**: Are your system prompts too verbose? Is the agent generating unnecessary "chatter" before the tool call?
- **Cost Analysis**: Lower token count = Lower cost = Higher ROI.

### 2. Latency (Response time)
- **Time-to-First-Token (TTFT)**: How quickly does the LLM start responding?
- **Total Duration**: For a ReAct agent, this includes all loops + tool execution times.
- **Goal**: In "production", users expect responses within 200ms-2s.

### 3. Loop count (Steps)
- **Multi-step Reasoning**: How many `Thought->Action` cycles did the agent need to solve the task?
- **Termination Quality**: Does it correctly terminate using enough evidence, or does it loop endlessly?

### 4. Failure Analysis (Error codes)
- **JSON Parser Error**: The LLM returned a malformed step.
- **Invalid Action**: The agent selected a tool that is not allowed.
- **Tool Failure**: A local tool failed or timed out.
- **Max Iterations**: The agent reached `MAX_ITERATIONS` without a final answer.

## How to use the Logs

Metrics are captured in `VinUni/Day03/logs/` by `src/telemetry/logger.py`. Use these JSON logs to compare:

- Chatbot latency vs Agent latency.
- Agent loop count for each test case.
- Failure events such as parser error, invalid action, tool fail, and max iteration.
- Token usage and rough API cost for OpenAI calls.

This repo uses `DEFAULT_PROVIDER=openai`, so no local model download is required.
