from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from .schemas import ReportPayload, RunRecord

def summarize(records: list[RunRecord]) -> dict:
    grouped: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        grouped[record.agent_type].append(record)
    summary: dict[str, dict] = {}
    for agent_type, rows in grouped.items():
        summary[agent_type] = {"count": len(rows), "em": round(mean(1.0 if r.is_correct else 0.0 for r in rows), 4), "avg_attempts": round(mean(r.attempts for r in rows), 4), "avg_token_estimate": round(mean(r.token_estimate for r in rows), 2), "avg_latency_ms": round(mean(r.latency_ms for r in rows), 2)}
    if "react" in summary and "reflexion" in summary:
        summary["delta_reflexion_minus_react"] = {"em_abs": round(summary["reflexion"]["em"] - summary["react"]["em"], 4), "attempts_abs": round(summary["reflexion"]["avg_attempts"] - summary["react"]["avg_attempts"], 4), "tokens_abs": round(summary["reflexion"]["avg_token_estimate"] - summary["react"]["avg_token_estimate"], 2), "latency_abs": round(summary["reflexion"]["avg_latency_ms"] - summary["react"]["avg_latency_ms"], 2)}
    return summary

def failure_breakdown(records: list[RunRecord]) -> dict:
    grouped: dict[str, Counter] = defaultdict(Counter)
    combined = Counter()
    for record in records:
        grouped[record.agent_type][record.failure_mode] += 1
        combined[record.failure_mode] += 1
    result = {agent: dict(counter) for agent, counter in grouped.items()}
    result["combined"] = dict(combined)
    return result

def build_report(records: list[RunRecord], dataset_name: str, mode: str = "mock") -> ReportPayload:
    examples = [{"qid": r.qid, "agent_type": r.agent_type, "gold_answer": r.gold_answer, "predicted_answer": r.predicted_answer, "is_correct": r.is_correct, "attempts": r.attempts, "failure_mode": r.failure_mode, "reflection_count": len(r.reflections), "tokens": r.token_estimate, "latency": r.latency_ms} for r in records]
    return ReportPayload(meta={"dataset": dataset_name, "mode": mode, "num_records": len(records), "agents": sorted({r.agent_type for r in records})}, summary=summarize(records), failure_modes=failure_breakdown(records), examples=examples, extensions=["structured_evaluator", "reflection_memory", "benchmark_report_json", "mock_mode_for_autograding"], discussion="Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.")

def save_report(report: ReportPayload, out_dir: str | Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    md_path = out_dir / "report.md"
    json_path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    s = report.summary
    react = s.get("react", {})
    reflexion = s.get("reflexion", {})
    delta = s.get("delta_reflexion_minus_react", {})
    ext_lines = "\n".join(f"- {item}" for item in report.extensions)
    
    total_tokens = sum(ex.get("tokens", 0) for ex in report.examples)
    total_cost = total_tokens * 0.00000025  # $0.25 per million tokens average
    
    # Build detailed examples table
    from collections import defaultdict
    grouped_examples = defaultdict(dict)
    for ex in report.examples:
        grouped_examples[ex["qid"]][ex["agent_type"]] = ex
        
    table_rows = [
        "| QID | Agent | Gold Answer | Predicted Answer | Correct? | Attempts | Tokens | Latency (ms) | Est. Cost (USD) |",
        "|---|---|---|---|---|---|---|---|---|"
    ]
    for qid, agents in sorted(grouped_examples.items()):
        react_ex = agents.get("react", {})
        reflexion_ex = agents.get("reflexion", {})
        
        if react_ex:
            corr = "✅" if react_ex.get("is_correct") else "❌"
            cost = react_ex.get("tokens", 0) * 0.00000025
            table_rows.append(f"| {qid} | ReAct | {react_ex.get('gold_answer')} | {react_ex.get('predicted_answer')} | {corr} | {react_ex.get('attempts')} | {react_ex.get('tokens')} | {react_ex.get('latency')} | ${cost:.7f} |")
            
        if reflexion_ex:
            corr = "✅" if reflexion_ex.get("is_correct") else "❌"
            cost = reflexion_ex.get("tokens", 0) * 0.00000025
            table_rows.append(f"| {qid} | Reflexion | {reflexion_ex.get('gold_answer')} | {reflexion_ex.get('predicted_answer')} | {corr} | {reflexion_ex.get('attempts')} | {reflexion_ex.get('tokens')} | {reflexion_ex.get('latency')} | ${cost:.7f} |")
            
    details_table = "\n".join(table_rows)

    md = f"""# Lab 16 Benchmark Report

## Metadata
- Dataset: {report.meta['dataset']}
- Mode: {report.meta['mode']}
- Records: {report.meta['num_records']}
- Agents: {', '.join(report.meta['agents'])}
- Total Estimated Cost: ${total_cost:.5f} USD ($0.25/1M tokens average)

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | {react.get('em', 0)} | {reflexion.get('em', 0)} | {delta.get('em_abs', 0)} |
| Avg attempts | {react.get('avg_attempts', 0)} | {reflexion.get('avg_attempts', 0)} | {delta.get('attempts_abs', 0)} |
| Avg token estimate | {react.get('avg_token_estimate', 0)} | {reflexion.get('avg_token_estimate', 0)} | {delta.get('tokens_abs', 0)} |
| Avg latency (ms) | {react.get('avg_latency_ms', 0)} | {reflexion.get('avg_latency_ms', 0)} | {delta.get('latency_abs', 0)} |

## Failure modes
```json
{json.dumps(report.failure_modes, indent=2)}
```

## Extensions implemented
{ext_lines}

## Discussion
{report.discussion}

## Detailed Run Logs
{details_table}
"""
    md_path.write_text(md, encoding="utf-8")
    return json_path, md_path
