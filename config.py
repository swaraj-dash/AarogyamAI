import os
import sys
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

def get_secret(key, default=None):
    """Gets a configuration secret from environment variables or Streamlit secrets."""
    val = os.getenv(key)
    if val is not None:
        return val
    # Fallback to Streamlit secrets if running inside Streamlit
    if 'streamlit' in sys.modules:
        try:
            import streamlit as st
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
    return default

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
default_db_path = os.path.join(BASE_DIR, "aarogyam.db")

TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")
DATABASE_PATH = get_secret("DATABASE_PATH", default_db_path)
TAVILY_API_KEY = get_secret("TAVILY_API_KEY")
DB_TYPE = get_secret("DB_TYPE", "sqlite")

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "generated_reports")

# Validate required tokens at start
if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY is not set. Gemini functions will fail.")

if not TELEGRAM_BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is not set. Telegram Bot will not start.")
