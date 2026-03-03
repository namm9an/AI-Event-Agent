"""
AI Event Agent — Enrichment Agent

Agent 1 of 3 in the hybrid pipeline (was Agent 2 of 4).
Takes pre-scraped markdown content and extracts structured event metadata.
No tools — pure LLM reasoning on content already fetched by Python layer.
"""

from crewai import Agent
from config import get_llm_string


def create_enrichment_agent() -> Agent:
    """
    Create the Enrichment Agent.

    Role: Extract structured event metadata from raw scraped content.
    Tools: None (all content pre-scraped by Python layer).
    Input: Raw markdown from scraper.py.
    Output: Structured event data as JSON array.
    """
    return Agent(
        role="Event Data Enricher",
        goal=(
            "Take raw markdown content from scraped event pages and extract structured "
            "event metadata. For each distinct event found, extract: name, date(s), location, city, "
            "status (upcoming/live/past), category (AI/ML/Cloud/etc.), organizer, event type "
            "(conference/meetup/webinar/hackathon/summit), description, event URL, and "
            "registration URL if available. Output as a JSON array of event objects.\n\n"
            "IMPORTANT: Extract EVERY distinct event you can find in the content. "
            "Look for event names, dates, venues, and registration links. "
            "Use empty strings for fields you cannot find — never invent data."
        ),
        backstory=(
            "You are a meticulous data analyst who specializes in extracting structured "
            "information from unstructured web content. You can identify event details even "
            "when they are buried in marketing copy, navigation menus, or nested page layouts. "
            "You always output clean, well-structured JSON. If a field is not found, you "
            "use empty strings instead of making up data."
        ),
        tools=[],
        llm=get_llm_string(),
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )
