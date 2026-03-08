"""
AI Event Agent — Python Scraping Layer

Deterministic search + scrape module. No LLM involved.
Handles all web search (SearXNG/DDGS) and page scraping (Crawl4AI).

Improvements over v1:
  - Dynamic year queries (no hardcoded years)
  - Site-targeted SearXNG queries for direct event pages
  - Curated seed sites always scraped (Tier 1 — India AI/tech events)
  - JSON-LD pre-extraction (Schema.org structured data, free structured fields)
  - 2-hop link following (listing pages → individual event pages)

Functions:
    search_events()         — Run queries, return unique URLs
    scrape_urls()           — Crawl4AI scrape each URL
    extract_jsonld_events() — Pull machine-readable event data from HTML
    search_speaker_pages()  — For each event, search + scrape speaker pages
    run_scraping_pipeline() — Orchestrate all of the above
"""

import asyncio
import json
import re
import time
from datetime import date as _date
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from crawl4ai import AsyncWebCrawler
from ddgs import DDGS
from rapidfuzz import fuzz

from config import (
    logger,
    DDGS_RETRY_COUNT,
    DDGS_BASE_DELAY,
    MAX_TOKENS_PER_PAGE,
    SEARXNG_URL,
)


# ============================================
# Dynamic Search Queries (year-aware)
# ============================================

def _build_queries() -> list[str]:
    """Build search queries using the current and next calendar year."""
    y = _date.today().year
    ny = y + 1
    return [
        # Generic discovery
        f"AI ML conference India {y} {ny}",
        f"upcoming AI events India {y}",
        f"machine learning meetup India {y} {ny}",
        f"GenAI generative AI summit India {y} {ny}",
        f"data science conference Bangalore Mumbai Delhi Hyderabad {y} {ny}",
        f"cloud computing summit India {y} {ny}",
        # Site-targeted — these land directly on individual event pages
        f"site:konfhub.com AI India {y}",
        f"site:hasgeek.com {y} {ny}",
        f"site:townscript.com AI India {y}",
        f"site:events.inc42.com {y}",
        f"site:devfolio.co AI hackathon India {y}",
        f"\"AI summit\" OR \"ML conference\" India site:eventbrite.co.in {y}",
        f"site:nasscom.in events {y} {ny}",
    ]


# ============================================
# Curated Seed Sites (Tier 1 — always scraped)
# ============================================

SEED_SITES = [
    "https://konfhub.com/events/india",
    "https://hasgeek.com",
    "https://nasscom.in/flagship-events",
    "https://analyticsvidhya.com/events/",
    "https://devfolio.co/hackathons",
    "https://events.inc42.com",
    "https://townscript.com/events/india/technology",
    "https://www.meetup.com/find/?keywords=AI%20Machine%20Learning&location=in--India",
]

# ============================================
# URL Quality Filter
# ============================================

_BLOCKED_TLDS = {
    ".ru", ".store", ".vin", ".be", ".lt", ".vc", ".lv", ".ee",
    ".by", ".kz", ".uz", ".am", ".ge", ".az", ".md", ".kg",
}
_BLOCKED_KEYWORDS = [
    "mydesi", "viral-video", "mms", "sputnik", "yandex",
    "datalopata", "sarkarivle", "tetespanas", "intiprahasia",
    "lordfilmss", "sosyalbilgiler", "hacettepemun", "rosserial",
    "pmlconf", "SkillFactory", "finam.ru",
]

# Known aggregator/listing domains — trigger 2-hop scraping
_LISTING_DOMAINS = {
    "10times.com", "eventbrite.co.in", "eventbrite.com",
    "townscript.com", "konfhub.com", "allevents.in",
    "meetup.com", "insider.in", "bookmyshow.com",
}

_MAX_URLS = 30  # increased from 20 to allow seed + search


def _is_useful_url(url: str) -> bool:
    """Return True if URL looks like a legitimate English event/tech page."""
    url_lower = url.lower()
    for tld in _BLOCKED_TLDS:
        if tld in url_lower:
            return False
    for kw in _BLOCKED_KEYWORDS:
        if kw.lower() in url_lower:
            return False
    return True


def _is_listing_page(url: str, markdown: str) -> bool:
    """Heuristic: detect aggregator listing pages that contain many events."""
    domain = urlparse(url).netloc.replace("www.", "")
    if domain in _LISTING_DOMAINS:
        return True
    # Content-based: many register/RSVP/view buttons = listing page
    register_count = markdown.lower().count("register") + markdown.lower().count("rsvp")
    return register_count >= 5


# ============================================
# SearXNG Search (preferred)
# ============================================

def _searxng_search(query: str, max_results: int = 10) -> list[dict]:
    """Run a search via SearXNG JSON API."""
    if not SEARXNG_URL:
        return []

    params = {
        "q": query,
        "format": "json",
        "language": "en-IN",
        "pageno": 1,
    }
    url = f"{SEARXNG_URL}/search?{urlencode(params)}"

    for attempt in range(DDGS_RETRY_COUNT):
        try:
            logger.info("SearXNG search (attempt %d): '%s'", attempt + 1, query)
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for r in data.get("results", [])[:max_results]:
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("url", ""),
                    "body": r.get("content", ""),
                })

            if results:
                logger.info("SearXNG returned %d results for '%s'", len(results), query)
                return results
            else:
                logger.warning("SearXNG: no results for '%s'", query)
                return []

        except Exception as e:
            delay = DDGS_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "SearXNG failed (attempt %d/%d): %s. Retrying in %ds...",
                attempt + 1, DDGS_RETRY_COUNT, str(e), delay
            )
            if attempt < DDGS_RETRY_COUNT - 1:
                time.sleep(delay)

    logger.error("SearXNG failed after %d attempts for '%s'", DDGS_RETRY_COUNT, query)
    return []


# ============================================
# DuckDuckGo Search (fallback)
# ============================================

def _ddgs_search(query: str, max_results: int = 10) -> list[dict]:
    """Run a DuckDuckGo search with exponential backoff."""
    for attempt in range(DDGS_RETRY_COUNT):
        try:
            logger.info("DuckDuckGo search (attempt %d): '%s'", attempt + 1, query)
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region="in-en", max_results=max_results))
            if results:
                logger.info("DDGS returned %d results for '%s'", len(results), query)
                return results
            else:
                logger.warning("DDGS: no results for '%s'", query)
                return []
        except Exception as e:
            delay = DDGS_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "DDGS failed (attempt %d/%d): %s. Retrying in %ds...",
                attempt + 1, DDGS_RETRY_COUNT, str(e), delay
            )
            if attempt < DDGS_RETRY_COUNT - 1:
                time.sleep(delay)

    logger.error("DDGS failed after %d attempts for '%s'", DDGS_RETRY_COUNT, query)
    return []


def _search(query: str, max_results: int = 10) -> list[dict]:
    """Search using SearXNG if available, otherwise fall back to DuckDuckGo."""
    if SEARXNG_URL:
        results = _searxng_search(query, max_results)
        if results:
            return results
        logger.warning("SearXNG returned nothing, falling back to DDGS for '%s'", query)
    return _ddgs_search(query, max_results)


# ============================================
# JSON-LD Pre-Extraction (Schema.org Event)
# ============================================

def extract_jsonld_events(html: str, source_url: str) -> list[dict]:
    """
    Extract machine-readable Event JSON-LD from raw HTML.

    Many event sites (Eventbrite, Meetup, Konfhub) embed structured data:
        <script type="application/ld+json">{"@type": "Event", ...}</script>

    Returns a list of normalised event dicts (same shape as LLM extraction output).
    """
    events = []
    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        try:
            data = json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            continue

        # Handle both single object and @graph arrays
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if data.get("@graph"):
                items = data["@graph"]
            else:
                items = [data]

        for item in items:
            if not isinstance(item, dict):
                continue
            event_type = item.get("@type", "")
            if isinstance(event_type, list):
                event_type = " ".join(event_type)
            if "event" not in event_type.lower():
                continue

            # Extract location
            location_obj = item.get("location", {})
            if isinstance(location_obj, dict):
                venue = location_obj.get("name", "")
                addr = location_obj.get("address", {})
                if isinstance(addr, dict):
                    city = addr.get("addressLocality", "")
                    country = addr.get("addressCountry", "")
                    full_addr = ", ".join(filter(None, [venue, addr.get("streetAddress", ""), city]))
                elif isinstance(addr, str):
                    city = ""
                    country = ""
                    full_addr = addr
                else:
                    city = ""
                    country = ""
                    full_addr = venue
            else:
                city = ""
                country = ""
                full_addr = str(location_obj) if location_obj else ""

            # Skip non-India events
            location_text = full_addr.lower() + city.lower() + country.lower()
            if country and "india" not in location_text and "in" not in country.lower():
                # Only skip if country is explicitly non-India
                if len(country) == 2 and country.upper() not in ("IN", ""):
                    logger.debug("Skipping non-India JSON-LD event: %s (country: %s)", item.get("name", ""), country)
                    continue

            # Extract performers/speakers
            speakers = []
            for performer in (item.get("performer") or item.get("performers") or []):
                if isinstance(performer, dict):
                    speakers.append({
                        "name": performer.get("name", ""),
                        "designation": performer.get("jobTitle", ""),
                        "company": performer.get("affiliation", {}).get("name", "") if isinstance(performer.get("affiliation"), dict) else "",
                        "linkedin_url": "",
                        "wikipedia_url": performer.get("sameAs", "") if isinstance(performer.get("sameAs"), str) else "",
                        "talk_title": "",
                        "talk_summary": "",
                        "topic_category": "",
                        "topic_links": [],
                        "previous_talks": [],
                        "linkedin_bio": "",
                    })

            start_date = item.get("startDate", "")
            event = {
                "name": item.get("name", "").strip(),
                "description": item.get("description", "")[:500],
                "date_text": start_date,
                "location": full_addr,
                "city": city,
                "status": "Upcoming",
                "category": ["AI", "Technology"],
                "url": item.get("url", source_url),
                "organizer": (item.get("organizer") or {}).get("name", "") if isinstance(item.get("organizer"), dict) else "",
                "event_type": "Conference",
                "registration_url": item.get("url", ""),
                "image_url": item.get("image", "") if isinstance(item.get("image"), str) else "",
                "speakers": speakers,
                "_source": "jsonld",
            }

            if event["name"]:
                events.append(event)
                logger.info("JSON-LD extracted event: '%s' @ %s", event["name"], city or "unknown city")

    return events


# ============================================
# 2-Hop Link Extraction
# ============================================

def _extract_event_links_from_listing(url: str, markdown: str) -> list[str]:
    """
    From a detected listing/aggregator page, extract individual event page URLs.

    Uses a regex heuristic on the markdown — looks for links that look like
    individual event pages (contain /e/, /event/, /events/, a slug, etc).
    """
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    domain = urlparse(url).netloc.replace("www.", "")

    # Match markdown links: [text](url)
    md_links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', markdown)
    href_links = re.findall(r'href=["\']([^"\']+)["\']', markdown)

    candidates = [href for _, href in md_links] + href_links
    candidates += [l for l in re.findall(r'https?://\S+', markdown)]

    event_url_patterns = re.compile(
        r'/(event|events|e|talk|talks|hackathon|conference|summit|meetup)/[a-z0-9_-]+',
        re.IGNORECASE,
    )

    seen: set[str] = set()
    results: list[str] = []

    for href in candidates:
        # Make absolute
        if href.startswith("/"):
            href = urljoin(base, href)

        if not href.startswith("http"):
            continue

        # Must be same domain or a known event platform
        href_domain = urlparse(href).netloc.replace("www.", "")

        # Check it looks like an event detail page
        path = urlparse(href).path
        if not event_url_patterns.search(path):
            continue

        if href in seen:
            continue

        if not _is_useful_url(href):
            continue

        seen.add(href)
        results.append(href)
        if len(results) >= 15:
            break

    logger.info("2-hop: extracted %d event links from listing page %s", len(results), url)
    return results


# ============================================
# Crawl4AI Scraping
# ============================================

async def _async_scrape(url: str, get_html: bool = False) -> tuple[str, str]:
    """
    Scrape a single URL using Crawl4AI.

    Returns:
        (markdown, raw_html) tuple. raw_html is populated only when get_html=True.
    """
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)

            if not result.success:
                logger.warning("Crawl4AI returned failure for %s", url)
                return "", ""

            markdown = result.markdown or ""
            html = result.html or "" if get_html else ""

            # Truncate to token limit (rough: 1 token ≈ 4 chars)
            char_limit = MAX_TOKENS_PER_PAGE * 4
            if len(markdown) > char_limit:
                markdown = markdown[:char_limit]
                markdown += "\n\n[... content truncated ...]"

            logger.info("Scraped %s (%d chars markdown)", url, len(markdown))
            return markdown, html

    except Exception as e:
        logger.error("Crawl4AI failed for %s: %s", url, str(e))
        return "", ""


def scrape_url(url: str, get_html: bool = False) -> tuple[str, str]:
    """Synchronous wrapper for scraping a single URL."""
    return asyncio.run(_async_scrape(url, get_html=get_html))


def scrape_urls(urls: list[str], get_html: bool = False) -> dict[str, dict]:
    """
    Scrape multiple URLs and return their content.

    Returns:
        Dict of {url: {"markdown": str, "html": str}}.
    """
    content: dict[str, dict] = {}

    for i, url in enumerate(urls):
        logger.info("Scraping URL %d/%d: %s", i + 1, len(urls), url)
        markdown, html = scrape_url(url, get_html=get_html)
        if markdown:
            content[url] = {"markdown": markdown, "html": html}
        else:
            logger.warning("Skipping empty content from %s", url)

    logger.info("Scrape phase complete: %d/%d URLs scraped successfully", len(content), len(urls))
    return content


# ============================================
# Event URL Discovery
# ============================================

def search_events(queries: Optional[list[str]] = None) -> list[dict]:
    """
    Search with multiple queries and collect unique event URLs.

    Uses dynamic year queries + site-targeted queries.

    Returns:
        List of unique {title, url, snippet} dicts.
    """
    if queries is None:
        queries = _build_queries()

    seen_urls: set[str] = set()
    unique_results: list[dict] = [{"title": s, "url": s, "snippet": ""} for s in SEED_SITES]
    seen_urls = {s for s in SEED_SITES}

    for query in queries:
        if len(unique_results) >= _MAX_URLS:
            break
        results = _search(query)
        for r in results:
            if len(unique_results) >= _MAX_URLS:
                break
            url = r.get("href", "")
            if url and url not in seen_urls and _is_useful_url(url):
                seen_urls.add(url)
                unique_results.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("body", ""),
                })

        time.sleep(0.5)

    logger.info(
        "Search phase complete: %d unique URLs (%d seeds + %d from search)",
        len(unique_results), len(SEED_SITES), len(unique_results) - len(SEED_SITES),
    )
    return unique_results


# ============================================
# LinkedIn URL Search
# ============================================

def _extract_name_from_linkedin_slug(url: str) -> str:
    """Extract a human-readable name from a LinkedIn URL slug."""
    match = re.search(r'linkedin\.com/in/([^/?#]+)', url, re.IGNORECASE)
    if not match:
        return ""
    slug = match.group(1)
    slug = re.sub(r'-[0-9a-f]{5,}$', '', slug)
    slug = re.sub(r'-\d+$', '', slug)
    return slug.replace('-', ' ').strip().lower()


def search_linkedin_url(name: str, company: str = "") -> str:
    """
    Search for a speaker's LinkedIn profile URL.
    Returns the first linkedin.com/in/ URL that fuzzy-matches the speaker name.
    """
    query = f'"{name}" {company} site:linkedin.com/in'.strip()
    results = _search(query, max_results=5)

    name_lower = name.lower().strip()
    best_url = ""
    best_score = 0

    for r in results:
        url = r.get("href", "")
        if "linkedin.com/in/" not in url.lower():
            continue
        slug_name = _extract_name_from_linkedin_slug(url)
        if not slug_name:
            continue
        score = fuzz.token_sort_ratio(name_lower, slug_name)
        logger.debug("LinkedIn match: '%s' vs slug '%s' → score %d", name, slug_name, score)
        if score > best_score:
            best_score = score
            best_url = url

    if best_score >= 70:
        logger.info("LinkedIn match accepted: '%s' → %s (score %d)", name, best_url, best_score)
        return best_url
    elif best_url:
        logger.warning("LinkedIn match rejected: '%s' → %s (score %d < 70)", name, best_url, best_score)
    return ""


# ============================================
# Speaker Page Search + Scrape
# ============================================

def search_speaker_pages(event_names: list[str]) -> dict[str, str]:
    """
    For each event name, search for speaker pages and scrape them.

    Returns:
        Dict of {url: markdown_content} for all speaker pages found.
    """
    speaker_content: dict[str, str] = {}

    for name in event_names:
        query = f"{name} speakers"
        results = _search(query, max_results=3)

        for r in results:
            url = r.get("href", "")
            if url and url not in speaker_content:
                markdown, _ = scrape_url(url)
                if markdown:
                    speaker_content[url] = markdown

        time.sleep(0.5)

    logger.info(
        "Speaker search complete: %d pages scraped for %d events",
        len(speaker_content), len(event_names)
    )
    return speaker_content


# ============================================
# Full Scraping Pipeline
# ============================================

def run_scraping_pipeline(queries: Optional[list[str]] = None) -> dict:
    """
    Run the complete scraping pipeline.

    Phase 1a: Seed sites + search → candidate URLs
    Phase 1b: Scrape all candidate URLs (with raw HTML for JSON-LD)
    Phase 1c: JSON-LD pre-extraction from raw HTML
    Phase 1d: 2-hop — detect listing pages → extract individual event URLs → scrape those
    Phase 2 : Speaker page search + scrape (handled in pipeline.py)

    Returns:
        {
            "event_urls": list[dict],          # {title, url, snippet}
            "event_content": dict[str, str],   # {url: markdown}
            "jsonld_events": list[dict],        # pre-extracted structured events
            "speaker_content": dict[str, str], # {url: markdown}
            "errors": list[str],
        }
    """
    errors: list[str] = []

    # ── Phase 1a: Discover candidate URLs ──────────────────────────────
    logger.info("=== Phase 1a: Discovering event URLs ===")
    event_urls = search_events(queries=queries)

    if not event_urls:
        errors.append("No event URLs found from any search query")
        return {
            "event_urls": [],
            "event_content": {},
            "jsonld_events": [],
            "speaker_content": {},
            "errors": errors,
        }

    # ── Phase 1b: Scrape all candidate URLs (with HTML for JSON-LD) ────
    logger.info("=== Phase 1b: Scraping %d candidate pages ===", len(event_urls))
    urls_to_scrape = [r["url"] for r in event_urls]
    scraped = scrape_urls(urls_to_scrape, get_html=True)

    # ── Phase 1c: JSON-LD pre-extraction ───────────────────────────────
    logger.info("=== Phase 1c: Extracting JSON-LD structured data ===")
    jsonld_events: list[dict] = []
    for url, data in scraped.items():
        html = data.get("html", "")
        if html:
            found = extract_jsonld_events(html, url)
            if found:
                logger.info("JSON-LD: %d events from %s", len(found), url)
                jsonld_events.extend(found)

    logger.info("JSON-LD phase complete: %d pre-extracted events", len(jsonld_events))

    # ── Phase 1d: 2-hop — expand listing pages ─────────────────────────
    logger.info("=== Phase 1d: 2-hop link expansion ===")
    hop2_urls: list[str] = []
    existing_urls = set(scraped.keys())

    for url, data in scraped.items():
        markdown = data.get("markdown", "")
        if _is_listing_page(url, markdown):
            links = _extract_event_links_from_listing(url, markdown)
            for link in links:
                if link not in existing_urls and len(hop2_urls) < 20:
                    hop2_urls.append(link)
                    existing_urls.add(link)

    if hop2_urls:
        logger.info("2-hop: scraping %d individual event pages", len(hop2_urls))
        hop2_scraped = scrape_urls(hop2_urls, get_html=True)
        # Also run JSON-LD on 2-hop pages
        for url, data in hop2_scraped.items():
            html = data.get("html", "")
            if html:
                found = extract_jsonld_events(html, url)
                if found:
                    jsonld_events.extend(found)
            scraped[url] = data
    else:
        logger.info("2-hop: no listing pages detected")

    # Build plain markdown dict for pipeline.py LLM extraction
    event_content = {url: data["markdown"] for url, data in scraped.items() if data.get("markdown")}

    if not event_content:
        errors.append("No event pages could be scraped")

    # ── Speaker page search ─────────────────────────────────────────────
    logger.info("=== Phase 1e: Searching for speaker pages ===")
    event_names = list(dict.fromkeys([r["title"] for r in event_urls if r.get("title")]))[:15]
    speaker_content = search_speaker_pages(event_names)

    logger.info(
        "Scraping pipeline complete: %d pages scraped, %d JSON-LD events, %d speaker pages",
        len(event_content), len(jsonld_events), len(speaker_content)
    )

    return {
        "event_urls": event_urls,
        "event_content": event_content,
        "jsonld_events": jsonld_events,
        "speaker_content": speaker_content,
        "errors": errors,
    }
