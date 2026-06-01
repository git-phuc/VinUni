from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chatbot.prompt import CHATBOT_SYSTEM_PROMPT
from chatbot.schema import CHATBOT_JSON_SCHEMA_TEXT, enforce_chatbot_contract
from shared.common import call_openai_chat, extract_json_object, load_test_cases, normalize_output


def build_chatbot_messages(raw_note: str, case_meta: dict[str, Any] | None = None) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "instruction": "Run chatbot baseline. Return one strict JSON object only.",
                    "baseline_constraints": [
                        "one LLM call",
                        "no tools",
                        "no ReAct trace",
                        "do not infer facts outside raw_note",
                    ],
                    "case_meta": case_meta or {},
                    "output_contract": CHATBOT_JSON_SCHEMA_TEXT,
                    "raw_note": raw_note,
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]


def run_chatbot_baseline(raw_note: str, case_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_llm_response = call_openai_chat(build_chatbot_messages(raw_note, case_meta), "chatbot", expect_json=True)
    parsed = extract_json_object(raw_llm_response)
    normalized = normalize_output(parsed, "chatbot_baseline")
    return {
        "result": enforce_chatbot_contract(normalized),
        "raw_llm_response": raw_llm_response,
    }


def load_test_case(case_id: str) -> dict[str, Any]:
    for item in load_test_cases():
        if item["id"] == case_id:
            return item
    raise ValueError(f"Unknown case_id: {case_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Day03 chatbot baseline with a real LLM.")
    parser.add_argument("--case", default="TC1_simple_cough", help="Case id from data/test_cases.json")
    parser.add_argument("--raw-note", default="", help="Custom raw clinical note")
    args = parser.parse_args()

    if args.raw_note:
        raw_note = args.raw_note
        case_meta = {"id": "custom_case", "title": "Custom case"}
    else:
        test_case = load_test_case(args.case)
        raw_note = test_case["raw_note"]
        case_meta = {
            "id": test_case["id"],
            "title": test_case["title"],
            "purpose": test_case["purpose"],
            "expected_winner": test_case["expected_winner"],
        }

    output = run_chatbot_baseline(raw_note, case_meta)
    print(json.dumps(output["result"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
