from __future__ import annotations

import re
from typing import Any


def split_segments(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.;\n]+", text) if part.strip()]


def push_fact(
    facts: list[dict[str, Any]],
    category: str,
    fact: str,
    source_span: str | None = None,
    risk_level: str = "major",
) -> None:
    if not fact or any(item["fact"].lower() == fact.lower() for item in facts):
        return
    facts.append(
        {
            "fact_id": f"F{len(facts) + 1:03d}",
            "fact": fact,
            "category": category,
            "source_span": source_span or fact,
            "risk_level": risk_level,
        }
    )


def extract_clinical_facts(raw_note: str) -> dict[str, Any]:
    if not raw_note.strip():
        raise ValueError("raw_note is empty")

    facts: list[dict[str, Any]] = []
    segments = split_segments(raw_note)
    lower = raw_note.lower()

    if segments:
        push_fact(facts, "chief_complaint", segments[0], segments[0], "major")

    for match in re.findall(r"(?:không|chưa ghi nhận|phủ nhận|chưa hỏi|chưa rõ|chưa có|chưa đo)\s+[^.,;\n]+", raw_note, flags=re.I):
        risk = (
            "safety-critical"
            if re.search(r"đau ngực|khó thở|tê yếu|bí tiểu|sốt|dị ứng|thuốc|inr|tim mạch|đau lan", match, flags=re.I)
            else "major"
        )
        push_fact(facts, "uncertainty", match.strip(), match.strip(), risk)

    for match in re.findall(r"(?:đang dùng|uống|dùng|warfarin|aspirin|insulin)\s*[^.,;\n]*", raw_note, flags=re.I):
        push_fact(facts, "medication", match.strip(), match.strip(), "safety-critical")

    for match in re.findall(r"(?:dị ứng|nổi ban|nổi mẩn)\s*[^.,;\n]*", raw_note, flags=re.I):
        push_fact(facts, "allergy", match.strip(), match.strip(), "safety-critical")

    for match in re.findall(r"(?:HA\s*\d+\/\d+|SpO2\s*\d+%?|mạch\s*\d+|sốt\s*\d+(?:[.,]\d+)?|INR\s*[^.,;\n]*)", raw_note, flags=re.I):
        push_fact(facts, "vital", match.strip(), match.strip(), "major")

    for segment in segments:
        if re.search(r"khám|phổi|họng|cột sống|ran|bầm tím", segment, flags=re.I):
            push_fact(facts, "physical_exam", segment, segment, "major")
        if re.search(r"dặn|hẹn|cần|kiểm tra|tái khám|chườm|theo dõi", segment, flags=re.I):
            push_fact(facts, "plan", segment, segment, "major")

    if "đau ngực" in lower:
        push_fact(facts, "red_flag", "Đau ngực cần đánh giá dấu hiệu nguy hiểm", "đau ngực", "safety-critical")
    if "khó thở" in lower:
        push_fact(facts, "red_flag", "Khó thở cần đánh giá mức độ và SpO2", "khó thở", "safety-critical")
    if "warfarin" in lower:
        push_fact(
            facts,
            "medication",
            "Warfarin là thuốc nguy cơ cao cần kiểm tra INR và nguy cơ chảy máu",
            "warfarin",
            "safety-critical",
        )

    return {"facts": facts}


def safety_review(raw_note: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    lower = raw_note.lower()
    missing: list[str] = []
    red_flags: list[str] = []
    contradictions: list[str] = []
    warnings: list[dict[str, str]] = []

    def add_missing(question: str) -> None:
        if question not in missing:
            missing.append(question)

    def add_warning(severity: str, warning_type: str, message: str) -> None:
        warnings.append({"severity": severity, "type": warning_type, "message": message})

    if "đau ngực" in lower:
        red_flags.append("Đau ngực là red flag cần đánh giá trước khi kết luận.")
        add_missing("Hỏi thời gian khởi phát đau ngực.")
        add_missing("Hỏi đau lan, vã mồ hôi, khó thở, buồn nôn.")
        add_missing("Hỏi tiền sử tim mạch và yếu tố nguy cơ.")
        add_warning("safety-critical", "red_flag", "Đau ngực thiếu dữ kiện cần bác sĩ đánh giá trước khi hoàn tất note.")

    if "warfarin" in lower:
        red_flags.append("Warfarin là thuốc nguy cơ cao khi có dấu hiệu chảy máu.")
        add_missing("Hỏi liều warfarin, lần dùng gần nhất và thuốc dùng kèm.")
        add_missing("Kiểm tra INR gần đây hoặc chỉ định kiểm tra INR.")
        add_missing("Đánh giá mức độ chảy máu và dấu hiệu mất máu.")
        add_warning("safety-critical", "medication_risk", "Warfarin kèm chảy máu/chưa có INR cần bác sĩ review.")

    if re.search(r"chưa hỏi|chưa rõ|chưa đo|chưa có|bác sĩ chưa khám xong", raw_note, flags=re.I):
        add_missing("Bổ sung các dữ kiện đang ghi là chưa hỏi/chưa rõ/chưa đo.")
        add_warning("major", "missing_question", "Input còn thiếu dữ kiện; không nên hoàn tất hồ sơ tự động.")

    if not re.search(r"dị ứng|chưa rõ dị ứng|chưa hỏi dị ứng", raw_note, flags=re.I):
        add_missing("Hỏi tình trạng dị ứng thuốc.")

    if not re.search(r"thuốc|đang dùng|uống|dùng", raw_note, flags=re.I):
        add_missing("Hỏi thuốc đang dùng.")

    if re.search(r"không dị ứng[\s\S]*dị ứng|dị ứng[\s\S]*không dị ứng", raw_note, flags=re.I):
        contradictions.append("Thông tin dị ứng có thể mâu thuẫn, cần xác nhận lại.")
        add_warning("safety-critical", "contradiction", "Thông tin dị ứng có khả năng mâu thuẫn.")

    high_risk_count = sum(1 for fact in facts if fact.get("risk_level") == "safety-critical")
    human_escalation = (
        any(warning["severity"] == "safety-critical" for warning in warnings)
        or high_risk_count >= 2
        or bool(re.search(r"bác sĩ chưa khám xong|chưa rõ đau ở đâu", raw_note, flags=re.I))
    )

    return {
        "missing_questions": missing,
        "red_flags": red_flags,
        "contradictions": contradictions,
        "human_escalation_required": human_escalation,
        "warnings": warnings,
    }


def needs_safety_review(raw_note: str, facts: list[dict[str, Any]]) -> bool:
    return bool(
        re.search(
            r"đau ngực|khó thở|warfarin|chảy máu|chưa hỏi|chưa rõ|chưa đo|chưa có|bác sĩ chưa khám xong",
            raw_note,
            flags=re.I,
        )
        or any(fact.get("risk_level") == "safety-critical" for fact in facts)
    )


def retrieve_patient_memory(memory_context: dict[str, Any] | None) -> dict[str, Any]:
    memory_context = memory_context or {}
    messages = memory_context.get("messages") or []
    runs = memory_context.get("runs") or []
    final_notes = memory_context.get("final_notes") or []

    prior_doctor_messages = [
        item.get("content", "")
        for item in messages
        if item.get("role") in {"doctor", "user"} and item.get("content")
    ][-8:]
    latest_run = runs[0] if runs else {}
    latest_final = final_notes[0].get("content", {}) if final_notes else {}

    return {
        "patient_memory_available": bool(messages or runs or final_notes),
        "prior_turn_count": len(messages),
        "prior_run_count": len(runs),
        "prior_doctor_messages": prior_doctor_messages,
        "latest_mode": latest_run.get("mode", ""),
        "latest_static_output": latest_run.get("result", {}),
        "latest_approved_or_saved_final": latest_final,
        "memory_rules": [
            "Use memory only as context, not as new clinical fact unless doctor supplied it.",
            "Prefer newer doctor messages over older static outputs.",
            "If memory conflicts with raw_note, flag contradiction and ask doctor to confirm.",
        ],
    }


def budget_check(raw_note: str, memory: dict[str, Any] | None, budget: dict[str, Any] | None) -> dict[str, Any]:
    memory = memory or {}
    budget = budget or {}
    max_iterations = int(budget.get("max_iterations", 6))
    max_tool_calls = int(budget.get("max_tool_calls", 6))
    max_llm_calls = int(budget.get("max_llm_calls", 6))
    estimated_context_chars = len(raw_note) + len(str(memory))
    complexity = "low"
    if estimated_context_chars > 4500 or re.search(r"đau ngực|warfarin|khó thở|chảy máu|mơ hồ|chưa rõ", raw_note, flags=re.I):
        complexity = "high"
    elif estimated_context_chars > 1800 or memory.get("patient_memory_available"):
        complexity = "medium"

    return {
        "max_iterations": max_iterations,
        "max_tool_calls": max_tool_calls,
        "max_llm_calls": max_llm_calls,
        "estimated_context_chars": estimated_context_chars,
        "complexity": complexity,
        "budget_policy": [
            "Prefer local tools before extra LLM calls.",
            "Stop with human escalation if safety remains unresolved.",
            "Do not spend more iterations to guess missing clinical facts.",
        ],
    }


def clinical_stage_router(raw_note: str, facts: list[dict[str, Any]], memory: dict[str, Any] | None) -> dict[str, Any]:
    memory = memory or {}
    safety_needed = needs_safety_review(raw_note, facts)
    needs_long_horizon = bool(memory.get("patient_memory_available") or len(split_segments(raw_note)) >= 4)
    uncertainty_markers = re.findall(r"chưa hỏi|chưa rõ|chưa đo|chưa có|không chắc|mơ hồ", raw_note, flags=re.I)
    recommended_stages = ["memory", "budget", "fact_extraction"]
    if safety_needed:
        recommended_stages.append("safety_review")
    if needs_long_horizon:
        recommended_stages.append("context_reconciliation")
    recommended_stages.extend(["guardrail_review", "finalization"])

    return {
        "recommended_stages": recommended_stages,
        "safety_review_required": safety_needed,
        "long_horizon_required": needs_long_horizon,
        "uncertainty_markers": uncertainty_markers,
        "dynamic_decision": {
            "can_skip_safety_review": not safety_needed,
            "must_escalate_if_unresolved": safety_needed or bool(uncertainty_markers),
            "should_use_memory": bool(memory.get("patient_memory_available")),
        },
    }


def guardrail_review(
    raw_note: str,
    facts: list[dict[str, Any]],
    safety: dict[str, Any] | None,
    candidate_output: dict[str, Any] | None,
) -> dict[str, Any]:
    safety = safety or {}
    candidate_output = candidate_output or {}
    output_text = str(candidate_output).lower()
    raw_lower = raw_note.lower()
    blocked_actions: list[str] = []
    required_edits: list[str] = []
    unsupported_claims: list[str] = []

    for pattern in ["kê đơn", "chẩn đoán xác định", "bắt đầu dùng", "ngừng thuốc", "liều"]:
        if pattern in output_text:
            blocked_actions.append(f"Output có dấu hiệu vượt ranh giới: {pattern}")

    for term in ["viêm phổi", "nhồi máu", "hen", "copd", "suy tim", "ung thư"]:
        if term in output_text and term not in raw_lower:
            unsupported_claims.append(f"Claim chưa có evidence trực tiếp trong raw note: {term}")

    if safety.get("human_escalation_required") and not candidate_output.get("human_escalation_required"):
        required_edits.append("Safety review yêu cầu escalation nhưng final chưa bật human_escalation_required.")
    if candidate_output.get("doctor_review_required") is False:
        required_edits.append("doctor_review_required phải luôn true.")

    final_allowed = not blocked_actions and not unsupported_claims and not required_edits
    return {
        "final_allowed": final_allowed,
        "blocked_actions": blocked_actions,
        "unsupported_claims": unsupported_claims,
        "required_edits": required_edits,
        "evidence_policy": "Final must be grounded in raw_note, tool observations, or doctor memory; otherwise ask a question.",
    }
