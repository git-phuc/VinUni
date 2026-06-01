import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_openai_is_default_provider_in_env_example():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DEFAULT_PROVIDER=openai" in env_example
    assert "OPENAI_MODEL=gpt-4o-mini" in env_example


def test_clinical_tools_extract_safety_facts():
    from src.tools.clinical_tools import clinical_stage_router, extract_clinical_facts, safety_review

    raw_note = "BN đau ngực. Chưa hỏi đau lan. Mạch 92, HA 135/85."
    facts = extract_clinical_facts(raw_note)["facts"]
    review = safety_review(raw_note, facts)
    router = clinical_stage_router(raw_note, facts, {"patient_memory_available": True})

    assert any(fact["category"] == "red_flag" for fact in facts)
    assert review["human_escalation_required"] is True
    assert review["missing_questions"]
    assert router["safety_review_required"] is True
    assert router["long_horizon_required"] is True


def test_agent_memory_budget_guardrail_tools():
    from src.tools.clinical_tools import budget_check, guardrail_review, retrieve_patient_memory

    memory = retrieve_patient_memory(
        {
            "messages": [{"role": "doctor", "content": "Bác sĩ xác nhận SpO2 98%."}],
            "runs": [{"mode": "agent", "result": {"result": {"final_answer": "old"}}}],
            "final_notes": [],
        }
    )
    budget = budget_check("BN đau ngực chưa hỏi đau lan.", memory, {"max_iterations": 6})
    guardrail = guardrail_review(
        "BN đau ngực chưa hỏi đau lan.",
        [],
        {"human_escalation_required": True},
        {"doctor_review_required": True, "human_escalation_required": False, "soap": {"assessment": "chẩn đoán xác định nhồi máu"}},
    )

    assert memory["patient_memory_available"] is True
    assert budget["complexity"] == "high"
    assert guardrail["final_allowed"] is False


def test_scoring_agent_trace_quality():
    from src.mix.scoring import score_clinical_output

    output = {
        "doctor_review_required": True,
        "human_escalation_required": True,
        "warnings": [{"message": "Đau ngực cần review"}],
        "missing_questions": ["Hỏi đau lan"],
        "soap": {"subjective": "đau ngực", "objective": "", "assessment": "", "plan": ""},
    }
    test_case = {
        "gold_facts": ["đau ngực"],
        "expected_missing_question_keywords": ["đau lan"],
        "expected_safety_keywords": ["đau ngực"],
        "expected_human_escalation": True,
    }
    trace = [{"thought": "x", "action": "safety_review", "observation": {}, "stop_condition": "continue"}]

    score = score_clinical_output(output, test_case, "agent", trace)
    assert score["total"] >= 90


def test_sqlite_session_storage_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DAY03_DB_PATH", str(tmp_path / "day03_test.sqlite3"))

    from src.shared.db import add_message, add_run, create_session, get_session

    session = create_session("Pytest session", "BN ho 3 ngày.")
    add_message(session["id"], "doctor", "Cần bản SOAP ngắn.")
    add_run(
        session["id"],
        "chatbot",
        "BN ho 3 ngày.",
        {"result": {"final_answer": "Draft SOAP"}},
        [],
        {"total": 80},
    )

    stored = get_session(session["id"])
    assert stored is not None
    assert stored["messages"][0]["role"] == "doctor"
    assert stored["runs"][0]["mode"] == "chatbot"
    assert stored["runs"][0]["score"]["total"] == 80
