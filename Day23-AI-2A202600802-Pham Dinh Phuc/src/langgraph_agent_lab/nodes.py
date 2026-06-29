"""Node functions for the LangGraph workflow.

Each function receives AgentState and returns a partial state update dict.
Do NOT mutate input state — return new values only.

LLM REQUIREMENT:
- classify_node MUST use a real LLM call (structured output for intent classification)
- answer_node MUST use a real LLM call (grounded response generation)
- evaluate_node SHOULD use LLM-as-judge (bonus points; heuristic acceptable for base score)
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from .llm import get_llm
from .state import AgentState, make_event


def _text(response: object) -> str:
    """Extract plain text from a LangChain chat response."""
    content = getattr(response, "content", response)
    if isinstance(content, list):  # some providers return content blocks
        parts = [block.get("text", "") if isinstance(block, dict) else str(block) for block in content]
        return "".join(parts).strip()
    return str(content).strip()


# ─── EXAMPLE: working node (provided for reference) ──────────────────
def intake_node(state: AgentState) -> dict:
    """Normalize raw query. This node is provided as a working example."""
    query = state.get("query", "").strip()
    return {
        "query": query,
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized")],
    }


# ─── classify_node: LLM + structured output ──────────────────────────


class Classification(BaseModel):
    """Structured classification output."""

    route: Literal["risky", "tool", "missing_info", "error", "simple"] = Field(
        description="The single best route for this ticket, respecting priority risky>tool>missing_info>error>simple"
    )
    risk_level: Literal["high", "low"] = Field(description="high only for the risky route, otherwise low")
    reason: str = Field(default="", description="one short sentence justifying the route")


CLASSIFY_SYSTEM = """You are a support-ticket triage classifier. Classify the ticket into exactly ONE route.

Apply this PRIORITY order — pick the HIGHEST route that matches:
1. risky        — actions with side effects: refunds, deletions, cancellations, sending emails, account changes.
2. tool         — information lookups: order status, tracking numbers, searching/fetching records.
3. missing_info — vague or incomplete request lacking actionable detail (e.g. "can you fix it?").
4. error        — system failures: timeouts, crashes, service unavailable, "cannot recover after attempts".
5. simple       — general questions answerable directly without tools or actions (e.g. how-to / policy).

Rules:
- If a ticket both looks up info AND performs a side-effecting action, choose risky (higher priority).
- Set risk_level = "high" only when route is risky; otherwise "low"."""


def classify_node(state: AgentState) -> dict:
    """Classify the query into a route using an LLM with structured output."""
    llm = get_llm()  # main model: gpt-4o-mini, temperature 0
    classifier = llm.with_structured_output(Classification)
    query = state.get("query", "")
    result: Classification = classifier.invoke(
        [
            ("system", CLASSIFY_SYSTEM),
            ("human", f"Support ticket:\n{query}\n\nClassify it."),
        ]
    )
    route = result.route
    risk_level = "high" if route == "risky" else "low"
    return {
        "route": route,
        "risk_level": risk_level,
        "messages": [f"classify:{route}"],
        "events": [
            make_event(
                "classify",
                "completed",
                f"route={route} ({result.reason})",
                route=route,
                risk_level=risk_level,
                reason=result.reason,
            )
        ],
    }


# ─── tool_node: mock tool with transient-failure simulation ──────────


def tool_node(state: AgentState) -> dict:
    """Execute a mock tool call, simulating transient failures on the error route."""
    route = state.get("route", "")
    attempt = state.get("attempt", 0)
    # Error scenarios fail transiently on the first couple of attempts so the retry loop is exercised.
    if route == "error" and attempt < 2:
        result = f"ERROR: transient tool failure on attempt {attempt}"
        event_type = "error"
    else:
        query = state.get("query", "")
        result = f"TOOL_OK: retrieved data for '{query[:50]}' (attempt {attempt})"
        event_type = "completed"
    return {
        "tool_results": [result],
        "messages": [f"tool:{event_type}"],
        "events": [make_event("tool", event_type, result, attempt=attempt, route=route)],
    }


# ─── evaluate_node: LLM-as-judge gate (gpt-5-nano) ───────────────────


class JudgeVerdict(BaseModel):
    """LLM-as-judge verdict on tool-result quality."""

    adequate: bool = Field(description="true if the tool result usefully addresses the query")
    reason: str = Field(default="", description="one short sentence explaining the verdict")


JUDGE_SYSTEM = """You are the QA gate for a support agent's tool calls in a MOCK environment.
Your only job is to decide whether the tool call SUCCEEDED or FAILED (this gates a retry loop).

- A result that begins with "TOOL_OK" or otherwise represents a successful data retrieval -> adequate=true.
- Mark adequate=false ONLY when the result is empty, an error/timeout/failure, or explicitly unusable.
- This is a mock payload, so do NOT require real order numbers or full detail; a successful retrieval is enough.
When in doubt, return adequate=true."""


def evaluate_node(state: AgentState) -> dict:
    """Evaluate the latest tool result — the retry-loop gate.

    Two-layer design:
    1. Deterministic safety gate: empty or "ERROR" result -> needs_retry (no LLM call wasted).
    2. LLM-as-judge (gpt-5-nano) confirms quality on the success path (bonus). Falls back to
       the heuristic verdict if the judge model is unavailable or errors.
    """
    tool_results = state.get("tool_results", []) or []
    latest = tool_results[-1] if tool_results else ""

    # Layer 1 — deterministic gate on hard failures.
    if not latest or "ERROR" in latest:
        return {
            "evaluation_result": "needs_retry",
            "messages": ["evaluate:needs_retry"],
            "events": [make_event("evaluate", "completed", "tool failed -> needs_retry", judge="heuristic")],
        }

    # Layer 2 — LLM-as-judge quality check on the success path.
    judge_model = os.getenv("JUDGE_MODEL", "gpt-5-nano")
    verdict = "success"
    judge_used = "heuristic"
    judge_reason = "non-error tool result"
    try:
        judge = get_llm(model=judge_model).with_structured_output(JudgeVerdict)
        result: JudgeVerdict = judge.invoke(
            [
                ("system", JUDGE_SYSTEM),
                ("human", f"Query:\n{state.get('query', '')}\n\nTool result:\n{latest}\n\nIs it adequate?"),
            ]
        )
        verdict = "success" if result.adequate else "needs_retry"
        judge_used = judge_model
        judge_reason = result.reason
    except Exception as exc:  # noqa: BLE001 — judge is best-effort; never fail the graph on it
        judge_reason = f"judge unavailable ({type(exc).__name__}), fell back to heuristic"

    return {
        "evaluation_result": verdict,
        "messages": [f"evaluate:{verdict}"],
        "events": [
            make_event("evaluate", "completed", f"verdict={verdict} ({judge_reason})", judge=judge_used)
        ],
    }


# ─── answer_node: LLM-grounded response ──────────────────────────────


ANSWER_SYSTEM = """You are a helpful customer-support agent. Write the final reply to the customer.
Ground your answer ONLY in the provided context when context exists; do not invent order numbers,
amounts, or facts that are not present. Be concise (2-4 sentences)."""


def answer_node(state: AgentState) -> dict:
    """Generate a final response using an LLM, grounded in available context."""
    llm = get_llm()  # main model: gpt-4o-mini
    query = state.get("query", "")
    tool_results = state.get("tool_results", []) or []
    approval = state.get("approval")

    context_parts: list[str] = []
    if tool_results:
        context_parts.append("Tool results:\n" + "\n".join(tool_results))
    if approval:
        context_parts.append(f"Human approval decision: {approval}")
    context = "\n\n".join(context_parts) if context_parts else "(no tool context — answer from general knowledge)"

    response = llm.invoke(
        [
            ("system", ANSWER_SYSTEM),
            ("human", f"Customer ticket:\n{query}\n\nContext:\n{context}\n\nWrite the reply."),
        ]
    )
    answer = _text(response)
    return {
        "final_answer": answer,
        "messages": ["answer:generated"],
        "events": [make_event("answer", "completed", "final answer generated", chars=len(answer))],
    }


# ─── ask_clarification_node ──────────────────────────────────────────


def ask_clarification_node(state: AgentState) -> dict:
    """Ask one specific clarifying question instead of hallucinating an answer."""
    llm = get_llm()
    query = state.get("query", "")
    response = llm.invoke(
        [
            (
                "system",
                "The user's support request is vague or was declined for safety. Ask exactly ONE specific "
                "clarifying question to obtain the missing detail needed to help. Output only the question.",
            ),
            ("human", f"Request: {query}"),
        ]
    )
    question = _text(response)
    return {
        "pending_question": question,
        "final_answer": question,
        "messages": ["clarify:asked"],
        "events": [make_event("clarify", "completed", "clarification requested", question=question)],
    }


# ─── risky_action_node ───────────────────────────────────────────────


def risky_action_node(state: AgentState) -> dict:
    """Prepare a risky, side-effecting action for human approval."""
    query = state.get("query", "")
    action = f"Side-effecting action requested: {query}. Requires human approval before execution."
    return {
        "proposed_action": action,
        "messages": ["risky:proposed"],
        "events": [make_event("risky_action", "completed", "risky action prepared for approval", action=action)],
    }


# ─── approval_node: human-in-the-loop ────────────────────────────────


def approval_node(state: AgentState) -> dict:
    """Human-in-the-loop approval step.

    Default: mock approval (approved=True) so tests/CI run offline.
    Extension: when LANGGRAPH_INTERRUPT=true, pause via langgraph.types.interrupt() for real HITL.
    """
    if os.getenv("LANGGRAPH_INTERRUPT", "").lower() == "true":
        from langgraph.types import interrupt

        decision = interrupt(
            {
                "proposed_action": state.get("proposed_action", ""),
                "query": state.get("query", ""),
                "prompt": "Approve this risky action? Provide {'approved': bool, 'comment': str}",
            }
        )
        if isinstance(decision, dict):
            approval = {
                "approved": bool(decision.get("approved", True)),
                "reviewer": decision.get("reviewer", "human"),
                "comment": decision.get("comment", ""),
            }
        else:
            approval = {"approved": bool(decision), "reviewer": "human", "comment": ""}
    else:
        approval = {"approved": True, "reviewer": "mock-reviewer", "comment": "auto-approved (mock HITL)"}

    return {
        "approval": approval,
        "messages": [f"approval:{approval['approved']}"],
        "events": [make_event("approval", "completed", f"approved={approval['approved']}", **approval)],
    }


# ─── retry_or_fallback_node ──────────────────────────────────────────


def retry_or_fallback_node(state: AgentState) -> dict:
    """Record a retry attempt: increment the bounded attempt counter and log the failure."""
    attempt = state.get("attempt", 0) + 1
    error_msg = f"transient failure handled; retry attempt {attempt}"
    return {
        "attempt": attempt,
        "errors": [error_msg],
        "messages": [f"retry:{attempt}"],
        "events": [make_event("retry", "completed", error_msg, attempt=attempt)],
    }


# ─── dead_letter_node ────────────────────────────────────────────────


def dead_letter_node(state: AgentState) -> dict:
    """Handle unresolvable failures after max retries — the third layer of resilience."""
    attempts = state.get("attempt", 0)
    message = (
        f"We could not complete your request automatically after {attempts} attempt(s). "
        "It has been escalated to a human support specialist (dead-letter queue)."
    )
    return {
        "final_answer": message,
        "messages": ["dead_letter"],
        "events": [make_event("dead_letter", "completed", "max retries exceeded -> dead letter", attempts=attempts)],
    }


# ─── finalize_node ───────────────────────────────────────────────────


def finalize_node(state: AgentState) -> dict:
    """Emit a final audit event. All routes must pass through here before END."""
    return {
        "messages": ["finalize"],
        "events": [make_event("finalize", "completed", "workflow finished", route=state.get("route"))],
    }
