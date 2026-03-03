"""
AI Event Agent — Scraper Agent

Agent 1 of 4 in the pipeline.
Uses DuckDuckGo to find AI/ML/Cloud event pages in India,
then scrapes them with Crawl4AI to extract raw markdown content.
"""

from crewai import Agent
from tools.search_tool import DuckDuckGoSearchTool
from tools.crawl_tool import Crawl4AITool
from config import get_llm_string


def create_scraper_agent() -> Agent:
    """
    Create the Scraper Agent.

    Role: Find and scrape AI/ML/Cloud event pages in India.
    Tools: DuckDuckGo search + Crawl4AI web scraper.
    Output: Raw markdown content from scraped event pages.
    """
    return Agent(
        role="AI Event Scraper",
        goal=(
            "Search the internet for AI, ML, and Cloud events happening in India. "
            "Find event listing pages, conference websites, meetup pages, and hackathon sites. "
            "Scrape each page to extract its full content as markdown."
        ),
        backstory=(
            "You are an expert web researcher specializing in finding technology events in India. "
            "You know the best sources for AI/ML events: KonfHub, Meetup.com, Eventbrite, "
            "HasGeek, DevFolio, and individual conference websites. You search systematically "
            "and scrape every relevant page you find."
        ),
        tools=[DuckDuckGoSearchTool(), Crawl4AITool()],
        llm=get_llm_string(),
        verbose=True,
        allow_delegation=False,
        max_iter=8,  # Balanced: thorough but not forever
    )
