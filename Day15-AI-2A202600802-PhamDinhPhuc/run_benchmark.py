from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

@app.command()
def main(
    dataset: str = "data/hotpot_mini.json",
    out_dir: str = "outputs/sample_run",
    reflexion_attempts: int = 3,
    mode: str = "mock",
    limit: int = 50
) -> None:
    from src.reflexion_lab import mock_runtime
    mock_runtime.RUN_MODE = mode
    
    examples = load_dataset(dataset)
    if limit > 0:
        examples = examples[:limit]
        
    react = ReActAgent()
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts)
    
    print(f"Starting benchmark evaluation (mode={mode}, limit={limit})...", flush=True)
    
    react_records = []
    print(f"Running ReAct Agent on {len(examples)} examples...", flush=True)
    for idx, example in enumerate(examples):
        print(f"[{idx+1}/{len(examples)}] ReAct: {example.question[:60]}...", flush=True)
        record = react.run(example)
        react_records.append(record)
        
    reflexion_records = []
    print(f"Running Reflexion Agent on {len(examples)} examples...", flush=True)
    for idx, example in enumerate(examples):
        print(f"[{idx+1}/{len(examples)}] Reflexion: {example.question[:60]}...", flush=True)
        record = reflexion.run(example)
        reflexion_records.append(record)
    all_records = react_records + reflexion_records
    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
    report = build_report(all_records, dataset_name=Path(dataset).name, mode=mode)
    json_path, md_path = save_report(report, out_path)
    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))

if __name__ == "__main__":
    app()
