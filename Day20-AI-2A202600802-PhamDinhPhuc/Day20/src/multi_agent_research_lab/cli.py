"""Command-line entrypoint for the lab starter."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.search_client import SearchClient
from multi_agent_research_lab.services.llm_client import LLMClient

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def run_baseline_agent(query: str) -> ResearchState:
    """A standard single-agent RAG pipeline."""
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)

    search_client = SearchClient()
    try:
        sources = search_client.search(query, max_results=request.max_sources)
    except Exception as e:
        sources = []
        state.errors.append(f"Search failed: {e}")
    state.sources = sources

    # Synthesize prompts
    formatted_sources = ""
    for i, src in enumerate(sources, 1):
        formatted_sources += f"[{i}] {src.title}\nURL: {src.url}\nSnippet: {src.snippet}\n\n"

    system_prompt = f"""You are a Single-Agent Research Assistant.
Your task is to compile a detailed, well-structured, and factual answer to the query: "{query}"

Here are the search results:
{formatted_sources}

Write a clear final response. Organize with Markdown headers and bullet points.
Include inline citation numbers matching the sources (e.g. [1], [2]) when making claims."""

    user_prompt = "Generate the final response."

    try:
        llm_response = LLMClient().complete(system_prompt, user_prompt)
        state.final_answer = llm_response.content.strip()
    except Exception as e:
        state.errors.append(f"LLM call failed: {e}")
        state.final_answer = f"Baseline Fallback Answer for: {query}\n\n" + "\n".join(
            f"- **{s.title}**: {s.snippet}" for s in sources
        )
    state.iteration = 1
    return state


def run_multi_agent_workflow(query: str) -> ResearchState:
    """Runs the orchestrated multi-agent workflow."""
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    workflow = MultiAgentWorkflow()
    return workflow.run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline RAG pipeline."""
    _init()
    console.print(f"[bold blue]Running Single-Agent Baseline for query:[/bold blue] '{query}'")

    from multi_agent_research_lab.evaluation.benchmark import run_benchmark

    state, metrics = run_benchmark("Single-Agent Baseline", query, run_baseline_agent)
    console.print(Panel(state.final_answer or "No answer", title="Single-Agent Final Answer"))
    console.print(
        f"Latency: {metrics.latency_seconds:.2f}s | "
        f"Cost: ${metrics.estimated_cost_usd or 0.0:.6f} | "
        f"Quality: {metrics.quality_score or 0.0:.1f}"
    )


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""
    _init()
    console.print(f"[bold green]Running Multi-Agent Workflow for query:[/bold green] '{query}'")

    from multi_agent_research_lab.evaluation.benchmark import run_benchmark

    state, metrics = run_benchmark("Multi-Agent Workflow", query, run_multi_agent_workflow)
    console.print(Panel(state.final_answer or "No answer", title="Multi-Agent Final Answer"))
    console.print(
        f"Latency: {metrics.latency_seconds:.2f}s | "
        f"Cost: ${metrics.estimated_cost_usd or 0.0:.6f} | "
        f"Quality: {metrics.quality_score or 0.0:.1f}"
    )


@app.command("benchmark")
def benchmark(
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Optional custom query. If not provided, runs standard queries.",
        ),
    ] = None,
) -> None:
    """Run comparative benchmark and generate Markdown report."""
    _init()

    queries = [
        "Explain the differences between flat RAG and GraphRAG pipelines.",
        "What are the core design patterns of multi-agent systems?",
    ]
    if query:
        queries = [query]

    console.print("[bold magenta]Starting comparative benchmark suite...[/bold magenta]")

    from multi_agent_research_lab.evaluation.benchmark import run_benchmark
    from multi_agent_research_lab.evaluation.report import render_markdown_report
    import os

    all_metrics = []
    for idx, q in enumerate(queries, 1):
        console.print(f"\n[bold yellow]Query {idx}/{len(queries)}: '{q}'[/bold yellow]")

        # Baseline
        console.print("Running baseline...")
        _, metrics_bl = run_benchmark(f"Single-Agent (Q{idx})", q, run_baseline_agent)
        all_metrics.append(metrics_bl)

        # Multi-Agent
        console.print("Running multi-agent...")
        _, metrics_ma = run_benchmark(f"Multi-Agent (Q{idx})", q, run_multi_agent_workflow)
        all_metrics.append(metrics_ma)

    # Render and save report
    report_content = render_markdown_report(all_metrics)

    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "benchmark_report.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    console.print(f"\n[bold green]Benchmark completed successfully![/bold green]")
    console.print(f"Report saved to: [underline]{report_path}[/underline]")


if __name__ == "__main__":
    app()

