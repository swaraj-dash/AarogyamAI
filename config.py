"""
Centralized configuration for AarogyamAI v2.

Design decisions (kept from v1, still correct):
- BASE_DIR anchoring: every path resolves relative to this file's absolute
  location so the DB/uploads/reports never fragment when the app is launched
  from a different working directory (a real bug class in the v1 bot).
- get_secret() priority chain: os.environ -> st.secrets -> default. Lets the
  same codebase run locally (.env), on Streamlit Cloud (secrets.toml), and in
  a container (real env vars) without branching application code.
- Streamlit is imported lazily and defensively so the Telegram bot process
  never pays the streamlit import cost or risks an ImportError.

New in v2:
- EMBEDDING_MODEL / EMBEDDING_DIM: config for the real vector-embedding layer
  that replaces the v1 pandas string-equality "RAG".
- MEMORY_* settings: tunables for the tiered memory system (working window
  size, consolidation cadence, similarity threshold for de-duplicating
  semantic memories) instead of these being magic numbers buried in code.
- LLM_MODEL is a single source of truth so we no longer have gemini-1.0-pro,
  gemini-1.5-flash-latest and gemini-2.0-flash silently drifting across
  different Streamlit pages (a real inconsistency in v1).
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str, default=None):
    """Read a config value from env vars first, then Streamlit secrets."""
    val = os.getenv(key)
    if val is not None:
        return val
    if "streamlit" in sys.modules:
        try:
            import streamlit as st
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
    return default


def _get_bool(key: str, default: bool) -> str:
    val = get_secret(key)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Secrets / connectivity -------------------------------------------------
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")
DATABASE_PATH = get_secret("DATABASE_PATH", os.path.join(BASE_DIR, "aarogyam.db"))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "generated_reports")
RAG_DATA_CSV = os.path.join(BASE_DIR, "rag_data", "india_state_meal_nutrient_recs.csv")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# --- LLM configuration (single source of truth, no more per-page drift) ----
LLM_MODEL = get_secret("LLM_MODEL", "gemini-2.0-flash")
EMBEDDING_MODEL = get_secret("EMBEDDING_MODEL", "models/text-embedding-004")
EMBEDDING_DIM = int(get_secret("EMBEDDING_DIM", 768))

# Dev/offline mode: when no GOOGLE_API_KEY is present (e.g. running tests or
# a laptop demo without secrets configured), the app falls back to a
# deterministic local embedder and a stub LLM instead of hard-crashing.
# This is a portfolio-friendly property: `pytest` runs green with zero
# network access and zero API keys.
OFFLINE_MODE = _get_bool("AAROGYAM_OFFLINE_MODE", default=not bool(GOOGLE_API_KEY))

# --- Tiered memory system tunables ------------------------------------------
MEMORY_WORKING_WINDOW = int(get_secret("MEMORY_WORKING_WINDOW", 20))       # messages
MEMORY_SUMMARIZE_AFTER = int(get_secret("MEMORY_SUMMARIZE_AFTER", 12))     # roll into summary
MEMORY_CONSOLIDATION_LOOKBACK_DAYS = int(get_secret("MEMORY_CONSOLIDATION_LOOKBACK_DAYS", 14))
MEMORY_DEDUP_SIMILARITY_THRESHOLD = float(get_secret("MEMORY_DEDUP_SIMILARITY_THRESHOLD", 0.90))
MEMORY_RETRIEVAL_TOP_K = int(get_secret("MEMORY_RETRIEVAL_TOP_K", 5))

# --- RAG tunables -------------------------------------------------------
RAG_TOP_K = int(get_secret("RAG_TOP_K", 3))

# Startup warnings (kept from v1 — cheap and genuinely useful in a demo)
if not GOOGLE_API_KEY and not OFFLINE_MODE:
    print("WARNING: GOOGLE_API_KEY is not set. Gemini calls will fail.")
if not TELEGRAM_BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is not set. Telegram bot will not start.")
