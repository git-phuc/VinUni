"""Persistence / crash-recovery demonstration (extension track).

Two-phase demo proving SQLite checkpoints survive a process boundary:

  Phase WRITE (process #1):  python scripts/demo_persistence.py write
      - builds the graph with a SqliteSaver on checkpoints.db
      - runs one scenario under a fixed thread_id, persisting every checkpoint
      - process then exits (simulating a crash / restart)

  Phase READ (process #2):   python scripts/demo_persistence.py read
      - a FRESH process + FRESH SqliteSaver opens the same checkpoints.db
      - recovers the final state via get_state() WITHOUT re-running the graph
      - prints get_state_history() (time-travel) to show the full checkpoint trail

Run both phases (see Makefile target `demo-persistence`) to show recovery across processes.
"""

from __future__ import annotations

import sys

from langgraph_agent_lab.graph import build_graph
from langgraph_agent_lab.persistence import build_checkpointer
from langgraph_agent_lab.state import Route, Scenario, initial_state

THREAD_ID = "demo-recovery-001"
DB = "checkpoints.db"
CONFIG = {"configurable": {"thread_id": THREAD_ID}}


def phase_write() -> None:
    print(f"[WRITE] process pid={__import__('os').getpid()} — running scenario, persisting to {DB}")
    graph = build_graph(checkpointer=build_checkpointer("sqlite", DB))
    scenario = Scenario(id=THREAD_ID, query="Please lookup order status for order 12345", expected_route=Route.TOOL)
    state = initial_state(scenario)
    result = graph.invoke(state, config=CONFIG)
    print(f"[WRITE] route={result['route']}  final_answer={result['final_answer'][:70]!r}")
    print("[WRITE] checkpoints flushed to disk. Process now exits (simulated crash).")


def phase_read() -> None:
    print(f"[READ ] FRESH process pid={__import__('os').getpid()} — re-opening {DB}, NO graph re-run")
    graph = build_graph(checkpointer=build_checkpointer("sqlite", DB))
    snapshot = graph.get_state(CONFIG)
    if not snapshot.values:
        print("[READ ] no state found — run the WRITE phase first.")
        sys.exit(1)
    vals = snapshot.values
    print(f"[READ ] RECOVERED thread_id={THREAD_ID}")
    print(f"[READ ]   route        = {vals.get('route')}")
    print(f"[READ ]   final_answer = {str(vals.get('final_answer'))[:70]!r}")
    print(f"[READ ]   events logged= {len(vals.get('events', []))}")

    history = list(graph.get_state_history(CONFIG))
    print(f"[READ ] time-travel: {len(history)} checkpoints persisted (newest first):")
    for i, ckpt in enumerate(history):
        nxt = ckpt.next or ("END",)
        last_msg = (ckpt.values.get("messages") or ["<start>"])[-1]
        print(f"[READ ]   #{i:02d} next={nxt} last_msg={last_msg!r}")


def main() -> None:
    phase = sys.argv[1] if len(sys.argv) > 1 else "write"
    if phase == "write":
        phase_write()
    elif phase == "read":
        phase_read()
    else:
        print("usage: demo_persistence.py [write|read]")
        sys.exit(2)


if __name__ == "__main__":
    main()
