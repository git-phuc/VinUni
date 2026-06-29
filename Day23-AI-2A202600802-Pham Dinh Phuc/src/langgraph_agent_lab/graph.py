"""Graph construction.

This module is intentionally import-safe. It imports LangGraph only inside the builder so unit tests
that check schema/metrics can run even if students are still debugging graph wiring.
"""

from __future__ import annotations

from typing import Any

from .state import AgentState


def build_graph(checkpointer: Any | None = None):
    """Build and compile the LangGraph support-ticket workflow.

    Architecture:

        START -> intake -> classify -> [route_after_classify]
          simple       -> answer -> finalize -> END
          tool         -> tool -> evaluate -> [route_after_evaluate]
                                                success     -> answer -> finalize -> END
                                                needs_retry -> retry  -> [route_after_retry]
                                                                          tool (loop)
                                                                          dead_letter -> finalize -> END
          missing_info -> clarify -> finalize -> END
          risky        -> risky_action -> approval -> [route_after_approval]
                                                       approved -> tool -> evaluate -> ...
                                                       rejected -> clarify -> finalize -> END
          error        -> retry -> [route_after_retry] -> ...
    """
    from langgraph.graph import END, START, StateGraph

    from . import nodes, routing

    graph = StateGraph(AgentState)

    # 1. Register all 11 nodes (names are the routing targets used below).
    graph.add_node("intake", nodes.intake_node)
    graph.add_node("classify", nodes.classify_node)
    graph.add_node("tool", nodes.tool_node)
    graph.add_node("evaluate", nodes.evaluate_node)
    graph.add_node("answer", nodes.answer_node)
    graph.add_node("clarify", nodes.ask_clarification_node)
    graph.add_node("risky_action", nodes.risky_action_node)
    graph.add_node("approval", nodes.approval_node)
    graph.add_node("retry", nodes.retry_or_fallback_node)
    graph.add_node("dead_letter", nodes.dead_letter_node)
    graph.add_node("finalize", nodes.finalize_node)

    # 2. Fixed edges.
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "classify")
    graph.add_edge("tool", "evaluate")
    graph.add_edge("risky_action", "approval")
    graph.add_edge("answer", "finalize")
    graph.add_edge("clarify", "finalize")
    graph.add_edge("dead_letter", "finalize")
    graph.add_edge("finalize", END)

    # 3. Conditional edges (explicit path maps keep the mermaid diagram readable).
    graph.add_conditional_edges(
        "classify",
        routing.route_after_classify,
        {"answer": "answer", "tool": "tool", "clarify": "clarify", "risky_action": "risky_action", "retry": "retry"},
    )
    graph.add_conditional_edges(
        "evaluate",
        routing.route_after_evaluate,
        {"retry": "retry", "answer": "answer"},
    )
    graph.add_conditional_edges(
        "retry",
        routing.route_after_retry,
        {"tool": "tool", "dead_letter": "dead_letter"},
    )
    graph.add_conditional_edges(
        "approval",
        routing.route_after_approval,
        {"tool": "tool", "clarify": "clarify"},
    )

    # 4. Compile with the checkpointer (persistence) supplied by the caller.
    return graph.compile(checkpointer=checkpointer)
