from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.runner import run_react_agent
from chatbot.runner import run_chatbot_baseline
from mix.scoring import choose_winner, matches_expected, score_clinical_output
from shared.common import load_test_cases


def run_comparison(raw_note: str, case_meta: dict[str, Any], test_case: dict[str, Any]) -> dict[str, Any]:
    chatbot = run_chatbot_baseline(raw_note, case_meta)
    agent = run_react_agent(raw_note, case_meta)
    chatbot_score = score_clinical_output(chatbot["result"], test_case, "chatbot")
    agent_score = score_clinical_output(agent["result"], test_case, "agent", agent.get("trace", []))
    actual_winner = choose_winner(chatbot_score["total"], agent_score["total"])
    return {
        "case_id": test_case.get("id", case_meta.get("id")),
        "expected_winner": test_case.get("expected_winner", case_meta.get("expected_winner")),
        "expected_reason": test_case.get("expected_reason", case_meta.get("expected_reason")),
        "actual_winner": actual_winner,
        "actual_matches_expected": matches_expected(
            actual_winner,
            test_case.get("expected_winner", case_meta.get("expected_winner")),
        ),
        "chatbot": {**chatbot, "score": chatbot_score},
        "agent": {**agent, "score": agent_score},
    }


def load_test_case(case_id: str) -> dict[str, Any]:
    for item in load_test_cases():
        if item["id"] == case_id:
            return item
    raise ValueError(f"Unknown case_id: {case_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Day03 mixed comparison: chatbot vs ReAct agent.")
    parser.add_argument("--case", default="TC3_chest_pain_missing", help="Case id from data/test_cases.json")
    args = parser.parse_args()

    test_case = load_test_case(args.case)
    case_meta = {
        "id": test_case["id"],
        "title": test_case["title"],
        "purpose": test_case["purpose"],
        "expected_winner": test_case["expected_winner"],
        "simulate_tool_failure": bool(test_case.get("simulate_tool_failure", False)),
    }
    output = run_comparison(test_case["raw_note"], case_meta, test_case)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
