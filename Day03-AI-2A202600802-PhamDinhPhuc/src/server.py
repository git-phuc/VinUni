from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from pathlib import Path
from urllib.parse import urlparse

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.runner import MAX_ITERATIONS, run_react_agent
import agent.runner as agent_runner
from agent.finalizer import run_finalization_chat
from chatbot.runner import run_chatbot_baseline
from mix.runner import run_comparison
from mix.scoring import score_clinical_output
from shared.common import LabError, PUBLIC_DIR, get_config, load_test_cases, resolve_request_case
from shared.db import add_final_note, add_message, add_run, create_session, get_session, init_db, latest_run, list_sessions


class Day03Handler(BaseHTTPRequestHandler):
    server_version = "Day03Python/1.0"

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            config = get_config()
            if path == "/api/day03/health":
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "runtime": "python",
                        "model": config["model"],
                        "base_url": config["base_url"],
                        "has_api_key": bool(config["api_key"] and config["api_key"] != "your_key_here"),
                        "max_iterations": agent_runner.MAX_ITERATIONS,
                        "agent_kind": "hybrid_staged_memory_budget_guardrails",
                    },
                )
                return
            if path == "/api/day03/cases":
                self.send_json(200, {"cases": load_test_cases()})
                return
            if path == "/api/day03/sessions":
                self.send_json(200, {"sessions": list_sessions()})
                return
            if path.startswith("/api/day03/sessions/"):
                session_id = path.rsplit("/", 1)[-1]
                session = self.require_session(session_id)
                self.send_json(200, {"session": session})
                return
            self.serve_static()
        except Exception as exc:
            self.send_error_json(exc)

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            body = self.parse_json_body()
            if path == "/api/day03/sessions":
                self.send_json(200, {"session": create_session(body.get("title"), body.get("raw_note", ""))})
                return
            if path.startswith("/api/day03/sessions/"):
                self.handle_session_post(path, body)
                return
            raw_note, case_meta, test_case = resolve_request_case(body)
            if path == "/api/day03/chatbot":
                result = run_chatbot_baseline(raw_note, case_meta)
                result["score"] = score_clinical_output(result["result"], test_case, "chatbot")
                self.send_json(200, result)
                return
            if path == "/api/day03/agent":
                self.send_json(200, run_react_agent(raw_note, case_meta))
                return
            if path == "/api/day03/compare":
                self.send_json(200, run_comparison(raw_note, case_meta, test_case))
                return
            raise LabError(404, "Not found")
        except Exception as exc:
            self.send_error_json(exc)

    def handle_session_post(self, path: str, body: dict[str, Any]) -> None:
        parts = path.strip("/").split("/")
        if len(parts) != 5:
            raise LabError(404, "Not found")
        session_id, action = parts[3], parts[4]
        session = self.require_session(session_id)

        if action == "run":
            mode = str(body.get("mode", "chatbot")).lower()
            raw_note = str(body.get("raw_note") or session.get("raw_note") or "").strip()
            if not raw_note:
                raise LabError(400, "raw_note is required before running a session")
            case_meta = {
                "id": session_id,
                "title": session.get("title", "User session"),
                "expected_winner": "unknown",
                "simulate_tool_failure": bool(body.get("simulate_tool_failure", False)),
                "memory_context": self.build_memory_context(session),
                "budget": {
                    "max_iterations": MAX_ITERATIONS,
                    "max_tool_calls": MAX_ITERATIONS,
                    "max_llm_calls": MAX_ITERATIONS,
                },
            }
            test_case = {
                "id": session_id,
                "title": session.get("title", "User session"),
                "raw_note": raw_note,
                "gold_facts": [],
                "expected_missing_question_keywords": [],
                "expected_safety_keywords": [],
                "expected_human_escalation": False,
                "expected_winner": "unknown",
            }
            if mode == "chatbot":
                payload = run_chatbot_baseline(raw_note, case_meta)
                payload["score"] = score_clinical_output(payload["result"], test_case, "chatbot")
                trace: list[dict[str, Any]] = []
                score = payload["score"]
            elif mode == "agent":
                payload = run_react_agent(raw_note, case_meta)
                trace = payload.get("trace", [])
                score = {}
            elif mode == "mix":
                payload = run_comparison(raw_note, case_meta, test_case)
                trace = payload.get("agent", {}).get("trace", [])
                score = {
                    "chatbot": payload.get("chatbot", {}).get("score", {}),
                    "agent": payload.get("agent", {}).get("score", {}),
                    "actual_winner": payload.get("actual_winner"),
                }
            else:
                raise LabError(400, "mode must be chatbot, agent, or mix")
            run = add_run(session_id, mode, raw_note, payload, trace, score)
            add_message(session_id, "user", raw_note)
            add_message(session_id, "assistant", self.summarize_run(mode, payload))
            self.send_json(200, {"payload": payload, "run": run, "session": self.require_session(session_id)})
            return

        if action == "chat":
            message = str(body.get("message", "")).strip()
            if not message:
                raise LabError(400, "message is required")
            add_message(session_id, "doctor", message)
            refreshed = self.require_session(session_id)
            response = run_finalization_chat(
                raw_note=refreshed.get("raw_note", ""),
                latest_run=latest_run(refreshed),
                conversation_messages=refreshed.get("messages", []),
                doctor_message=message,
            )
            assistant_message = self.finalizer_message(response["result"])
            add_message(session_id, "assistant", assistant_message)
            if response["result"].get("status") == "approved_by_doctor":
                add_final_note(session_id, response["result"], body.get("approved_by", "doctor"))
            self.send_json(200, {"payload": response, "session": self.require_session(session_id)})
            return

        if action == "finalize":
            content = body.get("content")
            if not isinstance(content, dict):
                raise LabError(400, "content JSON is required")
            final_note = add_final_note(session_id, content, body.get("approved_by", "doctor"))
            self.send_json(200, {"final_note": final_note, "session": self.require_session(session_id)})
            return

        raise LabError(404, "Not found")

    def require_session(self, session_id: str) -> dict[str, Any]:
        session = get_session(session_id)
        if not session:
            raise LabError(404, f"Unknown session_id: {session_id}")
        return session

    def summarize_run(self, mode: str, payload: dict[str, Any]) -> str:
        if mode == "mix":
            return f"Mix complete. Winner: {payload.get('actual_winner', 'unknown')}."
        result = payload.get("result", {})
        questions = result.get("missing_questions") or []
        escalation = "cần escalation" if result.get("human_escalation_required") else "không escalation"
        return f"{mode.title()} complete: {len(questions)} missing question(s), {escalation}."

    def finalizer_message(self, result: dict[str, Any]) -> str:
        message = str(result.get("assistant_message") or "").strip()
        if message:
            return message
        questions = result.get("questions_for_doctor") or []
        warnings = result.get("safety_warnings") or result.get("warnings") or []
        parts = ["Mình đã cập nhật bản nháp SOAP ở khung bên phải."]
        if questions:
            parts.append(f"Còn {len(questions)} điểm cần bác sĩ xác nhận.")
        if warnings:
            parts.append(f"Có {len(warnings)} cảnh báo/điểm cần kiểm tra.")
        parts.append("Bản này vẫn cần bác sĩ/chuyên gia duyệt trước khi dùng.")
        return " ".join(parts)

    def build_memory_context(self, session: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": session.get("id"),
            "title": session.get("title"),
            "messages": (session.get("messages") or [])[-16:],
            "runs": (session.get("runs") or [])[:5],
            "final_notes": (session.get("final_notes") or [])[:3],
        }

    def parse_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise LabError(400, "Request body must be valid JSON") from exc

    def serve_static(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path == "/":
            request_path = "/index.html"
        file_path = (PUBLIC_DIR / request_path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR.resolve())):
            raise LabError(403, "Forbidden")
        if not file_path.exists() or not file_path.is_file():
            raise LabError(404, "Not found")
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, exc: Exception) -> None:
        status = getattr(exc, "status", 500) if isinstance(getattr(exc, "status", 500), int) else 500
        self.send_json(status, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    config = get_config()
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", config["port"]), Day03Handler)
    print(f"Day03 Python Lab running at http://localhost:{config['port']}")
    print(f"Model: {config['model']}")
    print(f"API key configured: {bool(config['api_key'] and config['api_key'] != 'your_key_here')}")
    server.serve_forever()


if __name__ == "__main__":
    main()
