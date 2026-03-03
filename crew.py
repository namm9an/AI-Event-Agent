"""
AI Event Agent — Hybrid Pipeline

Two-phase architecture:
  Phase 1 (Python): DuckDuckGo search + Crawl4AI scrape (deterministic)
  Phase 2 (Direct LLM): Enrichment → Speaker → Formatter calls (no CrewAI ReAct)

Saves results to SQLite and tracks each run in scrape_runs.

Note: CrewAI was removed because its ReAct parser cannot handle Nemotron's
<think>...</think> output format. Direct ChatOpenAI calls give us full control
over response parsing.
"""

import json
import re
import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from config import get_chat_llm, logger
from scraper import run_scraping_pipeline
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


def _strip_thinking_tags(text: str) -> str:
    """
    Strip Nemotron/DeepSeek-style <think>...</think> reasoning blocks.
    Also handles variations: <thinking>, </think>, etc.
    """
    # Remove full <think>...</think> blocks (possibly multiline)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove any dangling opening/closing tags
    text = re.sub(r"</?think[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?thinking[^>]*>", "", text, flags=re.IGNORECASE)
    return text.strip()


def _extract_balanced_segment(text: str, open_char: str, close_char: str) -> str | None:
    """
    Extract first balanced JSON segment, ignoring braces inside strings.
    Example: finds first complete [...] or {...} block.
    """
    start = None
    depth = 0
    in_string = False
    escaped = False

    for idx, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = in_string
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == open_char:
            if depth == 0:
                start = idx
            depth += 1
        elif ch == close_char and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                return text[start:idx + 1]
    return None


def _extract_top_level_json_objects(text: str) -> list[str]:
    """
    Extract top-level JSON object substrings from a text blob using
    string-aware balanced brace scanning.
    """
    objects: list[str] = []
    depth = 0
    start = None
    in_string = False
    escaped = False

    for idx, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = in_string
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(text[start:idx + 1])
                start = None

    return objects


def _parse_events_json(raw_output: str) -> list[dict]:
    """
    Parse LLM JSON output into a list of event dicts.

    Handles:
    - Nemotron <think>...</think> reasoning blocks
    - Markdown code fences (```json ... ```)
    - Extra text before/after the JSON array
    - Malformed JSON with trailing commas
    """
    if not raw_output:
        return []

    # Step 1: Strip thinking tags
    text = _strip_thinking_tags(raw_output)

    # Step 2: Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Step 3: Find balanced JSON array/object segments
    array_segment = _extract_balanced_segment(text, "[", "]")
    if array_segment:
        text = array_segment
    else:
        # Try wrapped object: {"events": [...]}
        object_segment = _extract_balanced_segment(text, "{", "}")
        if object_segment:
            try:
                obj = json.loads(object_segment)
                for val in obj.values():
                    if isinstance(val, list):
                        return [e for e in val if isinstance(e, dict)]
            except json.JSONDecodeError:
                pass
        logger.error("No JSON array found in output:\n%s", raw_output[:800])
        return []

    # Step 4: Try direct parse
    try:
        events = json.loads(text)
        if isinstance(events, list):
            return [e for e in events if isinstance(e, dict)]
        elif isinstance(events, dict):
            return [events]
        return []
    except json.JSONDecodeError:
        pass

    # Step 5: Remove trailing commas (common LLM mistake) and retry
    text_fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        events = json.loads(text_fixed)
        if isinstance(events, list):
            logger.info("Parsed JSON after trailing-comma fix")
            return [e for e in events if isinstance(e, dict)]
    except json.JSONDecodeError:
        pass

    # Step 6: Recover individual objects via balanced-brace extraction.
    recovered = []
    for obj_str in _extract_top_level_json_objects(text):
        try:
            obj = json.loads(obj_str)
            if isinstance(obj, dict) and obj.get("name"):
                recovered.append(obj)
        except json.JSONDecodeError:
            continue

    if recovered:
        logger.warning("JSON array parse failed; recovered %d objects via brace-matching", len(recovered))
        return recovered

    logger.error("All JSON parse strategies failed.\nRaw output (first 800 chars):\n%s", raw_output[:800])
    return []


def _is_duplicate(
    event_data: dict,
    existing_events: list[Event],
    existing_by_url: dict[str, Event],
) -> Event | None:
    """
    Check if an event already exists in the database.
    First: exact URL match (indexed).
    Second: fuzzy name + date match (threshold 85%).

    """
    url = str(event_data.get("url", "") or "").strip()

    if url and url in existing_by_url:
        return existing_by_url[url]

    name = str(event_data.get("name", "") or "").strip()
    date_text = str(event_data.get("date_text", "") or "").strip()

    if name:
        for existing in existing_events:
            name_score = fuzz.ratio(name.lower(), existing.name.lower())
            date_score = fuzz.ratio(date_text.lower(), (existing.date_text or "").lower())

            if name_score >= 85 and (not date_text or date_score >= 85):
                logger.info(
                    "Fuzzy duplicate found: '%s' ≈ '%s' (name: %d%%, date: %d%%)",
                    name, existing.name, name_score, date_score
                )
                return existing

    return None


def _save_events(events_data: list[dict], db: Session) -> dict:
    """
    Save parsed events to the database with per-event error isolation.
    Returns stats dict: {new, updated, speakers_found, skipped}.

    Each event is flushed individually so a single bad event doesn't
    abort the entire batch.
    """
    stats = {"new": 0, "updated": 0, "speakers_found": 0, "skipped": 0}

    # Load all existing events once to avoid N full-table scans in _is_duplicate
    existing_events = db.query(Event).all()
    existing_by_url: dict[str, Event] = {event.url: event for event in existing_events if event.url}
    used_placeholder_urls: set[str] = set(existing_by_url.keys())

    for event_data in events_data:
        name = str(event_data.get("name", "") or "").strip()
        url = str(event_data.get("url", "") or "").strip()

        if not name:
            logger.warning("Skipping event with no name: %s", json.dumps(event_data)[:300])
            stats["skipped"] += 1
            continue

        if not url:
            slug = re.sub(r"[^a-z0-9-]", "-", name.lower())
            slug = re.sub(r"-+", "-", slug).strip("-")
            if not slug:
                slug = f"event-{uuid.uuid4().hex[:8]}"
            # Deduplicate placeholder URLs within the same batch
            candidate = f"https://event-agent.local/{slug}"
            suffix = 0
            while candidate in used_placeholder_urls or candidate in existing_by_url:
                suffix += 1
                candidate = f"https://event-agent.local/{slug}-{suffix}"
            url = candidate
            used_placeholder_urls.add(url)
            event_data["url"] = url
            logger.info("Generated placeholder URL for '%s': %s", name, url)

        try:
            with db.begin_nested():
                existing = _is_duplicate(
                    event_data,
                    existing_events=existing_events,
                    existing_by_url=existing_by_url,
                )

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
                    # Clear speakers and flush deletes before inserting refreshed rows.
                    existing.speakers.clear()
                    db.flush()
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
                    db.flush()
                    existing_events.append(event)
                    existing_by_url[url] = event
                    stats["new"] += 1
                    logger.info("Created new event: %s", name)

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

                db.flush()

        except Exception as exc:
            logger.warning("Skipping event '%s' due to error: %s", name, exc)
            stats["skipped"] += 1

    try:
        db.commit()
    except Exception as exc:
        logger.error("Final commit failed: %s", exc)
        db.rollback()

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
    Phase 2: Direct LLM calls (enrichment + speaker extraction + formatting)
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

        # Record scraped URLs now (before LLM phase) so they're available even if LLM fails
        scrape_run.urls_scraped = list(event_content.keys())
        db.commit()

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
        # PHASE 2: Direct LLM Calls (no CrewAI ReAct)
        # ==========================================
        # We call the LLM directly to avoid CrewAI's ReAct parser, which
        # cannot handle Nemotron's <think>...</think> output format.
        # ==========================================
        logger.info("=" * 60)
        logger.info("PHASE 2: Direct LLM Extraction")
        logger.info("=" * 60)

        llm = get_chat_llm(temperature=0.1, max_tokens=8192)

        # --- Step 2a: Event Enrichment ---
        logger.info("Step 2a: Extracting event metadata...")
        enrich_prompt = (
            "You are an event data extraction assistant. Extract ALL distinct AI, ML, Cloud, "
            "and Data Science events from the scraped content below.\n\n"
            "For each event output a JSON object with these fields:\n"
            "  name (string, required)\n"
            "  description (string)\n"
            "  date_text (string, raw date as found on page)\n"
            "  location (string, full venue address)\n"
            "  city (string, e.g. Bangalore, Mumbai, Delhi)\n"
            "  status (string: Upcoming | Live | Past | Unknown)\n"
            "  category (array of strings: AI, ML, Cloud, Data Science, etc.)\n"
            "  url (string, from the === PAGE: URL === header above the content)\n"
            "  organizer (string)\n"
            "  event_type (string: Conference | Meetup | Webinar | Hackathon | Summit)\n"
            "  registration_url (string)\n\n"
            "Rules:\n"
            "- Output ONLY a valid JSON array. No markdown, no explanation, no code blocks.\n"
            "- Use empty string for fields not found. Never invent data.\n"
            "- Extract EVERY distinct event you can find.\n\n"
            "SCRAPED CONTENT:\n\n"
            f"{event_text}"
        )
        enrich_response = llm.invoke([
            {"role": "system", "content": "You are a precise JSON extraction assistant. Output only valid JSON arrays."},
            {"role": "user", "content": enrich_prompt},
        ])
        enrich_raw = enrich_response.content if hasattr(enrich_response, "content") else str(enrich_response)
        logger.info("Enrichment response length: %d chars", len(enrich_raw))

        events_with_meta = _parse_events_json(enrich_raw)
        logger.info("Step 2a extracted %d events", len(events_with_meta))

        if not events_with_meta:
            logger.warning("No events from enrichment step — pipeline may still save 0 events")

        # --- Step 2b: Speaker Extraction ---
        logger.info("Step 2b: Extracting speakers...")
        events_json_str = json.dumps(events_with_meta, indent=2)
        speaker_prompt = (
            "You are a speaker identification assistant. You have event data and speaker page content.\n\n"
            "For each event in the JSON below, find speakers mentioned in the SPEAKER PAGE CONTENT "
            "or in the original event data. Add a 'speakers' array to each event object.\n\n"
            "Each speaker object must have:\n"
            "  name (string, required)\n"
            "  designation (string, job title)\n"
            "  company (string)\n"
            "  talk_title (string)\n"
            "  talk_summary (string)\n"
            "  topic_category (string, e.g. AI, ML, Cloud)\n"
            "  topic_links (array of strings, URLs to papers/projects)\n"
            "  linkedin_url (string)\n"
            "  linkedin_bio (string)\n"
            "  wikipedia_url (string)\n"
            "  previous_talks (array of strings)\n\n"
            "Rules:\n"
            "- Max 5 speakers per event.\n"
            "- If no speakers found, use empty array [].\n"
            "- NEVER fabricate speaker names or details.\n"
            "- Output ONLY the updated JSON array. No markdown, no explanation.\n\n"
            f"CURRENT EVENT DATA:\n{events_json_str}\n\n"
            f"SPEAKER PAGE CONTENT:\n{speaker_text}"
        )
        speaker_response = llm.invoke([
            {"role": "system", "content": "You are a precise JSON extraction assistant. Output only valid JSON arrays."},
            {"role": "user", "content": speaker_prompt},
        ])
        speaker_raw = speaker_response.content if hasattr(speaker_response, "content") else str(speaker_response)
        logger.info("Speaker response length: %d chars", len(speaker_raw))

        events_with_speakers = _parse_events_json(speaker_raw)
        # Fall back to events without speakers if speaker step fails
        if not events_with_speakers and events_with_meta:
            logger.warning("Speaker step returned no events — using enrichment output without speakers")
            events_with_speakers = [dict(e, speakers=[]) for e in events_with_meta]
        logger.info("Step 2b: %d events with speakers", len(events_with_speakers))

        # --- Step 2c: Final Formatting & Validation ---
        logger.info("Step 2c: Formatting and deduplicating...")
        events_with_speakers_str = json.dumps(events_with_speakers, indent=2)
        format_prompt = (
            "You are a data formatting and validation assistant.\n\n"
            "Clean and validate the event JSON below:\n"
            "- Remove duplicate events (same name + similar date = duplicate)\n"
            "- Normalize city names: Bengaluru → Bangalore, Bombay → Mumbai\n"
            "- Ensure status is one of: Upcoming, Live, Past, Unknown\n"
            "- Ensure event_type is one of: Conference, Meetup, Webinar, Hackathon, Summit\n"
            "- Ensure category is an array of strings\n"
            "- Ensure speakers is always an array (use [] if missing)\n"
            "- Fill missing required fields with empty strings\n\n"
            "Output ONLY the final JSON array. No markdown, no explanation, no code blocks.\n"
            "The output must start with [ and end with ].\n\n"
            f"EVENT DATA TO FORMAT:\n{events_with_speakers_str}"
        )
        format_response = llm.invoke([
            {"role": "system", "content": "You are a precise JSON formatting assistant. Output only valid JSON arrays starting with [ and ending with ]."},
            {"role": "user", "content": format_prompt},
        ])
        format_raw = format_response.content if hasattr(format_response, "content") else str(format_response)
        logger.info("Format response length: %d chars", len(format_raw))

        events_data = _parse_events_json(format_raw)
        # Fall back to pre-format data if formatter breaks
        if not events_data and events_with_speakers:
            logger.warning("Formatter step returned no events — using speaker step output")
            events_data = events_with_speakers

        # ==========================================
        # PHASE 3: Parse & Save to Database
        # ==========================================
        logger.info("=" * 60)
        logger.info("PHASE 3: Parsing & Saving to Database")
        logger.info("=" * 60)

        logger.info("Pipeline returned %d events", len(events_data))

        for i, evt in enumerate(events_data):
            logger.info(
                "Event %d: name='%s', url='%s'",
                i, evt.get("name", "MISSING"), evt.get("url", "MISSING")
            )

        stats = _save_events(events_data, db)

        scrape_run.status = "completed"
        scrape_run.completed_at = datetime.utcnow()
        scrape_run.events_found = len(events_data)
        scrape_run.events_new = stats["new"]
        scrape_run.events_updated = stats["updated"]
        scrape_run.speakers_found = stats["speakers_found"]
        scrape_run.errors = errors
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
