"""
AI Event Agent — Configuration Module

Loads environment variables and exposes shared configuration objects.
All secrets come from `.env` — never hardcoded.
"""

import logging
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load .env from the backend directory
load_dotenv()

# Suppress litellm noise (apscheduler warning is non-fatal)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Disable litellm telemetry to avoid the proxy import chain
os.environ["LITELLM_LOG"] = "ERROR"

# ============================================
# Logger Setup
# ============================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai_event_agent")


# ============================================
# LLM Inference Endpoint
# ============================================

LLM_INFERENCE_URL = os.getenv("LLM_INFERENCE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY", "none")
LLM_MODEL = os.getenv("LLM_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16")

if not LLM_INFERENCE_URL:
    raise ValueError("LLM_INFERENCE_URL is not set in .env")

# Set OpenAI env vars so litellm (used by CrewAI internally) routes correctly
os.environ["OPENAI_API_KEY"] = LLM_API_KEY
os.environ["OPENAI_API_BASE"] = LLM_INFERENCE_URL


def get_llm_string() -> str:
    """
    Return the LLM model string for CrewAI agents.
    CrewAI v1.9.3 uses litellm internally — passing a string model name
    with 'openai/' prefix lets litellm route to the OpenAI-compatible
    endpoint using OPENAI_API_BASE and OPENAI_API_KEY env vars.
    """
    return f"openai/{LLM_MODEL}"


def get_chat_llm(temperature: float = 0.3, max_tokens: int = 4096) -> ChatOpenAI:
    """
    Return a ChatOpenAI instance for direct LLM calls (chat endpoint).
    Uses clean model name (no prefix) since this bypasses litellm.
    """
    return ChatOpenAI(
        base_url=LLM_INFERENCE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=120,
    )


# ============================================
# Database
# ============================================

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./events.db")


# ============================================
# Auth
# ============================================

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
NORMAL_USER_USERNAME = os.getenv("NORMAL_USER_USERNAME", "user")
NORMAL_USER_PASSWORD = os.getenv("NORMAL_USER_PASSWORD", "user")
SUPER_ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME", "super_admin")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "super_admin")


# ============================================
# Scheduler + Reports
# ============================================

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
DEFAULT_SCRAPE_TIME = os.getenv("DEFAULT_SCRAPE_TIME", "00:00")
DEFAULT_REPORT_TIME = os.getenv("DEFAULT_REPORT_TIME", "12:00")
REPORTS_DIR = os.getenv("REPORTS_DIR", "./reports")


# ============================================
# Scraping Config
# ============================================

MAX_TOKENS_PER_PAGE = int(os.getenv("MAX_TOKENS_PER_PAGE", "6000"))
DDGS_RETRY_COUNT = int(os.getenv("DDGS_RETRY_COUNT", "3"))
DDGS_BASE_DELAY = int(os.getenv("DDGS_BASE_DELAY", "2"))
MAX_SPEAKERS_PER_EVENT = int(os.getenv("MAX_SPEAKERS_PER_EVENT", "5"))
SPEAKER_SEARCH_TIMEOUT = int(os.getenv("SPEAKER_SEARCH_TIMEOUT", "10"))
