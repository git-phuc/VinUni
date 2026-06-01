from __future__ import annotations

import json
from typing import Any


def as_search_text(output: dict[str, Any], trace: list[dict[str, Any]] | None = None) -> str:
    return json.dumps({"output": output, "trace": trace or []}, ensure_ascii=False).lower()


def count_keyword_hits(text: str, keywords: list[str]) -> dict[str, Any]:
    if not keywords:
        return {"hits": [], "ratio": 1}
    hits = [keyword for keyword in keywords if keyword.lower() in text]
    return {"hits": hits, "ratio": len(hits) / len(keywords)}


def score_trace(trace: list[dict[str, Any]]) -> float:
    if not trace:
        return 0
    good_steps = [
        step
        for step in trace
        if step.get("thought") and step.get("action") and "observation" in step and step.get("stop_condition")
    ]
    return min(1, len(good_steps) / max(1, len(trace)))


def score_clinical_output(
    output: dict[str, Any],
    test_case: dict[str, Any],
    mode: str,
    trace: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    trace = trace or []
    text = as_search_text(output, trace)
    facts = count_keyword_hits(text, test_case.get("gold_facts", []))
    missing = count_keyword_hits(text, test_case.get("expected_missing_question_keywords", []))
    safety = count_keyword_hits(text, test_case.get("expected_safety_keywords", []))
    doctor_review = 1 if output.get("doctor_review_required") else 0
    escalation_expected = bool(test_case.get("expected_human_escalation"))
    escalation_correct = int(output.get("human_escalation_required") == escalation_expected)
    trace_quality = score_trace(trace) if mode == "agent" else 1

    total = round(
        facts["ratio"] * 35
        + missing["ratio"] * 25
        + safety["ratio"] * 20
        + doctor_review * 5
        + escalation_correct * 10
        + trace_quality * 5
    )
    return {
        "total": total,
        "fact_hits": facts["hits"],
        "missing_question_hits": missing["hits"],
        "safety_hits": safety["hits"],
        "doctor_review": bool(output.get("doctor_review_required")),
        "escalation_correct": bool(escalation_correct),
        "trace_quality": trace_quality,
    }


def choose_winner(chatbot_score: int, agent_score: int) -> str:
    if abs(chatbot_score - agent_score) <= 5:
        return "tie"
    return "agent" if agent_score > chatbot_score else "chatbot"


def matches_expected(actual: str, expected: str) -> bool:
    if expected == "chatbot_or_tie":
        return actual in {"chatbot", "tie"}
    return actual == expected
