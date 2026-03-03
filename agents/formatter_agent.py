"""
AI Event Agent — Formatter Agent

Agent 3 of 3 in the hybrid pipeline (was Agent 4 of 4).
Takes event data with speakers and outputs clean, validated JSON
ready for database insertion.
No tools — pure LLM formatting.
"""

from crewai import Agent
from config import get_llm_string


def create_formatter_agent() -> Agent:
    """
    Create the Formatter Agent.

    Role: Validate and format event data into clean JSON for database storage.
    Tools: None (pure LLM formatting).
    Input: Event data with speakers from Speaker Agent.
    Output: Final validated JSON array of events with speakers.
    """
    return Agent(
        role="Data Formatter & Validator",
        goal=(
            "Take the event data with speakers and produce a final, clean JSON output. "
            "Validate all fields, remove duplicates, normalize categories, and ensure "
            "consistent formatting. Output MUST be a valid JSON array of event objects.\n\n"
            "Each event object must have these fields:\n"
            "- name (string, required)\n"
            "- description (string)\n"
            "- date_text (string, raw date as found)\n"
            "- location (string, full venue)\n"
            "- city (string, e.g. 'Bangalore', 'Mumbai')\n"
            "- status (string: 'Upcoming', 'Live', 'Past', or 'Unknown')\n"
            "- category (array of strings: 'AI', 'ML', 'Cloud', 'Data Science', etc.)\n"
            "- url (string, event page URL, required)\n"
            "- organizer (string)\n"
            "- event_type (string: 'Conference', 'Meetup', 'Webinar', 'Hackathon', 'Summit')\n"
            "- registration_url (string)\n"
            "- speakers (array of speaker objects)\n\n"
            "Each speaker object must have:\n"
            "- name (string, required)\n"
            "- designation (string)\n"
            "- company (string)\n"
            "- talk_title (string)\n"
            "- talk_summary (string)\n"
            "- topic_category (string)\n"
            "- topic_links (array of strings)\n"
            "- linkedin_url (string)\n"
            "- linkedin_bio (string)\n"
            "- wikipedia_url (string)\n"
            "- previous_talks (array of strings)\n\n"
            "IMPORTANT: Output ONLY the JSON array. No markdown code blocks, no extra text, "
            "no explanations. Just the raw JSON array starting with [ and ending with ]."
        ),
        backstory=(
            "You are a data quality engineer who ensures all data meets strict formatting "
            "standards before being stored in a database. You catch inconsistencies, remove "
            "duplicate events (same name + similar date = duplicate), normalize city names "
            "(Bengaluru → Bangalore), and validate that all required fields are present. "
            "You always output valid, parseable JSON."
        ),
        tools=[],
        llm=get_llm_string(),
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )
