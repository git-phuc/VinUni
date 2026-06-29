"""Report generation helper.

Renders a complete, submission-ready lab report (markdown) from MetricsReport data,
following the structure of reports/lab_report_template.md. The scenario tables are driven
entirely by the metrics computed during `run-scenarios`; the architecture / failure-analysis
narrative is static and describes the implemented graph.
"""

from __future__ import annotations

from pathlib import Path

from .metrics import MetricsReport

_ARCHITECTURE = """## 2. Architecture

The workflow is a `StateGraph(AgentState)` with **11 nodes** and **4 conditional routers**.

```
START -> intake -> classify -> [route_after_classify]
  simple       -> answer -> finalize -> END
  tool         -> tool -> evaluate -> [route_after_evaluate]
                                        success     -> answer -> finalize -> END
                                        needs_retry -> retry  -> [route_after_retry]
                                                                  attempt<max -> tool (loop)
                                                                  attempt>=max -> dead_letter -> finalize -> END
  missing_info -> clarify -> finalize -> END
  risky        -> risky_action -> approval -> [route_after_approval]
                                               approved -> tool -> evaluate -> ...
                                               rejected -> clarify -> finalize -> END
  error        -> retry -> [route_after_retry] -> ...
```

| Node | Role | LLM? |
|---|---|---|
| `intake` | normalize the raw query | no |
| `classify` | intent classification into one of 5 routes | **yes** — `gpt-4o-mini` + `.with_structured_output()` |
| `tool` | mock tool call; simulates transient failure on the error route | no |
| `evaluate` | retry-loop gate on tool-result quality | **yes (bonus)** — `gpt-5-nano` LLM-as-judge, heuristic fallback |
| `answer` | grounded final response | **yes** — `gpt-4o-mini` |
| `clarify` | ask one specific clarifying question | yes — `gpt-4o-mini` |
| `risky_action` | describe the side-effecting action | no |
| `approval` | human-in-the-loop gate (mock or `interrupt()`) | no |
| `retry` | increment the bounded attempt counter | no |
| `dead_letter` | escalate after retries are exhausted | no |
| `finalize` | emit terminal audit event (all routes pass through) | no |

Routing functions: `route_after_classify` (route string -> node), `route_after_evaluate`
(needs_retry -> retry, else answer), `route_after_retry` (bounded: attempt<max -> tool, else
dead_letter), `route_after_approval` (approved -> tool, else clarify).
"""

_STATE_SCHEMA = """## 3. State schema

| Field | Reducer | Why |
|---|---|---|
| `query` | overwrite | current normalized query |
| `route` | overwrite | classifier's decision for this run |
| `risk_level` | overwrite | `high` for risky route, else `low` |
| `attempt` / `max_attempts` | overwrite | bounded retry counter |
| `evaluation_result` | overwrite | gate value (`success`/`needs_retry`) read by `route_after_evaluate` |
| `pending_question` | overwrite | clarification asked on the missing-info path |
| `proposed_action` | overwrite | risky action awaiting approval |
| `approval` | overwrite | latest HITL decision dict |
| `final_answer` | overwrite | the single response surfaced to the user |
| `messages` | **append** (`add`) | human-readable trace of node hops |
| `tool_results` | **append** (`add`) | every tool invocation result (audit) |
| `errors` | **append** (`add`) | every transient failure encountered |
| `events` | **append** (`add`) | structured audit log; metrics are derived from it |

Design rule: *decision/value* fields overwrite (only the latest matters); *audit trail* fields
(`messages`, `tool_results`, `errors`, `events`) are append-only so nothing is lost across loops.
"""

_FAILURE_ANALYSIS = """## 5. Failure analysis

1. **Transient tool failure + retry.** `tool_node` returns an `ERROR...` string on the error route
   while `attempt < 2`. `evaluate_node` detects this deterministically (`"ERROR" in result`) and sets
   `needs_retry`, sending the graph through `retry`. The loop is **bounded** by `route_after_retry`
   (`attempt < max_attempts`), so it always terminates — either the tool eventually succeeds
   (S05) or the run hits `dead_letter` when attempts are exhausted (S07).

2. **Risky action without approval.** Refund/delete/email requests classify as `risky` and are forced
   through `risky_action -> approval` before any tool runs. Only `route_after_approval` returning
   `approved` lets execution proceed to `tool`; a rejection diverts to `clarify`. This guarantees no
   side-effecting action can reach the tool node without passing the HITL gate.

Other guards: the LLM-as-judge (`gpt-5-nano`) is best-effort and wrapped in try/except so a judge
outage never breaks the graph (it falls back to the heuristic verdict); every terminal path routes
through `finalize -> END`, so no scenario can hang.
"""

_IMPROVEMENT = """## 8. Improvement plan

With one more day I would productionize, in order: (1) replace the mock `tool_node` with real,
typed tool adapters behind a registry and add timeouts/circuit-breakers; (2) add exponential backoff
+ jitter to the retry loop instead of immediate retry; (3) emit OpenTelemetry traces / LangSmith runs
per `thread_id` for observability; (4) move HITL approvals to a durable queue (interrupt + resume via
the SQLite/Postgres checkpointer) so a human can approve hours later after a process restart.
"""


def render_report(metrics: MetricsReport) -> str:
    """Render a complete lab report (markdown) from metrics data."""
    sm = metrics.scenario_metrics

    # Section 1 — header / summary.
    summary_rows = [
        "## 1. Team / student",
        "",
        "- Name: Phạm Đình Phúc - 2A202600802",
        "- Repo/commit: git-phuc/VinUni — Day23 LangGraph Agentic Orchestration lab",
        "- Models: main `gpt-4o-mini`, judge `gpt-5-nano` (LLM-as-judge)",
        "",
        "### Run summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total scenarios | {metrics.total_scenarios} |",
        f"| Success rate | {metrics.success_rate:.0%} |",
        f"| Avg nodes visited | {metrics.avg_nodes_visited:.2f} |",
        f"| Total retries | {metrics.total_retries} |",
        f"| Total approvals (interrupts) | {metrics.total_interrupts} |",
        f"| Resume success (crash-recovery) | {metrics.resume_success} |",
    ]

    # Section 4 — per-scenario results.
    scenario_rows = [
        "## 4. Scenario results",
        "",
        "| Scenario | Expected | Actual | Success | Retries | Approvals | Nodes |",
        "|---|---|---|:---:|---:|---:|---:|",
    ]
    for m in sm:
        ok = "✅" if m.success else "❌"
        scenario_rows.append(
            f"| {m.scenario_id} | {m.expected_route} | {m.actual_route} | {ok} "
            f"| {m.retry_count} | {m.interrupt_count} | {m.nodes_visited} |"
        )

    persistence = [
        "## 6. Persistence / recovery evidence",
        "",
        "The graph compiles with a checkpointer selected by `configs/lab.yaml` (`checkpointer:`). "
        "Each scenario runs under a unique `thread_id` (`thread-<scenario_id>`), so its full state "
        "history is recoverable via `graph.get_state_history(config)`. Switching `checkpointer` to "
        "`sqlite` persists checkpoints to `checkpoints.db` (WAL mode), which survives a process "
        "restart — see Section 7 for the crash-recovery demonstration.",
    ]

    extension = [
        "## 7. Extension work",
        "",
        "- **LLM-as-judge** (`evaluate_node`): `gpt-5-nano` scores tool-result quality on the success path.",
        "- **SQLite persistence**: `build_checkpointer('sqlite')` -> `SqliteSaver` with WAL; checkpoints "
        "survive process restart (see `docs/persistence_evidence.md`).",
        "- **Graph diagram**: rendered image `docs/graph.png` + Mermaid source `docs/graph.mmd`.",
        "- **Real HITL**: setting `LANGGRAPH_INTERRUPT=true` makes `approval_node` pause via `interrupt()`.",
    ]

    parts = [
        "# Day 23 Lab Report — LangGraph Agentic Orchestration",
        "",
        "\n".join(summary_rows),
        _ARCHITECTURE,
        _STATE_SCHEMA,
        "\n".join(scenario_rows),
        _FAILURE_ANALYSIS,
        "\n".join(persistence),
        "\n".join(extension),
        _IMPROVEMENT,
    ]
    return "\n\n".join(parts).strip() + "\n"


def write_report(metrics: MetricsReport, output_path: str | Path) -> None:
    """Write the rendered report to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(metrics), encoding="utf-8")
