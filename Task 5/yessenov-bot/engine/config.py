"""Central configuration. Reads everything from the environment (.env in dev).

Keeping all tunables here means the rest of the engine never hard-codes an endpoint,
model name, or threshold — swap them via .env without touching code.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the directory that contains this `engine/` package's parent.
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
INDEX_DIR = ROOT / "data" / "index"

# Load .env from the project root if present (no-op in production where env is set directly).
load_dotenv(ROOT / ".env")


def _get(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def _get_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


# --- LLM (chat) ---
LLM_BASE_URL = _get("LLM_BASE_URL", "https://llm.alem.ai/v1")
CHAT_MODEL = _get("CHAT_MODEL", "gemma4")
CHAT_API_KEY = os.getenv("CHAT_API_KEY", "")

# --- Embeddings ---
EMBED_BASE_URL = _get("EMBED_BASE_URL", "https://llm.alem.ai/v1")
EMBED_MODEL = _get("EMBED_MODEL", "text-1024")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_DIM = _get_int("EMBED_DIM", 1024)

# --- Context budget / retrieval ---
MAX_INPUT_TOKENS = _get_int("MAX_INPUT_TOKENS", 4000)
TOP_K = _get_int("TOP_K", 6)
RELEVANCE_MAX_DISTANCE = _get_float("RELEVANCE_MAX_DISTANCE", 0.60)

# --- Vector store ---
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "numpy").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")

# --- Email ---
MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
MAIL_FROM_EMAIL = os.getenv("MAIL_FROM_EMAIL", "info@app.commit.kz")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Yessenov Data Lab")

# --- Foundation contact (used in the fallback message) ---
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "info@yessenovfoundation.org")
CONTACT_PHONE = os.getenv("CONTACT_PHONE", "")

# --- Scraper ---
SITE_ROOT = os.getenv("SITE_ROOT", "https://yessenovfoundation.org")
SCRAPE_MAX_PAGES = _get_int("SCRAPE_MAX_PAGES", 300)
SCRAPE_DELAY_SECONDS = _get_float("SCRAPE_DELAY_SECONDS", 0.5)
