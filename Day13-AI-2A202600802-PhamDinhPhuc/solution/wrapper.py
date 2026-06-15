"""YOUR mitigation + observability layer. The simulator calls mitigate() around the
opaque agent (a REAL LLM) for every request. This is the ONLY place observability can
live -- the agent is silent. Legal moves: retry / cache / route / guardrail / sanitize
/ fallback / session-reset / PROMPT ROUTING, plus your own logging/tracing/metrics.
Illegal: hardcoding answers, importing the agent internals, reading instructor files,
network exfiltration.

  call_next(question, config) -> result   # the only way to reach the black box
  context = {"session_id","turn_index","qid","cache": <shared dict>, "cache_lock": <Lock>}
  result  = {"answer","status","steps","trace","meta":{latency_ms,usage,...}}

PROMPT ROUTING: you can override the agent's system prompt PER REQUEST by setting it in
the config you pass to call_next, e.g.:
    conf = dict(config); conf["system_prompt"] = my_better_prompt
    result = call_next(question, conf)
(Or just edit solution/prompt.txt for a single static prompt used on every request.)
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time

try:
    from telemetry.cost import cost_from_usage
    from telemetry.logger import logger, new_correlation_id, set_correlation_id
    from telemetry.redact import redact
except Exception:
    logger = None

    def cost_from_usage(model, usage):
        return 0.0

    def new_correlation_id():
        return "req-local"

    def set_correlation_id(cid):
        return None

    def redact(text):
        return text, 0


_NOTE_PATTERN = re.compile(
    r"(?is)\b(?:ghi\s*chu|note|order\s+note|customer\s+note)\s*:\s*.*$"
)
_SUSPICIOUS_NOTE = re.compile(
    r"(?is)\b(ignore|disregard|override|system|developer|instruction|follow|obey|price|gia|tool|discount)\b"
)
_RETRY_STATUSES = {"loop", "max_steps", "no_action", "wrapper_error"}


def _enabled(config, key, default=False):
    value = (config or {}).get(key, default)
    if isinstance(value, dict):
        return bool(value.get("enabled", default))
    return bool(value)


def _sanitize_question(question):
    if not isinstance(question, str):
        return question

    def replace_note(match):
        note = match.group(0)
        if _SUSPICIOUS_NOTE.search(note):
            return "[order note removed]"
        return note

    return _NOTE_PATTERN.sub(replace_note, question)


def _cache_key(question, config):
    relevant_config = {
        "provider": config.get("provider"),
        "model": config.get("model"),
        "temperature": config.get("temperature"),
        "tool_budget": config.get("tool_budget"),
        "system_prompt": config.get("system_prompt"),
    }
    raw = json.dumps(
        {"question": " ".join(str(question).lower().split()), "config": relevant_config},
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _result_has_tool_error(result):
    trace = result.get("trace", []) if isinstance(result, dict) else []
    try:
        trace_text = json.dumps(trace, ensure_ascii=True, sort_keys=True).lower()
    except TypeError:
        trace_text = str(trace).lower()
    return '"error"' in trace_text or "tool_error" in trace_text


def _log_call(event, context, result, wall_ms, attempt, sanitized):
    if logger is None:
        return
    meta = result.get("meta", {}) if isinstance(result, dict) else {}
    usage = meta.get("usage", {}) or {}
    trace = result.get("trace", []) if isinstance(result, dict) else []
    try:
        logger.log_event(
            event,
            {
                "qid": context.get("qid"),
                "session_id": context.get("session_id"),
                "turn_index": context.get("turn_index"),
                "attempt": attempt,
                "sanitized_question": sanitized,
                "status": result.get("status") if isinstance(result, dict) else "wrapper_error",
                "reported_latency_ms": meta.get("latency_ms"),
                "wall_ms": wall_ms,
                "usage": usage,
                "cost_usd": cost_from_usage(meta.get("model", ""), usage),
                "tools_used": meta.get("tools_used", []),
                "steps": result.get("steps") if isinstance(result, dict) else None,
                "trace_len": len(trace) if isinstance(trace, list) else None,
                "tool_error_seen": _result_has_tool_error(result) if isinstance(result, dict) else True,
            },
        )
    except Exception:
        return


def _redact_answer(result, config):
    if not isinstance(result, dict) or not _enabled(config, "redact_pii", False):
        return result
    answer = result.get("answer")
    if isinstance(answer, str):
        result = copy.deepcopy(result)
        result["answer"] = redact(answer)[0]
    return result


def mitigate(call_next, question, config, context):
    config = dict(config or {})
    context = context or {}
    cid = new_correlation_id()
    set_correlation_id(cid)

    safe_question = _sanitize_question(question)
    sanitized = safe_question != question
    cache_enabled = _enabled(config, "cache", False)
    cache_key = _cache_key(safe_question, config) if cache_enabled else None
    cache = context.get("cache") if isinstance(context.get("cache"), dict) else None
    cache_lock = context.get("cache_lock")

    if cache_enabled and cache is not None and cache_lock is not None:
        with cache_lock:
            if cache_key in cache:
                cached = copy.deepcopy(cache[cache_key])
                _log_call("WRAPPER_CACHE_HIT", context, cached, 0, 0, sanitized)
                return cached

    retry_config = config.get("retry", {}) if isinstance(config.get("retry"), dict) else {}
    max_attempts = int(retry_config.get("max_attempts", 1))
    max_attempts = max(1, max_attempts if _enabled(config, "retry", False) else 1)
    backoff_ms = max(0, int(retry_config.get("backoff_ms", 0)))

    result = {"answer": None, "status": "wrapper_error", "steps": 0, "trace": [], "meta": {}}
    for attempt in range(1, max_attempts + 1):
        t0 = time.time()
        try:
            result = call_next(safe_question, config)
            if not isinstance(result, dict):
                result = {"answer": None, "status": "wrapper_error", "steps": 0, "trace": [], "meta": {}}
        except Exception as exc:
            result = {
                "answer": None,
                "status": "wrapper_error",
                "steps": 0,
                "trace": [{"error": exc.__class__.__name__}],
                "meta": {},
            }
        wall_ms = int((time.time() - t0) * 1000)
        _log_call("WRAPPER_AGENT_CALL", context, result, wall_ms, attempt, sanitized)

        status = result.get("status")
        if status == "ok" and not _result_has_tool_error(result):
            break
        if status not in _RETRY_STATUSES and not _result_has_tool_error(result):
            break
        if attempt < max_attempts and backoff_ms:
            time.sleep(backoff_ms / 1000.0)

    result = _redact_answer(result, config)
    if cache_enabled and cache is not None and cache_lock is not None and result.get("status") == "ok":
        with cache_lock:
            cache[cache_key] = copy.deepcopy(result)
    return result
