from __future__ import annotations

"""Phase C: Production Guardrails — Presidio PII + NeMo Guardrails + P95 Latency."""

import asyncio
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ADVERSARIAL_SET_PATH, GUARDRAILS_CONFIG_DIR, LATENCY_BUDGET_P95_MS, PRESIDIO_LANGUAGE


# ─── Task 9a: Presidio PII Detection ─────────────────────────────────────────

def setup_presidio():
    """Khởi tạo Presidio engine với custom Vietnamese PII recognizers. (Đã implement sẵn)

    Custom recognizers thêm vào:
        VN_CCCD  — số CCCD 12 chữ số hoặc CMND 9 chữ số
        VN_PHONE — số điện thoại Việt Nam (0[3-9]xxxxxxxx)

    Các recognizers mặc định đã có sẵn: EMAIL, PHONE_NUMBER (international), ...
    """
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine

    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[
            Pattern("CCCD 12 digits", r"\b\d{12}\b", 0.9),
            Pattern("CMND 9 digits",  r"\b\d{9}\b",  0.7),
        ],
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern("VN mobile", r"\b0[3-9]\d{8}\b", 0.9)],
    )

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    registry.add_recognizer(cccd_recognizer)
    registry.add_recognizer(phone_recognizer)

    analyzer  = AnalyzerEngine(registry=registry)
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


def pii_scan(text: str, analyzer=None, anonymizer=None) -> dict:
    """Task 9a: Quét PII trong văn bản bằng Presidio.

    Returns:
        {
          "has_pii":    bool,
          "entities":   [{"type": str, "text": str, "score": float, "start": int, "end": int}],
          "anonymized": str,   # text với PII được thay bằng <TYPE>
        }
    """
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()

    _NOISE_TYPES = {"DATE_TIME", "LOCATION", "NRP", "ORG", "IN_PAN", "US_BANK_NUMBER",
                    "US_DRIVER_LICENSE", "AU_ABN", "AU_ACN", "AU_TFN",
                    "PERSON", "PERSON_NAME"}
    _MIN_SCORE = 0.5

    raw = analyzer.analyze(text=text, language=PRESIDIO_LANGUAGE)
    results = [r for r in raw
               if r.entity_type not in _NOISE_TYPES and r.score >= _MIN_SCORE]

    if not results:
        return {"has_pii": False, "entities": [], "anonymized": text}

    anonymized = anonymizer.anonymize(text=text, analyzer_results=results).text
    entities = [
        {"type": r.entity_type, "text": text[r.start:r.end],
         "score": round(r.score, 3), "start": r.start, "end": r.end}
        for r in results
    ]
    return {"has_pii": True, "entities": entities, "anonymized": anonymized}


# ─── Task 9b + 11: NeMo Guardrails ───────────────────────────────────────────

# Jailbreak / prompt-injection patterns (mirrors rails.co)
_JAILBREAK_PATTERNS = [
    "bỏ qua tất cả hướng dẫn", "ignore your previous instructions",
    "ignore previous", "pretend you are dan", "you are now an unrestricted",
    "forget your system prompt", "system override", "đóng vai ai không có giới hạn",
    "không có giới hạn", "unrestricted ai", "dump all", "reveal all",
    "tiết lộ", "admin command", "priority 1", "ignore previous instructions",
    "<!-- ignore", "[admin", "bỏ qua tất cả policy", "system instructions",
    "tôi là ceo", "ra lệnh bạn", "đóng vai hr manager", "print all confidential",
    "list all employee", "bảng lương chi tiết", "lương tháng của nhân viên",
    "toàn bộ thông tin nhân viên",
]

_OFF_TOPIC_PATTERNS = [
    "viết một bài thơ", "bài thơ", "nấu phở", "nấu ăn", "bitcoin", "ethereum",
    "giá cổ phiếu", "recommend", "phim", "marvel", "giải phương trình",
    "vi phân", "thời tiết", "tin tức", "giải toán",
]

_PII_REQUEST_PATTERNS = [
    "cho tôi biết cccd", "số điện thoại của nhân viên", "thông tin cá nhân của",
    "email của nhân viên", "tiết lộ thông tin nhân viên",
    "cccd và số điện thoại của",
]


class _PatternRails:
    """Lightweight pattern-based guardrail (NeMo Guardrails fallback for Python 3.14)."""

    async def generate_async(self, messages: list[dict]) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        text_lower = last_user.lower()

        for pat in _JAILBREAK_PATTERNS + _PII_REQUEST_PATTERNS:
            if pat in text_lower:
                return "Xin lỗi, tôi không thể thực hiện yêu cầu này."

        for pat in _OFF_TOPIC_PATTERNS:
            if pat in text_lower:
                return "Xin lỗi, tôi chỉ có thể trả lời về chính sách nội bộ công ty."

        # LLM fallback for edge cases
        try:
            from openai import OpenAI
            from config import OPENAI_API_KEY, GEMINI_API_KEY
            if GEMINI_API_KEY:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(
                    f"Bạn là HR assistant. Câu hỏi sau có phải về chính sách HR công ty không? "
                    f"Trả lời chỉ 'YES' hoặc 'NO'.\nCâu hỏi: {last_user}"
                )
                if "NO" in resp.text.upper():
                    return "Xin lỗi, tôi chỉ có thể trả lời về chính sách nội bộ công ty."
        except Exception:
            pass

        return last_user  # allowed


def setup_nemo_rails():
    """Khởi tạo NeMo Guardrails từ guardrails/config.yml.

    Falls back to pattern-based implementation on Python 3.14 (nemoguardrails incompatible).
    """
    try:
        from nemoguardrails import RailsConfig, LLMRails
        config = RailsConfig.from_path(GUARDRAILS_CONFIG_DIR)
        rails  = LLMRails(config)
        return rails
    except Exception as e:
        print(f"NeMo Guardrails unavailable ({type(e).__name__}), using pattern-based fallback")
        return _PatternRails()


async def check_input_rail(text: str, rails=None) -> dict:
    """Task 9b: Kiểm tra input qua NeMo input rails (topic guard + jailbreak guard).

    Returns:
        {
          "allowed":        bool,
          "blocked_reason": str | None,
          "response":       str,          # NeMo's raw response
        }
    """
    if rails is None:
        rails = setup_nemo_rails()

    response = await rails.generate_async(
        messages=[{"role": "user", "content": text}]
    )
    refuse_keywords = ["xin lỗi", "không thể", "không được phép", "i cannot", "i'm sorry"]
    blocked = any(kw in response.lower() for kw in refuse_keywords)
    return {
        "allowed":        not blocked,
        "blocked_reason": "nemo_input_rail" if blocked else None,
        "response":       response,
    }


async def check_output_rail(question: str, answer: str, rails=None) -> dict:
    """Task 11: Kiểm tra LLM output qua NeMo output rails trước khi trả về user.

    NeMo output rails hoạt động trong context của cả cuộc hội thoại (input + output).
    Kiểm tra: có PII không? Nội dung có phù hợp không? Có hallucination rõ ràng không?

    Returns:
        {
          "safe":           bool,
          "flagged_reason": str | None,
          "final_answer":   str,          # answer đã qua guard (có thể bị redact)
        }
    """
    if rails is None:
        rails = setup_nemo_rails()

    response = await rails.generate_async(messages=[
        {"role": "user",      "content": question},
        {"role": "assistant", "content": answer},
    ])
    refuse_keywords = ["xin lỗi", "không thể cung cấp", "i cannot"]
    flagged = any(kw in response.lower() for kw in refuse_keywords)
    return {
        "safe":           not flagged,
        "flagged_reason": "nemo_output_rail" if flagged else None,
        "final_answer":   response if flagged else answer,
    }


# ─── Task 10: Adversarial Test Suite ─────────────────────────────────────────

def run_adversarial_suite(adversarial_set: list[dict], rails=None,
                           analyzer=None, anonymizer=None) -> list[dict]:
    """Task 10: Chạy 20 adversarial inputs qua full guard stack, so sánh với expected.

    Guard stack order:
        1. pii_scan()         → block nếu has_pii (cho category pii_injection)
        2. check_input_rail() → block nếu jailbreak / off-topic / prompt injection

    Returns:
        list of {
          "id": int, "category": str, "input": str,
          "expected": "blocked"|"allowed",
          "actual":   "blocked"|"allowed",
          "blocked_by": str | None,       # "presidio" | "nemo_input" | None
          "passed": bool,
        }
    """
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def _run_all():
        results = []
        for item in adversarial_set:
            blocked_by = None

            pii_result = pii_scan(item["input"], analyzer, anonymizer)
            if pii_result["has_pii"]:
                blocked_by = "presidio"

            if blocked_by is None:
                rail_result = await check_input_rail(item["input"], rails)
                if not rail_result["allowed"]:
                    blocked_by = "nemo_input"

            actual = "blocked" if blocked_by else "allowed"
            results.append({
                "id":         item["id"],
                "category":   item["category"],
                "input":      item["input"][:80] + "...",
                "expected":   item["expected"],
                "actual":     actual,
                "blocked_by": blocked_by,
                "passed":     actual == item["expected"],
            })
        return results

    results = asyncio.run(_run_all())
    passed = sum(1 for r in results if r["passed"])
    print(f"Adversarial suite: {passed}/{len(results)} passed")
    return results


# ─── Task 12: P95 Latency Measurement ────────────────────────────────────────

def measure_p95_latency(test_inputs: list[str], n_runs: int = 20,
                         rails=None, analyzer=None, anonymizer=None) -> dict:
    """Task 12: Đo P50/P95/P99 latency cho từng layer trong guard stack.

    Mục tiêu production: P95 total < LATENCY_BUDGET_P95_MS (500ms mặc định)

    Insight cần quan sát:
        - Presidio: local regex → rất nhanh (<10ms)
        - NeMo:     LLM API call → chậm (~200-800ms tuỳ model và network)
        → Tổng: dominated by NeMo

    Returns:
        {
          "presidio_ms":  {"p50": float, "p95": float, "p99": float},
          "nemo_ms":      {"p50": float, "p95": float, "p99": float},
          "total_ms":     {"p50": float, "p95": float, "p99": float},
          "latency_budget_ok": bool,
          "budget_ms": int,
        }
    """
    presidio_times, nemo_times, total_times = [], [], []

    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def _measure():
        for text in test_inputs[:n_runs]:
            t0 = time.perf_counter()
            pii_scan(text, analyzer, anonymizer)
            presidio_ms = (time.perf_counter() - t0) * 1000

            t1 = time.perf_counter()
            await check_input_rail(text, rails)
            nemo_ms = (time.perf_counter() - t1) * 1000

            presidio_times.append(presidio_ms)
            nemo_times.append(nemo_ms)
            total_times.append(presidio_ms + nemo_ms)

    asyncio.run(_measure())

    def percentiles(times):
        s = sorted(times)
        n = len(s)
        return {
            "p50": round(s[int(n * 0.50)], 2),
            "p95": round(s[int(n * 0.95)], 2),
            "p99": round(s[min(int(n * 0.99), n - 1)], 2),
        }

    total_p = percentiles(total_times)
    return {
        "presidio_ms": percentiles(presidio_times),
        "nemo_ms":     percentiles(nemo_times),
        "total_ms":    total_p,
        "latency_budget_ok": total_p["p95"] < LATENCY_BUDGET_P95_MS,
        "budget_ms": LATENCY_BUDGET_P95_MS,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os as _os
    _os.makedirs("reports", exist_ok=True)

    # Task 9a: PII scan demo
    test_pii = "Nhân viên Nguyễn Văn A, CCCD 034095001234, SĐT 0987654321 hỏi về nghỉ phép."
    pii_demo = pii_scan(test_pii)
    print(f"PII detected: {pii_demo['has_pii']}")
    print(f"Entities: {pii_demo['entities']}")
    print(f"Anonymized: {pii_demo['anonymized']}")

    # Shared components
    analyzer, anonymizer = setup_presidio()
    rails = setup_nemo_rails()

    # Task 10: Adversarial suite
    with open(ADVERSARIAL_SET_PATH, encoding="utf-8") as f:
        adversarial_set = json.load(f)
    print(f"\nLoaded {len(adversarial_set)} adversarial inputs")
    adv_results = run_adversarial_suite(adversarial_set, rails=rails,
                                        analyzer=analyzer, anonymizer=anonymizer)
    if adv_results:
        passed = sum(1 for r in adv_results if r["passed"])
        print(f"Adversarial suite: {passed}/{len(adv_results)} passed")

    # Task 12: P95 latency
    sample_inputs = [item["input"] for item in adversarial_set[:10]]
    latency = measure_p95_latency(sample_inputs, n_runs=10, rails=rails,
                                   analyzer=analyzer, anonymizer=anonymizer)
    print(f"\nLatency P95 — Presidio: {latency['presidio_ms']['p95']}ms | "
          f"NeMo: {latency['nemo_ms']['p95']}ms | "
          f"Total: {latency['total_ms']['p95']}ms")
    print(f"Budget OK ({latency['budget_ms']}ms): {latency['latency_budget_ok']}")

    # Save report
    report = {
        "adversarial_results": adv_results,
        "pass_rate": sum(1 for r in adv_results if r["passed"]) / len(adv_results) if adv_results else 0,
        "latency": latency,
        "pii_demo": pii_demo,
    }
    with open("reports/guard_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Phase C report saved → reports/guard_results.json")
