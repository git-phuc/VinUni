# Solo/Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: [Name or Solo]
- **Team Members**: [Your name]
- **Deployment Date**: [YYYY-MM-DD]

---

## 1. Executive Summary

*Brief overview of the agent's goal and success rate compared to the baseline chatbot.*

- **Success Rate**: [e.g., 85% on 20 test cases]
- **Key Outcome**: [e.g., "Our agent solved 40% more multi-step queries than the chatbot baseline by correctly utilizing the Search tool."]

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
*Diagram or description of the Thought-Action-Observation loop.*

### 2.2 Tool Definitions (Inventory)
| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `calc_tax` | `json` | Calculate VAT based on country code. |
| `search_api` | `string` | Retrieve real-time information from Google Search. |

### 2.3 LLM Providers Used
- **Primary**: [e.g., GPT-4o]
- **Secondary (Backup)**: [Optional; not required for OpenAI-only submission]

---

## 3. Telemetry & Performance Dashboard

*Analyze the industry metrics collected during the final test run.*

- **Average Latency (P50)**: [e.g., 1200ms]
- **Max Latency (P99)**: [e.g., 4500ms]
- **Average Tokens per Task**: [e.g., 350 tokens]
- **Total Cost of Test Suite**: [e.g., $0.05]

---

## 4. Root Cause Analysis (RCA) - Failure Traces

*Deep dive into why the agent failed.*

### Case Study: [e.g., Hallucination of tool args]
- **Case ID**: [e.g., TC04]
- **Failure Cause**: [e.g., Agent invented a parameter not defined in the tool description.]
- **Mitigation Plan**: [e.g., Redefined the tool description in `prompt.py` to add negative constraints.]
