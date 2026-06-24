import logging
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""
        logger.info("ResearcherAgent started...")

        # Step 1: Generate search query using LLM
        search_query = state.request.query
        system_query_prompt = f"""You are the Researcher Agent. The user's query is: "{state.request.query}".
Generate a single concise search query to search the web for relevant research papers, documentation, or articles.
Respond with ONLY the search query text. Do not include quotes, markdown formatting, or explanations."""

        user_query_prompt = f"Original query: {state.request.query}\nGenerate search query:"

        try:
            llm_response = LLMClient().complete(system_query_prompt, user_query_prompt)
            generated = llm_response.content.strip().replace('"', '')
            if generated:
                search_query = generated
        except Exception as e:
            logger.warning(f"Failed to generate search query using LLM ({e}). Defaulting to original user query.")

        # Step 2: Perform search
        logger.info(f"Researcher using search query: '{search_query}'")
        try:
            new_sources = SearchClient().search(search_query, max_results=state.request.max_sources)
        except Exception as e:
            logger.error(f"Search client execution failed: {e}")
            new_sources = []

        # Deduplicate and add to state
        existing_urls = {s.url for s in state.sources if s.url}
        added_count = 0
        for src in new_sources:
            if not src.url or src.url not in existing_urls:
                state.sources.append(src)
                if src.url:
                    existing_urls.add(src.url)
                added_count += 1

        # Step 3: Compile research notes
        formatted_sources = ""
        for i, src in enumerate(state.sources, 1):
            formatted_sources += f"[{i}] {src.title}\nURL: {src.url}\nSnippet: {src.snippet}\n\n"

        system_notes_prompt = f"""You are the Researcher Agent. The user query is: "{state.request.query}"
Here are the search results:
{formatted_sources}

Compile comprehensive, structured, and factual research notes relevant to the user query.
Organize notes by themes or key findings. Always reference the sources using citation numbers (e.g., [1], [2]) when mentioning facts."""

        user_notes_prompt = "Compile research notes based on the provided search results."

        try:
            llm_response = LLMClient().complete(system_notes_prompt, user_notes_prompt)
            notes = llm_response.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate research notes using LLM ({e}). Falling back to simple snippet concatenation.")
            # Fallback note compiling
            if state.sources:
                notes = "### Raw Research Notes (Fallback Summary)\n\n"
                for i, src in enumerate(state.sources, 1):
                    notes += f"- **{src.title}** (Source: {src.url or 'N/A'}):\n  {src.snippet}\n\n"
            else:
                notes = f"No search results found for query: '{search_query}'."

        state.research_notes = notes
        state.add_trace_event("research", {"search_query": search_query, "sources_added": added_count})
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=notes,
                metadata={"search_query": search_query, "sources_added": added_count},
            )
        )

        logger.info(f"ResearcherAgent finished. Compiled {len(notes)} characters of notes.")
        return state

