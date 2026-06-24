import logging
from langgraph.graph import END, START, StateGraph
from multi_agent_research_lab.agents import (
    AnalystAgent,
    CriticAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


def run_supervisor(state: ResearchState) -> ResearchState:
    logger.info("--- RUNNING SUPERVISOR NODE ---")
    return SupervisorAgent().run(state)


def run_researcher(state: ResearchState) -> ResearchState:
    logger.info("--- RUNNING RESEARCHER NODE ---")
    return ResearcherAgent().run(state)


def run_analyst(state: ResearchState) -> ResearchState:
    logger.info("--- RUNNING ANALYST NODE ---")
    return AnalystAgent().run(state)


def run_writer(state: ResearchState) -> ResearchState:
    logger.info("--- RUNNING WRITER NODE ---")
    return WriterAgent().run(state)


def run_critic(state: ResearchState) -> ResearchState:
    logger.info("--- RUNNING CRITIC NODE ---")
    return CriticAgent().run(state)


def route_next(state: ResearchState) -> str:
    if not state.route_history:
        return "supervisor"
    return state.route_history[-1]



class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph."""

    def build(self) -> object:
        """Create a LangGraph graph."""
        builder = StateGraph(ResearchState)

        # Add nodes
        builder.add_node("supervisor", run_supervisor)
        builder.add_node("researcher", run_researcher)
        builder.add_node("analyst", run_analyst)
        builder.add_node("writer", run_writer)
        builder.add_node("critic", run_critic)

        # Add edges
        builder.add_edge(START, "supervisor")

        builder.add_conditional_edges(
            "supervisor",
            route_next,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )

        builder.add_edge("researcher", "supervisor")
        builder.add_edge("analyst", "supervisor")
        builder.add_edge("writer", "critic")
        builder.add_edge("critic", "supervisor")

        return builder.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""
        compiled_graph = self.build()
        logger.info("Invoking compiled LangGraph workflow...")
        result = compiled_graph.invoke(state)

        if isinstance(result, dict):
            return ResearchState(**result)
        return result

