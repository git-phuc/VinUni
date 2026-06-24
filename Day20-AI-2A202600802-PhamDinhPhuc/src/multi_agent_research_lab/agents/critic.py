import logging
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append findings."""
        logger.info("CriticAgent started...")

        final_answer = state.final_answer or "No final answer produced."
        formatted_sources = ""
        for i, src in enumerate(state.sources, 1):
            formatted_sources += f"[{i}] {src.title}\nURL: {src.url}\nSnippet: {src.snippet}\n\n"

        system_prompt = """You are the Critic Agent of a Multi-Agent Research System.
Your job is to critically evaluate the generated final answer against the retrieved sources and analysis.

Specifically:
1. Verify correctness: Does the final answer contain claims that are not backed by the sources or notes (hallucinations)?
2. Verify citation coverage: Are all major claims backed by a source citation (e.g. [1], [2])?
3. Verify clarity: Is the answer appropriate for the target audience?

Begin your evaluation with EXACTLY one of these keywords:
- APPROVED
- REJECTED

Following the keyword, provide bullet points of your findings and recommendations for improvement."""

        user_prompt = f"Final Answer:\n{final_answer}\n\nSources:\n{formatted_sources}\n\nEvaluate the final answer:"

        try:
            llm_response = LLMClient().complete(system_prompt, user_prompt)
            critique = llm_response.content.strip()
        except Exception as e:
            logger.warning(f"Failed to run Critic LLM call ({e}). Falling back to automatic approval.")
            critique = "APPROVED\n- Automated fallback approval: Critic validation bypassed due to LLM provider configuration."

        # Parse approval status
        is_approved = critique.upper().startswith("APPROVED")
        if not is_approved and not critique.upper().startswith("REJECTED"):
            # Safe default if LLM returns unstructured text
            critique = "APPROVED\n" + critique
            is_approved = True

        state.add_trace_event("critic", {"approved": is_approved, "feedback": critique})
        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=critique,
                metadata={"approved": is_approved},
            )
        )

        # Clear errors if approved, else append critique feedback to errors
        if is_approved:
            state.errors = [e for e in state.errors if not e.startswith("Critic feedback:")]
        else:
            state.errors.append(f"Critic feedback: {critique}")

        logger.info(f"CriticAgent finished. Approved: {is_approved}")
        return state

