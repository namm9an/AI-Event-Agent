"""
AI Event Agent — Scrape & Extraction Pipeline

Two-phase architecture:
  Phase 1 (Python): DuckDuckGo search + Crawl4AI scrape (deterministic)
  Phase 2 (Direct LLM): Batched enrichment → Speaker → Formatter calls

Saves results to SQLite and tracks each run in scrape_runs.

Key improvements over crew.py:
- Thinking disabled via system prompt (prevents token starvation)
- Event extraction batched at 5 pages per LLM call (manageable for 3B active params)
- URL cap at 20 + non-English domain filter (handled in scraper.py)
- Auto-trigger report after successful scrape (handled in main.py)
"""

import json
import re
import uuid
from datetime import datetime, date as _date, timedelta

from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from config import get_chat_llm, logger
from scraper import run_scraping_pipeline, search_linkedin_url
from db.database import SessionLocal
from db.models import Event, ScrapeRun, SearchQuery, Speaker

# System prompt used for all LLM calls — suppresses chain-of-thought reasoning
_NO_THINK_SYSTEM = (
    "You are a precise JSON extraction assistant. "
    "Output ONLY a valid JSON array. "
    "Do NOT include any reasoning, thinking, commentary, or explanation. "
    "Your entire response must start with [ and end with ]. Nothing else."
)


def _build_speaker_text(speaker_content: dict[str, str]) -> str:
    """Build formatted speaker page text for LLM consumption."""
    parts = []
    for url, markdown in speaker_content.items():
        parts.append(f"=== SPEAKER PAGE: {url} ===\n{markdown}\n")
    return "\n".join(parts) if parts else "No additional speaker pages found."


def _strip_thinking_tags(text: str) -> str:
    """
    Strip Nemotron/DeepSeek-style <think>...</think> reasoning blocks.
    Also handles variations: <thinking>, </think>, etc.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</?think[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?thinking[^>]*>", "", text, flags=re.IGNORECASE)
    return text.strip()


def _extract_balanced_segment(text: str, open_char: str, close_char: str) -> str | None:
    """Extract first balanced JSON segment, ignoring braces inside strings."""
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
    """Extract top-level JSON object substrings from a text blob."""
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
    Handles thinking tags, markdown fences, trailing commas, and partial output.
    """
    if not raw_output:
        return []

    # Model outputs reasoning without opening <think> tag, then closes with </think>
    # Split on </think> and take only the actual answer that follows
    if "</think>" in raw_output:
        raw_output = raw_output.split("</think>")[-1].strip()

    text = _strip_thinking_tags(raw_output)
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    array_segment = _extract_balanced_segment(text, "[", "]")
    if array_segment:
        text = array_segment
    else:
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

    try:
        events = json.loads(text)
        if isinstance(events, list):
            return [e for e in events if isinstance(e, dict)]
        elif isinstance(events, dict):
            return [events]
        return []
    except json.JSONDecodeError:
        pass

    text_fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        events = json.loads(text_fixed)
        if isinstance(events, list):
            logger.info("Parsed JSON after trailing-comma fix")
            return [e for e in events if isinstance(e, dict)]
    except json.JSONDecodeError:
        pass

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
    """Check for duplicate events by URL match or fuzzy name+date match."""
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
    """Save parsed events to the database with per-event error isolation."""
    stats = {"new": 0, "updated": 0, "speakers_found": 0, "skipped": 0}

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

        # Skip events explicitly marked as Past
        if str(event_data.get("status", "")).strip().lower() == "past":
            logger.info("Skipping past event: %s", name)
            stats["skipped"] += 1
            continue

        if not url:
            slug = re.sub(r"[^a-z0-9-]", "-", name.lower())
            slug = re.sub(r"-+", "-", slug).strip("-")
            if not slug:
                slug = f"event-{uuid.uuid4().hex[:8]}"
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
                for speaker_data in speakers_data[:5]:
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
    return [r.query for r in rows if r.query]


def run_pipeline(queries: list[str] | None = None) -> dict:
    """
    Execute the hybrid scrape + extraction pipeline.

    Phase 1: Python scraping (deterministic search + crawl, capped at 20 URLs)
    Phase 2: Batched LLM extraction (5 pages per call, thinking disabled)
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

        scrape_run.urls_scraped = list(event_content.keys())
        db.commit()

        speaker_text = _build_speaker_text(speaker_content)
        max_speaker_chars = 15000
        if len(speaker_text) > max_speaker_chars:
            speaker_text = speaker_text[:max_speaker_chars] + "\n\n[... content truncated ...]"

        # ==========================================
        # PHASE 2: Batched LLM Extraction
        # ==========================================
        logger.info("=" * 60)
        logger.info("PHASE 2: Batched LLM Extraction (5 pages/call, thinking disabled)")
        logger.info("=" * 60)

        llm = get_chat_llm(temperature=0.1, max_tokens=8192)

        today_str = _date.today().strftime("%B %d, %Y")
        cutoff_str = (_date.today() - timedelta(days=20)).strftime("%B %d, %Y")

        # --- Step 2a: Batched Event Enrichment ---
        logger.info("Step 2a: Extracting events in batches of 5 pages...")
        event_items = list(event_content.items())
        batch_size = 5
        all_extracted_events: list[dict] = []

        for batch_start in range(0, len(event_items), batch_size):
            batch = dict(event_items[batch_start:batch_start + batch_size])
            batch_text = "\n".join(
                f"=== PAGE: {url} ===\n{md}\n" for url, md in batch.items()
            )

            max_batch_chars = 15000
            if len(batch_text) > max_batch_chars:
                batch_text = batch_text[:max_batch_chars] + "\n\n[... content truncated ...]"

            enrich_prompt = (
                "You are an event data extraction assistant. Extract ONLY AI, ML, Cloud, "
                "and Data Science events that are located in INDIA from the scraped content below.\n\n"
                f"Today's date is {today_str}. Only extract events that are upcoming or ended no earlier than {cutoff_str}. "
                "Skip any event that ended more than 20 days ago.\n\n"
                "For each event output a JSON object with these fields:\n"
                "  name (string, required)\n"
                "  description (string)\n"
                "  date_text (string, raw date as found on page)\n"
                "  location (string, full venue address)\n"
                "  city (string, Indian city e.g. Bangalore, Mumbai, Delhi, Hyderabad, Chennai, Pune)\n"
                "  status (string: Upcoming | Live | Past | Unknown)\n"
                "  category (array of strings: AI, ML, Cloud, Data Science, etc.)\n"
                "  url (string, from the === PAGE: URL === header above the content)\n"
                "  organizer (string)\n"
                "  event_type (string: Conference | Meetup | Webinar | Hackathon | Summit)\n"
                "  registration_url (string)\n\n"
                "Rules:\n"
                "- Output ONLY a valid JSON array starting with [ and ending with ]. No markdown, no explanation, no reasoning.\n"
                "- Use empty string for fields not found. Never invent data.\n"
                "- Extract EVERY distinct event you can find.\n\n"
                "SCRAPED CONTENT:\n\n"
                f"{batch_text}"
            )
            batch_response = llm.invoke([
                {"role": "system", "content": _NO_THINK_SYSTEM},
                {"role": "user", "content": enrich_prompt},
            ])
            batch_raw = batch_response.content if hasattr(batch_response, "content") else str(batch_response)
            logger.info(
                "Batch %d-%d enrichment: %d chars response",
                batch_start, batch_start + batch_size, len(batch_raw)
            )

            batch_events = _parse_events_json(batch_raw)
            logger.info(
                "Batch %d-%d extracted %d events",
                batch_start, batch_start + batch_size, len(batch_events)
            )
            all_extracted_events.extend(batch_events)

        events_with_meta = all_extracted_events
        total_batches = (len(event_items) + batch_size - 1) // batch_size
        logger.info("Step 2a total: %d events from %d batches", len(events_with_meta), total_batches)

        if not events_with_meta:
            logger.warning("No events from enrichment step — pipeline will save 0 events")

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
            "- Output ONLY the updated JSON array. No markdown, no explanation, no reasoning.\n\n"
            f"CURRENT EVENT DATA:\n{events_json_str}\n\n"
            f"SPEAKER PAGE CONTENT:\n{speaker_text}"
        )
        speaker_response = llm.invoke([
            {"role": "system", "content": _NO_THINK_SYSTEM},
            {"role": "user", "content": speaker_prompt},
        ])
        speaker_raw = speaker_response.content if hasattr(speaker_response, "content") else str(speaker_response)
        logger.info("Speaker response: %d chars", len(speaker_raw))

        events_with_speakers = _parse_events_json(speaker_raw)
        if not events_with_speakers and events_with_meta:
            logger.warning("Speaker step returned no events — using enrichment output without speakers")
            events_with_speakers = [dict(e, speakers=[]) for e in events_with_meta]
        logger.info("Step 2b: %d events with speakers", len(events_with_speakers))

        # --- Step 2b.5: LinkedIn URL Enrichment ---
        logger.info("Step 2b.5: Enriching missing LinkedIn URLs...")
        enriched_count = 0
        for event in events_with_speakers:
            for speaker in event.get("speakers", []):
                if not speaker.get("linkedin_url") and speaker.get("name"):
                    linkedin = search_linkedin_url(
                        speaker["name"], speaker.get("company", "")
                    )
                    if linkedin:
                        speaker["linkedin_url"] = linkedin
                        enriched_count += 1
                        logger.info("LinkedIn enriched: %s → %s", speaker["name"], linkedin)
        logger.info("Step 2b.5: Enriched %d LinkedIn URLs", enriched_count)

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
            "Output ONLY the final JSON array. No markdown, no explanation, no reasoning.\n"
            "The output must start with [ and end with ].\n\n"
            f"EVENT DATA TO FORMAT:\n{events_with_speakers_str}"
        )
        format_response = llm.invoke([
            {"role": "system", "content": _NO_THINK_SYSTEM},
            {"role": "user", "content": format_prompt},
        ])
        format_raw = format_response.content if hasattr(format_response, "content") else str(format_response)
        logger.info("Format response: %d chars", len(format_raw))

        events_data = _parse_events_json(format_raw)
        if not events_data and events_with_speakers:
            logger.warning("Formatter step returned no events — using speaker step output")
            events_data = events_with_speakers

        # ==========================================
        # PHASE 3: Save to Database
        # ==========================================
        logger.info("=" * 60)
        logger.info("PHASE 3: Saving %d events to Database", len(events_data))
        logger.info("=" * 60)

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
