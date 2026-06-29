# Persistence / Crash-Recovery Evidence (Extension Track)

Two extensions are demonstrated here: **SQLite checkpointer** (durable persistence) and
**time-travel** via `get_state_history()`. The diagram extension lives in
[`graph.png`](graph.png) (rendered image) / [`graph.mmd`](graph.mmd) (Mermaid source).

## How to reproduce

```bash
python scripts/export_diagram.py        # -> docs/graph.mmd (Mermaid)
python scripts/demo_persistence.py write # process #1: run + persist, then exit (simulated crash)
python scripts/demo_persistence.py read  # process #2: FRESH process recovers state from disk
# or: make demo-persistence
```

`build_checkpointer("sqlite", "checkpoints.db")` returns a `SqliteSaver(conn=sqlite3.connect(...))`
in WAL mode (see `src/langgraph_agent_lab/persistence.py`). Each run uses a unique
`thread_id`, so its checkpoint trail is independently recoverable.

## Captured output — recovery across a process boundary

Process #1 runs the graph and exits; process #2 is a brand-new Python process (different PID)
that only *reads* the persisted checkpoints — it never re-invokes the graph or the LLM.

```text
########## PROCESS 1 (write, then exits) ##########
[WRITE] process pid=15852 — running scenario, persisting to checkpoints.db
[WRITE] route=tool  final_answer='Thank you for your inquiry regarding order 12345. ...'
[WRITE] checkpoints flushed to disk. Process now exits (simulated crash).

########## PROCESS 2 (fresh, reads from disk) ##########
[READ ] FRESH process pid=21684 — re-opening checkpoints.db, NO graph re-run
[READ ] RECOVERED thread_id=demo-recovery-001
[READ ]   route        = tool
[READ ]   final_answer = 'Thank you for your inquiry regarding order 12345. ...'
[READ ]   events logged= 6
[READ ] time-travel: 8 checkpoints persisted (newest first):
[READ ]   #00 next=('END',)        last_msg='finalize'
[READ ]   #01 next=('finalize',)   last_msg='answer:generated'
[READ ]   #02 next=('answer',)     last_msg='evaluate:success'
[READ ]   #03 next=('evaluate',)   last_msg='tool:completed'
[READ ]   #04 next=('tool',)       last_msg='classify:tool'
[READ ]   #05 next=('classify',)   last_msg='intake:Please lookup order status for order 123'
[READ ]   #06 next=('intake',)     last_msg='<start>'
[READ ]   #07 next=('__start__',)  last_msg='<start>'
```

**What this proves**

- The two PIDs differ (`15852` → `21684`): the state is reconstructed purely from
  `checkpoints.db`, not from in-memory state — i.e. it survives a process kill/restart.
- `get_state()` recovers the terminal values (`route`, `final_answer`, 6 audit events).
- `get_state_history()` returns all **8 checkpoints** in reverse order — one per super-step —
  enabling time-travel replay from any prior checkpoint.
