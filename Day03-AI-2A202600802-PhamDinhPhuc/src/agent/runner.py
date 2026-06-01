from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider
from src.shared.common import load_test_cases, get_config

# Set maximum iterations/steps for production-ish staged ReAct Agent.
MAX_ITERATIONS = 6

def run_react_agent(raw_note: str, case_meta: dict[str, Any]) -> dict[str, Any]:
    """
    Runner wrapper that instantiates the OO LLM Provider and ReAct Agent, 
    and executes the reasoning loop. Maintains full backward-compatible return schema.
    """
    config = get_config()
    
    # 1. Select and configure LLM Provider
    provider_name = os.environ.get("DEFAULT_PROVIDER", "openai").lower()
    
    if provider_name == "gemini":
        from src.core.gemini_provider import GeminiProvider

        api_key = os.environ.get("GEMINI_API_KEY", config.get("api_key"))
        provider = GeminiProvider(
            model_name=os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
            api_key=api_key
        )
    elif provider_name == "local":
        from src.core.local_provider import LocalProvider

        model_path = os.environ.get("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        provider = LocalProvider(model_path=model_path)
    else:
        # Default to OpenAIProvider
        provider = OpenAIProvider(
            model_name=config.get("model", "gpt-4o-mini"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url")
        )
        
    # 2. Define tools description for system prompt injection
    tools = [
        {
            "name": "extract_clinical_facts",
            "description": "extract_clinical_facts(raw_note): Trích xuất thông tin lâm sàng như chief_complaint, negation, medication, allergy, vital, exam, và plan từ raw_note."
        },
        {
            "name": "safety_review",
            "description": "safety_review(raw_note, facts): Đánh giá an toàn lâm sàng dựa trên raw_note và facts đã trích xuất để tìm missing_questions, red_flags, contradictions, và xác định xem có cần human_escalation_required không."
        },
        {
            "name": "retrieve_patient_memory",
            "description": "retrieve_patient_memory(memory_context): Đọc memory của session hiện tại gồm các lượt chat, run cũ và final note đã lưu để agent hiểu bối cảnh dài hạn."
        },
        {
            "name": "budget_check",
            "description": "budget_check(raw_note, memory, budget): Kiểm tra cost/iteration budget và độ phức tạp trước khi quyết định gọi thêm LLM/tool."
        },
        {
            "name": "clinical_stage_router",
            "description": "clinical_stage_router(raw_note, facts, memory): Quyết định động stage tiếp theo, safety có bắt buộc không, và có cần long-horizon reconciliation không."
        },
        {
            "name": "guardrail_review",
            "description": "guardrail_review(raw_note, facts, safety, candidate_output): Kiểm tra final draft trước khi trả lời, chặn unsupported claim, tự chẩn đoán/kê đơn và thiếu doctor review."
        }
    ]
    
    # 3. Instantiate ReAct Agent and execute
    agent = ReActAgent(llm=provider, tools=tools, max_steps=MAX_ITERATIONS)
    return agent.run(raw_note, case_meta)


def load_test_case(case_id: str) -> dict[str, Any]:
    for item in load_test_cases():
        if item["id"] == case_id:
            return item
    raise ValueError(f"Unknown case_id: {case_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Day03 ReAct agent with a real LLM.")
    parser.add_argument("--case", default="TC3_chest_pain_missing", help="Case id from data/test_cases.json")
    parser.add_argument("--raw-note", default="", help="Custom raw clinical note")
    args = parser.parse_args()

    if args.raw_note:
        raw_note = args.raw_note
        case_meta = {"id": "custom_case", "title": "Custom case", "simulate_tool_failure": False}
    else:
        test_case = load_test_case(args.case)
        raw_note = test_case["raw_note"]
        case_meta = {
            "id": test_case["id"],
            "title": test_case["title"],
            "purpose": test_case["purpose"],
            "expected_winner": test_case["expected_winner"],
            "simulate_tool_failure": bool(test_case.get("simulate_tool_failure", False)),
        }

    output = run_react_agent(raw_note, case_meta)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
