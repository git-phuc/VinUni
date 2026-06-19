# Benchmark Results

_Generated: 2026-06-19T11:36:58_

## Standard Benchmark

| Agent Name     |   Agent Tokens Only |   Prompt Tokens Processed | Cross-Session Recall   | Response Quality   |   Memory Growth (Bytes) |   Compactions |
|----------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| Baseline Agent |                1382 |                     13912 | 0.00%                  | 0.00%              |                       0 |             0 |
| Advanced Agent |                1756 |                     24142 | 100.00%                | 100.00%            |                     273 |             0 |

## Long-Context Stress Benchmark

| Agent Name              |   Agent Tokens Only |   Prompt Tokens Processed | Cross-Session Recall   | Response Quality   |   Memory Growth (Bytes) |   Compactions |
|-------------------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| Baseline Agent (Stress) |                 371 |                     22964 | 0.00%                  | 0.00%              |                       0 |             0 |
| Advanced Agent (Stress) |                 342 |                     12372 | 100.00%                | 100.00%            |                     185 |             4 |
