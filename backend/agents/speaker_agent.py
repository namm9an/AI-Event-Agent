"""
AI Event Agent — Speaker Identification Agent

Agent 2 of 3 in the hybrid pipeline (was Agent 3 of 4).
Takes enriched event data + pre-scraped speaker page content
and identifies speakers per event.
No tools — pure LLM reasoning on content already fetched by Python layer.
"""

from crewai import Agent
from config import get_llm_string


def create_speaker_agent() -> Agent:
    """
    Create the Speaker Identification Agent.

    Role: Find speakers for each event from pre-scraped content.
    Tools: None (speaker pages already scraped by Python layer).
    Input: Enriched event data + all scraped content (event pages + speaker search pages).
    Output: Events with speaker lists.
    """
    return Agent(
        role="Speaker Researcher",
        goal=(
            "For each event in the input data, identify speakers and their details. "
            "You have been given pre-scraped content from event pages AND from speaker-specific "
            "search result pages. Look through ALL the content to find speaker information.\n\n"
            "For each speaker, extract: name, designation/title, company/organization, "
            "talk title, and a brief summary of what they spoke about.\n"
            "Also include if available: topic category, topic links, LinkedIn URL, "
            "LinkedIn bio snippet, Wikipedia URL, and previous talks list.\n\n"
            "Limit to a maximum of 5 speakers per event. "
            "If no speakers are found for an event, return an empty speakers array — "
            "do NOT make up names or details."
        ),
        backstory=(
            "You are a conference researcher who is an expert at identifying speakers at "
            "technology events. You can find speaker details from event agendas, speaker "
            "directories, session listings, and news articles. You know that Indian tech "
            "events often feature speakers from companies like Google, Microsoft, Amazon, "
            "Infosys, TCS, Wipro, and Indian AI startups. You never fabricate speaker "
            "information — if you can't find details, you leave fields empty."
        ),
        tools=[],
        llm=get_llm_string(),
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )
