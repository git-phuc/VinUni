import logging
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""
        logger.info("AnalystAgent started...")

        research_notes = state.research_notes or "No research notes compiled yet."

        system_prompt = """You are the Analyst Agent of a Multi-Agent Research System.
Your job is to read raw research notes and analyze them.
Specifically:
1. Extract key claims.
2. Compare differing viewpoints or perspectives, highlighting areas of consensus and divergence.
3. Assess the strength of the evidence (e.g. note if a source is weak, has potential bias, or is lack of details).
4. Identify any remaining gaps in the notes.

Format your analysis clearly in Markdown with headers and bullet points."""

        user_prompt = f"Here are the research notes:\n{research_notes}\n\nPerform the analysis:"

        try:
            llm_response = LLMClient().complete(system_prompt, user_prompt)
            analysis = llm_response.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate analysis notes using LLM ({e}). Falling back to simple summary.")
            analysis = (
                f"### Analysis Notes (Fallback Summary)\n\n"
                f"- **Summary**: Analyzed raw research notes ({len(research_notes)} characters).\n"
                f"- **Claims**: The documents discuss '{state.request.query}'.\n"
                f"- **Evaluation**: Evidence seems standard but needs further live verification."
            )

        state.analysis_notes = analysis
        state.add_trace_event("analysis", {"analysis_notes_length": len(analysis)})
        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=analysis,
                metadata={"analysis_notes_length": len(analysis)},
            )
        )

        logger.info("AnalystAgent finished.")
        return state

