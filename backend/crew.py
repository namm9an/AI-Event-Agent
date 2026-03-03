"""
AI Event Agent — Hybrid Pipeline

Two-phase architecture:
  Phase 1 (Python): DuckDuckGo search + Crawl4AI scrape (deterministic)
  Phase 2 (CrewAI): Enrichment → Speaker → Formatter agents (LLM reasoning)

Saves results to SQLite and tracks each run in scrape_runs.
"""

import json
import uuid
from datetime import datetime

from crewai import Crew, Task, Process
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from config import logger
from scraper import run_scraping_pipeline
from agents.enrichment_agent import create_enrichment_agent
from agents.speaker_agent import create_speaker_agent
from agents.formatter_agent import create_formatter_agent
from db.database import SessionLocal
from db.models import Event, ScrapeRun, SearchQuery, Speaker


def _build_scraped_content_text(
    event_content: dict[str, str],
    speaker_content: dict[str, str],
) -> tuple[str, str]:
    """
    Build formatted text blocks from scraped content for LLM consumption.

    Returns:
        (event_text, speaker_text) — formatted strings with URL headers.
    """
    # Build event content text
    event_parts = []
    for url, markdown in event_content.items():
        event_parts.append(f"=== PAGE: {url} ===\n{markdown}\n")
    event_text = "\n".join(event_parts)

    # Build speaker content text
    speaker_parts = []
    for url, markdown in speaker_content.items():
        speaker_parts.append(f"=== SPEAKER PAGE: {url} ===\n{markdown}\n")
    speaker_text = "\n".join(speaker_parts) if speaker_parts else "No additional speaker pages found."

    return event_text, speaker_text


def _parse_events_json(raw_output: str) -> list[dict]:
    """
    Parse the formatter agent's JSON output into a list of event dicts.
    Handles cases where the output has markdown code blocks or extra text.
    """
    text = raw_output.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    # Try to find JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    try:
        events = json.loads(text)
        if isinstance(events, list):
            return events
        elif isinstance(events, dict):
            return [events]
        else:
            logger.warning("Parsed JSON is not a list or dict: %s", type(events))
            return []
    except json.JSONDecodeError as e:
        logger.error("Failed to parse events JSON: %s\nRaw output: %s", e, text[:500])
        return []


def _is_duplicate(event_data: dict, db: Session) -> Event | None:
    """
    Check if an event already exists in the database.
    First: exact URL match.
    Second: fuzzy name + date match (threshold 85%).
    """
    url = event_data.get("url", "")

    if url:
        existing = db.query(Event).filter(Event.url == url).first()
        if existing:
            return existing

    name = event_data.get("name", "")
    date_text = event_data.get("date_text", "")

    if name:
        all_events = db.query(Event).all()
        for existing in all_events:
            name_score = fuzz.ratio(name.lower(), existing.name.lower())
            date_score = fuzz.ratio(date_text.lower(), (existing.date_text or "").lower())

            if name_score >= 85 and (not date_text or date_score >= 85):
                logger.info(
                    "Fuzzy duplicate found: '%s' ≈ '%s' (name: %d%%, date: %d%%)",
                    name, existing.name, name_score, date_score
                )
                return existing

    return None


def _save_events(events_data: list[dict], scrape_run: ScrapeRun, db: Session) -> dict:
    """
    Save parsed events to the database with deduplication.
    Returns stats dict: {new, updated, speakers_found}.
    """
    stats = {"new": 0, "updated": 0, "speakers_found": 0}

    for event_data in events_data:
        name = event_data.get("name", "").strip()
        url = event_data.get("url", "").strip()

        if not name:
            logger.warning("Skipping event with no name: %s", json.dumps(event_data)[:300])
            continue

        if not url:
            url = f"https://event-agent.local/{name.lower().replace(' ', '-')}"
            event_data["url"] = url
            logger.info("Generated placeholder URL for event '%s': %s", name, url)

        existing = _is_duplicate(event_data, db)

        if existing:
            existing.description = event_data.get("description", existing.description)
            existing.date_text = event_data.get("date_text", existing.date_text)
            existing.location = event_data.get("location", existing.location)
            existing.city = event_data.get("city", existing.city)
            existing.status = event_data.get("status", existing.status)
            existing.category = event_data.get("category", existing.category)
            existing.organizer = event_data.get("organizer", existing.organizer)
            existing.event_type = event_data.get("event_type", existing.event_type)
            existing.registration_url = event_data.get("registration_url", existing.registration_url)
            existing.image_url = event_data.get("image_url", existing.image_url)
            existing.last_scraped_at = datetime.utcnow()
            # Replace speaker rows on update to avoid duplicate accumulation.
            existing.speakers.clear()
            stats["updated"] += 1
            event_id = existing.id
            logger.info("Updated existing event: %s", existing.name)
        else:
            event_id = str(uuid.uuid4())
            event = Event(
                id=event_id,
                name=name,
                description=event_data.get("description", ""),
                date_text=event_data.get("date_text", ""),
                location=event_data.get("location", ""),
                city=event_data.get("city", ""),
                status=event_data.get("status", "Unknown"),
                category=event_data.get("category", []),
                url=url,
                organizer=event_data.get("organizer", ""),
                event_type=event_data.get("event_type", ""),
                registration_url=event_data.get("registration_url", ""),
                image_url=event_data.get("image_url", ""),
                scraped_at=datetime.utcnow(),
                last_scraped_at=datetime.utcnow(),
            )
            db.add(event)
            stats["new"] += 1
            logger.info("Created new event: %s", name)

        # Handle speakers
        speakers_data = event_data.get("speakers", [])
        for speaker_data in speakers_data[:5]:  # Max 5 per event
            if not speaker_data.get("name"):
                continue

            speaker = Speaker(
                id=str(uuid.uuid4()),
                event_id=event_id,
                name=speaker_data.get("name", ""),
                designation=speaker_data.get("designation", ""),
                company=speaker_data.get("company", ""),
                talk_title=speaker_data.get("talk_title", ""),
                talk_summary=speaker_data.get("talk_summary", ""),
                linkedin_url=speaker_data.get("linkedin_url", ""),
                linkedin_bio=speaker_data.get("linkedin_bio", ""),
                topic_links=speaker_data.get("topic_links", []),
                topic_category=speaker_data.get("topic_category", ""),
                previous_talks=speaker_data.get("previous_talks", []),
                wikipedia_url=speaker_data.get("wikipedia_url", ""),
            )
            db.add(speaker)
            stats["speakers_found"] += 1

    db.commit()
    return stats


def _load_active_queries(db: Session) -> list[str]:
    """Get active admin-managed queries ordered by priority."""
    rows = (
        db.query(SearchQuery)
        .filter(SearchQuery.is_active == True)  # noqa: E712
        .order_by(SearchQuery.priority.asc(), SearchQuery.created_at.asc())
        .all()
    )
    queries = [r.query for r in rows if r.query]
    return queries


def run_crew(queries: list[str] | None = None) -> dict:
    """
    Execute the hybrid pipeline.

    Phase 1: Python scraping (deterministic search + scrape)
    Phase 2: CrewAI agents (LLM enrichment + speaker extraction + formatting)
    Phase 3: Save to database with deduplication

    Returns:
        Dictionary with scrape run results.
    """
    db = SessionLocal()
    start_time = datetime.utcnow()

    run_id = str(uuid.uuid4())
    scrape_run = ScrapeRun(
        id=run_id,
        started_at=start_time,
        status="running",
    )
    db.add(scrape_run)
    db.commit()

    errors: list[str] = []

    try:
        # ==========================================
        # PHASE 1: Python Scraping (deterministic)
        # ==========================================
        logger.info("=" * 60)
        logger.info("PHASE 1: Python Scraping Layer")
        logger.info("=" * 60)

        if not queries:
            queries = _load_active_queries(db)

        scrape_result = run_scraping_pipeline(queries=queries)
        errors.extend(scrape_result["errors"])

        event_content = scrape_result["event_content"]
        speaker_content = scrape_result["speaker_content"]

        if not event_content:
            raise RuntimeError("No event pages were scraped — cannot proceed to extraction")

        logger.info(
            "Phase 1 complete: %d event pages, %d speaker pages scraped",
            len(event_content), len(speaker_content)
        )

        # Build text for LLM consumption
        event_text, speaker_text = _build_scraped_content_text(event_content, speaker_content)

        # Truncate if too large for LLM context
        max_chars = 40000  # ~10K tokens — balanced for Nemotron (large context but 3B active params)
        if len(event_text) > max_chars:
            event_text = event_text[:max_chars] + "\n\n[... content truncated ...]"
            logger.info("Event text truncated to %d chars", max_chars)

        if len(speaker_text) > max_chars:
            speaker_text = speaker_text[:max_chars] + "\n\n[... content truncated ...]"
            logger.info("Speaker text truncated to %d chars", max_chars)

        # ==========================================
        # PHASE 2: CrewAI Agents (LLM reasoning)
        # ==========================================
        logger.info("=" * 60)
        logger.info("PHASE 2: CrewAI LLM Extraction")
        logger.info("=" * 60)

        enricher = create_enrichment_agent()
        speaker_finder = create_speaker_agent()
        formatter = create_formatter_agent()

        enrich_task = Task(
            description=(
                "Below is raw markdown content scraped from multiple event pages. "
                "Extract ALL distinct AI, ML, Cloud, and Data Science events you can find.\n\n"
                "For each event, extract:\n"
                "- name, description, date_text (raw date string), location, city\n"
                "- status (Upcoming/Live/Past/Unknown)\n"
                "- category (array: AI, ML, Cloud, Data Science, etc.)\n"
                "- url (the page URL from the === PAGE: URL === header)\n"
                "- organizer, event_type, registration_url\n\n"
                "Output as a JSON array. Use empty strings for fields not found.\n\n"
                "SCRAPED CONTENT:\n\n"
                f"{event_text}"
            ),
            expected_output=(
                "A JSON array of event objects with all metadata fields. "
                "Each event must have at minimum: name and url."
            ),
            agent=enricher,
        )

        speaker_task = Task(
            description=(
                "Below is additional content from speaker-related pages. "
                "For each event from the previous task, find speakers in this content "
                "AND in the original event page content.\n\n"
                "For each speaker, extract: name, designation, company, talk_title, talk_summary.\n"
                "Additionally extract when available: topic_category, topic_links (array), "
                "linkedin_url, linkedin_bio, wikipedia_url, previous_talks (array).\n"
                "Maximum 5 speakers per event. Return empty speakers array if none found.\n"
                "Do NOT fabricate speaker information.\n\n"
                "SPEAKER PAGE CONTENT:\n\n"
                f"{speaker_text}"
            ),
            expected_output=(
                "The same event JSON array with a 'speakers' array added to each event. "
                "Each speaker: {name, designation, company, talk_title, talk_summary}."
            ),
            agent=speaker_finder,
        )

        format_task = Task(
            description=(
                "Take the event data with speakers and produce the final clean JSON output. "
                "Validate all fields, remove any duplicate events (same name + similar date), "
                "normalize city names (Bengaluru → Bangalore), and ensure consistent formatting.\n\n"
                "Output MUST be a valid JSON array. No markdown code blocks, no extra text — "
                "just the raw JSON array starting with [ and ending with ]."
            ),
            expected_output=(
                "A valid JSON array of event objects, each with all required fields "
                "and a speakers sub-array. Pure JSON, no code blocks or extra text."
            ),
            agent=formatter,
        )

        crew = Crew(
            agents=[enricher, speaker_finder, formatter],
            tasks=[enrich_task, speaker_task, format_task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Starting CrewAI extraction pipeline (run: %s)", run_id)
        result = crew.kickoff()

        # ==========================================
        # PHASE 3: Parse & Save to Database
        # ==========================================
        logger.info("=" * 60)
        logger.info("PHASE 3: Parsing & Saving to Database")
        logger.info("=" * 60)

        raw_output = str(result)
        events_data = _parse_events_json(raw_output)

        logger.info("Pipeline returned %d events", len(events_data))

        for i, evt in enumerate(events_data):
            logger.info(
                "Event %d: name='%s', url='%s'",
                i, evt.get("name", "MISSING"), evt.get("url", "MISSING")
            )

        stats = _save_events(events_data, scrape_run, db)

        scrape_run.status = "completed"
        scrape_run.completed_at = datetime.utcnow()
        scrape_run.events_found = len(events_data)
        scrape_run.events_new = stats["new"]
        scrape_run.events_updated = stats["updated"]
        scrape_run.speakers_found = stats["speakers_found"]
        scrape_run.errors = errors
        scrape_run.urls_scraped = list(event_content.keys())
        db.commit()

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            "Pipeline completed in %.1fs — %d events (%d new, %d updated), %d speakers",
            duration, len(events_data), stats["new"], stats["updated"], stats["speakers_found"]
        )

        return {
            "run_id": run_id,
            "status": "completed",
            "events_found": len(events_data),
            "events_new": stats["new"],
            "events_updated": stats["updated"],
            "speakers_found": stats["speakers_found"],
            "errors": errors,
            "duration_seconds": round(duration, 1),
        }

    except Exception as e:
        error_msg = str(e)
        errors.append(error_msg)
        logger.error("Pipeline failed: %s", error_msg)

        scrape_run.status = "failed"
        scrape_run.completed_at = datetime.utcnow()
        scrape_run.errors = errors
        db.commit()

        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "run_id": run_id,
            "status": "failed",
            "events_found": 0,
            "events_new": 0,
            "events_updated": 0,
            "speakers_found": 0,
            "errors": errors,
            "duration_seconds": round(duration, 1),
        }

    finally:
        db.close()
