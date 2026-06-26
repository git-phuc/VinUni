import logging
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""
        logger.info("WriterAgent started...")

        research_notes = state.research_notes or "No research notes available."
        analysis_notes = state.analysis_notes or "No analysis notes available."

        formatted_sources = ""
        for i, src in enumerate(state.sources, 1):
            formatted_sources += f"[{i}] {src.title}\nURL: {src.url}\nSnippet: {src.snippet}\n\n"

        system_prompt = f"""You are the Writer Agent of a Multi-Agent Research System.
Your task is to compile the final answer to the user's query: "{state.request.query}"

Audience: {state.request.audience}

You have the following inputs:
- Raw Research Notes:
{research_notes}

- Structured Analysis Notes:
{analysis_notes}

- Search Sources:
{formatted_sources}

Write a comprehensive, detailed, and highly clear final answer answering the user's query.
Requirements:
1. Synthesize both the research and analysis notes into a cohesive response.
2. Structure the answer professionally using Markdown headers, lists, and bold text.
3. Explicitly cite your sources using inline citation numbers matching the search sources (e.g. [1], [2], or inline URL links) when presenting claims or facts.
4. Adapt the style and technical depth to match the target audience: "{state.request.audience}"."""

        user_prompt = "Generate the final answer."

        try:
            llm_response = LLMClient().complete(system_prompt, user_prompt)
            answer = llm_response.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate final answer using LLM ({e}). Falling back to structured synthesis.")
            answer = (
                f"# Research Report: {state.request.query}\n\n"
                f"*(Note: Generated via fallback writer mode due to LLM provider configuration)*\n\n"
                f"## Executive Summary\n"
                f"Aggregated notes and structured analysis addressing '{state.request.query}' for {state.request.audience}.\n\n"
                f"## Summary of Findings\n"
                f"{research_notes}\n\n"
                f"## Analysis & Critical Evaluation\n"
                f"{analysis_notes}\n\n"
                f"## Bibliography\n"
            )
            for i, src in enumerate(state.sources, 1):
                answer += f"[{i}] **{src.title}** - URL: {src.url or 'N/A'}\n"

        state.final_answer = answer
        state.add_trace_event("write", {"final_answer_length": len(answer)})
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=answer,
                metadata={"final_answer_length": len(answer)},
            )
        )

        logger.info("WriterAgent finished.")
        return state

