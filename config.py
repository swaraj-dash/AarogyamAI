import os
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DATABASE_PATH = os.getenv("DATABASE_PATH", "aarogyam.db")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# Validate required tokens at start
if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY is not set. Gemini functions will fail.")

if not TELEGRAM_BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is not set. Telegram Bot will not start.")
