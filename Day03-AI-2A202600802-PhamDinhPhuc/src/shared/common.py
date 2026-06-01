from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
PUBLIC_DIR = ROOT_DIR / "public"
DATA_DIR = ROOT_DIR / "data"


class LabError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def load_env(path: Path = ROOT_DIR / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_config() -> dict[str, Any]:
    load_env()
    return {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "port": int(os.environ.get("PORT", "8783")),
    }


def load_test_cases() -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / "test_cases.json").read_text(encoding="utf-8"))


def call_openai_chat(messages: list[dict[str, str]], label: str, expect_json: bool = False) -> str:
    config = get_config()
    api_key = config["api_key"]
    if not api_key or api_key == "your_key_here":
        raise LabError(
            400,
            "Missing OPENAI_API_KEY. Copy VinUni/Day03/.env.example to VinUni/Day03/.env and set a real key.",
        )

    payload = {
        "model": config["model"],
        "temperature": 0.1,
        "messages": messages,
    }
    if expect_json:
        payload["response_format"] = {"type": "json_object"}
    request = urllib.request.Request(
        f"{config['base_url']}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        raise LabError(exc.code, f"{label} LLM call failed: {error_text[:700]}") from exc
    except urllib.error.URLError as exc:
        raise LabError(502, f"{label} LLM network error: {exc}") from exc

    provider_payload = json.loads(response_text)
    content = provider_payload.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise LabError(502, f"{label} LLM response did not include message content")
    return str(content)


def extract_json_object(text: str) -> dict[str, Any]:
    text = str(text).strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    candidate = fenced.group(1).strip() if fenced else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            return json.loads(candidate[start : end + 1])
        raise


def normalize_output(output: dict[str, Any] | None, mode: str) -> dict[str, Any]:
    output = output if isinstance(output, dict) else {}
    soap = output.get("soap") if isinstance(output.get("soap"), dict) else {}
    return {
        "mode": mode,
        "soap": {
            "subjective": str(soap.get("subjective", "")),
            "objective": str(soap.get("objective", "")),
            "assessment": str(soap.get("assessment", "")),
            "plan": str(soap.get("plan", "")),
        },
        "warnings": output.get("warnings") if isinstance(output.get("warnings"), list) else [],
        "missing_questions": output.get("missing_questions") if isinstance(output.get("missing_questions"), list) else [],
        "uncertainty": output.get("uncertainty") if isinstance(output.get("uncertainty"), list) else [],
        "doctor_review_required": output.get("doctor_review_required") is not False,
        "human_escalation_required": bool(output.get("human_escalation_required", False)),
        "final_answer": str(output.get("final_answer", "")),
    }


def compact_case_meta(test_case: dict[str, Any] | None) -> dict[str, Any]:
    test_case = test_case or {}
    return {
        "id": test_case.get("id", "custom_case"),
        "title": test_case.get("title", "Custom case"),
        "purpose": test_case.get("purpose", ""),
        "expected_winner": test_case.get("expected_winner", "unknown"),
        "expected_reason": test_case.get("expected_reason", ""),
        "simulate_tool_failure": bool(test_case.get("simulate_tool_failure", False)),
    }


def get_case(case_id: str | None) -> dict[str, Any] | None:
    if not case_id:
        return None
    return next((item for item in load_test_cases() if item["id"] == case_id), None)


def resolve_request_case(body: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    selected = get_case(body.get("case_id"))
    if body.get("case_id") and selected is None:
        raise LabError(404, f"Unknown case_id: {body['case_id']}")

    raw_note = body.get("raw_note") or (selected or {}).get("raw_note")
    if not raw_note or not str(raw_note).strip():
        raise LabError(400, "raw_note or case_id is required")

    case_meta = compact_case_meta(selected)
    case_meta.update(body.get("case_meta") or {})
    test_case = selected or {
        "id": case_meta.get("id", "custom_case"),
        "title": case_meta.get("title", "Custom case"),
        "raw_note": raw_note,
        "gold_facts": case_meta.get("gold_facts", []),
        "expected_missing_question_keywords": case_meta.get("expected_missing_question_keywords", []),
        "expected_safety_keywords": case_meta.get("expected_safety_keywords", []),
        "expected_human_escalation": bool(case_meta.get("expected_human_escalation", False)),
        "expected_winner": case_meta.get("expected_winner", "unknown"),
    }
    return str(raw_note).strip(), case_meta, test_case
