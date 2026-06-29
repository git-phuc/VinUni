"""Export the compiled LangGraph as a Mermaid diagram (extension: graph diagram).

Usage:  python scripts/export_diagram.py
Writes: docs/graph.mmd  (mermaid source) and docs/graph.png (rendered image).
The PNG render uses the mermaid.ink API; if offline it is skipped (the .mmd still works).
"""

from __future__ import annotations

from pathlib import Path

from langgraph_agent_lab.graph import build_graph


def main() -> None:
    drawable = build_graph(checkpointer=None).get_graph()
    docs = Path("docs")
    docs.mkdir(parents=True, exist_ok=True)

    mmd = docs / "graph.mmd"
    mmd.write_text(drawable.draw_mermaid(), encoding="utf-8")
    print(drawable.draw_mermaid())
    print(f"\nWrote {mmd}")

    png = docs / "graph.png"
    try:
        png.write_bytes(drawable.draw_mermaid_png())
        print(f"Wrote {png}")
    except Exception as exc:  # noqa: BLE001 — PNG render needs network; .mmd is the source of truth
        print(f"Skipped {png} (render unavailable: {type(exc).__name__})")


if __name__ == "__main__":
    main()
