import logging
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""
        settings = get_settings()

        # Guardrail: Enforce max iterations
        if state.iteration >= settings.max_iterations:
            next_step = "done" if state.final_answer else "writer"
            logger.info(f"Max iterations reached ({state.iteration}). Forcing route: {next_step}")
            state.record_route(next_step)
            state.add_trace_event("route", {"next": next_step, "reason": "max_iterations"})
            return state

        # Determine last critic feedback if any
        critic_feedback = "None"
        critic_results = [r for r in state.agent_results if r.agent == AgentName.CRITIC]
        if critic_results:
            critic_feedback = critic_results[-1].content

        system_prompt = f"""You are the Supervisor Agent of a Multi-Agent Research System.
Your task is to orchestrate a research workflow to answer the user query: "{state.request.query}"

Workflow nodes:
1. "researcher": Performs web search, collects documents, writes raw research notes. Choose this first if we don't have sources or research notes, or if the critic rejected the current response due to missing facts.
2. "analyst": Analyzes raw research notes, extracts key claims, structures insights. Choose this if we have research notes but no analysis notes yet, or if research notes have changed.
3. "writer": Synthesizes the final answer using the research and analysis notes. Choose this after analysis notes are ready, or if the writer needs to refine the answer.
4. "done": Only choose this if the critic has approved the final answer or if the final answer is already high-quality and complete.

Your decision should be based on the current state:
- Route history so far: {state.route_history}
- Researcher notes present: {state.research_notes is not None}
- Analyst notes present: {state.analysis_notes is not None}
- Final answer present: {state.final_answer is not None}
- Latest Critic feedback: {critic_feedback}

Respond with exactly one word from this list: researcher, analyst, writer, done. No markdown, no punctuation. Just the word."""

        user_prompt = f"""State of the workflow:
Query: {state.request.query}
Iteration: {state.iteration}
Route history: {state.route_history}
Researcher notes present: {state.research_notes is not None}
Analyst notes present: {state.analysis_notes is not None}
Final answer present: {state.final_answer is not None}
Errors/Critic reports: {state.errors}

Next step:"""

        next_step = None
        try:
            llm_response = LLMClient().complete(system_prompt, user_prompt)
            next_step = llm_response.content.strip().lower()
        except Exception as e:
            logger.warning(f"Supervisor LLM call failed or key missing ({e}). Falling back to deterministic router.")

        # Validate or fallback
        if next_step not in ["researcher", "analyst", "writer", "done"]:
            if not state.research_notes:
                next_step = "researcher"
            elif not state.analysis_notes:
                next_step = "analyst"
            elif not state.final_answer:
                next_step = "writer"
            else:
                next_step = "done"
            reason = "fallback"
        else:
            reason = "llm_decision"

        logger.info(f"Supervisor decided next step: {next_step} (via {reason})")
        state.record_route(next_step)
        state.add_trace_event("route", {"next": next_step, "reason": reason})

        # Append Supervisor's result to state
        state.agent_results.append(
            AgentResult(
                agent=AgentName.SUPERVISOR,
                content=f"Routed to: {next_step}",
                metadata={"reason": reason, "iteration": state.iteration},
            )
        )

        return state

