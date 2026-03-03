"""
AI Event Agent — DuckDuckGo Search Tool

Wraps the duckduckgo-search library as a CrewAI-compatible tool
with exponential backoff for rate limiting.
"""

import time
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from duckduckgo_search import DDGS
from config import logger, DDGS_RETRY_COUNT, DDGS_BASE_DELAY


class DuckDuckGoSearchInput(BaseModel):
    """Input schema for DuckDuckGoSearchTool."""
    query: str = Field(..., description="The search query string")


class DuckDuckGoSearchTool(BaseTool):


    name: str = "web_search"
    description: str = (
        "Search the web for information about AI, ML, and Cloud events in India. "
        "Returns a list of search results with titles, URLs, and snippets."
    )
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput

    def _run(self, query: str) -> str:
        """
        Execute a DuckDuckGo search with exponential backoff on rate limiting.

        Args:
            query: The search query string.

        Returns:
            Formatted string of search results (title, URL, snippet).
        """
        for attempt in range(DDGS_RETRY_COUNT):
            try:
                logger.info("DuckDuckGo search (attempt %d): '%s'", attempt + 1, query)

                with DDGS() as ddgs:
                    results = list(ddgs.text(query, region="in-en", max_results=10))

                if not results:
                    logger.warning("No results for query: '%s'", query)
                    return "No results found."

                # Format results as readable text
                formatted = []
                for i, r in enumerate(results, 1):
                    formatted.append(
                        f"{i}. {r.get('title', 'No title')}\n"
                        f"   URL: {r.get('href', 'No URL')}\n"
                        f"   {r.get('body', 'No description')}\n"
                    )

                output = "\n".join(formatted)
                logger.info("Search returned %d results for '%s'", len(results), query)
                return output

            except Exception as e:
                delay = DDGS_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "DuckDuckGo search failed (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, DDGS_RETRY_COUNT, str(e), delay
                )
                if attempt < DDGS_RETRY_COUNT - 1:
                    time.sleep(delay)

        logger.error("DuckDuckGo search failed after %d attempts for '%s'", DDGS_RETRY_COUNT, query)
        return "Search failed after retries. Skipping."
