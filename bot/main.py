"""
Bot entry point.

Startup sequence:
  1. init_db() — idempotent schema creation/migration.
  2. rag_service.build_index() — embeds the dish CSV into rag_dishes on
     first run (no-ops on subsequent runs, see services/rag_service.py).
  3. Register handlers: onboarding conversation, logging conversations,
     profile/tools commands, report/analytics commands, and the catch-all
     chat MessageHandler (must be registered LAST so it doesn't swallow
     conversation-handler messages — group priority handles this, see
     below).
  4. Start an APScheduler background job that runs SemanticMemory.consolidate()
     for every user once a day. This is the piece v1 had no equivalent of
     at all: a standing process that turns accumulated daily logs into
     durable long-term memory, rather than memory only ever being "the last
     20 chat messages."

Run with: python -m bot.main
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, ContextTypes

import config
import database as db
from bot.handlers import chat, log_food, log_metrics, profile, report, start, tools
from services import rag_service
from services.memory_service import SemanticMemory

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def _run_nightly_consolidation(context: ContextTypes.DEFAULT_TYPE = None):
    """Runs SemanticMemory.consolidate() for every registered user.

    Scheduled once/day. Failures for one user (e.g. a transient LLM error)
    are logged and skipped rather than aborting the whole batch — one
    user's bad day shouldn't block everyone else's memory from updating.
    """
    conn = db.get_db_connection()
    try:
        user_ids = [row["user_id"] for row in conn.execute("SELECT user_id FROM users").fetchall()]
    finally:
        conn.close()

    semantic_memory = SemanticMemory()
    logger.info("Starting nightly memory consolidation for %d users", len(user_ids))
    for user_id in user_ids:
        try:
            result = semantic_memory.consolidate(user_id)
            logger.info("Consolidated memory for user %s: %s", user_id, result)
        except Exception:
            logger.exception("Memory consolidation failed for user %s", user_id)


def build_application() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured — set it in .env or secrets")

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Conversation handlers (onboarding, daily log, food log) get default
    # group (0) so they can intercept their own free-text steps.
    application.add_handler(start.build_conversation_handler())
    application.add_handler(log_metrics.build_conversation_handler())
    application.add_handler(log_food.build_conversation_handler())

    for handler in profile.build_handlers():
        application.add_handler(handler)
    for handler in report.build_handlers():
        application.add_handler(handler)
    for handler in tools.build_handlers():
        application.add_handler(handler)

    # Catch-all chat handler in a LOWER-priority group so it only fires
    # when no ConversationHandler above claimed the update.
    application.add_handler(chat.build_message_handler(), group=1)

    return application


def main():
    db.init_db()
    seeded = rag_service.build_index()
    if seeded:
        logger.info("Seeded rag_dishes with %d embedded dishes", seeded)

    application = build_application()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_run_nightly_consolidation, "cron", hour=2, minute=0)
    scheduler.start()
    logger.info("Nightly memory consolidation scheduled for 02:00")

    logger.info("Starting AarogyamAI bot...")
    application.run_polling()


if __name__ == "__main__":
    main()
