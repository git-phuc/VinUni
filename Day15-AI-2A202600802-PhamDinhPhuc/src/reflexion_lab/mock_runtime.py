from __future__ import annotations
import os
import time
import json
from dotenv import load_dotenv
from openai import OpenAI
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .utils import normalize_answer
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM

# Load dotenv to find api key
load_dotenv()
key = os.getenv("OPENAI_API_KEY")
if not key or key == "your_api_key_here":
    from pathlib import Path
    day14_env = Path(__file__).resolve().parents[3] / "Day14-AI-2A202600802-PhamDinhPhuc" / ".env"
    if day14_env.exists():
        load_dotenv(day14_env, override=True)

# Global variables
RUN_MODE = "mock"  # Can be "mock" or "llm"
_last_run_tokens = 0
_last_run_latency = 0
client = None

FIRST_ATTEMPT_WRONG = {"hp2": "London", "hp4": "Atlantic Ocean", "hp6": "Red Sea", "hp8": "Andes"}
FAILURE_MODE_BY_QID = {"hp2": "incomplete_multi_hop", "hp4": "wrong_final_answer", "hp6": "entity_drift", "hp8": "entity_drift"}

def reset_last_run_metadata():
    global _last_run_tokens, _last_run_latency
    _last_run_tokens = 0
    _last_run_latency = 0

def get_last_run_metadata():
    global _last_run_tokens, _last_run_latency
    return {
        "tokens": _last_run_tokens,
        "latency_ms": _last_run_latency
    }

def add_metadata(tokens: int, latency_ms: int):
    global _last_run_tokens, _last_run_latency
    _last_run_tokens += tokens
    _last_run_latency += latency_ms

def get_openai_client():
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
    return client

def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> tuple[str, int, int]:
    openai_client = get_openai_client()
    kwargs = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
        
    start_time = time.time()
    response = openai_client.chat.completions.create(**kwargs)
    latency_ms = int((time.time() - start_time) * 1000)
    
    content = response.choices[0].message.content
    tokens = response.usage.total_tokens
    return content, tokens, latency_ms

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> str:
    if RUN_MODE == "mock":
        if example.qid not in FIRST_ATTEMPT_WRONG:
            return example.gold_answer
        if agent_type == "react":
            return FIRST_ATTEMPT_WRONG[example.qid]
        if attempt_id == 1 and not reflection_memory:
            return FIRST_ATTEMPT_WRONG[example.qid]
        return example.gold_answer

    # Real LLM call
    context_str = "\n\n".join([f"Title: {c.title}\nText: {c.text}" for c in example.context])
    reflections_str = "\n".join([f"- {r}" for r in reflection_memory]) if reflection_memory else "None"
    user_prompt = f"Question: {example.question}\n\nContext:\n{context_str}\n\nReflection memory of previous attempts:\n{reflections_str}\n\nConcise Answer:"
    
    content, tokens, latency_ms = call_llm(ACTOR_SYSTEM, user_prompt, json_mode=False)
    add_metadata(tokens, latency_ms)
    return content.strip()

def evaluator(example: QAExample, answer: str) -> JudgeResult:
    if RUN_MODE == "mock":
        if normalize_answer(example.gold_answer) == normalize_answer(answer):
            return JudgeResult(score=1, reason="Final answer matches the gold answer after normalization.")
        if normalize_answer(answer) == "london":
            return JudgeResult(score=0, reason="The answer stopped at the birthplace city and never completed the second hop to the river.", missing_evidence=["Need to identify the river that flows through London."], spurious_claims=[])
        return JudgeResult(score=0, reason="The final answer selected the wrong second-hop entity.", missing_evidence=["Need to ground the answer in the second paragraph."], spurious_claims=[answer])

    # Real LLM call
    user_prompt = f"Question: {example.question}\nGold Answer: {example.gold_answer}\nPredicted Answer: {answer}"
    content, tokens, latency_ms = call_llm(EVALUATOR_SYSTEM, user_prompt, json_mode=True)
    add_metadata(tokens, latency_ms)
    
    try:
        data = json.loads(content)
        score = int(data.get("score", 0))
        reason = str(data.get("reason", ""))
        missing = list(data.get("missing_evidence", []))
        spurious = list(data.get("spurious_claims", []))
        return JudgeResult(score=score, reason=reason, missing_evidence=missing, spurious_claims=spurious)
    except Exception as e:
        if normalize_answer(example.gold_answer) == normalize_answer(answer):
            return JudgeResult(score=1, reason="Fallback: Normalization match after parse error.")
        return JudgeResult(score=0, reason=f"Fallback failure. Error parsing evaluator JSON: {e}")

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> ReflectionEntry:
    if RUN_MODE == "mock":
        strategy = "Do the second hop explicitly: birthplace city -> river through that city." if example.qid == "hp2" else "Verify the final entity against the second paragraph before answering."
        return ReflectionEntry(attempt_id=attempt_id, failure_reason=judge.reason, lesson="A partial first-hop answer is not enough; the final answer must complete all hops.", next_strategy=strategy)

    # Real LLM call
    user_prompt = f"Question: {example.question}\nAttempt ID: {attempt_id}\nEvaluator Feedback: {judge.reason}\nMissing Evidence: {judge.missing_evidence}\nSpurious Claims: {judge.spurious_claims}"
    content, tokens, latency_ms = call_llm(REFLECTOR_SYSTEM, user_prompt, json_mode=True)
    add_metadata(tokens, latency_ms)
    
    try:
        data = json.loads(content)
        return ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=data.get("failure_reason", judge.reason),
            lesson=data.get("lesson", "Be more careful with multi-hop connections."),
            next_strategy=data.get("next_strategy", "Verify each entity name in the paragraphs.")
        )
    except Exception as e:
        return ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=judge.reason,
            lesson="Fallback reflection due to parsing error.",
            next_strategy="Carefully check each hop step-by-step."
        )
