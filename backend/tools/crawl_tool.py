"""
AI Event Agent — Crawl4AI Web Scraping Tool

Wraps Crawl4AI as a CrewAI-compatible tool.
Uses asyncio.run() wrapper to bridge Crawl4AI's async API
with CrewAI's synchronous agent loop.
"""

import asyncio
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from crawl4ai import AsyncWebCrawler
from config import logger, MAX_TOKENS_PER_PAGE


class Crawl4AIInput(BaseModel):
    """Input schema for Crawl4AITool."""
    url: str = Field(..., description="The URL of the web page to scrape")


class Crawl4AITool(BaseTool):
    """
    Scrape a web page and return its content as cleaned markdown.
    Handles JS-rendered pages via headless Chromium.
    Output is truncated to MAX_TOKENS_PER_PAGE tokens.
    """

    name: str = "web_scraper"
    description: str = (
        "Scrape a web page URL and return its content as cleaned markdown text. "
        "Use this to extract event details, speaker information, and other content "
        "from event listing pages and individual event pages."
    )
    args_schema: Type[BaseModel] = Crawl4AIInput

    def _run(self, url: str) -> str:
        """
        Scrape a URL and return truncated markdown content.

        Uses asyncio.run() to bridge Crawl4AI's async API with
        CrewAI's synchronous agent loop.

        Args:
            url: The URL to scrape.

        Returns:
            Markdown content from the page, truncated to MAX_TOKENS_PER_PAGE.
        """
        try:
            logger.info("Crawl4AI scraping: %s", url)
            result = asyncio.run(self._async_scrape(url))
            return result
        except Exception as e:
            logger.error("Crawl4AI failed for %s: %s", url, str(e))
            return f"Failed to scrape {url}: {str(e)}"

    async def _async_scrape(self, url: str) -> str:
        """
        Async scraping implementation using Crawl4AI.

        Args:
            url: The URL to scrape.

        Returns:
            Truncated markdown content.
        """
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)

            if not result.success:
                logger.warning("Crawl4AI returned failure for %s", url)
                return f"Failed to scrape {url}: page load unsuccessful"

            markdown = result.markdown or ""

            # Truncate to MAX_TOKENS_PER_PAGE (rough estimate: 1 token ≈ 4 chars)
            char_limit = MAX_TOKENS_PER_PAGE * 4
            if len(markdown) > char_limit:
                markdown = markdown[:char_limit]
                markdown += "\n\n[... content truncated to fit token limit ...]"
                logger.info(
                    "Truncated content from %s to %d chars (~%d tokens)",
                    url, char_limit, MAX_TOKENS_PER_PAGE
                )

            logger.info(
                "Successfully scraped %s (%d chars)",
                url, len(markdown)
            )
            return markdown
