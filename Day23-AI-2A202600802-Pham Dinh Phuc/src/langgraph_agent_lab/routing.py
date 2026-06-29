"""Routing functions for conditional edges.

Each function takes AgentState and returns a string — the name of the next node.
These strings MUST match node names registered in graph.py.
"""

from __future__ import annotations

from .state import AgentState

# route string (from classify_node) -> next graph node name
_CLASSIFY_MAP = {
    "simple": "answer",
    "tool": "tool",
    "missing_info": "clarify",
    "risky": "risky_action",
    "error": "retry",
}


def route_after_classify(state: AgentState) -> str:
    """Map the classified route to the next graph node (unknown -> answer)."""
    return _CLASSIFY_MAP.get(state.get("route", ""), "answer")


def route_after_evaluate(state: AgentState) -> str:
    """Retry-loop gate: needs_retry -> retry, otherwise -> answer."""
    return "retry" if state.get("evaluation_result") == "needs_retry" else "answer"


def route_after_retry(state: AgentState) -> str:
    """Bounded retry: try the tool again while attempts remain, else dead-letter."""
    if state.get("attempt", 0) < state.get("max_attempts", 3):
        return "tool"
    return "dead_letter"


def route_after_approval(state: AgentState) -> str:
    """HITL gate: approved -> proceed to tool, rejected -> clarify with the user."""
    approval = state.get("approval") or {}
    return "tool" if approval.get("approved") else "clarify"
