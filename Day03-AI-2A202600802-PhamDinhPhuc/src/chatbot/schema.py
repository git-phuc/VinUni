from __future__ import annotations

from typing import Any


ALLOWED_WARNING_TYPES = {
    "missing_question",
    "red_flag",
    "medication_risk",
    "uncertainty",
    "contradiction",
    "unsupported",
}

ALLOWED_SEVERITIES = {"minor", "major", "safety-critical"}

CHATBOT_JSON_SCHEMA_TEXT = """
{
  "mode": "chatbot_baseline",
  "soap": {
    "subjective": "Dữ kiện bệnh nhân kể, chỉ lấy từ raw note.",
    "objective": "Sinh hiệu, khám, xét nghiệm nếu raw note có; nếu không có thì để trống.",
    "assessment": "Nhận định của bác sĩ nếu raw note có; nếu không có ghi rõ cần bác sĩ xác nhận.",
    "plan": "Kế hoạch đã có trong raw note; không tự kê đơn hoặc tự thêm chỉ định."
  },
  "warnings": [
    {
      "severity": "minor | major | safety-critical",
      "type": "missing_question | red_flag | medication_risk | uncertainty | contradiction | unsupported",
      "message": "Cảnh báo ngắn, dựa trên raw note."
    }
  ],
  "missing_questions": ["Câu hỏi cần hỏi thêm, nếu có."],
  "uncertainty": ["Điểm chưa chắc chắn, nếu có."],
  "doctor_review_required": true,
  "human_escalation_required": true,
  "final_answer": "Tóm tắt ngắn cho bác sĩ, không thay quyết định lâm sàng."
}
""".strip()


def clean_string(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"n/a", "na", "none", "null"} else text


def clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [clean_string(item) for item in value]
    return [item for item in cleaned if item]


def clean_warnings(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    warnings: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        severity = clean_string(item.get("severity")).lower() or "major"
        warning_type = clean_string(item.get("type")).lower() or "uncertainty"
        message = clean_string(item.get("message"))
        if severity not in ALLOWED_SEVERITIES:
            severity = "major"
        if warning_type not in ALLOWED_WARNING_TYPES:
            warning_type = "uncertainty"
        if message:
            warnings.append({"severity": severity, "type": warning_type, "message": message})
    return warnings


def enforce_chatbot_contract(output: dict[str, Any]) -> dict[str, Any]:
    soap = output.get("soap") if isinstance(output.get("soap"), dict) else {}
    warnings = clean_warnings(output.get("warnings"))
    missing_questions = clean_string_list(output.get("missing_questions"))
    uncertainty = clean_string_list(output.get("uncertainty"))
    has_safety_critical = any(item["severity"] == "safety-critical" for item in warnings)

    return {
        "mode": "chatbot_baseline",
        "soap": {
            "subjective": clean_string(soap.get("subjective")),
            "objective": clean_string(soap.get("objective")),
            "assessment": clean_string(soap.get("assessment"))
            or "Chưa có chẩn đoán trong input; cần bác sĩ xác nhận.",
            "plan": clean_string(soap.get("plan")),
        },
        "warnings": warnings,
        "missing_questions": missing_questions,
        "uncertainty": uncertainty,
        "doctor_review_required": True,
        "human_escalation_required": bool(output.get("human_escalation_required") or has_safety_critical),
        "final_answer": clean_string(output.get("final_answer")) or "SOAP draft cần bác sĩ duyệt trước khi sử dụng.",
    }
