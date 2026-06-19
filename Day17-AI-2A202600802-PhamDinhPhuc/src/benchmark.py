from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Read JSON conversations from disk."""
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    """Return 0 / 0.5 / 1 depending on how many expected facts appear."""
    if not expected:
        return 1.0
    ans_lower = answer.lower()
    matched = sum(1 for exp in expected if exp.lower() in ans_lower)
    score = matched / len(expected)
    if score >= 0.99:
        return 1.0
    elif score >= 0.49:
        return 0.5
    else:
        return 0.0


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Add a lightweight quality score for offline mode."""
    if "tôi không biết" in answer.lower() or "không có thông tin" in answer.lower():
        return 0.0
    ans_lower = answer.lower()
    matched = sum(1 for exp in expected if exp.lower() in ans_lower)
    if matched == 0:
        return 0.0
    base_score = matched / len(expected)
    if len(answer) > 15 and (answer.endswith(".") or answer.endswith("!") or answer.endswith("?")):
        base_score += 0.1
    return min(1.0, base_score)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Evaluate one agent over many conversations."""
    # Reset/clear profiles folder for clean evaluation
    if hasattr(agent, "profile_store") and agent.profile_store:
        for p in agent.profile_store.root_dir.glob("*.md"):
            try:
                p.unlink()
            except Exception:
                pass

    total_agent_tokens = 0
    total_prompt_tokens = 0
    recall_scores = []
    quality_scores = []
    total_compactions = 0

    user_ids = set(c["user_id"] for c in conversations)
    
    # Measure initial size
    init_size = 0
    if hasattr(agent, "profile_store"):
        for uid in user_ids:
            init_size += agent.profile_store.file_size(uid)

    for conv in conversations:
        conv_id = conv["id"]
        user_id = conv["user_id"]

        # 1. Feed turns
        for turn in conv["turns"]:
            res = agent.reply(user_id, conv_id, turn)
            total_agent_tokens += res.get("token_usage", 0)
            total_prompt_tokens += res.get("prompt_tokens_processed", 0)

        # 2. Ask recall questions in a fresh thread
        for i, rq in enumerate(conv["recall_questions"]):
            recall_thread = f"recall-{conv_id}-{i}"
            res = agent.reply(user_id, recall_thread, rq["question"])
            total_agent_tokens += res.get("token_usage", 0)
            total_prompt_tokens += res.get("prompt_tokens_processed", 0)

            score = recall_points(res["response"], rq["expected_contains"])
            recall_scores.append(score)

            q = heuristic_quality(res["response"], rq["expected_contains"])
            quality_scores.append(q)

        # Accumulate compaction counts
        total_compactions += agent.compaction_count(conv_id)

    # Measure final size
    final_size = 0
    if hasattr(agent, "profile_store"):
        for uid in user_ids:
            final_size += agent.profile_store.file_size(uid)

    mem_growth = max(0, final_size - init_size)
    avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_quality,
        memory_growth_bytes=mem_growth,
        compactions=total_compactions
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Print a markdown table or tabulated output."""
    from tabulate import tabulate
    headers = [
        "Agent Name",
        "Agent Tokens Only",
        "Prompt Tokens Processed",
        "Cross-Session Recall",
        "Response Quality",
        "Memory Growth (Bytes)",
        "Compactions"
    ]
    table_data = []
    for r in rows:
        table_data.append([
            r.agent_name,
            r.agent_tokens_only,
            r.prompt_tokens_processed,
            f"{r.recall_score:.2%}",
            f"{r.response_quality:.2%}",
            r.memory_growth_bytes,
            r.compactions
        ])
    return tabulate(table_data, headers=headers, tablefmt="github")


def save_results(sections: list[tuple[str, list[BenchmarkRow]]], out_dir: Path) -> Path:
    """Persist the generated metrics as both markdown and JSON.

    `sections` is a list of (suite_title, rows). Returns the output directory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")

    md = [f"# Benchmark Results", f"", f"_Generated: {generated_at}_", ""]
    payload: dict[str, Any] = {"generated_at": generated_at, "suites": {}}
    for title, rows in sections:
        md += [f"## {title}", "", format_rows(rows), ""]
        payload["suites"][title] = [asdict(r) for r in rows]

    (out_dir / "benchmark_results.md").write_text("\n".join(md), encoding="utf-8")
    (out_dir / "benchmark_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_dir


def main() -> None:
    """Run both benchmark suites and save the metrics."""
    config = load_config(Path(__file__).resolve().parent.parent)

    convs = load_conversations(config.data_dir / "conversations.json")
    stress_convs = load_conversations(config.data_dir / "advanced_long_context.json")

    print("=== RUNNING STANDARD BENCHMARK ===")
    standard_rows = [
        run_agent_benchmark("Baseline Agent", BaselineAgent(config, force_offline=True), convs, config),
        run_agent_benchmark("Advanced Agent", AdvancedAgent(config, force_offline=True), convs, config),
    ]
    print(format_rows(standard_rows))
    print()

    print("=== RUNNING LONG-CONTEXT STRESS BENCHMARK ===")
    stress_rows = [
        run_agent_benchmark("Baseline Agent (Stress)", BaselineAgent(config, force_offline=True), stress_convs, config),
        run_agent_benchmark("Advanced Agent (Stress)", AdvancedAgent(config, force_offline=True), stress_convs, config),
    ]
    print(format_rows(stress_rows))

    sections = [
        ("Standard Benchmark", standard_rows),
        ("Long-Context Stress Benchmark", stress_rows),
    ]
    out_dir = save_results(sections, config.base_dir / "metrics")
    print(f"\nSaved metrics to: {out_dir / 'benchmark_results.md'} and benchmark_results.json")


if __name__ == "__main__":
    main()

