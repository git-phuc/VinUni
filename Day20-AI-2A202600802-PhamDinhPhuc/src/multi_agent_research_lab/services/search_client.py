import logging
import requests
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client with Tavily search and mock fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.tavily_api_key

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        If a Tavily API key is provided, performs a live Tavily search.
        Otherwise, or in case of failure, falls back to a curated mock search
        to ensure the workflow runs smoothly without external credentials.
        """
        if self.api_key and self.api_key.strip() and "tvly-" in self.api_key:
            try:
                logger.info(f"Performing live Tavily search for query: {query}")
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                }
                res = requests.post("https://api.tavily.com/search", json=payload, timeout=10)
                res.raise_for_status()
                data = res.json()
                results = []
                for item in data.get("results", []):
                    results.append(
                        SourceDocument(
                            title=item.get("title", "Untitled Source"),
                            url=item.get("url"),
                            snippet=item.get("content", ""),
                        )
                    )
                if results:
                    return results[:max_results]
            except Exception as e:
                logger.warning(f"Tavily search failed (falling back to mock): {e}")

        # Mock Fallback
        logger.info(f"Using mock search fallback for query: {query}")
        query_lower = query.lower()
        if "graphrag" in query_lower or "rag" in query_lower:
            mock_data = [
                SourceDocument(
                    title="GraphRAG: Unlocking LLM Knowledge on Complex Data",
                    url="https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-knowledge-on-complex-data/",
                    snippet="Microsoft's GraphRAG uses knowledge graphs to enable LLMs to perform structured search and reasoning over large unstructured text corpora, combining community detection with LLM summarization.",
                ),
                SourceDocument(
                    title="Comparing Flat RAG, GraphRAG, and Hybrid RAG Pipelines",
                    url="https://arxiv.org/abs/2408.01234",
                    snippet="Flat RAG relies on vector similarity of text chunks, which struggles with global query types (e.g. 'summarize the dataset'). GraphRAG organizes information hierarchically into knowledge graphs, yielding significantly higher quality for multi-hop questions.",
                ),
                SourceDocument(
                    title="Vellum: Implementing Production-Grade Knowledge Graphs for RAG",
                    url="https://www.vellum.ai/blog/production-graphrag",
                    snippet="A production hybrid RAG system combines vector search and knowledge graph traversal. This results in the best performance on detailed local entity queries and global thematic prompts.",
                ),
            ]
        else:
            mock_data = [
                SourceDocument(
                    title="Anthropic: Building Effective Agents and Workflow Patterns",
                    url="https://www.anthropic.com/engineering/building-effective-agents",
                    snippet="Anthropic outlines key patterns for AI agent architectures, emphasizing the transition from single-agent LLM wrappers to multi-agent state machines, router loops, and critic validation patterns.",
                ),
                SourceDocument(
                    title="LangGraph: Orchestrating Multi-Agent State Machines",
                    url="https://langchain-ai.github.io/langgraph/concepts/multi_agent/",
                    snippet="LangGraph is a library designed to build stateful, multi-agent systems where agents coordinate using a shared State, routing messages dynamically through nodes and conditional edges.",
                ),
                SourceDocument(
                    title="OpenAI Agents: Design and Optimization Guide",
                    url="https://developers.openai.com/docs/guides/agents",
                    snippet="OpenAI details design patterns for agentic orchestration, showcasing how task decomposition, state handoffs, and validation guardrails prevent agent loops and reduce response latency.",
                ),
            ]
        return mock_data[:max_results]

