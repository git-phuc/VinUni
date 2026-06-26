import logging
import re
from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

Runner = Callable[[str], ResearchState]


def estimate_tokens(text: str) -> int:
    """Approximate token count from character length."""
    return len(text) // 4


def calculate_estimated_cost(state: ResearchState) -> float:
    """Approximate the API usage cost based on prompt/completion content."""
    total_prompt_chars = 0
    total_completion_chars = 0

    # 1. Supervisor routing calls
    for _ in range(state.iteration):
        total_prompt_chars += 2000  # Approximate supervisor prompt size
        total_completion_chars += 20  # "researcher", "analyst", etc.

    # 2. Researcher search query & notes synthesis
    if state.research_notes:
        total_prompt_chars += len(state.request.query) + 200
        total_completion_chars += 50
        sources_len = sum(len(s.snippet) + len(s.title) for s in state.sources)
        total_prompt_chars += sources_len + 500
        total_completion_chars += len(state.research_notes)

    # 3. Analyst claims extraction
    if state.analysis_notes:
        total_prompt_chars += len(state.research_notes or "") + 500
        total_completion_chars += len(state.analysis_notes)

    # 4. Writer final answer compilation
    if state.final_answer:
        sources_len = sum(len(s.snippet) + len(s.title) for s in state.sources)
        total_prompt_chars += (
            len(state.research_notes or "")
            + len(state.analysis_notes or "")
            + sources_len
            + 800
        )
        total_completion_chars += len(state.final_answer)

    # 5. Critic review calls
    critic_results = [r for r in state.agent_results if r.agent == "critic"]
    for c in critic_results:
        sources_len = sum(len(s.snippet) + len(s.title) for s in state.sources)
        total_prompt_chars += len(state.final_answer or "") + sources_len + 800
        total_completion_chars += len(c.content)

    prompt_tokens = estimate_tokens(str(total_prompt_chars))
    completion_tokens = estimate_tokens(str(total_completion_chars))

    # Assume gpt-4o-mini pricing: $0.15 / 1M input, $0.60 / 1M output
    cost = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    return cost


def evaluate_quality(query: str, final_answer: str | None, sources_count: int) -> float:
    """Evaluate final answer quality using LLM-as-a-judge or simple heuristics."""
    if not final_answer or len(final_answer.strip()) < 10:
        return 0.0

    system_prompt = """You are an expert AI evaluator.
Evaluate the given answer to the query on a scale of 0.0 to 10.0.
Consider:
1. Accuracy: Is it factual and aligned with sources?
2. Citation coverage: Are claims backed by citations (e.g. [1], [2])?
3. Clarity and structure: Is it well-organized and easy to read?

Respond with ONLY a float number between 0.0 and 10.0. No text, no markdown. Just the number."""

    user_prompt = f"Query: {query}\n\nAnswer:\n{final_answer}\n\nSources count: {sources_count}\n\nScore:"

    try:
        response = LLMClient().complete(system_prompt, user_prompt)
        score = float(response.content.strip())
        return min(max(score, 0.0), 10.0)
    except Exception:
        # Fallback heuristics
        score = 5.0
        if len(final_answer) > 800:
            score += 1.5
        if "[" in final_answer and "]" in final_answer:
            score += 2.0
        if sources_count >= 3:
            score += 1.5
        return min(score, 10.0)


def calculate_citation_coverage(final_answer: str | None) -> int:
    """Count unique inline citations (e.g., [1], [2]) in the text."""
    if not final_answer:
        return 0
    citations = set(re.findall(r"\[\d+\]", final_answer))
    return len(citations)


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, estimate costs, evaluate quality, and generate metrics."""
    logger.info(f"Starting benchmark run: {run_name}")
    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started

    # Calculate advanced metrics
    cost = calculate_estimated_cost(state)
    quality = evaluate_quality(query, state.final_answer, len(state.sources))
    citations = calculate_citation_coverage(state.final_answer)

    notes = (
        f"Iterations: {state.iteration}. "
        f"Sources: {len(state.sources)}. "
        f"Citations: {citations}. "
        f"Errors: {len(state.errors)}."
    )

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost,
        quality_score=quality,
        notes=notes,
    )
    logger.info(f"Finished benchmark run: {run_name} in {latency:.2f}s (Quality: {quality})")
    return state, metrics

