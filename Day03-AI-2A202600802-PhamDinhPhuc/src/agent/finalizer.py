from __future__ import annotations

import json
from typing import Any

from shared.common import call_openai_chat, extract_json_object


FINALIZER_SYSTEM_PROMPT = """
Bạn là clinical documentation finalization assistant cho bác sĩ/chuyên gia.

Nhiệm vụ:
- Hỗ trợ bác sĩ chỉnh sửa raw note và output SOAP thành một bản nháp cuối rõ ràng.
- Hỏi lại những dữ kiện còn thiếu hoặc mâu thuẫn.
- Nhắc các điểm an toàn cần bác sĩ kiểm tra trước khi ký.
- Giữ vai trò documentation support, không tự chẩn đoán, không tự kê đơn, không thay thế quyết định lâm sàng.

Ranh giới an toàn:
- Nếu người dùng hỏi "bệnh gì" hoặc muốn chốt chẩn đoán, chỉ tổng hợp dữ kiện hiện có, nêu differential/uncertainty ở mức thận trọng nếu có trong dữ kiện, và yêu cầu bác sĩ xác nhận.
- Luôn đánh dấu bản cuối là draft_pending_doctor_approval trừ khi bác sĩ/chuyên gia nói rõ đã duyệt.
- Không bịa thông tin không có trong raw note, run output hoặc message của bác sĩ.

Trả về đúng 1 JSON object, không markdown.
"""


FINALIZER_CONTRACT = {
    "assistant_message": "Câu trả lời ngắn cho bác sĩ/chuyên gia trong cuộc chat.",
    "final_note_draft": {
        "subjective": "",
        "objective": "",
        "assessment": "",
        "plan": "",
    },
    "questions_for_doctor": [],
    "safety_warnings": [],
    "cannot_decide": [],
    "status": "draft_pending_doctor_approval | ready_for_doctor_review | approved_by_doctor",
    "doctor_review_required": True,
}


def build_finalizer_messages(
    raw_note: str,
    latest_run: dict[str, Any] | None,
    conversation_messages: list[dict[str, Any]],
    doctor_message: str,
) -> list[dict[str, str]]:
    compact_messages = [
        {
            "role": item.get("role", "user"),
            "content": item.get("content", ""),
            "created_at": item.get("created_at", ""),
        }
        for item in conversation_messages[-12:]
    ]
    return [
        {"role": "system", "content": FINALIZER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Continue the doctor-in-the-loop finalization chat.",
                    "raw_note": raw_note,
                    "latest_run": latest_run or {},
                    "conversation_so_far": compact_messages,
                    "new_doctor_message": doctor_message,
                    "output_contract": FINALIZER_CONTRACT,
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]


def run_finalization_chat(
    raw_note: str,
    latest_run: dict[str, Any] | None,
    conversation_messages: list[dict[str, Any]],
    doctor_message: str,
) -> dict[str, Any]:
    raw_response = call_openai_chat(
        build_finalizer_messages(raw_note, latest_run, conversation_messages, doctor_message),
        "finalizer",
        expect_json=True,
    )
    parsed = extract_json_object(raw_response)
    parsed = normalize_finalizer_output(parsed)
    return {"result": parsed, "raw_llm_response": raw_response}


def normalize_finalizer_output(parsed: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        parsed = {}
    if not isinstance(parsed.get("final_note_draft"), dict) and isinstance(parsed.get("draft"), dict):
        parsed["final_note_draft"] = parsed["draft"]
    parsed.setdefault("assistant_message", "")
    parsed.setdefault("final_note_draft", {})
    parsed.setdefault("questions_for_doctor", [])
    parsed.setdefault("safety_warnings", [])
    parsed.setdefault("cannot_decide", [])
    parsed.setdefault("status", "draft_pending_doctor_approval")
    parsed["doctor_review_required"] = parsed.get("doctor_review_required") is not False
    if not str(parsed.get("assistant_message") or "").strip():
        questions = parsed.get("questions_for_doctor") or []
        warnings = parsed.get("safety_warnings") or parsed.get("warnings") or []
        parts = ["Mình đã cập nhật bản nháp SOAP ở khung bên phải."]
        if questions:
            parts.append(f"Còn {len(questions)} điểm cần bác sĩ xác nhận.")
        if warnings:
            parts.append(f"Có {len(warnings)} cảnh báo/điểm cần kiểm tra.")
        parts.append("Bản này vẫn cần bác sĩ/chuyên gia duyệt trước khi dùng.")
        parsed["assistant_message"] = " ".join(parts)
    return parsed
