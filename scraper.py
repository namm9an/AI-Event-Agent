"""
AI Event Agent — Python Scraping Layer

Deterministic search + scrape module. No LLM involved.
Handles all web search (DuckDuckGo) and page scraping (Crawl4AI)
that the CrewAI agents previously failed to do via ReAct.

Functions:
    search_events() — Run multiple DuckDuckGo queries, return unique URLs
    scrape_urls() — Crawl4AI scrape each URL, return {url: markdown} dict
    search_speaker_pages() — For each event, search speakers, scrape results
    run_scraping_pipeline() — Orchestrate all of the above
"""

import asyncio
import re
import time
from typing import Optional
from urllib.parse import urlencode

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
# DuckDuckGo Search
# ============================================

SEARCH_QUERIES = [
    "AI ML conference India 2025 2026",
    "upcoming AI events India",
    "machine learning meetup India 2025 2026",
    "cloud computing summit India 2025 2026",
    "data science conference Bangalore Mumbai Delhi 2025 2026",
    "GenAI generative AI event India 2025 2026",
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
_MAX_URLS = 20


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


# ============================================
# SearXNG Search (preferred)
# ============================================

def _searxng_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Run a search via SearXNG JSON API.

    Returns:
        List of {title, href, body} dicts (same shape as DDGS).
    """
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
                "SearXNG search failed (attempt %d/%d): %s. Retrying in %ds...",
                attempt + 1, DDGS_RETRY_COUNT, str(e), delay
            )
            if attempt < DDGS_RETRY_COUNT - 1:
                time.sleep(delay)

    logger.error("SearXNG search failed after %d attempts for '%s'", DDGS_RETRY_COUNT, query)
    return []


# ============================================
# DuckDuckGo Search (fallback)
# ============================================

def _ddgs_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Run a single DuckDuckGo search with exponential backoff.
    """
    for attempt in range(DDGS_RETRY_COUNT):
        try:
            logger.info("DuckDuckGo search (attempt %d): '%s'", attempt + 1, query)
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region="in-en", max_results=max_results))

            if results:
                logger.info("Search returned %d results for '%s'", len(results), query)
                return results
            else:
                logger.warning("No results for query: '%s'", query)
                return []

        except Exception as e:
            delay = DDGS_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "DuckDuckGo search failed (attempt %d/%d): %s. Retrying in %ds...",
                attempt + 1, DDGS_RETRY_COUNT, str(e), delay
            )
            if attempt < DDGS_RETRY_COUNT - 1:
                time.sleep(delay)

    logger.error("DuckDuckGo search failed after %d attempts for '%s'", DDGS_RETRY_COUNT, query)
    return []


def _search(query: str, max_results: int = 10) -> list[dict]:
    """Search using SearXNG if available, otherwise fall back to DuckDuckGo."""
    if SEARXNG_URL:
        results = _searxng_search(query, max_results)
        if results:
            return results
        logger.warning("SearXNG returned nothing, falling back to DuckDuckGo for '%s'", query)
    return _ddgs_search(query, max_results)


def search_events(queries: Optional[list[str]] = None) -> list[dict]:
    """
    Search DuckDuckGo with multiple queries and collect unique event URLs.

    Args:
        queries: List of search queries. Defaults to SEARCH_QUERIES.

    Returns:
        List of unique {title, url, snippet} dicts (deduplicated by URL).
    """
    if queries is None:
        queries = SEARCH_QUERIES

    seen_urls: set[str] = set()
    unique_results: list[dict] = []

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

        # Small delay between queries to avoid rate limiting
        time.sleep(1)

    logger.info(
        "Search phase complete: %d unique URLs (capped at %d, filtered) from %d queries",
        len(unique_results), _MAX_URLS, len(queries),
    )
    return unique_results


def _extract_name_from_linkedin_slug(url: str) -> str:
    """Extract a human-readable name from a LinkedIn URL slug.

    E.g. 'https://linkedin.com/in/rakesh-sharma-123abc' -> 'rakesh sharma'
    """
    match = re.search(r'linkedin\.com/in/([^/?#]+)', url, re.IGNORECASE)
    if not match:
        return ""
    slug = match.group(1)
    # Remove trailing hash/id segments (digits at the end)
    slug = re.sub(r'-[0-9a-f]{5,}$', '', slug)
    slug = re.sub(r'-\d+$', '', slug)
    # Replace hyphens with spaces
    return slug.replace('-', ' ').strip().lower()


def search_linkedin_url(name: str, company: str = "") -> str:
    """
    Search DuckDuckGo for a speaker's LinkedIn profile URL.
    Returns the first linkedin.com/in/ URL that fuzzy-matches the speaker name,
    or empty string if no good match is found.
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
# Crawl4AI Scraping
# ============================================

async def _async_scrape(url: str) -> str:
    """
    Scrape a single URL using Crawl4AI.

    Args:
        url: URL to scrape.

    Returns:
        Markdown content (truncated to MAX_TOKENS_PER_PAGE).
    """
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)

            if not result.success:
                logger.warning("Crawl4AI returned failure for %s", url)
                return ""

            markdown = result.markdown or ""

            # Truncate to token limit (rough: 1 token ≈ 4 chars)
            char_limit = MAX_TOKENS_PER_PAGE * 4
            if len(markdown) > char_limit:
                markdown = markdown[:char_limit]
                markdown += "\n\n[... content truncated ...]"

            logger.info("Scraped %s (%d chars)", url, len(markdown))
            return markdown

    except Exception as e:
        logger.error("Crawl4AI failed for %s: %s", url, str(e))
        return ""


def scrape_url(url: str) -> str:
    """
    Synchronous wrapper for scraping a single URL.

    Args:
        url: URL to scrape.

    Returns:
        Markdown content.
    """
    return asyncio.run(_async_scrape(url))


def scrape_urls(urls: list[str]) -> dict[str, str]:
    """
    Scrape multiple URLs and return their content.

    Args:
        urls: List of URLs to scrape.

    Returns:
        Dict of {url: markdown_content}. Empty string for failed URLs.
    """
    content: dict[str, str] = {}

    for i, url in enumerate(urls):
        logger.info("Scraping URL %d/%d: %s", i + 1, len(urls), url)
        markdown = scrape_url(url)
        if markdown:
            content[url] = markdown
        else:
            logger.warning("Skipping empty content from %s", url)

    logger.info("Scrape phase complete: %d/%d URLs scraped successfully", len(content), len(urls))
    return content


# ============================================
# Speaker Page Search + Scrape
# ============================================

def search_speaker_pages(event_names: list[str]) -> dict[str, str]:
    """
    For each event name, search for speaker pages and scrape them.

    Args:
        event_names: List of event names to search speakers for.

    Returns:
        Dict of {search_query: markdown_content} for all speaker pages found.
    """
    speaker_content: dict[str, str] = {}

    for name in event_names:
        query = f"{name} speakers"
        results = _search(query, max_results=3)

        for r in results:
            url = r.get("href", "")
            if url and url not in speaker_content:
                markdown = scrape_url(url)
                if markdown:
                    speaker_content[url] = markdown

        # Delay between event speaker searches
        time.sleep(1)

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
    Run the complete Python scraping pipeline.

    Returns:
        {
            "event_urls": list[dict],  # {title, url, snippet}
            "event_content": dict[str, str],  # {url: markdown}
            "speaker_content": dict[str, str],  # {url: markdown}
            "errors": list[str],
        }
    """
    errors: list[str] = []

    # Step 1: Search for event URLs
    logger.info("=== Phase 1: Searching for events ===")
    event_urls = search_events(queries=queries)

    if not event_urls:
        errors.append("No event URLs found from any search query")
        return {
            "event_urls": [],
            "event_content": {},
            "speaker_content": {},
            "errors": errors,
        }

    # Step 2: Scrape event pages
    logger.info("=== Phase 2: Scraping %d event pages ===", len(event_urls))
    urls_to_scrape = [r["url"] for r in event_urls]
    event_content = scrape_urls(urls_to_scrape)

    if not event_content:
        errors.append("No event pages could be scraped")

    # Step 3: Search and scrape speaker pages
    logger.info("=== Phase 3: Searching for speaker pages ===")
    # Use event titles from search results as event names
    event_names = [r["title"] for r in event_urls if r.get("title")]
    # Deduplicate and limit to avoid too many searches
    unique_names = list(dict.fromkeys(event_names))[:15]
    speaker_content = search_speaker_pages(unique_names)

    return {
        "event_urls": event_urls,
        "event_content": event_content,
        "speaker_content": speaker_content,
        "errors": errors,
    }
